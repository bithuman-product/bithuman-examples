// Expression 2 on a Mac: a 16 kHz WAV in, lip-synced frames out, rendered on
// this machine. Needs BITHUMAN_API_SECRET; the session is billed to it.
//
//   ./setup.sh && swift run -c release MacOSExpression2

import AVFoundation
import CoreGraphics
import Expression2
import Foundation
import ImageIO
import UniformTypeIdentifiers

/// A frame is BGR888 — `width * height * 3` bytes, blue first.
func writePNG(_ bgr: [UInt8], width: Int, height: Int, to url: URL) {
    var rgba = [UInt8](repeating: 255, count: width * height * 4)
    for i in 0 ..< width * height {
        rgba[i * 4 + 0] = bgr[i * 3 + 2]
        rgba[i * 4 + 1] = bgr[i * 3 + 1]
        rgba[i * 4 + 2] = bgr[i * 3 + 0]
    }
    guard let ctx = CGContext(data: &rgba, width: width, height: height,
                              bitsPerComponent: 8, bytesPerRow: width * 4,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue),
          let image = ctx.makeImage(),
          let dest = CGImageDestinationCreateWithURL(
              url as CFURL, UTType.png.identifier as CFString, 1, nil)
    else { return }
    CGImageDestinationAddImage(dest, image, nil)
    CGImageDestinationFinalize(dest)
}

/// Read a 16 kHz mono WAV into the `[Float]` the engine feeds on.
func readPCM(_ url: URL) throws -> [Float] {
    let file = try AVAudioFile(forReading: url)
    guard let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat,
                                        frameCapacity: AVAudioFrameCount(file.length)),
          file.processingFormat.channelCount == 1
    else { fatalError("expected a mono WAV") }
    try file.read(into: buffer)
    return Array(UnsafeBufferPointer(start: buffer.floatChannelData![0],
                                     count: Int(buffer.frameLength)))
}

let model = URL(fileURLWithPath: "Model", isDirectory: true)
let out = URL(fileURLWithPath: "out", isDirectory: true)
try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)

// 1. Open the identity. Both downloads are containers, opened as they are;
//    `stagingDir` is a writable directory the engine unpacks them into once.
//    Keep it between runs and the next start is much faster.
let engine = try Expression2Engine.create(
    avatarContainer: model.appendingPathComponent("agent.imx"),
    sharedEngineContainer: model.appendingPathComponent("shared-engine.imx"),
    stagingDir: model.appendingPathComponent("staged"))
print("engine ready: \(engine.width)x\(engine.height), isReady=\(engine.isReady)")

let samples = try readPCM(model.appendingPathComponent("speech16k.wav"))
print("audio: \(samples.count) samples, "
    + String(format: "%.2f s", Double(samples.count) / 16_000))

// 2. Feed the whole utterance, then drain. Generation is asynchronous:
//    `pull()` returns nil until a chunk of frames lands, so a drain on the
//    line after `feed()` gets nothing at all. Poll — 100 idle ticks is done.
let started = Date()
engine.feed(samples)
engine.flushTail()

var frames = 0, idleTicks = 0
while idleTicks < 100 {
    var got = false
    while let (frame, _) = engine.pull() {
        if frames == 0 {
            writePNG(frame, width: engine.width, height: engine.height,
                     to: out.appendingPathComponent("first-frame.png"))
        }
        frames += 1
        got = true
    }
    if got { idleTicks = 0 } else { idleTicks += 1; usleep(50_000) }
}

let elapsed = Date().timeIntervalSince(started)
print("generated \(frames) frames in " + String(format: "%.2f s", elapsed)
    + String(format: " (%.1f FPS, %.2fx real time)",
             Double(frames) / elapsed,
             Double(frames) / 20 / elapsed)
    + " -> out/first-frame.png")
