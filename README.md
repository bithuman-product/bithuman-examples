# bitHuman examples

Working examples for bitHuman real-time avatars: speech in, a lip-synced face out, on iOS, Android, macOS, the web (Next.js), Python, REST and the CLI.

From 12 October 2026, API and SDK use requires the Creator plan or higher. Every example needs an [API secret](#your-api-secret).

## Start here

Find the row that matches what you are building and open that directory. Each one has its own README with a one-command run.

| You are building | Open | Where it runs |
|---|---|---|
| **Anything — first time** | [`python/quickstart/`](python/quickstart/) | your machine, CPU. One script; the sample avatar downloads itself. |
| **Talk to an avatar on my machine** | [`api/cli/`](api/cli/) — one command, `bithuman run wise-pup` · [`python/self-host/`](python/self-host/) — your own agent code | your machine: your LiveKit server, OpenAI Realtime on your key, the avatar rendered locally |
| A Python service or a LiveKit agent | [`python/`](python/) | your own CPU box, or the bitHuman cloud |
| A Mac, iPhone or iPad app | [`swift/`](swift/) | on the device; the engine checks your API secret when a session starts |
| An Android app | [`android/essence2-hello/`](android/essence2-hello/) · [`android/expression2-hello/`](android/expression2-hello/) | on-device: two complete Gradle projects that build from a clone, from Maven Central coordinates ([Android: Essence 2](https://docs.bithuman.ai/examples/android-essence-2) · [Android: Expression 2](https://docs.bithuman.ai/examples/android-expression-2)) |
| A Flutter app | [`app/avatar_chat/`](app/avatar_chat/) | Android; its iOS and macOS builds are not verified yet — see [Known gaps](#known-gaps) |
| Something in another language | [`api/rest-api/`](api/rest-api/) | HTTP — curl scripts and Python, one per endpoint |
| A demo with no code at all | [`api/cli/`](api/cli/) | the `bithuman` command |
| Next.js, Gradio, Java, or a local conversation brain on a Mac | [`integrations/`](integrations/) | varies — one README each |

## See them running

Each of these was built from this repository and run on a real device with the published SDKs. The docs page for each has the clip, the commands and how to make it your own.

| | Example | Runs on | Docs page |
|---|---|---|---|
| <img src="https://docs.bithuman.ai/examples/web-embed/poster.webp" width="96" alt="Web embed"> | an iframe (no folder needed) | any browser | [Web](https://docs.bithuman.ai/platforms/web#complete-example) |
| <img src="https://docs.bithuman.ai/examples/cli-linux/poster.webp" width="96" alt="CLI render"> | [`api/cli/`](api/cli/) | macOS, Linux | [CLI](https://docs.bithuman.ai/platforms/cli#complete-example) |
| <img src="https://docs.bithuman.ai/examples/python-macos/poster.webp" width="96" alt="Python window"> | [`python/quickstart/`](python/quickstart/) | macOS, Linux | [Python](https://docs.bithuman.ai/platforms/python#complete-example) |
| <img src="https://docs.bithuman.ai/examples/ios-expression-2/poster.webp" width="96" alt="iPhone frame"> | [`swift/ios-expression2/`](swift/ios-expression2/) | iPhone, iPad | [iOS: Expression 2](https://docs.bithuman.ai/examples/ios-expression-2) |
| <img src="https://docs.bithuman.ai/examples/macos-expression-2/poster.webp" width="96" alt="Mac frame"> | [`swift/macos-expression2/`](swift/macos-expression2/) | Mac | [macOS](https://docs.bithuman.ai/examples/macos-expression-2) |
| <img src="https://docs.bithuman.ai/examples/android-expression-2/poster.webp" width="96" alt="Android, Expression 2"> | [`android/expression2-hello/`](android/expression2-hello/) | Android phone | [Android: Expression 2](https://docs.bithuman.ai/examples/android-expression-2) |
| <img src="https://docs.bithuman.ai/examples/android-essence-2/poster.webp" width="96" alt="Android, Essence 2"> | [`android/essence2-hello/`](android/essence2-hello/) | Android phone | [Android: Essence 2](https://docs.bithuman.ai/examples/android-essence-2) |

## Which model

| | **Essence 2** (`essence-2`) | **Expression 2** (`expression-2`) |
|---|---|---|
| Renders | a photoreal person from one portrait | any character (people, animals, cartoons) from one portrait |
| Output | the avatar's own resolution, up to 1920×1080, at 25 fps | 416×720 at 20 fps |
| Runs on | the cloud, macOS, Linux, iPhone, iPad, Android; the browser where the avatar has a browser build | the cloud, macOS, Linux, iPhone, iPad, Android, the browser |

Both are created once from a portrait (about 2 to 2.5 hours) and then run anywhere their SDK does. Not sure? Create with `"model": "auto"`. The full comparison is on [Models](https://docs.bithuman.ai/models).

`essence-1` and `expression-1` are the first generation and are not where to start. `expression-1` runs in the bitHuman cloud only.

## Your API secret

One API secret, from [www.bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys). From 12 October 2026 it needs the Creator plan or higher. Sessions bill active session time, talking or idle, to the second ([pricing](https://docs.bithuman.ai/pricing)). Export it before running anything:

```bash
export BITHUMAN_API_SECRET="<your API secret>"
```

`BITHUMAN_API_SECRET` is the one name every example reads — Python, CLI, REST, Flutter and Swift — except the LiveKit workers (`python/cloud-essence`, `python/quickstart/cloud-avatar.py`, `python/self-host`, `integrations/offline-mac`). They read `BITHUMAN_MASTER_SECRET` and refuse to start while `BITHUMAN_API_SECRET` is set, because `livekit-plugins-bithuman` 1.8.4 and older reads that name by itself and, for a cloud avatar, copies it into participant attributes that everyone in the room can read. (The legacy `swift/ios-avatar/` hands it to `bitHumanKit` as `config.apiKey`, a field that keeps its published name.)

Your API secret belongs in the environment or an untracked `.env`, never in a commit or on a command line. Every example ships a `.env.example` to copy from, and `.env` is gitignored.

**Never put a key in a build flag.** `--dart-define=BITHUMAN_API_SECRET=…` (Flutter) and a generated `BuildConfig` field (Android Gradle) each put the secret on the command line of every build step — readable by any local `ps`, and captured by build logs and crash reporters — and then compile it into the app as a plain string that `strings` will find in the shipped binary or APK. Those flags are for local development on your own machine.

**What a shipped app holds.** The Apple and Android SDKs authenticate with an API secret, so an app you distribute carries that secret on every device. Treat it as exposed: whoever extracts it can call the API as your account, including spending your credits and creating further secrets. Until device-scoped tokens are available:

- fetch the secret from your backend when the app starts; never compile it into the app or pass it as a build flag;
- create a separate secret for each app, so you can rotate one without touching the others;
- watch usage in your dashboard, and rotate the secret at once if usage looks wrong.

## Known gaps

Said plainly here so you do not find them halfway through a build:

- **`app/avatar_chat/` is verified on Android only.** Android builds from a clone: every engine it needs is a public Maven Central coordinate. Its iOS and macOS builds have not been re-verified; for a working Apple app today use [`swift/`](swift/), which builds against the public Swift package.
- **`swift/hello-voice-chat/`, `swift/macos-voice/` and `swift/ios-avatar/` are legacy.** They use `bitHumanKit` 2.4.0, the frozen first-generation Apple package. New apps start from `macos-expression2`, `ios-expression2` or `ios-essence2`.
- **There is no `web/` directory.** The web surface is not in this repository.
- **Every `swift/` example here builds.** The ones that had rotted against removed SDK APIs were deleted rather than left to mislead, and the `swift-build-packages` step of [`ci/run-local.sh`](ci/run-local.sh) holds no exemption list — so a package that stops building fails the step instead of joining a list.

## Keeping this honest

This file deliberately contains no version numbers — a number written down here is a number that goes stale in silence. Versions live in the directory that uses them, and [`scripts/check_published_versions.py`](scripts/check_published_versions.py) reads Maven Central, PyPI and the public tap before every merge ([`ci/run-local.sh`](ci/run-local.sh)), and fails when a file advertises a version the registry does not serve. See [AGENTS.md](AGENTS.md).

[`scripts/check_claims.py`](scripts/check_claims.py) refuses claims the product cannot back (a free plan for building apps, idle time billed as free, offline Macs or phones, the legacy Swift package presented as current), and [`scripts/check_links.py`](scripts/check_links.py) checks that every bitHuman link here resolves, anchors included. Both run before every merge ([`ci/run-local.sh`](ci/run-local.sh), see [`ci/README.md`](ci/README.md)), and each proves it can fail before it grades anything.

## Documentation

[docs.bithuman.ai](https://docs.bithuman.ai) · [Platforms](https://docs.bithuman.ai/platforms) · [Examples on the docs site](https://docs.bithuman.ai/examples) · [Pricing](https://docs.bithuman.ai/pricing)

<details>
<summary>This repository supersedes six older ones</summary>

They remain archived and read-only; nothing new lands in them.

- [bithuman-archive/bithuman-examples](https://github.com/bithuman-archive/bithuman-examples)
- bithuman-archive/bithuman-apps-legacy _(private; the June-2026 `bithuman-apps` — that name now belongs to the private repo holding bitHuman's own apps)_
- [bithuman-archive/public-livekit-ui-example](https://github.com/bithuman-archive/public-livekit-ui-example)
- bithuman-labs/local-deployment-examples _(private)_
- [bithuman-ai/sdk-examples-python](https://github.com/bithuman-ai/sdk-examples-python)
- [bithuman-product/bithuman-sdk-public](https://github.com/bithuman-product/bithuman-sdk-public)

</details>

## License

Apache 2.0 — see [LICENSE](LICENSE).
