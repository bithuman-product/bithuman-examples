# ios-expression2 — a talking avatar on the iPhone you already have

A complete SwiftUI app that renders a lip-synced **Expression 2** avatar **on
the device**, at 416x720, 20 FPS (one frame per 50 ms of audio), paced on the
audio clock, with no server in the loop.

It is deliberately the cheap Apple path:

| | this example | [`ios-avatar`](../ios-avatar) (the `bitHumanKit` umbrella) |
|---|---|---|
| device floor | none — measured on an **iPhone 15** | iPhone 16 Pro or later |
| Apple entitlements | none | two, 1–3 business days to approve |
| account or key | none, for a showcase identity | yes |
| first-launch download | none — the model ships inside the app | ~1.6 GB |
| what drives it | a bundled WAV, or your microphone | on-device speech, a language model and speech synthesis |

The **Speak** path is what every number below was measured on. The **Talk to
it** (microphone) path builds and installs with it but has never been driven by
a human voice on a device — it is a fifteen-line starting point, not a result.

The full tutorial, with every file explained, is at
<https://docs.bithuman.ai/examples/swift-ios-expression2>.

## What you need

- A Mac with **Xcode 26 or newer**, and an Apple Developer team.
- A **physical iPhone or iPad** with Apple Silicon. The Simulator cannot run
  this engine.
- The **bitHuman CLI**, which `setup.sh` calls once to stage the shared engine
  graphs: `brew install bithuman-product/bithuman/bithuman-cli`. `setup.sh`
  checks for it before it downloads anything.

You do **not** need an account, a key or credits: `setup.sh` defaults to
`A23WJF0199` (*Wise Pup*), an identity in the free showcase that the download
endpoint serves to anyone. Pass your own agent's code to render your own
identity instead.

## Run it

```bash
git clone https://github.com/bithuman-product/bithuman-examples.git
cd bithuman-examples/swift/ios-expression2

# 1. fetch the payload into Sources/Model/  (anonymous — no account, no key)
./setup.sh
#    …or your own agent:
#    BITHUMAN_API_SECRET=… ./setup.sh <YOUR_AGENT_CODE>

# 2. open it, pick your team under Signing & Capabilities, pick your iPhone, Run
open IOSExpression2.xcodeproj
```

**Set your API secret before you Run.** From package 2.14.2 the engine bills the
session it renders (talking time only) and `create` refuses without a key —
*"refusing to serve: no API secret was found, …"*. In Xcode: *Product → Scheme →
Edit Scheme → Run → Environment Variables*, add `BITHUMAN_API_SECRET`. The download
above stays anonymous; only rendering needs the key. An app you ship calls
`Expression2Credential.set(key)` with a key from your backend or the Keychain.

`setup.sh` puts three things in `Sources/Model/`:

| file | where it comes from | why |
|---|---|---|
| `agent.avatar` | `GET /v1/agent/{code}/model/download?model=expression-2` | the identity |
| `shared_engine/` | `bithuman engine install mac` | the identity does **not** carry `w2v_frontend_cpuAndNE.mlpackage`; this directory does |
| `speech16k.wav` | the same door, `member=demo_speech_16k.wav` — one file out of the identity's own bundle | something for it to say. 16 kHz, mono, 16-bit PCM |

None of them is committed — the payload is yours, and `.gitignore` keeps it out.

## Two things to know before you build

1. **This app stages the identity's members itself.** `Expression2Engine` also
   takes both containers in one call —
   `create(avatarContainer:sharedEngineContainer:stagingDir:)`, which is what
   [`macos-expression2`](../macos-expression2) uses — but this app came from a
   tag whose iOS build refused a published `.avatar` by member name, so it
   reads them out with `Expression2Container.read` instead. That is the loop in
   `Renderer.load`, and it is a few lines. Either form is current.
2. **`pull()` is asynchronous.** It returns `nil` until a chunk of frames
   lands, so a bare `while let (frame, _) = engine.pull()` on the line after
   `feed()` drains nothing and your view stays empty. Poll, and feed and drain
   at the same time — see the comment in `speak()`.

## Measured

On an iPhone 15 (iPhone15,4), iOS 26.6.1, built with Xcode 26.3 on
macOS 26.6.2, 2026-09-09:

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
project.yml              xcodegen source for IOSExpression2.xcodeproj (optional)
Sources/App.swift        the whole app — engine, audio, view
Sources/Info.plist       one privacy string, for the microphone button only
Sources/Model/           the payload (git-ignored)
```
