# bitHuman Examples — repo guide

A collection of runnable examples that wire the [bithuman](https://pypi.org/project/bithuman/) Python SDK, the [Swift package](https://docs.bithuman.ai/platforms/ios) (`Expression2`, `Essence2Kit`), the native Android SDKs, the CLI, and the REST API into end-to-end stacks.

From 12 October 2026, API and SDK use requires the Creator plan or higher; never tell a user they can build on a free plan. Sessions bill active session time, talking or idle, to the second. The phone and Mac SDKs render only: the conversation comes from the developer's own speech, language-model and voice services, or from bitHuman's managed agent through the web embed or LiveKit.

This repository is the canonical home for these examples, and the only one. The copy
that used to live in `bithuman-product/homebrew-bithuman` under `Examples/` is GONE —
that path 404s today, verified 2026-09-22. Anything still pointing at it is broken, not
merely stale: two Dockerfiles cloned that repo and copied from that path, so their images
could not build at all. If you find another reference, fix it rather than preserving it.

## What is bitHuman?

Real-time avatar animation: audio in, lip-synced video out.

**essence-2 and expression-2 are two different products, not two tiers of one.** Essence 2 renders a photoreal person and Expression 2 any character (people, animals, cartoons), each created once from one portrait. Both render on iPhone, iPad, Mac, Android arm64, a Linux PC with no GPU, and in the bitHuman cloud ([Models](https://docs.bithuman.ai/models)).

Quote speed only from [docs.bithuman.ai/performance.json](https://docs.bithuman.ai/performance.json), as "× real time" with the device. `essence-1` and `expression-1` are the first generation and are not where a new integration starts; `expression-1` runs in the bitHuman cloud only.

## Layout

```
app/                                  avatar_chat/: the Flutter app. Verified on Android; its iOS
                                      and macOS builds are not re-verified (README table).
                                      (there is no web/ directory — the web surface is not in this repo)

python/                               Python SDK examples (pip install bithuman)
  quickstart/                         First avatar in ~5 minutes (local-avatar.py, cloud-avatar.py) + terminal
                                      scripts: quickstart.py, microphone.py, conversation.py (OpenAI Realtime, no LiveKit)
  cloud-essence/                      Essence via bitHuman Cloud + LiveKit (no GPU, no model files)
  self-host/                          Voice agent on YOUR machine: livekit-server --dev + OpenAI Realtime +
                                      the avatar rendered in-process (Essence 2 or Expression 2, CPU, no Docker)
  (other self-hosting options: docs.bithuman.ai/deploy/self-hosted)

api/                                  No-SDK surfaces
  cli/                                Command-line tools (no code): run, render, info, pull, list, doctor
  rest-api/curl/                      One curl script per endpoint
  rest-api/python/                    Full Python scripts per endpoint

swift/                                Swift package for Apple platforms — the avatar renders on the device
  macos-expression2/                  expression-2 on a Mac: a WAV in, frames out (API secret)
  ios-expression2/                    the same engine as an iPhone / iPad app
  ios-essence2/                       essence-2 as an iPhone / iPad app (Essence2Kit)
  macos-voice/                        legacy (bitHumanKit 2.4.0): a voice agent with no avatar
  hello-voice-chat/                   legacy (bitHumanKit 2.4.0): the same agent in 20 lines
  ios-avatar/                         legacy (bitHumanKit 2.4.0): source, not a runnable project

android/                              Gradle + maven.bithuman.ai setup for the native Android SDKs,
                                      (the Flutter app in app/ is the successor once its Apple engine is published)
  expression2-hello/                  expression-2 on a phone: a WAV in, frames rendered on the device, played back
  essence2-hello/                     essence-2, the same shape, full-resolution frames

integrations/                         Framework and language bridges
  nextjs-ui/                          Next.js + LiveKit frontend
  java-websocket/                     Java WebSocket client (+ the wire protocol spec)
  gradio-web/                         Gradio + FastRTC browser UI (pure Python)
  offline-mac/                        a local conversation brain on a Mac (Ollama + Apple Speech); online for the avatar
```

## For AI coding agents

If you are an AI agent wiring bitHuman into a user's codebase:

### Decision tree

| User says... | Recommend | Why |
|---|---|---|
| "Never used this before" | [python/quickstart/](python/quickstart/) | One script, sample model auto-downloads |
| "Web app, fastest demo" | [python/cloud-essence/](python/cloud-essence/) | LiveKit plugin, no GPU, no model files |
| "Web app, custom face" | [python/cloud-essence/](python/cloud-essence/) (Expression agent) | Same plugin, any face image |
| "Talk to an avatar on my machine" | `bithuman run wise-pup` ([api/cli/](api/cli/)), or [python/self-host/](python/self-host/) for your own agent code | One command; or ~70 lines of LiveKit Agents, rendered in-process |
| "Kiosk / 24/7 / edge box" | [python/self-host/](python/self-host/) | CPU only, your own LiveKit server |
| "On-prem servers" | [docs: your servers](https://docs.bithuman.ai/deploy/self-hosted) | your Mac or Linux machines, no GPU needed |
| "Mac/iPad/iPhone app" | [swift/macos-expression2/](swift/macos-expression2/), [swift/ios-expression2/](swift/ios-expression2/) or [swift/ios-essence2/](swift/ios-essence2/) | Renders on the device; needs an API secret |
| "Android app" | [android/](android/) | maven.bithuman.ai coordinates + the `google()` repo trap |
| "Mac, no code" | `brew install bithuman-product/bithuman/bithuman-cli` → see [api/cli/](api/cli/) | 30 seconds |
| "REST API, any language" | [api/rest-api/curl/](api/rest-api/curl/) | Just curl |
| "A local brain on a Mac" | [integrations/offline-mac/](integrations/offline-mac/) | Ollama + Apple Speech; the avatar still checks the API secret online |
| "Offline, no internet" | [docs: fully offline](https://docs.bithuman.ai/deploy/offline) | Business and Enterprise, Linux and macOS computers (Apple silicon), bought in the console or through sales |

### Onboarding

1. **Get an API secret**: [www.bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys) → API Secrets. Set **`BITHUMAN_API_SECRET`** — the one name every example reads, except a LiveKit worker, which reads **`BITHUMAN_MASTER_SECRET`** and refuses to start while `BITHUMAN_API_SECRET` is set (`livekit-plugins-bithuman` 1.8.4 and older reads that name by itself and, for a cloud avatar, copies it into room-readable participant attributes). The legacy `bitHumanKit` 2.4.0 (`swift/ios-avatar/`) takes it through `config.apiKey`, a field that keeps its published name; the example reads `BITHUMAN_API_SECRET` into it.
2. **Pick the model**: Essence 2 (a photoreal person) or Expression 2 (any character). See [docs.bithuman.ai/models](https://docs.bithuman.ai/models).
3. **Copy the example folder**. Every folder ships a `.env.example` + one-command run path.
4. **Pricing**: [docs.bithuman.ai/pricing](https://docs.bithuman.ai/pricing), or `GET https://api.bithuman.ai/v1/pricing` — read the rate from there rather than quoting a number here. API and SDK use requires the Creator plan or higher from 12 October 2026.

### Names — use these exactly

An example that calls the same thing three names is an example nobody can search. Measured 2026-09-22 against the published artifacts, not from memory:

| Thing | Write | Not |
|---|---|---|
| The models | `essence-2`, `expression-2`, `essence-1`, `expression-1` | `Essence`/`Expression` bare (ambiguous between generations), `essence2-light`, `light xxx`, `tessera` (retired) |
| The credential | "API secret"; `BITHUMAN_API_SECRET`; header `api-secret`; in a LiveKit worker `BITHUMAN_MASTER_SECRET` | "API secret"; BITHUMAN_API_KEY (a deprecated alias, still read — never write it); `BITHUMAN_API_TOKEN`, `BITHUMAN_RUNTIME_TOKEN` (tokens minted per call are passed per call, never through the environment) |
| Python entry | `bithuman.open(...)` → `Avatar.render(...)` — the taught surface of the published wheel. For LiveKit and other `bithuman<3` callers, `AsyncBithuman`. | `AsyncAvatar` — it exists and works, but the wheel's own source calls it an alias of the compatibility class, so it is the third-choice name for a teaching example |
| The Python package | `bithuman` on PyPI | `bithuman-cli` — **retired on PyPI and it will not come back**; the CLI ships only via the tap formula, the tap's `install.sh`, or a release tarball |
| The Swift package | `Expression2` or `Essence2Kit`, from `homebrew-bithuman.git` | a local path, a vendored copy; the legacy `bitHumanKit` for a new app |

### Versions

★No file in this repository may advertise a version the registry does not serve, and the top-level README carries no version literal at all. `scripts/check_published_versions.py` reads bitHuman's Maven repository (maven.bithuman.ai), PyPI and the tap's tag list — never a local checkout — and `ci/run-local.sh` runs it before every merge (step `published-versions`; run it periodically too, since GitHub Actions is off), because the failure it guards against takes no commit: `android/README.md` sat thirteen releases behind while nobody touched it. It carries eleven controls (`--selftest`) proving it can go red — including one proving an unreachable registry exits non-zero instead of passing, and three on the waiver ledger's own rules, which were wrong when first written.

Two escapes, both narrow: `<!-- version-check-ignore: reason -->` on a line whose old number is the point (a dated measurement), and `.github/version-waivers.json` for a defect in a lane you do not own — every waiver carries an owner, a reason and an expiry, and an expired one is a hard failure.

### Machine-readable

- [OpenAPI spec](https://docs.bithuman.ai/api/openapi.yaml)
- [llms.txt](https://docs.bithuman.ai/llms.txt) / [llms-full.txt](https://docs.bithuman.ai/llms-full.txt)

### What NOT to do

- Don't tell anyone `homebrew-bithuman.git` is *only* a Homebrew tap. It is **both**: the tap that installs the `bithuman-cli` formula **and** the SwiftPM binary package. `.package(url: "https://gitlab.com/bithuman/sdk/homebrew-bithuman", from: …)` is the correct and only way to depend on the Swift products (`Expression2`, `Essence2Kit`, `Essence2`) — it is what `swift/README.md` and every `Package.swift` in `swift/` already do, and what the `swift-typecheck-ios` step of `ci/run-local.sh` fetches its xcframeworks from. (This line used to say the opposite, and contradicted every Swift example in this repository.)
- Don't clone Swift SDK source or reference apps — both private. Consume the published binary.
- Don't hardcode your API secret. Use env vars — never argv either (`ps` shows it).
- **Don't write a version number from memory.** Read it from the registry: maven.bithuman.ai's `maven-metadata.xml`, PyPI's JSON API, `git ls-remote --tags` on the tap. `scripts/check_published_versions.py` is the authority and `ci/run-local.sh` fails on a version the registry does not serve — see "Versions" below.
- Don't point users at `web/` — there is no such directory; the web path is one iframe ([Web](https://docs.bithuman.ai/platforms/web)). `app/avatar_chat/` is verified on Android only (see README, "Known gaps"). Point Apple developers at `swift/`.
- Don't put a secret in `--dart-define` or a Gradle `BuildConfig` field in anything a user is told to ship: both land in build argv and in the built binary. Local development only. For anything distributed, follow "What a shipped app holds" in the README: fetch the secret from your backend at startup, one secret per app, rotate on unusual usage.
- Don't add a relative link without checking it resolves from the file's own directory. These examples were moved out of `homebrew-bithuman/Examples/`, so paths that read plausibly may no longer exist.
