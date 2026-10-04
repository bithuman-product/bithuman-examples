# Swift examples — iOS, iPadOS and macOS

One Swift package renders both second-generation models, Essence 2 (a photoreal person)
and Expression 2 (any character), on iPhone, iPad and Mac. The avatar renders on the
device; your app passes in 16 kHz mono speech and draws the frames. The engines check
your API secret when a session starts and report usage to bitHuman.

```swift
.package(url: "https://github.com/bithuman-product/homebrew-bithuman.git", from: "2.20.3")
```

Write `2.20.1` (the current version) or at least `2.18.0`: `from:` is a floor, and older tags pin engines that behave
differently. The current version is on
[docs.bithuman.ai/versions.json](https://docs.bithuman.ai/versions.json); see
[Install](https://docs.bithuman.ai/platforms/ios#install).

**Both engines need your API secret.** From 12 October 2026, API and SDK use requires
the Creator plan or higher. Sessions bill active session time, talking or idle, to the
second ([pricing](https://docs.bithuman.ai/pricing)). Without a key the engines refuse
to start: `Expression2Engine.create` throws `meteringRefused`. Export
`BITHUMAN_API_SECRET` before running a Mac example; for an iOS example set it in the
scheme (*Edit Scheme → Run → Environment Variables*). An app you ship calls
`Expression2Credential.set(key)` or `Essence2Credential.set(key)` with a key it fetched
from your backend — see "What a shipped app holds" in the
[top-level README](../README.md#your-api-secret). Create a key at
[bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys).

## The examples

Start with the first row that matches the machine on your desk. Each example's
`setup.sh` fetches what it needs and, if a download fails, says which one and what the
server answered. [`ci/run-local.sh`](../ci/run-local.sh) is run by hand on a Mac before
merging (GitHub Actions are off for this repository): it builds the Mac packages,
typechecks the iOS sources, and builds the two committed Xcode projects from a clean
copy for the Simulator and a device (steps `swift-build-packages`,
`swift-typecheck-ios`, `swift-xcodebuild-ios`).

| Example | Runs on | What it shows |
|---|---|---|
| [macos-expression2/](macos-expression2/) | any Apple silicon Mac on macOS 14+ | Expression 2 on your Mac: a WAV in, lip-synced frames out, in one file |
| [ios-expression2/](ios-expression2/) | any Apple silicon iPhone or iPad on iOS 16+, or the Simulator | the same engine as a whole SwiftUI app |
| [ios-essence2/](ios-essence2/) | an Apple silicon iPhone or iPad on iOS 26 | a photoreal Essence 2 avatar as a whole SwiftUI app (`Essence2Kit`) |

Every one of them needs an API secret.

### Legacy examples

These three use `bitHumanKit` 2.4.0, the frozen first-generation package (legacy). They
are kept for existing apps; a new app starts from the rows above.

| Example | Runs on | What it shows |
|---|---|---|
| [macos-voice/](macos-voice/) | Mac, M3 or newer | legacy: a voice agent with no avatar |
| [hello-voice-chat/](hello-voice-chat/) | Mac, M3 or newer | legacy: the same agent in 20 lines, with no UI |
| [ios-avatar/](ios-avatar/) | iPhone 16 Pro or newer | legacy: source to attach to your own app target; read its README first |

## The products

| Product | You write | What it is | Deployment target |
|---|---|---|---|
| `Expression2` | `import Expression2` | the Expression 2 engine with a Swift API | iOS 16 · macOS 13 |
| `Essence2Kit` | `import Essence2Kit` | the Essence 2 engine with a Swift API; it includes `Essence2` | iOS 26 · macOS 26 |
| `Essence2` | `import Essence2` | the Essence 2 engine as a C library, for C, C++ and plugins | iOS 26 · macOS 26 |

Do not add `BithumanEngineProtocol` beside `Expression2`, which already carries a copy
of it. The package also vends the legacy `bitHumanKit` 2.4.0 for existing apps.

Every product ships `ios-arm64`, `ios-arm64-simulator` and `macos-arm64`, and every
simulator slice is arm64 only. Essence 2 needs a physical device; Expression 2 also
runs in the Simulator. Both iOS projects here set
`EXCLUDED_ARCHS[sdk=iphonesimulator*] = x86_64`, so a generic Simulator build needs no
`ARCHS=arm64`; in your own project add that setting or pass `ARCHS=arm64`.

## Device floors

| You ship | Device | OS |
|---|---|---|
| `Expression2` | any Apple silicon iPhone, iPad or Mac | iOS 16 / macOS 13 declared; the Mac engine core is built for macOS 14, so the Mac example targets 14 |
| `Essence2Kit`, `Essence2` | any Apple silicon iPhone; iPad with M-series; Mac with M3 or newer | iOS 26 / macOS 26 |

## No code at all

On a Mac you can reach the same engines without Xcode, with the bitHuman CLI:

```bash
curl -fsSL https://install.bithuman.ai | sh    # or: brew install bithuman-product/bithuman/bithuman-cli
bithuman run
```

## Documentation

- [Apple SDK — install, minimal code, device floors](https://docs.bithuman.ai/platforms/ios) · [macOS](https://docs.bithuman.ai/platforms/macos)
- [Apple API reference](https://docs.bithuman.ai/platforms/swift/reference)
- [iOS example: Expression 2](https://docs.bithuman.ai/examples/ios-expression-2) · [macOS example](https://docs.bithuman.ai/examples/macos-expression-2)
- [iOS example: Essence 2](https://docs.bithuman.ai/examples/ios-essence-2)
- [CLI](https://docs.bithuman.ai/platforms/cli) · [Models](https://docs.bithuman.ai/models)
