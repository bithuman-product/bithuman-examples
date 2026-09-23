# bitHuman Examples — repo guide

A collection of runnable examples that wire the [bithuman](https://pypi.org/project/bithuman/) Python SDK, the [bitHumanKit](https://docs.bithuman.ai/sdk/swift) Swift SDK, the native Android SDKs, the CLI tools, and the REST API into end-to-end stacks.

This repository is the canonical home for these examples, and the only one. The copy
that used to live in `bithuman-product/homebrew-bithuman` under `Examples/` is GONE —
that path 404s today, verified 2026-09-22. Anything still pointing at it is broken, not
merely stale: two Dockerfiles cloned that repo and copied from that path, so their images
could not build at all. If you find another reference, fix it rather than preserving it.

## What is bitHuman?

Real-time avatar animation: audio in, lip-synced video out.

**essence-2 and expression-2 are two different products, not two tiers of one.** Pick by where the face comes from — a prebuilt `.imx` avatar file (essence-2, any CPU, 1920×1080 at 25 fps) or any face image chosen at runtime (expression-2, GPU or Apple Silicon M3+, 416×720 at 20 fps).

★Do not present the two frame rates as a ranking. An essence-2 frame carries **6.92× the pixels** of an expression-2 frame (2,073,600 vs 299,520); 25 and 20 are not measuring the same thing, and neither model is "the fast one". `essence-1` and `expression-1` are the first generation and are not where a new integration starts.

## Layout

```
app/                                  avatar_chat/: the one Flutter app (macOS · iOS · Android).
                                      Android builds from a clone; iOS and macOS do not — the
                                      plugin's Apple engine is not published (README table).
                                      (there is no web/ directory — the web surface is not in this repo)

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
  macos-expression2/                  expression-2 on a Mac: a WAV in, frames out, no account
  ios-expression2/                    the same engine on iPhone, 416x720 @ 20 FPS, no server
  macos-voice/                        macOS voice agent (audio only, no API secret)
  hello-voice-chat/                   the same agent in 20 lines, no window
  ios-avatar/                         the bitHumanKit umbrella on iOS — source, not a runnable project

android/                              Gradle + Maven Central setup for the native Android SDKs,
                                      (the Flutter app in app/ is the successor once its Apple engine is published)

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
| "Mac/iPad/iPhone app" | [swift/macos-expression2/](swift/macos-expression2/) or [swift/ios-expression2/](swift/ios-expression2/) | All on-device, no account |
| "Android app" | [android/](android/) | Maven Central coordinates + the `google()` repo trap |
| "Mac, no code" | `brew install bithuman-product/bithuman/bithuman-cli` → see [api/cli/](api/cli/) | 30 seconds |
| "REST API, any language" | [api/rest-api/curl/](api/rest-api/curl/) | Just curl |
| "100% offline Mac" | [integrations/offline-mac/](integrations/offline-mac/) | Ollama + Apple Speech |

### Onboarding

1. **Get an API secret**: [www.bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys) → API Secrets. Set **`BITHUMAN_API_SECRET`** — the one name every example reads. `bitHumanKit` 2.4.0 (`swift/ios-avatar/`) takes it through `config.apiKey`, a field that keeps its published name; the example reads `BITHUMAN_API_SECRET` into it.
2. **Pick the model**: Essence (`.imx`, CPU) or Expression (any face, GPU/M3+). See [docs.bithuman.ai/getting-started/models](https://docs.bithuman.ai/getting-started/models).
3. **Copy the example folder**. Every folder ships a `.env.example` + one-command run path.
4. **Pricing**: [docs.bithuman.ai/getting-started/pricing](https://docs.bithuman.ai/getting-started/pricing) — read the tier off that page rather than quoting a number here, which is how the Android version table went thirteen releases stale.

### Names — use these exactly

An example that calls the same thing three names is an example nobody can search. Measured 2026-09-22 against the published artifacts, not from memory:

| Thing | Write | Not |
|---|---|---|
| The models | `essence-2`, `expression-2`, `essence-1`, `expression-1` | `Essence`/`Expression` bare (ambiguous between generations), `essence2-light`, `light xxx`, `tessera` (retired) |
| The credential | "API secret"; `BITHUMAN_API_SECRET`; header `api-secret` | "API secret"; BITHUMAN_API_KEY (a deprecated alias, still read — never write it); `BITHUMAN_API_TOKEN`, `BITHUMAN_RUNTIME_TOKEN` (short-lived tokens are passed per call, never through the environment) |
| Python entry | `bithuman.open(...)` → `Avatar.render(...)` — the taught surface of the published wheel. For LiveKit and other `bithuman<3` callers, `AsyncBithuman`. | `AsyncAvatar` — it exists and works, but the wheel's own source calls it an alias of the compatibility class, so it is the third-choice name for a teaching example |
| The Python package | `bithuman` on PyPI | `bithuman-cli` — **retired on PyPI and it will not come back**; the CLI ships only via the tap formula, the tap's `install.sh`, or a release tarball |
| The Swift package | `bitHumanKit`, from `homebrew-bithuman.git` | a local path, a vendored copy |

### Versions

★No file in this repository may advertise a version the registry does not serve, and the top-level README carries no version literal at all. `scripts/check_published_versions.py` reads Maven Central, PyPI and the tap's tag list — never a local checkout — and `.github/workflows/published-versions.yml` runs it on every pull request **and once a day**, because the failure it guards against takes no commit: `android/README.md` sat thirteen releases behind while nobody touched it. It carries eleven controls (`--selftest`) proving it can go red — including one proving an unreachable registry exits non-zero instead of passing, and three on the waiver ledger's own rules, which were wrong when first written.

Two escapes, both narrow: `<!-- version-check-ignore: reason -->` on a line whose old number is the point (a dated measurement), and `.github/version-waivers.json` for a defect in a lane you do not own — every waiver carries an owner, a reason and an expiry, and an expired one is a hard failure.

### Machine-readable

- [OpenAPI spec](https://docs.bithuman.ai/api/openapi.yaml)
- [llms.txt](https://docs.bithuman.ai/llms.txt) / [llms-full.txt](https://docs.bithuman.ai/llms-full.txt)

### What NOT to do

- Don't tell anyone `homebrew-bithuman.git` is *only* a Homebrew tap. It is **both**: the tap that installs the `bithuman-cli` formula **and** the SwiftPM binary package. `.package(url: "https://github.com/bithuman-product/homebrew-bithuman.git", from: …)` is the correct and only way to depend on `bitHumanKit` — it is what `swift/README.md` and every `Package.swift` in `swift/` already do, and what `.github/workflows/swift-examples.yml` fetches its xcframeworks from. (This line used to say the opposite, and contradicted every Swift example in this repository.)
- Don't clone Swift SDK source or reference apps — both private. Consume the published binary.
- Don't hardcode your API secret. Use env vars — never argv either (`ps` shows it).
- **Don't write a version number from memory.** Read it from the registry: Maven Central's `maven-metadata.xml`, PyPI's JSON API, `git ls-remote --tags` on the tap. `scripts/check_published_versions.py` is the authority and CI fails on a version the registry does not serve — see "Versions" below.
- Don't point users at `web/` — there is no such directory. `app/avatar_chat/` exists but does not build for iOS or macOS from a clone (see README, "Known gaps"). Point them at `swift/` or `android/`, which are fully open.
- Don't put a secret in `--dart-define` or a Gradle `BuildConfig` field in anything a user is told to ship: both land in build argv and in the built binary. Local development only; sign-in for anything distributed.
- Don't add a relative link without checking it resolves from the file's own directory. These examples were moved out of `homebrew-bithuman/Examples/`, so paths that read plausibly may no longer exist.
