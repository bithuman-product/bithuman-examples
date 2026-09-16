# avatar_chat — the one Flutter app (macOS · iOS · Android)

Clone, add your API secret, run, talk to an avatar on a real device. The avatar is the
interface: full-screen picture, translucent glass chrome that hides itself, one layout on
every platform (`package:bithuman/ui_kit.dart`).

## What builds from a clone today, and what does not

| platform | from a clone | what is missing |
|---|---|---|
| Android | `flutter build apk` — **once `ai.bithuman:expression2-android:0.4.6` is on Maven Central** | Central carries 0.4.1 today; the plugin's Android half needs 0.4.6 (a human press). Everything else resolves publicly. |
| iOS / macOS | not yet | the plugin stages the expression-2 engine SOURCE from a private repository (`scripts/bootstrap.sh`); the switch to the published `Expression2.xcframework` is built but not landed. |

That table is the whole truth of this directory. Nothing here fails silently: the build
stops at the dependency it cannot resolve, and the row above names it.

## Run

```bash
flutter pub get
# Android (Galaxy, arm64): the identity is fetched by CODE through the metered door with
# your secret, into the SDK's own store on the device.
flutter build apk --debug --target-platform android-arm64 --dart-define=AGENT_CODE=A02HCY0444
# macOS / iOS: the identity directory is pushed into the app's container (see the plugin's README).
flutter build macos --debug --dart-define=AGENT_DIR=/absolute/path/to/agent
# iOS: AGENT_DIR is RELATIVE to the app's Documents dir, and it is REQUIRED — an iOS build made
# without it starts, reads an empty AGENT_DIR, and refuses with "AGENT_DIR is not set" before it
# looks at the model that is already in the container. (2026-09-16: a UI-fix build shipped to the
# lab iPhone without it and the owner saw exactly that refusal.) The lab container carries `agent/`:
flutter build ios --release --dart-define=AGENT_DIR=agent
```

## The secret

Never in a build flag you distribute (`--dart-define` ends up in the binary as a plain
string). The app resolves it in this order and stops at the first that is present:
a `BITHUMAN_API_SECRET` dart-define (local development only) → the process environment
(macOS) → the OS secure store (Keychain / Keystore), which the app fills the first time you
type the key into its credential screen. With no key it shows the refusal
`metering_no_credential` and the field; it never spins.

For a test device, seed the store without a prompt: write the secret to
`Documents/.bootstrap_secret` (iOS: `xcrun devicectl device copy to …`; Android: `adb push`
then `run-as <pkg> cp … app_flutter/.bootstrap_secret`). The app moves it into the secure
store on first start and deletes the file.

## Measurement levers (dart-defines, off by default)

`BH_MIC=false` opens a speaker-only session; `BH_SCRIPT='prompt|prompt|@collapse|@restore'`
types prompts 25 s apart (macOS `@collapse`/`@restore` drive the floating-circle companion)
and writes Flutter's frame timings to the breadcrumb file; `BH_ENGINE=essence2` selects the
other engine. The native presenter's own levers are documented in the plugin.
