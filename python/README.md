# Python SDK Examples

All Python examples use `pip install bithuman`. Pick the one that matches where you want the avatar to run.

## Quick decision

| I want to... | Example | What I need |
|---|---|---|
| Fastest cloud demo (no GPU) | [cloud-essence/](cloud-essence/) | API secret + agent ID |
| Cloud with custom face image (Expression) | [Deployment guide ↗](https://docs.bithuman.ai/guides/deployment) | API secret + face image |
| Run on my own server (CPU) | [local-essence/](local-essence/) | API secret + `.imx` file |
| Self-hosted NVIDIA GPU (Expression) | [Self-hosted GPU guide ↗](https://docs.bithuman.ai/guides/deployment) | NVIDIA GPU 8 GB+ |
| Run on Mac M3+ | [Swift SDK examples ↗](../swift/) | Apple Silicon M3+ |

## Learning path

If you're new to bitHuman, follow this order:

1. **Start with** [cloud-essence/](cloud-essence/) — no model files, no GPU, just an API secret. Gives you a working avatar in minutes.
2. **Try local rendering** with [local-essence/](local-essence/) — download a `.imx` model and run it on your own machine (CPU only).
3. **Add AI conversation** — the `conversation.py` script in local-essence/ wires OpenAI for voice chat.
4. **Explore Expression** — dynamic faces from any image — via the [deployment guide ↗](https://docs.bithuman.ai/guides/deployment).

## Install

```bash
pip install "bithuman[expression-2]" --upgrade   # the extra opens Expression 2 avatars

# For LiveKit agent examples (cloud-* and docker stacks):
pip install "livekit-agents>=1.4" "livekit-plugins-bithuman>=1.4"
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

Most also include:
- **docker-compose.yml** — full stack (LiveKit + agent + web UI)
- **agent.py** — LiveKit agent entry point
- **quickstart.py** — standalone script (no LiveKit needed)

## Two models

These examples all use the second-generation models (`essence-2`,
`expression-2`). The rates that used to be copied into this table were the
**first**-generation ones, which are half — so the pricing page is linked
instead of duplicated, because it is the single source for every billing number
and this copy went stale.

| | **Essence** | **Expression** |
|---|---|---|
| Avatar source | `.imx` file from [bithuman.ai](https://www.bithuman.ai/#explore) | Any face image |
| Compute | CPU only | NVIDIA GPU or Apple M3+ |
| Pricing | [docs.bithuman.ai/guides/pricing ↗](https://docs.bithuman.ai/guides/pricing) | same page |

## Documentation

- [Python quickstart](https://docs.bithuman.ai/getting-started/quickstart)
- [Avatar sessions](https://docs.bithuman.ai/guides/deployment)
- [Self-hosted GPU](https://docs.bithuman.ai/guides/deployment)
- [LiveKit Cloud plugin](https://docs.bithuman.ai/guides/deployment)
