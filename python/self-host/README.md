# Talk to an avatar on your machine — your own LiveKit server

A voice agent with a face, where everything except the voice model runs on your computer:

- **LiveKit** is the stock `livekit-server --dev`, on your machine.
- **OpenAI Realtime** (your own `OPENAI_API_KEY`) listens, thinks and speaks.
- **The bitHuman avatar is rendered inside `agent.py`**, on your CPU — no GPU needed.
- **One switch picks the model:** `BITHUMAN_AVATAR=wise-pup` is Expression 2, `BITHUMAN_AVATAR=sofia-ramirez` is Essence 2.
- **Two secrets, both in `.env`:** your API secret as `BITHUMAN_MASTER_SECRET` (both models refuse to render without it) and `OPENAI_API_KEY`. A LiveKit worker never gets `BITHUMAN_API_SECRET`: `livekit-plugins-bithuman` 1.8.4 and older reads that name by itself and, for a cloud avatar, copies it into the room. `agent.py` passes the secret to the plugin explicitly and refuses to start while `BITHUMAN_API_SECRET` is set.

No Docker and no web app to build: `agent.py` serves a small page on `localhost` that joins your local room.
Rather not write code? `bithuman run wise-pup` does the same in one command — see [api/cli/](../../api/cli/).

## Run it

Prerequisites: Python 3.10–3.14, and `livekit-server` 1.9.12 or newer (`livekit-server --version`; on macOS `brew upgrade livekit`). Older servers make the browser drop and rejoin the room every 15 s.

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
cp .env.example .env                                      # then fill BITHUMAN_MASTER_SECRET and OPENAI_API_KEY

# 4. Run, in two terminals
livekit-server --dev --config livekit.yaml                # terminal 1: ws://localhost:7880, keys devkey / secret
python agent.py dev                                       # terminal 2: prints "Open in Chrome: http://localhost:8089/?..."
```

Open the printed link in Chrome, click **Start** and allow the microphone. The avatar appears a few seconds
later; say "hi" and it answers, lip-synced. Talk over it and it stops to listen.

<p>
<img src="screenshots/expression-2-wise-pup.jpg" alt="wise-pup (Expression 2) mid-sentence" height="280">
<img src="screenshots/essence-2-sofia-ramirez.jpg" alt="sofia-ramirez (Essence 2) mid-sentence" height="280">
</p>

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
| `BITHUMAN_REALTIME_MODEL` | `gpt-realtime-2.1-mini` | The OpenAI Realtime model. |
| `BITHUMAN_VOICE` | `coral` | Any OpenAI Realtime voice. |
| `BITHUMAN_INSTRUCTIONS` | `You are a friendly assistant. Keep answers short.` | The agent's system prompt. |
| `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | `ws://localhost:7880`, `devkey`, `secret` | Your LiveKit server. The page on port 8089 is served only for a `localhost` URL. |

Want a different speech-to-text, LLM or text-to-speech? `agent.py` is a plain
[LiveKit Agents](https://docs.livekit.io/agents/) program: replace the `RealtimeModel` with any
`stt=`, `llm=`, `tts=` plugins; the avatar lines stay the same.

## What you pay

bitHuman credits for the seconds the avatar is talking — an idle avatar is not billed. OpenAI bills your
OpenAI key directly for the Realtime session.

## How it works

```
Chrome (localhost:8089) <—>  livekit-server --dev  <—>  agent.py
                                                       ├─ OpenAI Realtime: your voice in, the reply's voice out
                                                       └─ bitHuman AvatarSession(model_path=…): renders the face
                                                          from the reply's voice and publishes video + audio
```

`agent.py` is about 90 lines: it resolves `BITHUMAN_AVATAR` to a local file, starts an `AgentSession` with
`openai.realtime.RealtimeModel`, and starts `bithuman.AvatarSession(model_path=…)` in the same process
(local mode — the API secret never leaves the process). The avatar renders on the CPU; on a machine with an
NVIDIA GPU, LiveKit's WebRTC library may use it to encode the video, which is expected.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `This example needs Python 3.10 to 3.14` | a Python that `bithuman` ships no wheel for | Make the venv with Python 3.10–3.14 |
| `No module named 'PIL'` | The plugin imports Pillow without declaring it | `pip install -r requirements.txt` (it lists `pillow`) |
| `BITHUMAN_API_SECRET is not set` | `.env` missing or not filled | `cp .env.example .env` and fill both secrets |
| The avatar never appears | No or invalid `BITHUMAN_API_SECRET` — both models refuse to render without it | Set a valid secret in `.env`, restart `agent.py` |
| `Address already in use` for port 8089 | another `agent.py` is still running | stop it, then start again |
| The page says it could not connect | `livekit-server --dev` is not running | start it (terminal 1), then click Start again |
| Nothing happens after joining | `livekit-server --dev` is not running, or `agent.py` is not | Start both, terminal 1 first |
| The video stalls for 1–2 s every 15 s, or a LiveKit Meet tile goes black | `livekit-server` older than 1.9.12: the browser leaves and rejoins the room every 15 s | `brew upgrade livekit` (macOS) or rerun `curl -sSL https://get.livekit.io \| bash`, then restart `livekit-server --dev` |
| `livekit-server` exits: `listen udp [2600:…]:7882: bind: cannot assign requested address` | Plain `--dev` opens WebRTC on every interface address; a temporary IPv6 address vanished at start-up | Start it with `--config livekit.yaml` (in this folder: WebRTC on IPv4 only) |
| Another device on your network cannot join | `--dev` listens on localhost only | `livekit-server --dev --bind 0.0.0.0 --node-ip <your LAN IP>`; browsers also need HTTPS for the mic off `localhost` |
