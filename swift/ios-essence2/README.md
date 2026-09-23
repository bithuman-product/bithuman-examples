# ios-essence2 — a photoreal Essence 2 avatar on your iPhone

A complete SwiftUI app that renders an **Essence 2** avatar **on the device**, at the
avatar's own resolution (up to 1920x1080) and 25 fps, with no server in the loop. It
shows the avatar's idle motion and speaks a bundled line with the lips in sync;
**Speak** plays it again.

`Essence2` is a C library: the `be_essence2_*` functions in `be_essence2.h` are the
whole API, and the `Renderer` actor in `Sources/App.swift` is the Swift wrapper.

The docs page is <https://docs.bithuman.ai/examples/swift-ios-essence2>.

## What you need

- A Mac with **Xcode 26 or newer**, and an Apple Developer team.
- A **physical iPhone or iPad** with Apple silicon on **iOS 26**. The Simulator cannot
  run this engine. No Apple entitlement is needed.
- A bitHuman **API secret** (free: [bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys)).
  The engine bills talking time; idle is free. The downloads need no key.
- About 430 MB free on the phone and 380 MB on the Mac.

## Run it

```bash
git clone https://github.com/bithuman-product/bithuman-examples.git
cd bithuman-examples/swift/ios-essence2
./setup.sh                 # the avatar, the engine resources, a speech clip
open IOSEssence2.xcodeproj
```

Then set your API secret: *Product → Scheme → Edit Scheme → Run → Environment
Variables*, add `BITHUMAN_API_SECRET`. Pick your team under *Signing & Capabilities*,
select your iPhone, and press **Run**. The console prints
`[ios-essence2] engine ready: 1080x1920, ready in <n> s`.

`project.yml` is the [XcodeGen](https://github.com/yonaskolb/XcodeGen) source of the
project; `xcodegen generate` rewrites `IOSEssence2.xcodeproj` from it.

## Other avatars

`./setup.sh <AGENT_CODE>` fetches another sample avatar; the app reads the frame size
back from the engine.

| Avatar | Agent code | Frame |
|---|---|---|
| warm-clear-professional-presenter (default) | `A21SKT4314` | 1080x1920 |
| sofia-ramirez | `A52DHS2219` | 1080x1920 |
| kwame-warm-museum-guide | `A62SJB3901` | 1080x1920 |
| afro-latina-astrophysics-mentor | `A23KSG5258` | 1920x1080 |
| calm-product-specialist-advisor | `A24EKJ8433` | 1280x720 |

For your own avatar, create one with `"model": "essence-2"`
([Agents API](https://docs.bithuman.ai/api/agents)) and download it with your
`api-secret` header.

## Files

```
setup.sh                  fetches the payload and checks it
project.yml               XcodeGen source for IOSEssence2.xcodeproj
IOSEssence2.xcodeproj     the project (generated from project.yml)
Sources/App.swift         the whole app: engine, audio, view
Sources/Info.plist        the app's Info.plist
Sources/Model/            the avatar and the speech clip (git-ignored)
Sources/EngineResources/  the shared engine resources (git-ignored)
```

A shipped app should not read the secret from the scheme: fetch it from your backend
or the Keychain at launch and pass it to `be_essence2_set_api_secret`.
