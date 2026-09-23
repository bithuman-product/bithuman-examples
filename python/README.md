# Python SDK Examples

All Python examples use `pip install bithuman`. Pick the one that matches where you want the avatar to run.

## Quick decision

| I want to... | Example | What I need |
|---|---|---|
| Fastest cloud demo (no GPU) | [cloud-essence/](cloud-essence/) | API secret + agent ID |
| A voice agent on my own machine: my own LiveKit server, OpenAI Realtime, the avatar rendered here | [self-host/](self-host/) | API secret + OpenAI key; Python 3.11–3.13 |
| Talk to an avatar in a terminal window, no LiveKit | [quickstart/conversation.py](quickstart/) | API secret + OpenAI key |
| Other self-hosting options (containers, GPU servers) | [Self-hosting guide ↗](https://docs.bithuman.ai/guides/self-hosting) | varies |
| Run on Mac M3+ | [Swift SDK examples ↗](../swift/) | Apple Silicon M3+ |

## Learning path

If you're new to bitHuman, follow this order:

1. **Start with** [cloud-essence/](cloud-essence/) — no model files, no GPU, just an API secret. Gives you a working avatar in minutes.
2. **Try local rendering** with [quickstart/](quickstart/) — the sample avatar downloads itself and renders on your machine.
3. **Talk to it** — [self-host/](self-host/) runs a voice agent (OpenAI Realtime) on your own LiveKit server, with the avatar rendered in the same process.

## Install

```bash
pip install "bithuman[expression-2]" --upgrade   # the extra opens Expression 2 avatars

# For the LiveKit agent examples (self-host/, cloud-essence/) — Python 3.11–3.13:
pip install "livekit-agents[openai]>=1.8.2,<1.9" "livekit-plugins-bithuman>=1.8.2,<1.9" pillow
```

Pre-built wheels cover Python 3.10–3.14 on **Linux x86_64, Linux aarch64 and
Apple Silicon macOS 14+** — the three platform tags the release actually
publishes. There is **no Windows and no Intel-Mac wheel**; on Windows, run these
examples under WSL2. `pip install` on any other platform stops with a message
naming your platform rather than installing something older.

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
| Pricing | [docs.bithuman.ai/guides/pricing ↗](https://docs.bithuman.ai/guides/pricing) | same page |

## Documentation

- [Python quickstart](https://docs.bithuman.ai/getting-started/quickstart)
- [Python SDK](https://docs.bithuman.ai/sdk/python)
- [Self-hosting](https://docs.bithuman.ai/guides/self-hosting)
- [LiveKit plugin](https://docs.bithuman.ai/sdk/livekit)
