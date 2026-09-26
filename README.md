# bitHuman examples

Runnable demos of the bitHuman avatar SDKs: audio in, a lip-synced face out.

## Start here

Find the row that matches what you are building and open that directory. Each one has its own README with a one-command run.

| You are building | Open | Where it runs |
|---|---|---|
| **Anything — first time** | [`python/quickstart/`](python/quickstart/) | your machine, CPU. One script; the sample avatar downloads itself. |
| **Talk to an avatar on my machine** | [`api/cli/`](api/cli/) — one command, `bithuman run wise-pup` · [`python/self-host/`](python/self-host/) — your own agent code | your machine: your LiveKit server, OpenAI Realtime on your key, the avatar rendered locally |
| A Python service or a LiveKit agent | [`python/`](python/) | your own CPU box, or the bitHuman cloud |
| A Mac, iPhone or iPad app | [`swift/`](swift/) | on-device — no server, no cloud GPU |
| An Android app | [`android/`](android/) | on-device, from Maven Central coordinates. Notes, not a project — the complete Kotlin app is printed in full at [Kotlin / Android — Hello, avatar](https://docs.bithuman.ai/examples/kotlin-android-hello). |
| One Flutter app for all three | [`app/avatar_chat/`](app/avatar_chat/) | Android builds from a clone; **Apple does not** — see [Known gaps](#known-gaps) |
| Something in another language | [`api/rest-api/`](api/rest-api/) | HTTP — curl scripts and Python, one per endpoint |
| A demo with no code at all | [`api/cli/`](api/cli/) | the `bithuman` command |
| Next.js, Gradio, Java, or a fully offline Mac | [`integrations/`](integrations/) | varies — one README each |

## See them running

Each of these was built from this repository and run on a real device with the published SDKs. The docs page for each has the clip, the commands and how to make it your own.

| | Example | Runs on | Docs page |
|---|---|---|---|
| <img src="https://docs.bithuman.ai/examples/web/hero.webp" width="96" alt="Web embed"> | an iframe (no folder needed) | any browser | [Web](https://docs.bithuman.ai/examples/web) |
| <img src="https://docs.bithuman.ai/examples/cli/hero.webp" width="96" alt="CLI render"> | [`api/cli/`](api/cli/) | macOS, Linux | [CLI](https://docs.bithuman.ai/examples/cli) |
| <img src="https://docs.bithuman.ai/examples/python/hero.webp" width="96" alt="Python window"> | [`python/quickstart/`](python/quickstart/) | macOS, Linux | [Python](https://docs.bithuman.ai/examples/python) |
| <img src="https://docs.bithuman.ai/examples/ios/hero.webp" width="96" alt="iPhone frame"> | [`swift/ios-expression2/`](swift/ios-expression2/) | iPhone, iPad | [iOS: Expression 2](https://docs.bithuman.ai/examples/swift-ios-expression2) |
| <img src="https://docs.bithuman.ai/examples/macos/hero.webp" width="96" alt="Mac frame"> | [`swift/macos-expression2/`](swift/macos-expression2/) | Mac | [macOS](https://docs.bithuman.ai/examples/macos-expression2) |
| <img src="https://docs.bithuman.ai/examples/android/expression2.webp" width="96" alt="Android, Expression 2"> | [`android/expression2-hello/`](android/expression2-hello/) | Android phone | [Android: Expression 2](https://docs.bithuman.ai/examples/android-expression2) |
| <img src="https://docs.bithuman.ai/examples/android/essence2.webp" width="96" alt="Android, Essence 2"> | [`android/essence2-hello/`](android/essence2-hello/) | Android phone | [Android: Essence 2](https://docs.bithuman.ai/examples/android-essence2) |

## Which model

| | **Essence 2** (`essence-2`) | **Expression 2** (`expression-2`) |
|---|---|---|
| Renders | a photoreal person from one portrait | any character (people, animals, cartoons) from one portrait |
| Output | the avatar's own resolution, up to 1920×1080, at 25 fps | 416×720 at 20 fps |
| Runs on | the cloud, macOS, Linux, iPhone, iPad, Android; the browser where the avatar has a browser build | the cloud, macOS, Linux, iPhone, iPad, Android, the browser |

Both are created once from a portrait (about 2 to 2.5 hours) and then run anywhere their SDK does. Not sure? Create with `"model": "auto"`. The full comparison is on [Models](https://docs.bithuman.ai/concepts/models).

`essence-1` and `expression-1` are the first generation and are not where to start. `expression-1` is GPU-only and has no mobile build.

## Your API secret

One API secret, from [www.bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys). Export it before running anything:

```bash
export BITHUMAN_API_SECRET="<your API secret>"
```

`BITHUMAN_API_SECRET` is the one name every example reads — Python, CLI, REST, Flutter and Swift — except the LiveKit workers (`python/cloud-essence`, `python/quickstart/cloud-avatar.py`, `python/self-host`, `integrations/offline-mac`). They read `BITHUMAN_MASTER_SECRET` and refuse to start while `BITHUMAN_API_SECRET` is set, because `livekit-plugins-bithuman` 1.8.4 and older reads that name by itself and, for a cloud avatar, copies it into participant attributes that everyone in the room can read. (`swift/ios-avatar/` hands it to `bitHumanKit` as `config.apiKey`, a field that keeps its published name.)

Your API secret belongs in the environment or an untracked `.env`, never in a commit or on a command line. Every example ships a `.env.example` to copy from, and `.env` is gitignored.

**Never put a key in a build flag.** `--dart-define=BITHUMAN_API_SECRET=…` (Flutter) and a generated `BuildConfig` field (Android Gradle) each put the secret on the command line of every build step — readable by any local `ps`, and captured by build logs and crash reporters — and then compile it into the app as a plain string that `strings` will find in the shipped binary or APK. Those flags are for local development on your own machine. **For anything you distribute, ship sign-in instead**, so the app obtains a short-lived token at runtime and the long-lived secret never leaves your machine.

## Known gaps

Said plainly here so you do not find them halfway through a build:

- **`app/avatar_chat/` does not build for iOS or macOS from a clone.** The Flutter plugin's Apple half stages its engines from a private repository, and no published engine asset exists that a clone could use instead; the build stops at `cannot find 'Expression2Engine' in scope`. Android *does* build — every engine it needs is a public Maven Central coordinate resolved anonymously. For a working Apple app today use [`swift/`](swift/), which builds against the public Swift package and ships both engines.
- **There is no `web/` directory.** The web surface is not in this repository.
- **Every `swift/` example here builds.** The ones that had rotted against removed SDK APIs were deleted rather than left to mislead, and [`.github/workflows/swift-examples.yml`](.github/workflows/swift-examples.yml) now holds an empty exemption list — so a package that stops building fails the job instead of joining a list.

## Keeping this honest

This file deliberately contains no version numbers — a number written down here is a number that goes stale in silence. Versions live in the directory that uses them, and [`scripts/check_published_versions.py`](scripts/check_published_versions.py) reads Maven Central, PyPI and the public tap on every pull request *and once a day*, and fails when a file advertises a version the registry does not serve. See [AGENTS.md](AGENTS.md).

## Documentation

[docs.bithuman.ai](https://docs.bithuman.ai)

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
