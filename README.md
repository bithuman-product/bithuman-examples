# bitHuman examples

Runnable bitHuman demos for every surface we support — mobile, web, Python, the REST API and CLI, native Swift, and third-party framework integrations.

## Find your platform

| Surface | Directory | Notes |
|---|---|---|
| macOS · iOS · Android | `app/avatar_chat/` | The one Flutter app. **Android builds from a clone today; iOS and macOS do not** — see [What `app/` stops at](#what-app-stops-at). For a working on-device app on iPhone or Mac, use `swift/`. |
| Web | `web/` | Not here yet. |
| Python | `python/` | SDK quickstart, self-hosted Essence (CPU), and cloud-hosted Essence via LiveKit. |
| REST API & CLI | `api/` | `api/rest-api/` curl and Python scripts per endpoint; `api/cli/` shell scripts for the `bithuman` CLI. |
| Swift (native, on-device) | `swift/` | macOS, iOS and iPadOS apps, plus playback, server and benchmark samples. |
| Integrations (Next.js, Gradio, Java) | `integrations/` | Next.js + LiveKit frontend, Gradio browser UI, Java WebSocket client, offline macOS stack. |

`android/` holds Gradle and Maven Central setup notes for the native Android SDKs — coordinates, repositories, and what a release build needs. It is notes only: there is no Gradle project checked in, because the complete Kotlin project for both models is printed in full on [Kotlin / Android — Hello, avatar](https://docs.bithuman.ai/examples/kotlin-android-hello), and that page is compiled by a scheduled gate so it cannot drift from something that builds.

### What `app/` stops at

`app/avatar_chat/` is the one Flutter app (macOS · iOS · Android, one `lib/main.dart`, the
shared UI kit). `flutter pub get` resolves from a clone — the plugin is pinned by tag from
the public tap. **Android builds; iOS and macOS do not**, and the reason is one artifact
that has never been published:

| platform | from a clone | why |
|---|---|---|
| **Android** | **builds** — `flutter build apk` | every engine it needs is a public Maven Central coordinate, resolved anonymously: `ai.bithuman:expression2-android` and `ai.bithuman:essence2-android`, both pulled in by the plugin. |
| **iOS / macOS** | **does not build** | the plugin's Apple half stages its engines from a **private** repository (`scripts/bootstrap.sh` clones `bithuman-product/bithuman-models`, which answers 404 without access) and then fails at `cannot find 'Expression2Engine' in scope`. There is **no published engine asset** a clone could use instead — publishing one is a decision for the owner of that engine, and until it is made, this cannot be fixed from inside this repository. |

That is the whole truth of `app/`: one platform of three builds from a clone today.
Plainly — you can clone this repository and build and run the Android app on a phone, with
no private access; you cannot build this Flutter app for iPhone, iPad or Mac, because the
Apple engine it needs is not published anywhere you can fetch it. For a working on-device
app on iPhone or Mac, use `swift/` — it builds against the **public** Swift package, which
does ship both engines.

## What you need

- A bitHuman API secret: https://www.bithuman.ai/developer/api-keys
- Export it before running anything. Python, CLI and REST examples read `BITHUMAN_API_SECRET`; Swift examples read `BITHUMAN_API_KEY`.

```bash
export BITHUMAN_API_SECRET="your_secret"
```

Credentials belong in environment variables or an untracked `.env` file. They are never committed — every example ships a `.env.example` to copy from, and `.env` is gitignored.

**A build flag is not a safe place for a key.** Passing a secret through
`--dart-define=BITHUMAN_API_SECRET=…` (Flutter) or a generated `BuildConfig` field
(Android Gradle) puts it in the command line of every build step — visible to any local
`ps`, and captured by build logs and crash reporters — and compiles it into the app as a
plain string, where `strings` on the shipped binary or APK will find it. Those flags are
for local development on your own machine only. **Never use them for a build you
distribute**: ship sign-in instead, so the app obtains a short-lived token at runtime and
the long-lived secret never leaves your machine.

## History

This repository supersedes the following repositories. They remain archived and read-only; nothing new lands in them.

- [bithuman-archive/bithuman-examples](https://github.com/bithuman-archive/bithuman-examples)
- bithuman-archive/bithuman-apps _(private)_
- [bithuman-archive/public-livekit-ui-example](https://github.com/bithuman-archive/public-livekit-ui-example)
- bithuman-labs/local-deployment-examples _(private)_
- [bithuman-ai/sdk-examples-python](https://github.com/bithuman-ai/sdk-examples-python)
- [bithuman-product/bithuman-sdk-public](https://github.com/bithuman-product/bithuman-sdk-public)

## Documentation

https://docs.bithuman.ai

## License

Apache 2.0 — see [LICENSE](LICENSE).
