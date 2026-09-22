# Swift examples — iOS, iPadOS and macOS

One SwiftPM package vends both second-generation models and a whole on-device
voice agent, for iPhone, iPad and Mac alike. Everything here renders on the
device: no server, no cloud GPU, no Docker.

```swift
.package(url: "https://github.com/bithuman-product/homebrew-bithuman.git", from: "2.14.0")
```

Write `2.14.0` and nothing lower — `from:` is a floor, and the tags below it
pin engines that fail in ways nothing throws. See
[Pin the version](https://docs.bithuman.ai/sdk/ios#pin-the-version).

## The examples

Every one of these builds from a clone against the published package. Start
with the first row that matches the machine on your desk.

| Example | Runs on | Needs an account? | What it shows |
|---|---|---|---|
| [macos-expression2/](macos-expression2/) | any Apple Silicon Mac | no | Expression 2 on your Mac: a WAV in, lip-synced frames out, in one file |
| [ios-expression2/](ios-expression2/) | any Apple Silicon iPhone or iPad | no | the same engine as a whole SwiftUI app, measured rendering on an iPhone 15 |
| [macos-voice/](macos-voice/) | Mac, M3 or newer | no | a voice agent with no avatar — recognition, a language model and speech, all on device |
| [hello-voice-chat/](hello-voice-chat/) | Mac, M3 or newer | no | the same thing in 20 lines, with no UI at all |
| [ios-avatar/](ios-avatar/) | iPhone 16 Pro or newer | yes | the voice agent *with* a lip-synced avatar. Source to attach to your own app target — read its README before you clone it |

## The products

The published package vends **four** library products. Most apps want one of
the first three; do not take `BithumanEngineProtocol` beside `Expression2`,
which already carries a copy of it.

| Product | You write | What it is |
|---|---|---|
| `Expression2` | `import Expression2` | the Expression 2 engine, pre-compiled, with a Swift API. Any Apple Silicon device |
| `Essence2` | `import Essence2` | the Essence 2 engine as a static C library. iOS 26 / macOS 26, and **four link settings** your target must carry — [which, and why](https://docs.bithuman.ai/sdk/ios#what-essence-2-needs-at-link) |
| `bitHumanKit` | `import bitHumanKit` | the voice-agent umbrella: recognition, a language model, speech, avatar, renderer views |
| `BithumanEngineProtocol` | `import BithumanEngineProtocol` | the common engine interface, as source |

Every product ships `ios-arm64`, `ios-arm64-simulator` and `macos-arm64`, and
every simulator slice is arm64 only.

## Device floors

The products do not share one, and only `bitHumanKit` carries the strict one.

| You ship | Device | OS |
|---|---|---|
| `Expression2` | any Apple Silicon iPhone, iPad or Mac | iOS 16 / macOS 13 |
| `Essence2` | any Apple Silicon iPhone; iPad with M-series; Mac with M3 or newer | iOS 26 / macOS 26 |
| `bitHumanKit` | iPhone 16 Pro or newer; iPad Pro M4 or newer; Mac with M3 or newer | iOS 26 / macOS 26 |

`bitHumanKit` on iOS also needs two Apple entitlements that take Apple 1–3
business days to grant. Neither engine product needs any.

## No code at all

On a Mac you can reach the same engines without Xcode:

```bash
brew install bithuman-product/bithuman/bithuman-cli
bithuman run
```

## Documentation

- [Apple SDK — install, minimal code, device floors](https://docs.bithuman.ai/sdk/ios)
- [Apple API reference](https://docs.bithuman.ai/sdk/ios-api)
- [Expression 2 on iPhone, every file explained](https://docs.bithuman.ai/examples/swift-ios-expression2)
- [Essence 2 on iPhone, every file explained](https://docs.bithuman.ai/examples/swift-ios-essence2)
- [CLI](https://docs.bithuman.ai/sdk/cli) · [Models](https://docs.bithuman.ai/concepts/models)
