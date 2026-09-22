# Swift SDK (Apple Platforms)

The Swift SDK (`bitHumanKit`) runs all inference on-device: STT, LLM, TTS, and lip-sync animation. No server, no cloud GPU, no Docker. Import the package, point it at a model, and ship a native app.

bitHumanKit is distributed as a SwiftPM binary package with zero transitive Swift dependencies.

## Examples

| Example | Platform | Model | API key? | What it shows |
|---------|----------|-------|----------|---------------|
| [macos-voice/](macos-voice/) | macOS | -- (audio only) | No | Minimal voice agent: `VoiceChat` + `VoiceChatConfig`. No avatar, no billing. |
| [macos-avatar/](macos-avatar/) | macOS | Expression | Yes (2 cr/min) | Voice agent with lip-synced avatar: `ExpressionWeights`, `AvatarConfig`, `AvatarCoordinator`, `FramePump`, `AvatarRendererView` via `NSViewRepresentable`. |
| [ios-avatar/](ios-avatar/) | iOS / iPadOS | Expression | Yes (2 cr/min) | Same avatar pipeline on iPhone/iPad: `HardwareCheck.evaluate()` gate, `UIViewRepresentable`, memory entitlements. |
| [essence-playback/](essence-playback/) | macOS / iPad | Essence | Yes (1 cr/min) | Essence `.imx` model: `Bithuman.createRuntime(modelPath:)`, `EssenceRuntime.pushAudio()`, `frames()` AsyncStream. |

Each example is a standalone SPM project. Clone, open in Xcode (or `swift run` from the terminal), and go.

## Developer tools

These are lower-level harnesses (benchmarks, A/B comparisons, a server daemon) carried over from the SDK's own development. They show how to consume the individual engine products directly.

| Example | Consumes | What it shows |
|---------|----------|---------------|
| [hello-voice-chat/](hello-voice-chat/) | `bitHumanKit` | The smallest possible SPM executable embedding the SDK: `VoiceChat` + `VoiceChatConfig`, no avatar, no billing. |
| [compare-quality/](compare-quality/) | `Expression` — **retired; does not build** | Render a WAV → lip-synced MP4 to A/B animator quality. It attaches a product the published package no longer vends, so `swift build` stops at `product 'Expression' … not found`. Kept as a record; use `Expression2` for a current engine. |
| [compare-llm/](compare-llm/) | upstream MLX OSS | Load each on-device LLM (iOS vs macOS split) on a fixed prompt set. No bitHuman binary — same OSS path as `LLMClient`. |
| [compare-tts/](compare-tts/) | `Voice` (private source) | Load Kokoro + Qwen3-TTS and synthesize a fixed utterance. **Requires the private bithuman-sdk-internal sibling checkout** (see its README). |
| [bench-essence/](bench-essence/) | `bitHumanKit` | Essence runtime perf + correctness bench. Full correctness path needs an internal test seam (see its README). |
| [essence-server/](essence-server/) | `bitHumanKit` + LiveKit + Hummingbird | Native Swift LiveKit avatar service: hosts N runtimes behind HTTP `/launch`, republishes video + audio. |

## SwiftPM products

The published package vends **four** library products. Read from the tag
`from: "2.13.8"` resolves, on 2026-09-21:

| Product | `import` | What it is |
|---------|----------|------------|
| `bitHumanKit` | `import bitHumanKit` | Umbrella SDK — speech in, a language model, speech out, and an avatar. |
| `Expression2` | `import Expression2` | The Expression 2 engine alone: a generated scene at 416x720, with a Swift API. |
| `Essence2` | `import Essence2` | The Essence 2 engine alone, as a C interface. Also importable as `CLibEssence2`. |
| `BithumanEngineProtocol` | `import BithumanEngineProtocol` | The source-only common engine interface. Do **not** take it beside `Expression2`, which already carries a binary copy. |

> **There is no `Expression` product and no `Bithuman` product.** Those are older
> spellings this README used to document, and a target that names one fails with
> `product 'Expression' … not found in package 'homebrew-bithuman'`. One example
> here still names `Expression` — see the note on `compare-quality/` above.

**Attach exactly one engine product per app.** `Expression2` and `Essence2` in
one target link green on the Simulator and fail at a device link with duplicate
symbols.

