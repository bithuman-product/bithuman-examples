// IOSEssence2 — an Essence 2 avatar on a real iPhone, rendered on the device.
//
// Engine:  essence-2, via the `Essence2` product of the SwiftPM package
//          https://github.com/bithuman-product/homebrew-bithuman.git
// Inputs:  Sources/Model/agent.imx      the identity, from the download door
//          Sources/Model/speech16k.wav  16 kHz mono 16-bit PCM speech
//          the engine resources, at the app bundle's resource root
// Output:  the identity's own canvas at 25 fps, drawn in SwiftUI, beside the audio.
//
// `import Essence2` gives you the engine's C interface and nothing else: there
// is no Swift engine type on this rail, so `Renderer` below IS the wrapper.
// Every call here is public API of the shipped binary.
// See https://docs.bithuman.ai/examples/swift-ios-essence2

import SwiftUI
import AVFoundation
import Accelerate
import Essence2

let FPS = 25.0
let TICK = 1.0 / FPS          // 0.04 s — Essence 2's own rate

func log(_ line: String) { NSLog("[ios-essence2] %@", line) }

// MARK: - 1. Where the two inputs live in the app bundle

enum Payload {
    static var root: URL? { Bundle.main.url(forResource: "Model", withExtension: nil) }
    static var imx: URL? { root?.appendingPathComponent("agent.imx") }
    static var speechWAV: URL? { root?.appendingPathComponent("speech16k.wav") }
}

// MARK: - 2. A 16-bit PCM WAV reader that walks the RIFF chunks
//
// Do NOT assume the samples start at byte 44. macOS `afconvert` writes an FLLR
// padding chunk between the header and the data, so the classic shortcut reads
// padding as audio and the avatar mouths noise.

struct WAVError: LocalizedError {
    let what: String
    var errorDescription: String? { what }
}

func readPCM16MonoWAV(_ url: URL) throws -> [Int16] {
    let d = try Data(contentsOf: url)
    guard d.count > 12, d[0..<4].elementsEqual("RIFF".utf8), d[8..<12].elementsEqual("WAVE".utf8)
    else { throw WAVError(what: "\(url.lastPathComponent) is not a RIFF/WAVE file") }

    func u16(_ i: Int) -> Int { Int(d[i]) | Int(d[i + 1]) << 8 }
    func u32(_ i: Int) -> Int { u16(i) | u16(i + 2) << 16 }

    var i = 12, channels = 0, rate = 0, bits = 0, off = -1, len = 0
    while i + 8 <= d.count {
        let id = String(bytes: d[i..<i + 4], encoding: .ascii) ?? ""
        var sz = u32(i + 4)
        if sz < 0 || i + 8 + sz > d.count { sz = d.count - (i + 8) }
        if id == "fmt " { channels = u16(i + 10); rate = u32(i + 12); bits = u16(i + 22) }
        if id == "data" { off = i + 8; len = sz }
        i += 8 + sz + (sz & 1)
    }
    guard off > 0, len > 1 else { throw WAVError(what: "\(url.lastPathComponent) has no data chunk") }
    guard channels == 1, rate == 16_000, bits == 16 else {
        throw WAVError(what: "need 16 kHz mono 16-bit PCM; \(url.lastPathComponent) is "
                             + "\(rate) Hz, \(channels) ch, \(bits)-bit")
    }
    var out = [Int16](repeating: 0, count: len / 2)
    out.withUnsafeMutableBytes { dst in d.copyBytes(to: dst, from: off..<(off + (len / 2) * 2)) }
    return out
}

// MARK: - 3. The engine lives inside an actor
//
// The handle is a raw pointer and is not Sendable. Keeping it inside an actor is
// what lets this compile under Swift 6 strict concurrency AND keeps the first
// load off the main thread.

enum EngineError: LocalizedError {
    case create(Int32), notReady, noGeometry, refused(String)
    var errorDescription: String? {
        switch self {
        case .create(let rc):
            // The three the header documents. -3 is the metering refusal:
            // no API secret, or one the service rejected (stderr says which).
            let why: String
            switch rc {
            case -1: why = " — bad argument"
            case -2: why = " — the bundle could not be opened"
            case -3: why = " — no API secret, or the service rejected it."
                         + " Set BITHUMAN_API_SECRET in the Run scheme, or pass a key"
                         + " to be_essence2_set_api_secret"
            default: why = ""
            }
            return "be_essence2_create returned \(rc)" + why
        case .notReady: return "the engine never became ready"
        case .noGeometry:
            // Without this the app hangs POLITELY: a zero-byte pull buffer makes
            // be_essence2_pull_frame return 0 ("out too small") for ever, which
            // the draw loop reads as "nothing this tick" and holds a frame that
            // never arrives. A named throw beats a frozen face.
            return "be_essence2_get_info reported a 0-pixel canvas"
        case .refused(let why): return why
        }
    }
}

