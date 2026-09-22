# bitHuman Examples — repo guide

A collection of runnable examples that wire the [bithuman](https://pypi.org/project/bithuman/) Python SDK, the [bitHumanKit](https://docs.bithuman.ai/sdk/swift) Swift SDK, the native Android SDKs, the CLI tools, and the REST API into end-to-end stacks.

This repository is the canonical home for these examples, and the only one. The copy
that used to live in `bithuman-product/homebrew-bithuman` under `Examples/` is GONE —
that path 404s today, verified 2026-09-22. Anything still pointing at it is broken, not
merely stale: two Dockerfiles cloned that repo and copied from that path, so their images
could not build at all. If you find another reference, fix it rather than preserving it.

## What is bitHuman?

Real-time avatar animation. Audio in, lip-synced video out — essence-2 at 25 FPS, expression-2 at 20 FPS (one frame per 50 ms of audio). Two models: Essence (CPU, `.imx`) and Expression (GPU/M3+, any face image).

## Layout

```
app/                                  avatar_chat/: the one Flutter app (macOS · iOS · Android).
                                      pub get resolves from a clone; the build stops at one
                                      published-artifact gate per platform (README table).
web/                                  EMPTY. Not started here yet.

python/                               Python SDK examples (pip install bithuman)
  quickstart/                         First avatar in ~5 minutes (local-avatar.py, cloud-avatar.py)
  cloud-essence/                      Essence via bitHuman Cloud + LiveKit (no GPU, no model files)
  local-essence/                      Essence on any machine (CPU, your own .imx)
  (Expression / self-hosted GPU: docs.bithuman.ai/guides/deployment)

api/                                  No-SDK surfaces
  cli/                                Command-line tools (no code): run, render, info, pull, list, doctor
  rest-api/curl/                      One curl script per endpoint
  rest-api/python/                    Full Python scripts per endpoint

swift/                                Swift SDK for Apple platforms — all inference on-device
  macos-voice/                        macOS voice agent (audio only, no API key)
  macos-avatar/                       macOS voice + lip-synced Expression avatar
  ios-avatar/                         iOS/iPadOS Expression avatar with hardware gate
  ios-expression2/                    expression-2 on iPhone, 416x720 @ 20 FPS, no server
  essence-playback/                   Essence .imx on Apple Silicon
  hello-voice-chat/                   Smallest SPM executable that embeds the SDK
  essence-server/                     Native Swift LiveKit avatar service (HTTP /launch)
  bench-essence/                      Essence perf + correctness bench
  compare-quality/ compare-llm/ compare-tts/    Engine A/B harnesses

android/                              Gradle + Maven Central setup for the native Android SDKs,
                                      (the Flutter app in app/ is the successor once its two gates open)

integrations/                         Framework and language bridges
  nextjs-ui/                          Next.js + LiveKit frontend
  java-websocket/                     Java WebSocket client (+ the wire protocol spec)
  gradio-web/                         Gradio + FastRTC browser UI (pure Python)
  offline-mac/                        100% offline macOS stack (Ollama + Apple Speech)
```

## For AI coding agents

If you are an AI agent wiring bitHuman into a user's codebase:

### Decision tree

| User says... | Recommend | Why |
|---|---|---|
| "Never used this before" | [python/quickstart/](python/quickstart/) | One script, sample model auto-downloads |
| "Web app, fastest demo" | [python/cloud-essence/](python/cloud-essence/) | LiveKit plugin, no GPU, no model files |
| "Web app, custom face" | [python/cloud-essence/](python/cloud-essence/) (Expression agent) | Same plugin, any face image |
| "Kiosk / 24/7 / edge box" | [python/local-essence/](python/local-essence/) | CPU only, no idle timeout |
| "On-prem, NVIDIA GPU" | [docs: deployment](https://docs.bithuman.ai/guides/deployment) | Docker, dynamic face |
| "Mac/iPad/iPhone app" | [swift/macos-avatar/](swift/macos-avatar/) or [swift/ios-avatar/](swift/ios-avatar/) | All on-device |
| "Android app" | [android/](android/) | Maven Central coordinates + the `google()` repo trap |
| "Mac, no code" | `brew install bithuman-product/bithuman/bithuman-cli` → see [api/cli/](api/cli/) | 30 seconds |
| "REST API, any language" | [api/rest-api/curl/](api/rest-api/curl/) | Just curl |
| "100% offline Mac" | [integrations/offline-mac/](integrations/offline-mac/) | Ollama + Apple Speech |

### Onboarding

1. **Get an API key**: [www.bithuman.ai](https://www.bithuman.ai) → Developer → API Keys. Set `BITHUMAN_API_SECRET` (Python/REST/CLI) or `BITHUMAN_API_KEY` (Swift).
2. **Pick the model**: Essence (`.imx`, CPU) or Expression (any face, GPU/M3+). See [docs.bithuman.ai/getting-started/models](https://docs.bithuman.ai/getting-started/models).
3. **Copy the example folder**. Every folder ships a `.env.example` + one-command run path.
4. **Pricing**: [docs.bithuman.ai/getting-started/pricing](https://docs.bithuman.ai/getting-started/pricing). Free tier: 99 cr/month.

### Machine-readable

- [OpenAPI spec](https://docs.bithuman.ai/api/openapi.yaml)
- [llms.txt](https://docs.bithuman.ai/llms.txt) / [llms-full.txt](https://docs.bithuman.ai/llms-full.txt)

### What NOT to do

- Add `homebrew-bithuman.git` as the SPM dependency (it is the Homebrew tap and CLI installer, not a Swift package; the SDK internals are closed-source — consume the published binary).
- Don't clone Swift SDK source or reference apps — both private.
- Don't hardcode API keys. Use env vars.
- Don't pin Swift SDK below 0.8.1.
- Don't point users at `web/` (empty). `app/avatar_chat/` is here but stops at one published-artifact gate per platform (see README, "What `app/` stops at"). Point them at `swift/` or `android/`, which are fully open.
- Don't put a secret in `--dart-define` or a Gradle `BuildConfig` field in anything a user is told to ship: both land in build argv and in the built binary. Local development only; sign-in for anything distributed.
- Don't add a relative link without checking it resolves from the file's own directory. These examples were moved out of `homebrew-bithuman/Examples/`, so paths that read plausibly may no longer exist.
