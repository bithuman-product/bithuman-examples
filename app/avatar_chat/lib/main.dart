// avatar_chat — talk to a bitHuman avatar. macOS · iOS · Android, both engines.
//
// Everything that touches audio, frames or an engine lives in the public plugin;
// this file is the thin part a developer is expected to read and change:
//   - which agent to load        (AGENT_DIR)
//   - which engine                (the toggle below)
//   - the voice and the persona   (BithumanRealtimeSession args)
//
// Credentials: BITHUMAN_API_SECRET is read at build time from --dart-define and
// used for exactly one thing — minting a one-minute OpenAI Realtime client secret
// from api.bithuman.ai. No OpenAI key exists on the device. Sign-in replaces this
// in the next iteration; the dart-define stays as the headless/CI path.

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:bithuman/bithuman.dart';
import 'package:bithuman/ui_kit.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:bithuman/bithuman_realtime.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

/// Where the secret comes from, in order:
///   1. `--dart-define` — local development ONLY. A dart-define is compiled into the
///      binary and appears in the argv of every build step, so it is never a way to
///      ship a key.
///   2. the process environment — for a CI or measurement run, where the key never
///      enters the build.
///   3. the KEYCHAIN — what an installed app uses. Typed once by the person using it,
///      stored by the OS, never in the bundle, never in a plist, never in the build.
/// An installed app has no dart-define and no launch environment, so (3) is the only
/// one that exists for the person whose phone it is.
const _apiSecretDefine = String.fromEnvironment('BITHUMAN_API_SECRET');
const _keychain = FlutterSecureStorage(
  iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  mOptions: MacOsOptions(accessibility: KeychainAccessibility.first_unlock),
);
const _keychainKey = 'bithuman_api_secret';

/// A refusal, in the shape the estate's generated table uses: a CODE, the sentence
/// the user reads, and the remedy. Verbatim from models/_core/errors/codes.json so
/// this app does not become a second place these sentences are written.
class _Refusal {
  const _Refusal(this.code, this.message, this.fix);
  final String code, message, fix;
}

/// ★Each of these is a DIFFERENT condition with a different remedy, and the table's
/// own note on `metering_no_credential` forbids naming the other two there: "This
/// code is raised ONLY when no credential exists, and the sentence it replaced named
/// all three." One message for four causes is why the screen was confusing.
const _noCredential = _Refusal(
  'metering_no_credential',
  'no credential was supplied, so this render cannot be attributed to an account',
  'Enter your bitHuman API secret below. You can create one in a minute at bithuman.ai.');
const _credentialRejected = _Refusal(
  'metering_credential_rejected',
  'the credential was rejected — revoked, or from another environment',
  'Check the api-secret this app was given, or generate a new one in the bitHuman portal.');
const _outOfCredits = _Refusal(
  'metering_out_of_credits',
  'this account has no credits remaining',
  'Top up at https://bithuman.ai and the next beat will be accepted.');
const _unreachable = _Refusal(
  'metering_unreachable',
  'the metering service could not be reached, so this session was not registered',
  'Check this device\'s network. Nothing is wrong with your key — our service did not answer.');
const _agentDir = String.fromEnvironment('AGENT_DIR');
/// Android: the identity is fetched BY CODE through the metered door into the SDK's
/// own store, with this app's credential — there is no container to push. The same
/// dart-define names the identity on every platform once the Apple half fetches too.
const _agentCode = String.fromEnvironment('AGENT_CODE', defaultValue: 'A02HCY0444');
const _mintUrl = 'https://api.bithuman.ai/v1/realtime/ephemeral-token';

