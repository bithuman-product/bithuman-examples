# bitHuman examples

Runnable bitHuman demos for every surface we support — mobile, web, Python, the REST API and CLI, native Swift, and third-party framework integrations.

## Find your platform

| Surface | Directory | Notes |
|---|---|---|
| macOS · iOS · Android | `app/` | One Flutter app, both engines. In progress. |
| Web | `web/` | In progress. |
| Python | `python/` | SDK quickstart, self-hosted Essence (CPU), and cloud-hosted Essence via LiveKit. |
| REST API & CLI | `api/` | `api/rest-api/` curl and Python scripts per endpoint; `api/cli/` shell scripts for the `bithuman` CLI. |
| Swift (native, on-device) | `swift/` | macOS, iOS and iPadOS apps, plus playback, server and benchmark samples. |
| Integrations (Next.js, Gradio, Java) | `integrations/` | Next.js + LiveKit frontend, Gradio browser UI, Java WebSocket client, offline macOS stack. |

`android/` holds Gradle and Maven Central setup notes for the native Android SDKs until the Flutter app in `app/` lands.

## What you need

- A bitHuman API secret: https://www.bithuman.ai/developer/api-keys
- Export it before running anything. Python, CLI and REST examples read `BITHUMAN_API_SECRET`; Swift examples read `BITHUMAN_API_KEY`.

```bash
export BITHUMAN_API_SECRET="your_secret"
```

Credentials belong in environment variables or an untracked `.env` file. They are never committed — every example ships a `.env.example` to copy from, and `.env` is gitignored.

## History

This repository supersedes the following repositories. They remain archived and read-only; nothing new lands in them.

- [bithuman-archive/bithuman-examples](https://github.com/bithuman-archive/bithuman-examples)
- [bithuman-archive/bithuman-apps](https://github.com/bithuman-archive/bithuman-apps)
- [bithuman-archive/public-livekit-ui-example](https://github.com/bithuman-archive/public-livekit-ui-example)
- [bithuman-labs/local-deployment-examples](https://github.com/bithuman-labs/local-deployment-examples)
- [bithuman-ai/sdk-examples-python](https://github.com/bithuman-ai/sdk-examples-python)
- [bithuman-product/bithuman-sdk-public](https://github.com/bithuman-product/bithuman-sdk-public)

## Documentation

https://docs.bithuman.ai

## License

Apache 2.0 — see [LICENSE](LICENSE).
