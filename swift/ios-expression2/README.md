# ios-expression2 — a talking avatar on the iPhone you already have

A complete SwiftUI app that renders a lip-synced **Expression 2** avatar **on
the device**, at 416x720, 20 FPS (one frame per 50 ms of audio), paced on the
audio clock, with no server in the loop.

It is deliberately the cheap Apple path:

| | this example | [`ios-avatar`](../ios-avatar) (the legacy `bitHumanKit` umbrella) |
|---|---|---|
| device floor | none — measured on an **iPhone 15**; iOS 16 or newer | iPhone 16 Pro or later |
| Apple entitlements | none | two, 1–3 business days to approve |
| API secret | yes | yes |
| first-launch download | none — the model ships inside the app | ~1.6 GB |
| what drives it | a bundled WAV, or your microphone | on-device speech, a language model and speech synthesis |

The **Speak** path is what every number below was measured on. The **Talk to
it** (microphone) path builds and installs with it but has never been driven by
a human voice on a device — it is a fifteen-line starting point, not a result.

The docs page, with the app running on an iPhone, is
<https://docs.bithuman.ai/examples/ios-expression-2>.

## What you need

- A Mac with **Xcode 26 or newer**, and an Apple Developer team.
- An Apple silicon **iPhone or iPad on iOS 16 or newer**, or the iOS Simulator on an
  Apple silicon Mac (Expression 2 runs in both; the numbers below are from a phone).
- Nothing to install: `setup.sh` is three downloads (`curl`), the same ones the
  [iOS page's First frame](https://docs.bithuman.ai/platforms/ios#first-frame) uses.

- A bitHuman **API secret** to render, from [bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys)
  (Creator plan or higher from 12 October 2026). The engine bills active session time,
  talking or idle. The download is anonymous: `setup.sh` defaults to `A23WJF0199`
  (*Wise Pup*), an identity in the public showcase. Pass your own agent's code to
  render your own identity instead.

## Run it

```bash
git clone https://gitlab.com/bithuman/sdk/bithuman-examples.git
cd bithuman-examples/swift/ios-expression2

# 1. fetch the payload into Sources/Model/  (an anonymous download)
./setup.sh
#    …or your own agent:
#    BITHUMAN_API_SECRET=… ./setup.sh <YOUR_AGENT_CODE>

# 2. open it, pick your team under Signing & Capabilities, pick your iPhone, Run
open IOSExpression2.xcodeproj
```

If `setup.sh` stops, it says which download failed and what the server answered
(for example a 401 for an avatar that is not public); fix that and run it again.

**Set your API secret before you Run.** The engine bills the session it renders and
`create` refuses without a key —
*"refusing to serve: no API secret was found, …"* <!-- claims-check-ignore: the engine's own refusal, quoted -->. In Xcode: *Product → Scheme →
Edit Scheme → Run → Environment Variables*, add `BITHUMAN_API_SECRET`. The download
above stays anonymous; only rendering needs the key. An app you ship calls
`Expression2Credential.set(key)` with a key from your backend or the Keychain.

`setup.sh` puts three files in `Sources/Model/` (about 370 MB):

| file | where it comes from | why |
|---|---|---|
| `agent.imx` | `GET /v1/agent/{code}/model/download?model=expression-2` | the avatar |
| `shared-engine.imx` | the release file `expression2-engine-mac-arm64-1.0.0/mac-arm64-1.0.0.engine` | the engine graphs every avatar shares; the `mac` file is the right one for iPhone too |
| `speech16k.wav` | the same door, `member=demo_speech_16k.wav`: one file out of the avatar's own bundle | something for it to say. 16 kHz, mono, 16-bit PCM |

None of them is committed — the payload is yours, and `.gitignore` keeps it out.

## Two things to know before you build

1. **One call opens both downloads.** `Renderer.load` is
   `Expression2Engine.create(avatarContainer:sharedEngineContainer:stagingDir:)`,
   the same call as the iOS page and [`macos-expression2`](../macos-expression2).
   The staging directory (in the app's Caches) is where the engine unpacks the
   files once; later launches reuse it.
2. **`pull()` is asynchronous.** It returns `nil` until a chunk of frames
   lands, so a bare `while let (frame, _) = engine.pull()` on the line after
   `feed()` drains nothing and your view stays empty. Poll, and feed and drain
   at the same time — see the comment in `speak()`.

## Simulator builds

The package's simulator slices are arm64 only, so the project sets
`EXCLUDED_ARCHS[sdk=iphonesimulator*] = x86_64`: *Any iOS Simulator Device* and
`xcodebuild -destination 'generic/platform=iOS Simulator'` build without an
`ARCHS=arm64` override. If you copy the code into your own project, add the same
setting (or pass `ARCHS=arm64`), otherwise the build fails with
`Unable to find module dependency: 'Expression2'`.

Checked 2026-09-30 in an iPhone 17 / iOS 26.3 Simulator (Xcode 26.3), with an 8 s
cut of the speech clip:

```
[ios-expression2] engine ready: 416x720 · isReady=true in 7.8s
[ios-expression2] audio 16 kHz mono: 128000 samples, 8.00 s
[ios-expression2] generated 160 frames at 416x720 in 7.73 s (20.7 FPS, 1.04x real time)
```

## Measured

On an iPhone 15 (iPhone15,4), iOS 26.6.1, built with Xcode 26.3 on
macOS 26.6.2, 2026-09-09 (before this app moved to the one-call `create`; not
re-measured on a phone since):

```
[ios-expression2] engine ready: 14 members staged · 416x720 · isReady=true in 7.3s
[ios-expression2] audio 16 kHz mono: 83797 samples, 5.24 s
[ios-expression2] generated 117 frames at 416x720 in 2.62 s (44.6 FPS, 2.00x real time)
[ios-expression2] first frame 416x720 written to Documents/first-frame.png (771436 B)
[ios-expression2] played 117 frames in 4.68 s (25.0 FPS) beside 5.24 s of audio
```

The frame pulled off the phone reads 416x720, min 0, max 255, mean 92.66 — a
picture, against an all-black buffer of the same size that the same check calls
flat in the same run. First launch spends most of those 7.3 s compiling the
engine's graphs on the device; later launches were 1.7 s.

Pull that frame off the phone with:

```bash
xcrun devicectl device copy from --device <udid> \
  --domain-type appDataContainer \
  --domain-identifier ai.bithuman.example.ios-expression2 \
  --source Documents/first-frame.png --destination ./first-frame.png
```

## Files

```
setup.sh                 fetches the payload
project.yml              XcodeGen source; `xcodegen generate` rewrites IOSExpression2.xcodeproj
Sources/App.swift        the whole app — engine, audio, view
Sources/Info.plist       one privacy string, for the microphone button only
Sources/Model/           the payload (git-ignored)
```
