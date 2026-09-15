# bitHuman examples

Runnable bitHuman demos for every surface we support — mobile, web, Python, the REST API and CLI, native Swift, and third-party framework integrations.

## Find your platform

| Surface | Directory | Notes |
|---|---|---|
| macOS · iOS · Android | `app/` | **Not here yet — and not installable outside bitHuman today.** See [Why `app/` is empty](#why-app-is-empty). For a working on-device app now, use `swift/` (macOS, iOS) or `android/`. |
| Web | `web/` | Not here yet. |
| Python | `python/` | SDK quickstart, self-hosted Essence (CPU), and cloud-hosted Essence via LiveKit. |
| REST API & CLI | `api/` | `api/rest-api/` curl and Python scripts per endpoint; `api/cli/` shell scripts for the `bithuman` CLI. |
| Swift (native, on-device) | `swift/` | macOS, iOS and iPadOS apps, plus playback, server and benchmark samples. |
| Integrations (Next.js, Gradio, Java) | `integrations/` | Next.js + LiveKit frontend, Gradio browser UI, Java WebSocket client, offline macOS stack. |

`android/` holds Gradle and Maven Central setup notes for the native Android SDKs until the Flutter app in `app/` lands.

### Why `app/` is empty

The one-Flutter-app demo is built and running on macOS, iOS and Android internally, but it
cannot be built from a clone of this repository, so shipping it here would hand you a
directory that fails at the first command. Two things are missing, both outside your
control:

- the umbrella Flutter plugin it depends on, `bithuman`, **is not published on pub.dev**;
- that plugin stages its engines per clone from a **private** repository, and its
  bootstrap stops rather than degrade when it cannot reach it.

Until one of those changes, the honest answer is that there is nothing here for you to
run. The native examples are not a lesser substitute — they are fully open: `swift/` builds
against the public Swift package and `android/` against the published Maven artifacts.

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