/// Text-only mode: `--dart-define=BH_MIC=false` opens a speaker-only session, so
/// the app never touches the microphone and the OS never asks for permission.
/// Typing still works — a typed turn is the same turn a spoken one is. Useful on
/// a shared or headless device, and for anyone who wants to try the avatar before
/// granting a mic.
const _useMic = bool.fromEnvironment('BH_MIC', defaultValue: true);
/// Headless measurement: `--dart-define=BH_SCRIPT=<prompt>|<prompt>|…` types each
/// prompt in turn, 25 s apart, once the session is open — a conversation with real
/// turn ends and no microphone, so a measurement run cannot hear the room.
const _script = String.fromEnvironment('BH_SCRIPT');

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // ★The avatar is the interface, so the window must be the whole screen. iOS
  // gives a Flutter app the full display for free; Android does NOT — the window
  // stops above the navigation bar (135 px of opaque 3-button bar on the Galaxy,
  // rows 2205-2340 of 2340) and below the status bar unless the app asks for
  // edge-to-edge. Without this call the chrome sat in a black band under the
  // avatar, which is what the owner saw. edgeToEdge draws the avatar under both
  // bars and leaves them on screen; SafeArea keeps the chrome clear of them.
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    systemNavigationBarColor: Colors.transparent,
    systemNavigationBarDividerColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarIconBrightness: Brightness.light,
    systemNavigationBarContrastEnforced: false,
  ));
  runApp(const MaterialApp(
    debugShowCheckedModeBanner: false,
    home: ChatPage(),
    themeMode: ThemeMode.dark,
  ));
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});
  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> with WidgetsBindingObserver {
  BithumanAvatar? _avatar;
  BithumanRealtimeSession? _session;
  String _secret = '';   // in memory for the lifetime of the screen; never written by this widget
  /// macOS: the window is the floating-circle companion (WindowChrome.enterBubble).
  bool _collapsed = false;
  final String _engine = const String.fromEnvironment('BH_ENGINE', defaultValue: 'expression2'); // or 'essence2'
  String _status = 'Loading the avatar…';
  String _caption = '';
  /// ★Never a raw exception. When boot cannot continue this holds the REFUSAL that
  /// explains which of the four conditions happened and what to do about it.
  _Refusal? _refusal;
  /// true while the user is being asked for a key (or re-asked after a rejection).
  bool _needsKey = false;
  String? _keyError;          // shape complaint on the entry field, not a refusal
  final _input = TextEditingController();
  final _keyInput = TextEditingController();
  final _chrome = GlobalKey<AutoHidingChromeState>();
  void _showChrome() => _chrome.currentState?.poke();

  /// Map the app's status text onto the kit's ONE definition of session states.
  SessionState get _state {
    final t = _status;
    if (t.startsWith('Listening')) return SessionState.listening;
    if (t.startsWith('Thinking')) return SessionState.thinking;
    if (t.startsWith('Connecting') || t.startsWith('Avatar ready')) return SessionState.connecting;
    if (t.startsWith('Could not') || t.startsWith('Connection') || t.startsWith('Disconnected')) return SessionState.error;
    return SessionState.ready;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _boot();
  }

  /// Breadcrumbs that land in the FILESYSTEM, not the console. A phone run that
  /// prints nothing is indistinguishable from one that never started; a file the app
  /// appends to at each stage makes silence localise instead of generalise.
  Future<void> _mark(String stage) async {
    try {
      final f = File('${(await getApplicationDocumentsDirectory()).path}/boot_status.txt');
      await f.writeAsString('${DateTime.now().toIso8601String()} $stage\n',
                            mode: FileMode.append, flush: true);
    } catch (_) {/* a breadcrumb must never be the thing that fails the boot */}
  }

  /// ONE-TIME PROVISIONING, for a handset the team controls. If a file named
  /// `.bootstrap_secret` has been placed in this app's Documents, its contents are
  /// moved into the Keychain and the FILE IS DELETED. The secret therefore never
  /// exists in the bundle, the build, a plist or anything committed — it arrives out
  /// of band on one device and ends up where the OS keeps secrets.
  /// This is provisioning, not a way to ship a key: a build a customer installs has
  /// no such file, and the app asks them for one.
  Future<void> _consumeBootstrapSecret() async {
    try {
      final f = File('${(await getApplicationDocumentsDirectory()).path}/.bootstrap_secret');
      if (!await f.exists()) return;
      final v = (await f.readAsString()).trim();
      if (v.isEmpty) { await f.delete(); await _mark('bootstrap:consumed keychain=fail=empty-file'); return; }
      // ★Record the WRITE RESULT before deleting the file. The file must go either way
      // (secret hygiene), but without this a failed Keychain write and a device that was
      // never provisioned look identical — and then the entry screen has two possible
      // causes and no way to tell them apart.
      String outcome;
      try {
        await _keychain.write(key: _keychainKey, value: v);
        final back = await _keychain.read(key: _keychainKey);
        outcome = (back == v) ? 'ok' : 'fail=readback-mismatch';
      } catch (e) {
        outcome = 'fail=$e';
      }
      await _mark('bootstrap:consumed keychain=$outcome');
      await f.delete();
    } catch (e) {
      await _mark('bootstrap:consumed keychain=fail=$e');
    }
  }

  /// dart-define → environment → Keychain. Returns '' when the person has not given
  /// one yet, which is a NORMAL state with a remedy, not an error.
  Future<String> _resolveSecret() async {
    await _consumeBootstrapSecret();
    if (_apiSecretDefine.isNotEmpty) return _apiSecretDefine;
    final env = Platform.environment['BITHUMAN_API_SECRET'] ?? '';
    if (env.isNotEmpty) return env;
    try {
      return (await _keychain.read(key: _keychainKey)) ?? '';
    } catch (_) {
      return '';   // a locked or unavailable Keychain reads as "no key yet"
    }
  }

  Future<void> _boot() async {
    await _mark('boot:start');
    try {
      final byCode = Platform.isAndroid;
      if (!byCode && _agentDir.isEmpty) throw StateError('AGENT_DIR is not set — see README.');
      // Absolute on the desktop; relative on a phone, where the agent is pushed
      // into this app's own container and resolved against its documents dir.
      final agentDir = byCode
          ? _agentCode
          : _agentDir.startsWith('/')
              ? _agentDir
              : '${(await getApplicationDocumentsDirectory()).path}/$_agentDir';
      final secret = await _resolveSecret();
      await _mark('boot:agentDir=$agentDir secret=${secret.isEmpty ? "absent" : "present"}');
      if (secret.isEmpty) {
        // NOT an exception. A missing credential is an expected condition with a
        // known remedy, so it renders as the refusal and an entry field.
        await _mark('boot:refuse=${_noCredential.code}');
        setState(() { _needsKey = true; _refusal = _noCredential; });
        return;
      }
      // The engine reads its members from this directory; the download door and
      // the store put them there. Both engines accept the same call.
      await BithumanAvatar.setExpression2AgentDir(agentDir);
      await _mark('boot:load:begin');
      final avatar = await BithumanAvatar.load(agentDir, engine: _engine,
          apiSecret: byCode ? secret : null);
      await _mark('boot:load:ok ${avatar.frameWidth}x${avatar.frameHeight}');
      setState(() { _avatar = avatar; _status = 'Avatar ready — connecting…'; });
      if (Platform.isMacOS) {
        // The window takes the canvas's shape at its native size (aspect locked) and
        // loses its border: full extent, never cropped, glass chrome over the picture.
        await avatar.fitWindowToCanvas();
        await WindowChrome.attach();
      }

      _secret = secret;   // memory only, for the session reopened after a background stint
      await _openSession(avatar, secret);
      if (_script.isNotEmpty) {
        _recordFrameTimings();
        final prompts = _script.split('|').where((p) => p.trim().isNotEmpty).toList();
        var i = 0;
        Timer.periodic(const Duration(seconds: 25), (t) {
          if (i >= prompts.length || _session == null) { t.cancel(); return; }
          final p = prompts[i++].trim();
          // '@collapse' / '@restore' drive the macOS companion from a script.
          if (p == '@collapse') { _collapse(); _mark('script:collapse'); return; }
          if (p == '@restore') { _restore(); _mark('script:restore'); return; }
          setState(() => _caption = 'you: $p');
          _session!.sendText(p);
          _mark('script:sent:$i');
        });
      }
    } on _Refusal catch (r) {
      await _mark('boot:refuse=${r.code}');
      setState(() {
        _refusal = r;
        // A rejected or unfunded key is still a key problem: offer the field again.
        _needsKey = r.code == _credentialRejected.code;
      });
    } catch (e) {
      await _mark('boot:error=$e');
      setState(() {
        _refusal = _Refusal('startup_failed', 'the app could not start', '$e');
      });
    }
  }

  /// Store a key the person typed and boot again. Shape is checked here only to catch
  /// an obvious paste error; whether a key is VALID is the service's answer, not ours.
  Future<void> _submitKey() async {
    final k = _keyInput.text.trim();
    if (k.length < 8 || k.contains(' ')) {
      setState(() => _keyError = 'That does not look like an API secret — no spaces, and longer than this.');
      return;
    }
    setState(() { _keyError = null; _needsKey = false; _refusal = null; });
    try { await _keychain.write(key: _keychainKey, value: k); } catch (_) {}
    await _mark('key:stored');
    await _boot();
  }

  Future<String> _mint(String secret) async {
    HttpClientResponse res;
    String body;
    try {
      final c = HttpClient()..connectionTimeout = const Duration(seconds: 15);
      final req = await c.postUrl(Uri.parse(_mintUrl));
      req.headers.set('api-secret', secret);
      req.headers.contentType = ContentType.json;
      req.write('{}');
      res = await req.close();
      body = await res.transform(utf8.decoder).join();
    } on SocketException {
      // ★The service did not answer. This must NEVER read as a rejected key: the
      // table's note is explicit that our outage must not read as the customer's
      // revocation, and a published wheel shipped exactly that confusion.
      throw _unreachable;
    } on HttpException {
      throw _unreachable;
    }
    if (res.statusCode == 200) {
      return (jsonDecode(body)['data'] as Map)['value'] as String;
    }
    if (res.statusCode == 401 || res.statusCode == 403) throw _credentialRejected;
    if (res.statusCode == 402) throw _outOfCredits;
    if (res.statusCode == 429) {
      throw const _Refusal('token_request_failed', 'a token could not be requested',
          'Too many sessions were started in the last minute. Wait a moment and try again.');
    }
    throw _Refusal('token_request_failed', 'a token could not be requested',
        'The service answered HTTP ${res.statusCode}.');
  }

  String _describe(RealtimeStatus s) => switch (s) {
        RealtimeStatus.connecting => 'Connecting…',
        RealtimeStatus.open => 'Connected — say something, or type.',
        RealtimeStatus.userSpeaking => 'Listening…',
        RealtimeStatus.userStopped => 'Thinking…',
        RealtimeStatus.responseDone => 'Connected — say something, or type.',
        RealtimeStatus.closed => 'Disconnected.',
        RealtimeStatus.error => 'Connection error.',
      };

  /// One HTTP call with your bitHuman secret; the device only ever holds the one-minute
  /// "ek_…" that comes back. Called at boot and again after a background stint.
  Future<void> _openSession(BithumanAvatar avatar, String secret) async {
    final ek = await _mint(secret);
    final session = BithumanRealtimeSession(
      apiKey: ek,
      model: 'gpt-realtime-mini',
      avatar: avatar,
      systemPrompt: 'You are a friendly bitHuman avatar. Keep every reply to one or two short sentences.',
      voice: 'alloy',
      vadThreshold: 1500,
    );
    session.statusStream.listen((s) { if (mounted) setState(() => _status = _describe(s)); });
    session.botTranscriptStream.listen((d) { if (mounted) setState(() => _caption = 'agent: $d'); });
    session.userTranscriptStream.listen((t) { if (mounted) setState(() => _caption = 'you: $t'); });
    await session.start(enableMic: _useMic);
    if (mounted) setState(() => _session = session);
    await _mark('boot:session:open');
  }

  /// ★OFF SCREEN MEANS OFF. Measured on a shared Galaxy (2026-09-15): the player rendered
  /// idle frames for 74 minutes in the background. When the app leaves the screen the
  /// session is closed and the native presenter is held (no picture, no sound, no CPU);
  /// when it returns, the presenter is released and a fresh session is minted. The engine
  /// stays warm, so the return is seconds, not the first-run load.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final a = _avatar;
    if (a == null) return;
    if (state == AppLifecycleState.paused || state == AppLifecycleState.hidden) {
      if (_session != null) {
        _session?.stop(); _session = null;
        a.setIdleHold(true);
        _mark('lifecycle:off-screen session closed, presenter held');
      }
    } else if (state == AppLifecycleState.resumed) {
      if (_session == null && _secret.isNotEmpty) {
        a.setIdleHold(false);
        _mark('lifecycle:on-screen presenter released, reopening the session');
        _openSession(a, _secret).catchError((e) => _mark('lifecycle:reopen failed $e'));
      }
    }
  }

  /// Measurement runs only: Flutter's own frame clock (build + raster per frame), the
  /// instrument that can see what the glass chrome costs. Every 10 s one line goes to
  /// the breadcrumb file: frames, fps, and raster/build percentiles in ms.
  void _recordFrameTimings() {
    final raster = <double>[], build = <double>[];
    var t0 = DateTime.now();
    SchedulerBinding.instance.addTimingsCallback((timings) {
      for (final t in timings) {
        raster.add(t.rasterDuration.inMicroseconds / 1000.0);
        build.add(t.buildDuration.inMicroseconds / 1000.0);
      }
      final dt = DateTime.now().difference(t0).inMilliseconds;
      if (dt < 10000) return;
      double pct(List<double> v, double q) { final c = [...v]..sort(); return c[(c.length - 1) * q ~/ 1]; }
      final n = raster.length;
      _mark('frames: n=$n fps=${(n * 1000 / dt).toStringAsFixed(1)} chrome=${_chrome.currentState?.visible == true ? "visible" : "hidden"} '
            'raster p50/p90/p99=${pct(raster, .5).toStringAsFixed(1)}/${pct(raster, .9).toStringAsFixed(1)}/${pct(raster, .99).toStringAsFixed(1)} '
            'build p50/p90/p99=${pct(build, .5).toStringAsFixed(1)}/${pct(build, .9).toStringAsFixed(1)}/${pct(build, .99).toStringAsFixed(1)}');
      raster.clear(); build.clear(); t0 = DateTime.now();
    });
  }

  /// macOS companion: the window becomes the floating circle; the session runs on.
  Future<void> _collapse() async {
    setState(() => _collapsed = true);       // circular UI first, so the shrink never shows the square layout
    await WindowChrome.enterBubble();
  }

  Future<void> _restore() async {
    setState(() => _collapsed = false);
    await WindowChrome.exitBubble();
  }

  /// A typed turn is the same turn a spoken one is: same units back, same barge-in.
  void _send() {
    final t = _input.text.trim();
    if (t.isEmpty || _session == null) return;
    _input.clear();
    setState(() => _caption = 'you: $t');
    _session!.sendText(t);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _session?.stop();
    _avatar?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final a = _avatar;
    final phone = Platform.isIOS || Platform.isAndroid;
    return Scaffold(
      backgroundColor: Colors.black,
      // ★The avatar is the interface: it runs edge to edge under the Dynamic Island
      // and the home indicator. Only the CHROME respects the safe areas.
      body: a == null
          ? SafeArea(
              child: Center(
                child: _refusal != null
                    ? _RefusalView(refusal: _refusal!, needsKey: _needsKey, controller: _keyInput,
                                   fieldError: _keyError, onSubmit: _submitKey)
                    : LoadingState(stage: _status),
              ),
            )
          : _collapsed
          ? BubbleView(
              state: _state,
              onRestore: _restore,
              canvasWidth: a.frameWidth > 0 ? a.frameWidth.toDouble() : 416,
              canvasHeight: a.frameHeight > 0 ? a.frameHeight.toDouble() : 720,
              child: Texture(textureId: a.textureId),
            )
          : AutoHidingChrome(
              key: _chrome,
              body: Stack(fit: StackFit.expand, children: [
                // HEROSHOT: the ruled fit policy — phones portrait-only, a landscape
                // model crops its sides, a portrait model shows its full extent.
                AvatarCanvasFit(
                  canvasWidth: a.frameWidth > 0 ? a.frameWidth.toDouble() : 416,
                  canvasHeight: a.frameHeight > 0 ? a.frameHeight.toDouble() : 720,
                  surface: phone ? AvatarSurface.phone : AvatarSurface.desktop,
                  child: Texture(textureId: a.textureId),
                ),
                // A soft scrim so light chrome never sits on a light chin.
                const IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.center, end: Alignment.bottomCenter,
                        colors: [Color(0x00000000), Color(0x73000000)],
                      ),
                    ),
                  ),
                ),
              ]),
              child: SafeArea(
                minimum: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                child: Column(children: [
                  Row(children: [
                    StatusPill(state: _state, label: _status),
                    const Spacer(),
                    if (Platform.isMacOS)
                      GlassIconButton(icon: Icons.close_fullscreen_rounded, tooltip: 'Collapse to the corner', onTap: _collapse),
                  ]),
                  const Spacer(),
                  if (_caption.isNotEmpty)
                    Frosted(
                      borderRadius: BorderRadius.circular(Glass.rCaption),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      child: Text(_caption, textAlign: TextAlign.center,
                          style: const TextStyle(color: Colors.white, fontSize: 14)),
                    ),
                  const SizedBox(height: 10),
                  PromptCapsule(
                    controller: _input,
                    onTap: _showChrome,
                    onSend: () { _send(); _showChrome(); },
                  ),
                ]),
              ),
            ),
    );
  }
}

