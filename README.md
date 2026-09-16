# bitHuman examples

Runnable bitHuman demos for every surface we support — mobile, web, Python, the REST API and CLI, native Swift, and third-party framework integrations.

## Find your platform

| Surface | Directory | Notes |
|---|---|---|
| macOS · iOS · Android | `app/avatar_chat/` | The one Flutter app. **Builds from a clone once two artifacts are published** — see [What `app/` stops at](#what-app-stops-at). For a working on-device app today, use `swift/` (macOS, iOS) or `android/`. |
| Web | `web/` | Not here yet. |
| Python | `python/` | SDK quickstart, self-hosted Essence (CPU), and cloud-hosted Essence via LiveKit. |
| REST API & CLI | `api/` | `api/rest-api/` curl and Python scripts per endpoint; `api/cli/` shell scripts for the `bithuman` CLI. |
| Swift (native, on-device) | `swift/` | macOS, iOS and iPadOS apps, plus playback, server and benchmark samples. |
| Integrations (Next.js, Gradio, Java) | `integrations/` | Next.js + LiveKit frontend, Gradio browser UI, Java WebSocket client, offline macOS stack. |

`android/` holds Gradle and Maven Central setup notes for the native Android SDKs.

### What `app/` stops at

`app/avatar_chat/` is the one Flutter app (macOS · iOS · Android, one `lib/main.dart`, the
shared UI kit). `flutter pub get` resolves from a clone — the plugin is pinned by commit
from the public tap. The build then stops at exactly one gate per platform, both outside
this repository:

| platform | stops at | what unblocks it |
|---|---|---|
| Android | ~~`Could not find ai.bithuman:expression2-android:0.4.6`~~ — **resolved 2026-09-16** | Nothing is pending. The plugin now pins 0.4.7 (and `essence2-android:0.5.8`); both answer 200 on `repo1.maven.org`. |
| iOS / macOS | `cannot find 'Expression2Engine' in scope` | the plugin consuming the published `Expression2.xcframework` instead of staging engine source from a private repository |

Measured from a fresh clone with no private access and an empty local Maven cache. Nothing
fails silently: each build names the artifact it cannot get. Until those land, the native
examples are the ones to run — they are fully open: `swift/` builds against the public
Swift package and `android/` against the published Maven artifacts.

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
