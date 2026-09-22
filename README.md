# bitHuman examples

Runnable demos of the bitHuman avatar SDKs: audio in, a lip-synced face out.

## Start here

Find the row that matches what you are building and open that directory. Each one has its own README with a one-command run.

| You are building | Open | Where it runs |
|---|---|---|
| **Anything — first time** | [`python/quickstart/`](python/quickstart/) | your machine, CPU. One script; the sample avatar downloads itself. |
| A Python service or a LiveKit agent | [`python/`](python/) | your own CPU box, or the bitHuman cloud |
| A Mac, iPhone or iPad app | [`swift/`](swift/) | on-device — no server, no cloud GPU |
| An Android app | [`android/`](android/) | on-device, from Maven Central coordinates. Notes, not a project — the complete Kotlin app is printed in full at [Kotlin / Android — Hello, avatar](https://docs.bithuman.ai/examples/kotlin-android-hello). |
| One Flutter app for all three | [`app/avatar_chat/`](app/avatar_chat/) | Android builds from a clone; **Apple does not** — see [Known gaps](#known-gaps) |
| Something in another language | [`api/rest-api/`](api/rest-api/) | HTTP — curl scripts and Python, one per endpoint |
| A demo with no code at all | [`api/cli/`](api/cli/) | the `bithuman` command |
| Next.js, Gradio, Java, or a fully offline Mac | [`integrations/`](integrations/) | varies — one README each |

## Which model

**essence-2 and expression-2 are two different products, not two tiers of one.** Pick by where the face comes from.

| | **essence-2** | **expression-2** |
|---|---|---|
| The face comes from | a prebuilt `.imx` avatar file | any face image, chosen at runtime |
| Native output | 1920×1080 at 25 fps | 416×720 at 20 fps |
| Needs | any CPU | a GPU, or Apple Silicon M3+ |

**Choose essence-2** when you ship one character over and over and you want it full-frame: it is the 1080p product, and it runs on a plain CPU with no accelerator at all.

**Choose expression-2** when the face is not known until runtime — a user's own photo, a different character per session — and you have a GPU or an M3+ Mac.

Do not read the two frame rates as a ranking. An essence-2 frame carries **6.92× the pixels** of an expression-2 frame (2,073,600 vs 299,520), so 25 and 20 are measuring different things and neither model is "the fast one". Choose on the face, then on the hardware you have.

`essence-1` and `expression-1` are the first generation and are not where to start. `expression-1` is GPU-only and has no mobile build.

## Your API key

One key, from [www.bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys). Export it before running anything:

```bash
export BITHUMAN_API_SECRET="your_secret"
```

`BITHUMAN_API_SECRET` is the name to use in anything you write. Every Python, CLI, REST, Flutter and current Swift example reads it. One example still reads `BITHUMAN_API_KEY` instead — `swift/ios-avatar/` — so export both if you are working across all of them.

A key belongs in the environment or an untracked `.env`, never in a commit. Every example ships a `.env.example` to copy from, and `.env` is gitignored.

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
- bithuman-archive/bithuman-apps _(private)_
- [bithuman-archive/public-livekit-ui-example](https://github.com/bithuman-archive/public-livekit-ui-example)
- bithuman-labs/local-deployment-examples _(private)_
- [bithuman-ai/sdk-examples-python](https://github.com/bithuman-ai/sdk-examples-python)
- [bithuman-product/bithuman-sdk-public](https://github.com/bithuman-product/bithuman-sdk-public)

</details>

## License

Apache 2.0 — see [LICENSE](LICENSE).
