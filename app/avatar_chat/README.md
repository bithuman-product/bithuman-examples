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

## Two apps side by side, one per engine

`BH_ENGINE` is a **compile-time** dart-define, so an expression-2 build and an essence-2
build are different binaries. While they also shared one bundle identifier, installing
either **replaced** the other — and on Apple they shared one microphone TCC row and one
Keychain item too, so the survivor inherited consent earned by code that was no longer
installed. Two identifiers fix all three, and two build settings are the whole mechanism:

| setting | default | what it changes |
|---|---|---|
| `BH_APP_ID_SUFFIX` | *(empty)* | appended to `ai.bithuman.example.avatarChat` |
| `BH_APP_NAME` | `avatar_chat` (macOS) / `Avatar Chat` (iOS) | `CFBundleName` / `CFBundleDisplayName` |

Both default to exactly what this app has always produced, so an unqualified
`flutter build` is unchanged. Override them through the Flutter tool's documented
`FLUTTER_XCODE_<setting>` bridge, which passes them to `xcodebuild`:

```bash
# the expression-2 app — the default engine keeps the unqualified identifier
flutter build macos --release --dart-define=BH_ENGINE=expression2 \
  --dart-define=AGENT_DIR=/absolute/path/to/AGENT.imx

# the essence-2 app, installable BESIDE it
FLUTTER_XCODE_BH_APP_ID_SUFFIX=.essence2 \
FLUTTER_XCODE_BH_APP_NAME="bitHuman Essence-2" \
flutter build macos --release --dart-define=BH_ENGINE=essence2 \
  --dart-define=AGENT_DIR=/absolute/path/to/OTHER.imx
```

On macOS the Finder shows the `.app` **file name**, not `CFBundleDisplayName`, so name
the copy you install after the model as well. On iOS `CFBundleDisplayName` is the
home-screen label and the two apps appear as separate icons.

★ A distinct identifier means a distinct **microphone grant** and a distinct **Keychain
item**. That is the point — each app carries its own consent — but it also means the
second app asks for both. Provision it the same way you provisioned the first.

## The secret

Never in a build flag you distribute (`--dart-define` ends up in the binary as a plain
string). The app resolves it in this order and stops at the first that is present:
a `BITHUMAN_API_SECRET` dart-define (local development only) → the process environment →
the OS secure store (Keychain / Keystore), which the app fills the first time you type the
key into its credential screen.

A key found in the **environment** is also written to the secure store, once, if the store
is empty — the same one-time provisioning `.bootstrap_secret` does, without the secret ever
touching a file. Launch the app once with the variable set and the next cold launch, with
no variable, goes straight to the avatar:

```bash
# macOS                         # iOS
BITHUMAN_API_SECRET=… open …    xcrun devicectl device process launch --device <udid> \
                                  -e '{"BITHUMAN_API_SECRET":"…"}' <bundle-id>
```

An existing stored key is never overwritten, so a person who typed their own keeps it. With no key it shows the refusal
`metering_no_credential` and the field; it never spins.

For a test device, seed the store without a prompt: write the secret to
`.bootstrap_secret` (iOS: `xcrun devicectl device copy to …` into `Documents/`; macOS: the
app's own `~/Library/Application Support/ai.bithuman.example.avatarChat/` — never the
person's Documents folder, which is iCloud-synced on most Macs and behind a consent prompt the
app must not need to boot). The app moves it into the secure store on first start and
deletes the file.

On Android, use the app's own external files directory — and note that the code which reads
it is **not in a default build**. It is compiled in only when a build asks for it:

```bash
flutter build apk --release --dart-define=BH_TEST_PROVISIONING=true   # a team handset only
adb shell "mkdir -p /sdcard/Android/data/<applicationId>/files"
printf %s "$BITHUMAN_API_SECRET" | adb shell "cat > /sdcard/Android/data/<applicationId>/files/.bootstrap_secret"
adb shell "chmod 666 /sdcard/Android/data/<applicationId>/files/.bootstrap_secret"   # ← required
```

**The `chmod` is not optional.** A file adb writes there is owned by `shell` (uid 2000), not
by the app, and lands as `-rw-rw----` — so the app cannot open its own provisioning file and
the boot reports
`fail=PathAccessException … (OS Error: Permission denied, errno = 13)`. The seeding then looks
done from the host: the file is sitting in the right directory with the right length, and only
`bootstrap_result.txt` says it never got read. Verified on a Galaxy S25 (SM-S936U1).

This repository is public, so a credential-reading path is a pattern people copy into
production apps. Reading a secret out of external storage is a reasonable way to seed a
handset the team controls; it is **not** something a shipped app should do. `BH_TEST_PROVISIONING`
is a compile-time constant, so in a default build the branch folds away and the tree-shaker
drops it: the APK contains no such path at all, rather than one that is merely never taken.

`run-as` is **not** the route: it works only on a debuggable build, and the builds a test
device should be carrying are release builds, so the private `app_flutter/` directory cannot
be written from adb at all. The external files directory is app-scoped under scoped storage —
no other app can read it, and it is removed with the app. The app consumes the file on its
next start, records `ok` or `fail=…` (never the secret) in `files/bootstrap_result.txt` so
provisioning can be CONFIRMED rather than assumed, and deletes the file either way.

Provisioning from the launch environment — the sibling route that stores `BITHUMAN_API_SECRET`
into the secure store on first boot — **does not exist on Android**: an installed app has no
launch environment, so the drop point above is the only route on a handset. Do not reach for
the Apple recipe here and conclude it is broken.

The secret never belongs in a dart-define, a `BuildConfig` field, the manifest, a resource or
a properties file for a build that leaves your machine: all of those put a live credential
inside the APK.

## Both models on one device

The engine is a compile-time constant, so one package id means installing one model
REPLACES the other. `bhModel` gives each its own application id and home-screen label:

| build | application id | home-screen label |
|---|---|---|
| `flutter build apk` (default) | `ai.bithuman.example.avatar_chat` | bitHuman Expression-2 |
| `ORG_GRADLE_PROJECT_bhModel=essence2 flutter build apk --dart-define=BH_ENGINE=essence2` | `ai.bithuman.example.avatar_chat.essence2` | bitHuman Essence-2 |

Seeding a credential onto a team handset is a separate opt-in (`BH_TEST_PROVISIONING`, above);
neither app carries a credential, and a default build carries no code that reads one.

The default is unchanged in both id and behaviour, so the bare command above still builds
what it always built and still upgrades an existing install in place. An unrecognised
`bhModel` fails the build rather than quietly producing a third package id.

## Measurement levers (dart-defines, off by default)

`BH_MIC=false` opens a speaker-only session; `BH_SCRIPT='prompt|prompt|@collapse|@restore'`
types prompts 25 s apart (macOS `@collapse`/`@restore` drive the floating-circle companion)
and writes Flutter's frame timings to the breadcrumb file; `BH_ENGINE=essence2` selects the
other engine. The native presenter's own levers are documented in the plugin.