actor Renderer {
    private var handle: be_essence2_handle?
    private(set) var width = 0
    private(set) var height = 0
    private var buf = [UInt8]()

    /// Open the identity and wait for the engine to warm up.
    ///
    /// `apiSecret` is handed to the meter BEFORE the session exists, because the
    /// secret this process's later sessions are billed to is process state, not
    /// a per-session argument.
    func load(imx: URL, apiSecret: String?) async throws -> String {
        if let s = apiSecret, !s.isEmpty { _ = be_essence2_set_api_secret(s) }

        var h: be_essence2_handle?
        // `motion_dir` NULL and `chunk` 0: the engine owns both. Passing the
        // .imx path straight out of the read-only app bundle is correct: the
        // engine sniffs the container and unpacks it itself, under
        // NSTemporaryDirectory()/essence2-unpacked. Nothing is written beside
        // the .imx, so the bundle being read-only is not a problem — but the
        // unpacked copy does cost about as much disk again. See the note below
        // the code.
        let rc = imx.path.withCString { be_essence2_create($0, nil, 0, &h) }
        guard rc == 0, let h else { throw EngineError.create(rc) }
        handle = h

        // create() returns as soon as the bundle is open; the model compile runs
        // on a background thread and audio pushed before it finishes is dropped.
        var waited = 0.0
        while be_essence2_is_ready(h) == 0 {
            if waited > 120 { throw EngineError.notReady }
            try await Task.sleep(nanoseconds: 100_000_000); waited += 0.1
        }

        var w: Int32 = 0, hgt: Int32 = 0
        be_essence2_get_info(h, &w, &hgt)
        width = Int(w); height = Int(hgt)
        // get_info reports the dims of the most recently produced frame, so it
        // is the one call here that can legitimately answer 0. Refuse loudly:
        // a 0-byte buffer turns every later pull into a silent "out too small".
        guard width > 0, height > 0 else { throw EngineError.noGeometry }
        buf = [UInt8](repeating: 0, count: width * height * 3)   // tightly packed RGB
        return String(format: "%dx%d, ready in %.1f s", width, height, waited)
    }

    /// Push 16 kHz mono int16 audio, retrying while the engine's ring is full.
    /// Returns false only if it stayed full for a second, which means the draw
    /// loop has stopped pulling.
    func push(_ samples: ArraySlice<Int16>) async -> Bool {
        guard let h = handle else { return false }
        let n = Int32(samples.count)
        for _ in 0..<100 {
            let rc = samples.withUnsafeBufferPointer { be_essence2_push_audio(h, $0.baseAddress, n) }
            if rc == 0 { return true }
            if rc != -2 { return false }          // -2 is "ring full, try again"
            try? await Task.sleep(nanoseconds: 10_000_000)
        }
        return false
    }

    /// The next frame, or nil when the engine has nothing this tick.
    ///
    /// Once it is ready this is a CONTINUOUS stream — generated frames at their
    /// scheduled slots, the identity's own motion in between — so a draw loop
    /// needs nothing else. A nil means hold the frame you already have.
    /// Throws once metering has refused the session, which is the `-3` the C
    /// header documents: no frame will follow it.
    func pull() throws -> [UInt8]? {
        guard let h = handle else { return nil }
        let n = buf.withUnsafeMutableBufferPointer {
            be_essence2_pull_frame(h, $0.baseAddress, Int32($0.count))
        }
        if n == -3 { throw EngineError.refused(renderReason(h)) }
        return n > 0 ? buf : nil
    }

    func framesReady() -> Int { handle.map { Int(be_essence2_frames_available($0)) } ?? 0 }

    /// Ask the engine whether its own runtime failed. A dead runtime otherwise
    /// reaches you as an absence: idle frames forever, and a face that will
    /// never speak.
    func renderStatus() -> String? {
        guard let h = handle else { return nil }
        var failures: Int64 = 0
        var reason = [CChar](repeating: 0, count: 512)
        let rc = be_essence2_render_status(h, &reason, Int32(reason.count), &failures)
        return rc == 0 ? nil : reason.withUnsafeBufferPointer { String(cString: $0.baseAddress!) }
    }

    private func renderReason(_ h: be_essence2_handle) -> String {
        var failures: Int64 = 0
        var reason = [CChar](repeating: 0, count: 512)
        _ = be_essence2_render_status(h, &reason, Int32(reason.count), &failures)
        let detail = reason.withUnsafeBufferPointer { String(cString: $0.baseAddress!) }
        return "the engine stopped: metering refused this session"
             + (detail.isEmpty ? "" : " — \(detail)")
    }

    func close() {
        if let h = handle { be_essence2_destroy(h) }
        handle = nil
    }
}

