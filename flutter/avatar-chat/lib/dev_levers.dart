import 'package:flutter/foundation.dart' show kReleaseMode;

/// DEV LEVERS of this app — every `--dart-define` that drives the app by itself,
/// declared in ONE place, and a RELEASE build reads none of them.
///
/// Each lever is `enabled && …` / `enabled ? … : …` with `enabled = !kReleaseMode`, a
/// compile-time constant: in `flutter build … --release` the expression folds to its
/// unset value and the define's VALUE never enters the AOT snapshot. CI builds a
/// release APK with every lever set to a sentinel and asserts the sentinel is absent
/// from `libapp.so` (and present in a debug build — the control).
///
/// Why (2026-09-16): a proof build that types scripted prompts on a timer (`BH_SCRIPT`)
/// with the plugin's stress driver and injected mic phrase sat on the owner's phone
/// as a release APK — "the agent starts self talking non-stop". The plugin's own levers
/// live in its `lib/src/dev_levers.dart`; Android sysprops behind `FLAG_DEBUGGABLE`.
///
/// NOT levers (configuration a release build legitimately carries): `BITHUMAN_API_SECRET`
/// (a credential path this file's header documents), `AGENT_DIR` / `AGENT_CODE`
/// (which identity), `BH_ENGINE` (which model), `BH_MIC` (a speaker-only session is a
/// product mode — typing is a turn).
class DevLevers {
  DevLevers._();

  /// True in debug and profile builds; false in every release build.
  static const bool enabled = !kReleaseMode;

  /// Headless measurement: `<prompt>|<prompt>|…` typed in turn once the session is
  /// open — a conversation with real turn ends and no microphone.
  static const String script = enabled ? String.fromEnvironment('BH_SCRIPT') : '';

  /// Seconds between scripted prompts (shorter than a reply = a barge-in arm).
  static const int scriptGapS =
      enabled ? int.fromEnvironment('BH_SCRIPT_GAP_S', defaultValue: 25) : 25;
}