## Hardware floor

**It is per product, not per platform** — this table used to state
`bitHumanKit`'s floor as if it were the whole SDK's, which sent people to buy a
phone they did not need:

| You ship | Device floor | OS floor | Apple entitlements |
|----------|--------------|----------|--------------------|
| `Expression2` | any Apple Silicon iPhone, iPad or Mac — no hardware gate in the binary | iOS 16 / macOS 13 | none |
| `Essence2` | any Apple Silicon iPhone; iPad with M-series; Mac with M3 or newer | iOS 26 / iPadOS 26 / macOS 26 | none |
| `bitHumanKit` | iPhone 16 Pro or newer; iPad Pro M4 or newer (16 GB) | iOS 26 / iPadOS 26 / macOS 26 | **two, granted in 1–3 business days** |

Only `bitHumanKit` carries a device gate and entitlements. The measured
evidence, read out of the published binaries, is on
[docs.bithuman.ai/sdk/ios](https://docs.bithuman.ai/sdk/ios#requirements).

## Links

| Resource | URL |
|----------|-----|
| SwiftPM package | [github.com/bithuman-product/homebrew-bithuman](https://github.com/bithuman-product/homebrew-bithuman) |
| Overview docs | [docs.bithuman.ai/sdk/ios](https://docs.bithuman.ai/sdk/ios) |
| Expression 2 app, every file | [docs.bithuman.ai/examples/swift-ios-expression2](https://docs.bithuman.ai/examples/swift-ios-expression2) |
| Essence 2 app, every file | [docs.bithuman.ai/examples/swift-ios-essence2](https://docs.bithuman.ai/examples/swift-ios-essence2) |
| Check a resolve from any OS | [docs.bithuman.ai/examples/apple-swiftpm-check](https://docs.bithuman.ai/examples/apple-swiftpm-check) |
| CLI (no-code) | [docs.bithuman.ai/sdk/cli](https://docs.bithuman.ai/sdk/cli) |

## Integration

Add the package to your Xcode project or `Package.swift`:

```swift
dependencies: [
    .package(url: "https://github.com/bithuman-product/homebrew-bithuman.git", from: "2.13.8")
]
```

Then `import bitHumanKit` in your source files.

**Write `2.13.8` and nothing lower.** `from:` is a *floor*, and SwiftPM keeps
whatever `Package.resolved` already holds — so a lower number leaves a project on
an Essence 2 engine older than `essence2-v1.9.0`, and on that engine an iPhone
under a 16 Pro warms up, refuses by name and stays idle-only: the face moves, it
never speaks, and nothing is thrown. Every manifest in this directory was raised
from `2.11.0` to `2.13.8` on 2026-09-21 for that reason. If you already resolved
once, run `swift package update` — `Package.resolved` does not move on its own.
Why, in full:
[docs.bithuman.ai/sdk/ios](https://docs.bithuman.ai/sdk/ios#the-floor-is-the-number-that-matters).

## CLI (no-code path)

For quick testing without writing code, install the CLI via Homebrew:

```bash
brew install bithuman-product/bithuman/bithuman-cli
bithuman run
```

See [docs.bithuman.ai/sdk/cli](https://docs.bithuman.ai/sdk/cli) for usage.

## Reference apps

Reference apps (Mac, iPad, iPhone) live in the private `bithuman-apps` repo (collaborator-only). They consume the SDK via the published SwiftPM binary package — the same way any external developer would. Prebuilt binaries are linked from the [quickstart docs](https://docs.bithuman.ai/sdk/swift).

## Python SDK on Apple Silicon

For developers who prefer Python, the `bithuman` PyPI package includes a macOS arm64 wheel with the bundled Swift daemon. See the [deployment guide](https://docs.bithuman.ai/guides/deployment) for running Expression on Mac from Python -- no Xcode required.

## Documentation

- [Swift SDK overview](https://docs.bithuman.ai/sdk/swift)
- [Quickstart](https://docs.bithuman.ai/sdk/swift)
- [CLI reference](https://docs.bithuman.ai/getting-started/cli)
- [Models overview](https://docs.bithuman.ai/getting-started/models)