// MARK: - 4. RGB888 -> CGImage. Two vImage passes and no intermediate copy.

func makeCGImage(_ rgb: [UInt8], _ w: Int, _ h: Int) -> CGImage? {
    let n = w * h
    guard w > 0, h > 0, rgb.count >= n * 3, let out = malloc(n * 4) else { return nil }
    rgb.withUnsafeBufferPointer { sBuf in
        guard let s = sBuf.baseAddress else { return }
        var src = vImage_Buffer(data: UnsafeMutableRawPointer(mutating: s),
                                height: vImagePixelCount(h), width: vImagePixelCount(w),
                                rowBytes: w * 3)
        var dst = vImage_Buffer(data: out, height: vImagePixelCount(h),
                                width: vImagePixelCount(w), rowBytes: w * 4)
        // RGB888 -> (255,R,G,B), then permute to (R,G,B,255) for noneSkipLast.
        vImageConvert_RGB888toARGB8888(&src, nil, 255, &dst, false, vImage_Flags(kvImageNoFlags))
        var map: [UInt8] = [1, 2, 3, 0]
        vImagePermuteChannels_ARGB8888(&dst, &dst, &map, vImage_Flags(kvImageNoFlags))
    }
    guard let provider = CGDataProvider(dataInfo: out, data: out, size: n * 4,
                                        releaseData: { info, _, _ in free(info) })
    else { free(out); return nil }
    return CGImage(width: w, height: h, bitsPerComponent: 8, bitsPerPixel: 32,
                   bytesPerRow: w * 4, space: CGColorSpaceCreateDeviceRGB(),
                   bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipLast.rawValue),
                   provider: provider, decode: nil, shouldInterpolate: false,
                   intent: .defaultIntent)
}

// MARK: - 4b. The view we draw into
//
// Do NOT push 25 fps through an `@Published` property. Every assignment
// re-evaluates the SwiftUI body around it. Hand the frame to a CALayer instead;
// SwiftUI never sees it change.

@MainActor
final class FrameSink {
    fileprivate weak var layer: CALayer?
    func show(_ cg: CGImage) { layer?.contents = cg }
}

struct FrameView: UIViewRepresentable {
    let sink: FrameSink
    func makeUIView(context: Context) -> UIView {
        let v = UIView()
        v.backgroundColor = UIColor(white: 0.12, alpha: 1)
        v.layer.contentsGravity = .resizeAspect
        v.layer.masksToBounds = true
        v.layer.cornerRadius = 16
        sink.layer = v.layer
        return v
    }
    func updateUIView(_ v: UIView, context: Context) { sink.layer = v.layer }
}

// MARK: - 5. The session: load, idle, speak

@MainActor
final class AvatarSession: ObservableObject {
    @Published var status = "opening the identity…"
    @Published var detail = ""
    @Published var ready = false
    @Published var busy = false
    @Published var hasFrame = false
    let sink = FrameSink()

    private let renderer = Renderer()
    private var player: AVAudioPlayer?
    private var w = 0, h = 0
    private var loop: Task<Void, Never>?

    func boot() async {
        guard let imx = Payload.imx,
              FileManager.default.fileExists(atPath: imx.path) else {
            status = "No identity in the bundle."
            detail = "Run ./setup.sh, then build again."
            return
        }
        // The key is read from the process environment. In Xcode:
        // Product -> Scheme -> Edit Scheme… -> Run -> Arguments ->
        // Environment Variables -> BITHUMAN_API_SECRET.
        let secret = ProcessInfo.processInfo.environment["BITHUMAN_API_SECRET"]
        if secret?.isEmpty ?? true {
            log("no BITHUMAN_API_SECRET in the environment — this session cannot be "
                + "attributed to an account. See docs.bithuman.ai/guides/pricing")
        }
        do {
            let t0 = Date()
            let line = try await renderer.load(imx: imx, apiSecret: secret)
            w = await renderer.width
            h = await renderer.height
            status = "Ready."
            detail = line + String(format: " · %.1f s to first ready", Date().timeIntervalSince(t0))
            log("engine ready: \(line)")
            ready = true
            startLoop()
            speak()                      // say the bundled line once on launch
        } catch {
            status = "The engine did not start."
            detail = "\(error.localizedDescription)"
            log("FAILED: \(error)")
        }
    }

