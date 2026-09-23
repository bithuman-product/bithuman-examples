# bitHuman CLI

The `bithuman` command runs a talking avatar on your machine and renders
lip-synced video — no code.

## Talk to an avatar on your machine

One command stands up the whole conversation on your computer: a local
LiveKit server, a voice agent on OpenAI Realtime (your own key), and the
avatar rendered locally — no GPU needed. The avatar name picks the model.

```bash
# 1. Install (both bring livekit-server)
brew install bithuman-product/bithuman/bithuman-cli      # macOS, Apple Silicon
curl -fsSL https://install.bithuman.ai | sh               # Linux x86_64 / aarch64

# 2. Keys — never on the command line
bithuman login                                            # opens the browser; stores your API secret
export OPENAI_API_KEY="<your OpenAI key>"                 # the conversation runs on your OpenAI key

# 3. Talk
bithuman run wise-pup                                     # Expression 2
bithuman run sofia-ramirez                                # Essence 2
```

The first run downloads the avatar and sets up the voice agent once (a
minute or two). The terminal prints `http://127.0.0.1:8088/<CODE>` and your
browser opens it: allow the microphone, say "hi", and the avatar answers,
lip-synced; talk over it and it stops to listen. Ctrl-C ends the session.

| You pass | You get |
|---|---|
| `wise-pup` | Expression 2 (a sample avatar) |
| `sofia-ramirez` | Essence 2 (a sample avatar) |
| a path to an avatar file | that avatar, rendered here |

To render your own agent here, download it first — `bithuman pull <AGENT_CODE> --model expression-2`
(or `essence-2`) prints the file — then `bithuman run <that file>`.

Settings, all from the environment:

| Variable | Default | What it does |
|---|---|---|
| `OPENAI_API_KEY` | — | Your OpenAI key. Without it, signed in, the voice runs on your bitHuman account instead. |
| `BITHUMAN_REALTIME_MODEL` | `gpt-realtime-mini` | The OpenAI Realtime model |
| `BITHUMAN_VOICE` | `alloy` | Any OpenAI Realtime voice |
| `BITHUMAN_INSTRUCTIONS` | a short assistant prompt | The agent's system prompt |

Before you start: the voice agent needs **Python 3.11 or newer** on the
machine (macOS: `brew install python@3.13`; Ubuntu: `sudo apt install
python3-venv`), and `run` needs **livekit-server 1.13 or newer** — an older
Homebrew install shows `Agent dispatch failed` in the page; `brew upgrade
livekit` fixes it.

Want your own agent code instead of the built-in voice agent? See
[python/self-host](../../python/self-host/): the same conversation as a
70-line LiveKit Agents program on your own LiveKit server.

## Install

The CLI is one self-contained binary on a Homebrew tap and as a prebuilt
download for every supported platform (see the commands above). Prebuilt
binaries are also attached to each
[release](https://github.com/bithuman-product/homebrew-bithuman/releases).
The CLI is not on PyPI: `pip install bithuman` installs the Python library.

Every command that renders needs your API secret — `bithuman login`, or
`export BITHUMAN_API_SECRET` from
[www.bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys).
Check the setup with `bithuman doctor` and the account with `bithuman account`.

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
| `bithuman render <avatar> speech.wav -o demo.mp4` | Offline render: audio in, MP4 out, on macOS or Linux. `<avatar>` is an agent code, a showcase name, or a file. |
| `bithuman open <avatar>` | What the avatar is, and whether it runs on this machine. |
| `bithuman account` | Identity, plan and credit balance. |
| `bithuman mcp` | Built-in MCP server over stdio (JSON-RPC), for MCP clients. |
| `bithuman completion bash\|zsh\|fish\|elvish\|powershell` | Shell completions. |

### Run a live avatar — see [above](#talk-to-an-avatar-on-your-machine) and [mac-app.sh](mac-app.sh)

### Render a video offline — see [render-video.sh](render-video.sh)

```bash
bithuman render model.imx speech.wav -o demo.mp4
```

`render` works on macOS (Apple silicon) and Linux. It needs `ffmpeg` on your `PATH`.

### Check your API secret

```bash
bithuman account        # exit 0 when your API secret works; prints plan and balance
```

---

## On-device voice (no cloud)

`BITHUMAN_LOCAL=1 bithuman run <avatar>` swaps OpenAI for an on-device
voice agent (whisper.cpp + llama.cpp + Supertonic). Its setup and hardware
notes are on [docs.bithuman.ai/sdk/cli/local-mode](https://docs.bithuman.ai/sdk/cli/local-mode).

---

## REST API via curl

For API calls from the terminal without Python, see
[rest-api.sh](rest-api.sh) or the full curl examples in
[../rest-api/curl/](../rest-api/curl/).

---

## Scripts in this directory

| Script | Description |
|--------|-------------|
| [render-video.sh](render-video.sh) | Render a lip-synced MP4 from `.imx` + audio using `bithuman render` |
| [mac-app.sh](mac-app.sh) | `./mac-app.sh install` (runs `brew install`) then `./mac-app.sh run <model.imx>`. ★There is no `bithuman install` subcommand — installing is Homebrew's job, not the CLI's. |
| [rest-api.sh](rest-api.sh) | Quickstart: validate API secret + make an agent speak via curl |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BITHUMAN_API_SECRET` | Yes | Your API secret from [www.bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys) (BITHUMAN_API_KEY is still read as a deprecated alias) |
| `OPENAI_API_KEY` | No | Your OpenAI key for the `bithuman run` voice agent (signed in without it, the voice runs on your account) |
| `BITHUMAN_REALTIME_MODEL`, `BITHUMAN_VOICE`, `BITHUMAN_INSTRUCTIONS` | No | Voice agent settings ([table above](#talk-to-an-avatar-on-your-machine)) |
| `BITHUMAN_LOCAL` | No | `=1` uses the on-device voice agent |

## Documentation

- [CLI](https://docs.bithuman.ai/sdk/cli) and [CLI reference](https://docs.bithuman.ai/sdk/cli/reference)
- [Talk to an avatar on your machine](https://docs.bithuman.ai/guides/local-voice-avatar)
- [REST API](https://docs.bithuman.ai/api)
- [Full documentation](https://docs.bithuman.ai)