/// What a person sees when the app cannot start. Three things, always: WHAT happened
/// in the estate's own words, the CODE so a support conversation names one thing, and
/// the REMEDY. Plus the entry field when the remedy is "give me a key".
class _RefusalView extends StatelessWidget {
  const _RefusalView({
    required this.refusal,
    required this.needsKey,
    required this.controller,
    required this.fieldError,
    required this.onSubmit,
  });
  final _Refusal refusal;
  final bool needsKey;
  final TextEditingController controller;
  final String? fieldError;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 28),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.key_off_outlined, color: Colors.orangeAccent, size: 40),
          const SizedBox(height: 14),
          Text(refusal.message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white, fontSize: 16)),
          const SizedBox(height: 10),
          Text(refusal.fix,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 13)),
          const SizedBox(height: 6),
          Text(refusal.code,
              style: const TextStyle(color: Colors.white38, fontSize: 11, fontFamily: 'Menlo')),
          if (needsKey) ...[
            const SizedBox(height: 20),
            TextField(
              controller: controller,
              obscureText: true,
              autocorrect: false,
              enableSuggestions: false,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'bitHuman API secret',
                errorText: fieldError,
                border: const OutlineInputBorder(),
              ),
              onSubmitted: (_) => onSubmit(),
            ),
            const SizedBox(height: 10),
            FilledButton(onPressed: onSubmit, child: const Text('Save and start')),
            const SizedBox(height: 8),
            const Text('Stored in this device\'s Keychain — never in the app bundle.',
                style: TextStyle(color: Colors.white38, fontSize: 11)),
          ],
        ]),
      );
}