    /// 5a. The draw loop. One frame per 40 ms tick, on an ABSOLUTE grid, for the
    /// life of the app: generated frames while there is speech, the identity's
    /// own motion between utterances, and the frame already on screen when the
    /// engine has nothing this tick.
    private func startLoop() {
        loop?.cancel()
        loop = Task { [weak self] in
            let start = Date()
            var n = 0
            while !Task.isCancelled {
                guard let self else { return }
                do {
                    // ONE call. Once the engine is ready it emits a continuous
                    // stream through pull(): generated frames while there is
                    // speech, the identity's own motion between utterances. A
                    // nil means HOLD THE FRAME ALREADY ON SCREEN — never
                    // substitute one, and do not reach for be_essence2_idle_frame
                    // here: that call advances the same shared offset and would
                    // step the motion twice.
                    if let f = try await self.renderer.pull(),
                       let cg = makeCGImage(f, self.w, self.h) {
                        self.sink.show(cg)
                        self.hasFrame = true
                    }
                } catch {
                    self.status = "Stopped."
                    self.detail = error.localizedDescription
                    log("STOPPED: \(error)")
                    return
                }
                n += 1
                let wait = start.addingTimeInterval(Double(n) * TICK).timeIntervalSinceNow
                if wait > 0 { try? await Task.sleep(nanoseconds: UInt64(wait * 1e9)) }
            }
        }
    }

    /// 5b. Speak the bundled line. Feed, pre-roll, then start the speaker.
    func speak() {
        guard ready, !busy, let wav = Payload.speechWAV else { return }
        busy = true
        status = "Speaking…"
        Task {
            defer { busy = false }
            let pcm: [Int16]
            do { pcm = try readPCM16MonoWAV(wav) } catch {
                status = "The WAV is not usable."; detail = error.localizedDescription; return
            }
            let seconds = Double(pcm.count) / 16_000.0
            log(String(format: "audio: %d samples, %.2f s", pcm.count, seconds))

            try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .default)
            try? AVAudioSession.sharedInstance().setActive(true)
            player = try? AVAudioPlayer(contentsOf: wav)

            // Feed in 100 ms chunks. push() retries on the engine's "ring full".
            //
            // PRE-ROLL. The engine schedules generated frames a little ahead
            // of the audio, so starting the speaker on the first chunk leaves
            // the mouth behind for the whole utterance. Feed 1.6 s first.
            let preroll = 16 * 1600                  // 1.6 s of 16 kHz mono
            var started = false
            var i = 0
            while i < pcm.count {
                let j = min(i + 1600, pcm.count)
                guard await renderer.push(pcm[i..<j]) else {
                    status = "The engine stopped accepting audio."; return
                }
                i = j
                if !started, i >= preroll {
                    started = true
                    log("pre-roll fed; \(await renderer.framesReady()) frames queued")
                    player?.play()
                }
            }
            if !started { player?.play() }
            try? await Task.sleep(nanoseconds: UInt64(seconds * 1e9))
            if let why = await renderer.renderStatus() { log("render status: \(why)") }
            status = "Ready."
        }
    }

    /// Not optional, and it must be SYNCHRONOUS. Exiting with a Metal
    /// completion handler still in flight crashes inside `__cxa_finalize`.
    /// `be_essence2_quiesce_all` stops every live engine and BLOCKS until their
    /// background GPU work has drained, which is exactly what is needed here —
    /// a `Task` queued at terminate time may never run.
    func shutdown() {
        loop?.cancel()
        _ = be_essence2_quiesce_all(3000)
    }
}

// MARK: - 6. UI

@MainActor
final class AppDelegate: NSObject, UIApplicationDelegate {
    // @MainActor on the class is what makes this mutable static concurrency-safe
    // under Swift 6.
    static weak var session: AvatarSession?
    func applicationWillTerminate(_ application: UIApplication) {
        AppDelegate.session?.shutdown()
    }
}

@main
struct IOSEssence2App: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate
    var body: some Scene { WindowGroup { ContentView() } }
}

struct ContentView: View {
    @StateObject private var session = AvatarSession()

    var body: some View {
        VStack(spacing: 14) {
            Text("bitHuman · Essence 2 on device").font(.headline)
            ZStack {
                FrameView(sink: session.sink)
                if !session.hasFrame { ProgressView().tint(.white) }
            }
            .frame(maxHeight: 560)
            Button(session.busy ? "Speaking…" : "Speak") { session.speak() }
                .buttonStyle(.borderedProminent)
                .disabled(!session.ready || session.busy)
            Text(session.status).font(.subheadline)
            Text(session.detail).font(.caption2).foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .task {
            AppDelegate.session = session
            await session.boot()
        }
    }
}
