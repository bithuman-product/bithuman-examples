// IOSEssence2 — an Essence 2 avatar on a real iPhone, rendered on the device.
//
// Engine:  essence-2, via the `Essence2Kit` product of the SwiftPM package
//          https://github.com/bithuman-product/homebrew-bithuman.git
// Inputs:  Sources/Model/agent.imx      the avatar, from the download door
//          Sources/Model/speech16k.wav  16 kHz mono 16-bit PCM speech
//          Sources/EngineResources      the engine's three runtime files (setup.sh)
// Output:  the avatar's own canvas at 25 fps, drawn in SwiftUI, with the voice.
//
// `Essence2Engine.frames(following: player)` hands out 25 frames a second: idle
// motion between replies, and a reply's frames as the player plays their audio,
// so the lips stay on the voice for the whole reply.
// See https://docs.bithuman.ai/examples/swift-ios-essence2

import SwiftUI
import AVFoundation
import Accelerate
import Essence2Kit

func log(_ line: String) { NSLog("[ios-essence2] %@", line) }

// MARK: - 1. Where the inputs live in the app bundle

enum Payload {
    static var root: URL? { Bundle.main.url(forResource: "Model", withExtension: nil) }
    static var imx: URL? { root?.appendingPathComponent("agent.imx") }
    static var speechWAV: URL? { root?.appendingPathComponent("speech16k.wav") }
    /// The runtime files, bundled by setup.sh; nil lets Essence2Kit fetch them once instead.
    static var resources: URL? {
        guard let r = Bundle.main.resourceURL,
              FileManager.default.fileExists(atPath: r.appendingPathComponent("w2v_ess_fp16_v1.onnx").path)
        else { return nil }
        return r
    }
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

// MARK: - 3. B, G, R bytes -> CGImage. Two vImage passes and no intermediate copy.

func makeCGImage(bgr: [UInt8], _ w: Int, _ h: Int) -> CGImage? {
    let n = w * h
    guard w > 0, h > 0, bgr.count >= n * 3, let out = malloc(n * 4) else { return nil }
    bgr.withUnsafeBufferPointer { sBuf in
        guard let s = sBuf.baseAddress else { return }
        var src = vImage_Buffer(data: UnsafeMutableRawPointer(mutating: s),
                                height: vImagePixelCount(h), width: vImagePixelCount(w),
                                rowBytes: w * 3)
        var dst = vImage_Buffer(data: out, height: vImagePixelCount(h),
                                width: vImagePixelCount(w), rowBytes: w * 4)
        // (B,G,R) -> (255,B,G,R), then permute to (R,G,B,255) for noneSkipLast.
        vImageConvert_RGB888toARGB8888(&src, nil, 255, &dst, false, vImage_Flags(kvImageNoFlags))
        var map: [UInt8] = [3, 2, 1, 0]
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

// MARK: - 4. The view we draw into
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

// MARK: - 5. The session: load, show, speak

@MainActor
final class AvatarSession: ObservableObject {
    @Published var status = "opening the avatar…"
    @Published var detail = ""
    @Published var ready = false
    @Published var busy = false
    @Published var hasFrame = false
    let sink = FrameSink()

    private var engine: Essence2Engine?
    private let audio = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private let format = AVAudioFormat(standardFormatWithSampleRate: 16_000, channels: 1)!
    private var reply: AVAudioPCMBuffer?          // the audio of the reply being shown
    private var loop: Task<Void, Never>?

    func boot() async {
        guard let imx = Payload.imx, FileManager.default.fileExists(atPath: imx.path) else {
            status = "No avatar in the bundle."
            detail = "Run ./setup.sh, then build again."
            return
        }
        // The key is read from the process environment. In Xcode:
        // Product -> Scheme -> Edit Scheme… -> Run -> Arguments ->
        // Environment Variables -> BITHUMAN_API_SECRET. In an app you ship, fetch it
        // from your backend and call Essence2Credential.set(_:).
        Essence2Credential.set(ProcessInfo.processInfo.environment["BITHUMAN_API_SECRET"])
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default)
            try AVAudioSession.sharedInstance().setActive(true)
            audio.attach(player)
            audio.connect(player, to: audio.mainMixerNode, format: format)
            try audio.start()

            let t0 = Date()
            let e = try await Essence2Engine.create(identity: imx, resourcesDirectory: Payload.resources)
            engine = e
            status = "Ready."
            detail = "\(e.width)x\(e.height)" + String(format: " · %.1f s to ready", Date().timeIntervalSince(t0))
            log("engine ready: \(detail)")
            ready = true
            startLoop(e)
            speak()                      // say the bundled line once on launch
        } catch {
            status = "The engine did not start."
            detail = "\(error)"
            log("FAILED: \(error)")
        }
    }

    /// 5a. The draw loop, for the life of the app. `frames(following:)` paces itself
    /// (25 per second): idle motion between replies, and a reply's frames as the player
    /// plays their audio. Start the reply's audio with its first speech frame.
    private func startLoop(_ e: Essence2Engine) {
        loop?.cancel()
        let frames = e.frames(following: player)
        loop = Task { [weak self] in
            for await f in frames {
                guard let self else { return }
                if f.audioTime == 0, let r = self.reply {
                    self.player.stop()
                    self.player.scheduleBuffer(r)
                    self.player.play()
                }
                if let cg = makeCGImage(bgr: f.bgr, f.width, f.height) {
                    self.sink.show(cg)
                    self.hasFrame = true
                }
                if f.endsReply {
                    self.busy = false
                    self.status = "Ready."
                }
                if let why = e.meteringRefusal ?? e.runtimeFailure {
                    self.status = "Stopped."
                    self.detail = why
                    log("STOPPED: \(why)")
                    return
                }
            }
        }
    }

    /// 5b. Speak the bundled line: feed the whole reply, say that is all of it, and let
    /// the draw loop start the audio with the reply's first speech frame.
    func speak() {
        guard ready, !busy, let e = engine, let wav = Payload.speechWAV else { return }
        let pcm: [Int16]
        do { pcm = try readPCM16MonoWAV(wav) } catch {
            status = "The WAV is not usable."; detail = error.localizedDescription; return
        }
        let samples = pcm.map { Float($0) / 32768 }
        guard let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(samples.count))
        else { return }
        buf.frameLength = buf.frameCapacity
        samples.withUnsafeBufferPointer { buf.floatChannelData![0].update(from: $0.baseAddress!, count: samples.count) }
        reply = buf
        busy = true
        status = "Speaking…"
        log(String(format: "audio: %d samples, %.2f s", pcm.count, Double(pcm.count) / 16_000))
        e.feed(samples)
        e.flushTail()
    }

    /// Not optional, and it must be SYNCHRONOUS. Exiting with a Metal completion
    /// handler still in flight crashes inside `__cxa_finalize`; `quiesceAll` stops
    /// every live engine and BLOCKS until their background GPU work has drained.
    func shutdown() {
        loop?.cancel()
        engine?.shutdown()
        Essence2Engine.quiesceAll(timeoutMs: 3000)
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
