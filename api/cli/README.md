# bitHuman CLI Tools

Command-line tools for running a live avatar locally and rendering
lip-synced video offline — no code.

## Install

The `bithuman` command is a single self-contained binary published on a
Homebrew tap and as a prebuilt download for every supported platform.
Runnable examples are in this directory. For the Python library
(`from bithuman import AsyncBithuman`) see the [Python examples](../../python/).

```bash
# macOS — Homebrew (recommended; pulls native deps).
brew install bithuman-product/bithuman/bithuman-cli

# macOS / Linux — universal one-liner.
curl -fsSL https://raw.githubusercontent.com/bithuman-product/homebrew-bithuman/main/install.sh | sh
```

Prebuilt binaries are also attached to each
[release](https://github.com/bithuman-product/homebrew-bithuman/releases).
The CLI is not distributed on PyPI: `pip install bithuman` installs the
Python library only.

All commands need a bitHuman API secret. Get yours at
[www.bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys).

```bash
export BITHUMAN_API_SECRET="your_secret_here"
bithuman doctor      # verify host setup + API secret presence
```

---

## Commands

Run `bithuman <command> --help` for the full flag list. Read from the tap's
own [`llms.txt`](https://raw.githubusercontent.com/bithuman-product/homebrew-bithuman/main/llms.txt)
on 2026-09-22 — this page used to claim a six-command surface and omitted five,
including `login`, which is the command a first-run developer wants most.

| Command | Description |
|---------|-------------|
| `bithuman login` | Sign in. The alternative to exporting a secret by hand. |
| `bithuman doctor` | Host capability check (arch, OS, RAM, disk, API secret, brain availability). `--json` exits 0 iff `.ready` is true. |
| `bithuman list` | Browse showcase avatars — manifest + local cache state. |
| `bithuman pull <slug>` | Download a showcase avatar by slug into the local cache; prints the cached `.imx` path. |
| `bithuman run [<model.imx>]` | Live avatar — self-contained LiveKit pool + embedded server. Prints a landing-page URL to open in a browser. |
| `bithuman render <model.imx> --audio speech.wav --output demo.mp4` | Offline batch render an MP4 from a model + WAV, on macOS or Linux. |
| `bithuman info <model.imx>` | Print metadata for an `.imx` model file. |
| `bithuman whoami` / `bithuman account` | Identity, plan and credit balance. |
| `bithuman mcp` | Built-in MCP server over stdio (JSON-RPC), for MCP clients. |
| `bithuman completion bash\|zsh\|fish\|elvish\|powershell` | Shell completions. |

### Run a live avatar — see [live-stream.sh](live-stream.sh) and [mac-app.sh](mac-app.sh)

```bash
bithuman run model.imx
# Open the printed http://127.0.0.1:8088/<CODE> URL in your browser,
# grant mic permission, and talk.
```

### Render a video offline — see [render-video.sh](render-video.sh)

```bash
bithuman render model.imx --audio speech.wav --output demo.mp4
```

`render` works on macOS (Apple silicon) and Linux. It needs `ffmpeg` on your `PATH`.

### Validate your API secret

There is no `bithuman validate` subcommand — use the REST endpoint:

```bash
curl -s -X POST https://api.bithuman.ai/v1/validate \
  -H "api-secret: $BITHUMAN_API_SECRET" | python3 -m json.tool
```

---

## Brain selection

`bithuman run` connects the avatar to a *brain* (the LLM + TTS that
generates speech). Pick one of two paths via env vars:

| Brain | How to enable | Notes |
|-------|---------------|-------|
| Cloud (default) | `export OPENAI_API_KEY=sk-...` | OpenAI Realtime; instant, no downloads. |
| On-device | `export BITHUMAN_LOCAL=1` | whisper.cpp + llama.cpp + Supertonic + Silero. Needs `pip install 'livekit-agents[silero]~=1.5' supertonic pywhispercpp llama-cpp-python soxr`. ~5 GB first-run download, then offline. |

```bash
export OPENAI_API_KEY=sk-...     # cloud (default)
bithuman run model.imx

# or, fully on-device. (NOT `bithuman-cli[local]`: that coordinate is not on
# PyPI — it 404s. NOT `bithuman[local]` either: there is no such extra — pip
# warns and exits 0 having installed none of it.)
pip install 'livekit-agents[silero]~=1.5' supertonic pywhispercpp llama-cpp-python soxr
BITHUMAN_LOCAL=1 bithuman run model.imx
```

Hardware requirements for the on-device brain: macOS Apple Silicon
M3+ or Linux x86_64 / aarch64.

---

## REST API via curl

For API calls from the terminal without Python, see
[rest-api.sh](rest-api.sh) or the full curl examples in
[../rest-api/curl/](../rest-api/curl/).

```bash
curl -s -X POST https://api.bithuman.ai/v1/validate \
  -H "Content-Type: application/json" \
  -H "api-secret: $BITHUMAN_API_SECRET" | python3 -m json.tool
```

---

## Scripts in this directory

| Script | Description |
|--------|-------------|
| [render-video.sh](render-video.sh) | Render a lip-synced MP4 from `.imx` + audio using `bithuman render` |
| [live-stream.sh](live-stream.sh) | Start the live avatar server using `bithuman run` |
| [mac-app.sh](mac-app.sh) | `./mac-app.sh install` (runs `brew install`) then `./mac-app.sh run <model.imx>`. ★There is no `bithuman install` subcommand — installing is Homebrew's job, not the CLI's. |
| [rest-api.sh](rest-api.sh) | Quickstart: validate API secret + make an agent speak via curl |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BITHUMAN_API_SECRET` | Yes | Your API secret from [www.bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys) (BITHUMAN_API_KEY is still read as a deprecated alias) |
| `OPENAI_API_KEY` | One of | Cloud brain for `bithuman run` (default path) |
| `BITHUMAN_LOCAL` | One of | `=1` flips `bithuman run` to the on-device brain |

## Documentation

- [CLI reference](https://docs.bithuman.ai/getting-started/cli)
- [REST API reference](https://docs.bithuman.ai/api-reference/overview)
- [Full documentation](https://docs.bithuman.ai)
