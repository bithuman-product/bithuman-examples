# avatar_chat — a Flutter avatar app (Android)

Clone, add your API secret, run, talk to an avatar on a real device. The API secret needs the Creator plan or higher from 12 October 2026, and sessions bill active session time ([pricing](https://docs.bithuman.ai/pricing)). The avatar is the
interface: full-screen picture, translucent glass chrome that hides itself, one layout on
every platform (`package:bithuman/ui_kit.dart`).

## What builds from a clone today, and what does not

| platform | from a clone | why |
|---|---|---|
| **Android** | **builds** — `flutter build apk` | every engine it needs is a public coordinate on bitHuman's Maven repository (`https://maven.bithuman.ai`, which the plugin declares), resolved anonymously by Gradle: `ai.bithuman:expression2-android` and `ai.bithuman:essence2-android`, both pulled in by the plugin this app pins. |
| **iOS / macOS** | **not yet verified for this app** | since plugin 2.6.20 the Apple half links the published engines (a new Flutter app builds for iOS 16+ and, from plugin 2.6.36, macOS 26+ after the plugin's `scripts/bootstrap.sh`), but this app's own iOS/macOS build has not been re-run; for Apple today, build `swift/` in this repository |

That table is the whole truth of this directory. Nothing here fails silently: the build
stops at the dependency it cannot resolve, and the row above names it.

**So, plainly, today:** you can clone this repository and build and run the Android app on a phone, with Expression 2 or Essence 2 and no private access at all. For iPhone, iPad or Mac, the plugin can now fetch its Apple engines from public releases (2.6.20), but this app's own Apple build has not been re-verified; for a working on-device app on iPhone or Mac today, build `swift/` in this repository, which uses the **public** Swift package.

### Which engine the Android app runs

The plugin is pinned by tag in `pubspec.yaml`, and that tag fixes the engine versions.
This app pins **`flutter-plugin-v2.6.36`**, which resolves **`ai.bithuman:essence2-android:0.9.4`**
and **`ai.bithuman:expression2-android:0.6.0`** from bitHuman's Maven repository. The voice
session goes through bitHuman's realtime relay (since 2.6.20): the app passes your API secret
and mints no token.

Both coordinates resolve anonymously from `https://maven.bithuman.ai`, which the plugin adds
for the `ai.bithuman` group only; neither needs Google's Maven. `google()` is still in the repository list because the Android Gradle
Plugin fetches its own `aapt2` from there.

## Run

```bash
flutter pub get
# Android (arm64): the identity is fetched by its agent code with your API secret,
# into the SDK's own store on the device.
flutter build apk --debug --target-platform android-arm64 --dart-define=AGENT_CODE=A02HCY0444
# macOS / iOS: the identity directory is pushed into the app's container (see the plugin's README).
flutter build macos --debug --dart-define=AGENT_DIR=/absolute/path/to/agent
# iOS: AGENT_DIR is RELATIVE to the app's Documents dir, and it is REQUIRED — an iOS build made
# without it starts, reads an empty AGENT_DIR, and refuses with "AGENT_DIR is not set" before it
# looks at the model that is already in the container. For a container that carries `agent/`:
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
# macOS — the variable is in the launching shell's environment, nowhere else
BITHUMAN_API_SECRET=… open -n -a "…​.app"
```

An existing stored key is never overwritten, so a person who typed their own keeps it.

### ★ Do not seed a phone through `devicectl -e` — argv is not private

`xcrun devicectl device process launch -e '{"BITHUMAN_API_SECRET":"…"}'` looks like the
environment route, and it is not: the JSON is an **argument**, so the live secret sits in
that process's `argv` and every process on the host can read it out of `ps` for as long as
the app runs. **A credential anywhere in a process tree is exposed to everything that can
read that tree**, including the diagnostic you run later for something else. `devicectl` offers no stdin route for
the child environment, so on a phone use `.bootstrap_secret` instead: the value lands in
the app's own container, the app moves it into the Keychain and **deletes the file**. That
trades "readable by every process on the host" for "briefly on the device's own disk",
which is the better side of the trade.

```bash
# the phone: argv-free. The app consumes and deletes this on first start.
printf %s "$SECRET" > "$TMP/.bootstrap_secret"        # $TMP on a tmpfs you control
xcrun devicectl device copy to --device <udid> --domain-type appDataContainer \
  --domain-identifier <bundle-id> --source "$TMP/.bootstrap_secret" \
  --destination Documents/.bootstrap_secret
shred -u "$TMP/.bootstrap_secret" 2>/dev/null || rm -f "$TMP/.bootstrap_secret"
```

Launched with no key at all, the app does not hang: it shows the refusal
`metering_no_credential` and the credential screen, and waits for you to type one.

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
`bootstrap_result.txt` says it never got read.

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

## Testing the credential path

Launch the app cold, with nothing in the environment and nothing staged, to test the
credential the way a person meets it: the environment is read before the Keychain, so a
test that always sets `BITHUMAN_API_SECRET` never exercises the Keychain at all. On macOS the
app uses the file-based login keychain, so `security add-generic-password` and the app use the
same store. (A team-signed build may prefer the data-protection keychain; an ad-hoc-signed app
cannot use it.)
