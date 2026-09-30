# Python SDK Examples

All Python examples use the `bithuman` package from PyPI (`pip install "bithuman[expression-2]"`). Pick the one that matches where you want the avatar to run.

## Quick decision

| I want to... | Example | What I need |
|---|---|---|
| Fastest cloud demo (no GPU) | [cloud-essence/](cloud-essence/) | API secret + agent code (e.g. the public sample `A23WJF0199`) |
| A voice agent on my own machine: my own LiveKit server, OpenAI Realtime, the avatar rendered here | [self-host/](self-host/) | API secret + OpenAI key; Python 3.10–3.14 |
| Talk to an avatar in a terminal window, no LiveKit | [quickstart/conversation.py](quickstart/) | API secret + OpenAI key |
| Other ways to run it on your own servers (Mac, Linux or Windows, no GPU needed) | [Your servers ↗](https://docs.bithuman.ai/deploy/self-hosted) | varies |
| A Mac, iPhone or iPad app | [Swift examples ↗](../swift/) | Apple silicon; an API secret |

## Learning path

If you're new to bitHuman, follow this order:

1. **Start with** [cloud-essence/](cloud-essence/) — no model files, no GPU, just an API secret. Gives you a working avatar in minutes.
2. **Try local rendering** with [quickstart/](quickstart/) — the sample avatar downloads itself and renders on your machine.
3. **Talk to it** — [self-host/](self-host/) runs a voice agent (OpenAI Realtime) on your own LiveKit server, with the avatar rendered in the same process.

## Install

```bash
pip install "bithuman[expression-2]" --upgrade
```

The `[expression-2]` extra is what opens Expression 2 avatars such as the
`wise-pup` sample; without it `bithuman.open()` stops with "this avatar needs
one more package". Essence 2 avatars (`sofia-ramirez`) need nothing extra, but
installing the extra always is the simplest rule.

For the LiveKit agent examples (`self-host/`, `cloud-essence/`, `quickstart/cloud-avatar.py`):

```bash
pip install "bithuman[expression-2]" "livekit-agents[openai,silero]>=1.8.2,<1.9" \
            "livekit-plugins-bithuman>=1.8.2,<1.9" pillow python-dotenv
```

Each example's `requirements.txt` already lists exactly this, so
`pip install -r requirements.txt` in its folder is enough.

Pre-built wheels cover Python 3.10–3.14 on **Linux x86_64, Linux aarch64,
Apple silicon macOS 14+ and Windows 11 x86_64** (no WSL needed; see
[Windows](https://docs.bithuman.ai/platforms/windows)). Intel Macs and Windows
on Arm have no wheel yet; `pip install` there stops with a message naming your
platform rather than installing something older.

The window examples in `quickstart/` (`microphone.py`, `conversation.py`,
`quickstart.py`) play sound through `sounddevice`; on Linux that needs the
PortAudio library: `sudo apt install libportaudio2`.

## Your API secret in a LiveKit worker

Every example here that is a LiveKit worker reads your API secret as
**`BITHUMAN_MASTER_SECRET`**, never `BITHUMAN_API_SECRET`, and refuses to start
if `BITHUMAN_API_SECRET` is set. The reason, in plain terms:

- `livekit-plugins-bithuman` (1.8.4 and older) reads `BITHUMAN_API_SECRET` on
  its own and, for a cloud avatar, puts it in the avatar participant's
  attributes. Everyone who joins the room can read those attributes, so the
  secret would reach every browser in the room.
- So the worker keeps the real secret under another name and uses it for one
  thing: asking bitHuman for a **one-hour token that can only start this
  agent's avatar in this room** (`POST /v1/runtime-tokens/mint`). Only that
  token is handed to the plugin, so the room only ever sees a short-lived
  token scoped to one agent and one room, never your secret.
- When the avatar renders inside your own process (`self-host/`), the secret
  is passed to the plugin directly and never leaves the process.

The scripts that are not LiveKit workers (`local-avatar.py`, `quickstart.py`,
`microphone.py`, `conversation.py`) use `BITHUMAN_API_SECRET` as usual.

## Example structure

Every example ships:
- **README.md** — prerequisites, one-command run, config table
- **.env.example** — copy to `.env` and fill in your keys
- **requirements.txt** — Python dependencies

Some also include:
- **agent.py** — LiveKit agent entry point
- **docker-compose.yml** — full stack (LiveKit + agent + web UI), `cloud-essence/` only

## Two models

These examples all use the second-generation models (`essence-2`,
`expression-2`). The rates that used to be copied into this table were the
**first**-generation ones, which are half — so the pricing page is linked
instead of duplicated, because it is the single source for every billing number
and this copy went stale.

| | **Essence 2** | **Expression 2** |
|---|---|---|
| Avatar source | an avatar file from [bithuman.ai](https://www.bithuman.ai/#explore) | an avatar file, or any face image |
| Showcase avatar to try | `sofia-ramirez` | `wise-pup` |
| Pricing | [docs.bithuman.ai/pricing ↗](https://docs.bithuman.ai/pricing) | same page |

## Documentation

- [Python quickstart](https://docs.bithuman.ai/platforms/python)
- [Python SDK](https://docs.bithuman.ai/platforms/python)
- [Self-hosting](https://docs.bithuman.ai/deploy/self-hosted)
- [LiveKit plugin](https://docs.bithuman.ai/platforms/livekit)
