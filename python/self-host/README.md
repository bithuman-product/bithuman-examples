# Talk to an avatar on your machine — your own LiveKit server

A voice agent with a face, where everything except the voice model runs on your computer:

- **LiveKit** is the stock `livekit-server --dev`, on your machine.
- **OpenAI Realtime** (your own `OPENAI_API_KEY`) listens, thinks and speaks.
- **The bitHuman avatar is rendered inside `agent.py`**, on your CPU — no GPU needed.
- **One switch picks the model:** `BITHUMAN_AVATAR=wise-pup` is Expression 2, `BITHUMAN_AVATAR=sofia-ramirez` is Essence 2.
- **Two secrets, both in `.env`:** `BITHUMAN_API_SECRET` (both models refuse to render without it) and `OPENAI_API_KEY`.

No Docker and no web app to build: `agent.py` prints a LiveKit Meet link that joins your local room.
Rather not write code? `bithuman run wise-pup` does the same in one command — see [api/cli/](../../api/cli/).
On a Mac, use that CLI for Expression 2: it renders on the Neural Engine at the full 20 fps, while this
example's Expression 2 plays below that on a Mac today.

## Run it

Prerequisites: Python 3.11, 3.12 or 3.13, and `livekit-server`.

```sh
# 1. LiveKit server + Python
brew install livekit python@3.13                          # macOS
curl -sSL https://get.livekit.io | bash                   # Linux; on Ubuntu 24.04 also: sudo apt install python3.12-venv

# 2. The example
git clone https://github.com/bithuman-product/bithuman-examples
cd bithuman-examples/python/self-host
python3.13 -m venv .venv && . .venv/bin/activate          # Ubuntu 24.04: python3.12
pip install -r requirements.txt

# 3. Keys — in .env, never on the command line
cp .env.example .env                                      # then fill BITHUMAN_API_SECRET and OPENAI_API_KEY

# 4. Run, in two terminals
livekit-server --dev                                      # terminal 1: ws://localhost:7880, keys devkey / secret
python agent.py dev                                       # terminal 2: prints "Open in Chrome: https://meet.livekit.io/custom?..."
```

Open the printed link in Chrome. LiveKit Meet asks for the microphone and, because the page connects to
`localhost`, for local-network access — allow both, then join. The avatar appears a few seconds later; say
"hi" and it answers, lip-synced. Talk over it and it stops to listen.

The first run downloads the avatar once (about 150–200 MB) into `~/.cache/bithuman/examples/`.

## Pick the avatar

`BITHUMAN_AVATAR` in `.env` takes any of these; restart `python agent.py dev` after changing it.

| Value | You get |
|---|---|
| `wise-pup` | Expression 2 (a showcase avatar) |
| `sofia-ramirez` | Essence 2 (a showcase avatar) |
| your agent code, e.g. `A24EKJ8433` | your own avatar, downloaded with your API secret |
| a path, e.g. `./my-avatar.imx` | an avatar file you already have |

The model comes from the avatar: there is no separate model setting.

## Configuration

Everything is read from `.env` ([.env.example](.env.example)):

| Variable | Default | What it does |
|---|---|---|
| `BITHUMAN_API_SECRET` | — (required) | Your bitHuman API secret. Rendering is metered on it. |
| `OPENAI_API_KEY` | — (required) | Your OpenAI key, for OpenAI Realtime. |
| `BITHUMAN_AVATAR` | `wise-pup` | Which avatar (table above). |
| `BITHUMAN_REALTIME_MODEL` | `gpt-realtime-mini` | The OpenAI Realtime model. |
| `BITHUMAN_VOICE` | `coral` | Any OpenAI Realtime voice. |
| `BITHUMAN_INSTRUCTIONS` | `You are a friendly assistant. Keep answers short.` | The agent's system prompt. |
| `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | `ws://localhost:7880`, `devkey`, `secret` | Your LiveKit server. The join link is printed only for a `localhost` URL. |

Want a different speech-to-text, LLM or text-to-speech? `agent.py` is a plain
[LiveKit Agents](https://docs.livekit.io/agents/) program: replace the `RealtimeModel` with any
`stt=`, `llm=`, `tts=` plugins; the avatar lines stay the same.

## What you pay

bitHuman credits for the seconds the avatar is talking — an idle avatar is not billed. OpenAI bills your
OpenAI key directly for the Realtime session.

## How it works

```
Chrome (LiveKit Meet)  <—>  livekit-server --dev  <—>  agent.py
                                                       ├─ OpenAI Realtime: your voice in, the reply's voice out
                                                       └─ bitHuman AvatarSession(model_path=…): renders the face
                                                          from the reply's voice and publishes video + audio
```

`agent.py` is about 70 lines: it resolves `BITHUMAN_AVATAR` to a local file, starts an `AgentSession` with
`openai.realtime.RealtimeModel`, and starts `bithuman.AvatarSession(model_path=…)` in the same process
(local mode — the API secret never leaves the process). The avatar renders on the CPU; on a machine with an
NVIDIA GPU, LiveKit's WebRTC library may use it to encode the video, which is expected.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `This example needs Python 3.11, 3.12 or 3.13` | `livekit-plugins-bithuman` installs without `bithuman` on 3.10 and 3.14 | Make the venv with Python 3.11–3.13 |
| `No module named 'PIL'` | The plugin imports Pillow without declaring it | `pip install -r requirements.txt` (it lists `pillow`) |
| `BITHUMAN_API_SECRET is not set` | `.env` missing or not filled | `cp .env.example .env` and fill both secrets |
| The avatar never appears | No or invalid `BITHUMAN_API_SECRET` — both models refuse to render without it | Set a valid secret in `.env`, restart `agent.py` |
| Meet says it cannot connect | Chrome blocked local-network access for meet.livekit.io | Site settings → allow local network access, reload |
| Nothing happens after joining | `livekit-server --dev` is not running, or `agent.py` is not | Start both, terminal 1 first |
| Another device on your network cannot join | `--dev` listens on localhost only | `livekit-server --dev --bind 0.0.0.0 --node-ip <your LAN IP>`; browsers also need HTTPS for the mic off `localhost` |
