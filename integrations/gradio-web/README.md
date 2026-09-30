# Web UI — Gradio + FastRTC

Talk to a bitHuman avatar through your browser using Gradio and FastRTC.

## Prerequisites

- **Python 3.10–3.14** (tested on 3.12 and 3.14 on Linux x86_64). The `bithuman` package has wheels for Linux x86_64 and aarch64, Apple silicon macOS 14+ and Windows 11 x86_64.
- A bitHuman API secret ([www.bithuman.ai](https://www.bithuman.ai/developer/api-keys) → Developer → API Secrets). Creator plan or higher from 12 October 2026.
- An OpenAI API key (OpenAI Realtime does the listening and speaking).
- Avatar files are optional: with none, the public `wise-pup` sample downloads on first run.

## Quick Start

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set BITHUMAN_API_SECRET and OPENAI_API_KEY

python app.py
```

Opens a Gradio web interface at **http://localhost:7860**.

Select an avatar from the dropdown and click to start talking. Every `.imx` file in `BITHUMAN_MODEL_ROOT` appears there, named by its filename stem (`my-avatar.imx` shows as `my-avatar`). With no folder set, the app uses `~/.cache/bithuman/examples` and downloads the `wise-pup` sample into it the first time.

The avatar renders on this machine's CPU and bills active session time on your API secret ([pricing](https://docs.bithuman.ai/pricing)).

## Your API secret stays on the server

`app.py` reads `BITHUMAN_API_SECRET` from `.env` and uses it only inside the Python process. The page has no secret field, and nothing the browser receives contains it. The flip side: anyone who can open the page can start sessions billed to your secret. The app listens on `127.0.0.1` only; before you expose it (`share=True`, a public host, `GRADIO_SERVER_NAME=0.0.0.0`), put your own login in front of it.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `BITHUMAN_API_SECRET` | Yes | API secret from bithuman.ai. Server-side only |
| `OPENAI_API_KEY` | Yes | For AI conversation (OpenAI Realtime API) |
| `BITHUMAN_MODEL_ROOT` | No | Folder with `.imx` avatar files (default `~/.cache/bithuman/examples`) |
| `GRADIO_SERVER_NAME` | No | Listen address (default `127.0.0.1`) |

## Architecture

```
Browser ──WebRTC (FastRTC)──> Gradio App ──SDK──> .imx model (CPU)
   |                             |
   mic + camera              AI conversation
                              (OpenAI Realtime)
```

1. Gradio serves the web UI with an avatar dropdown (the API secret is not part of the UI)
2. FastRTC `AsyncAudioVideoStreamHandler` handles browser WebRTC
3. bitHuman SDK loads the selected `.imx` model and renders frames locally
4. OpenAI Realtime API provides AI conversation

## What It Demonstrates

- FastRTC `AsyncAudioVideoStreamHandler` for browser-based WebRTC
- Gradio UI with avatar selection dropdown
- Full AI conversation pipeline: mic → cloud LLM → bitHuman → video stream

## Troubleshooting

**`Set BITHUMAN_API_SECRET` / `Set OPENAI_API_KEY` at start?**
Fill both in `.env` (see `.env.example`).

**`There is no current event loop in thread 'MainThread'` on Python 3.14?**
You have an older copy of `app.py`; this version builds its LiveKit audio queue inside the running event loop and starts on Python 3.10–3.14.

**Your own avatars not in the dropdown?**
Set `BITHUMAN_MODEL_ROOT` to a directory containing `.imx` files:
```bash
export BITHUMAN_MODEL_ROOT=/path/to/models
ls $BITHUMAN_MODEL_ROOT/*.imx   # Should list your avatar files
```

**WebRTC connection fails?**
Make sure port 7860 is accessible. If running remotely, use SSH port forwarding:
```bash
ssh -L 7860:localhost:7860 user@your-server
```

**No audio / avatar doesn't respond?**
Check that `OPENAI_API_KEY` is set and valid in `.env`.

## Files

| File | Description |
|------|-------------|
| `app.py` | Gradio + FastRTC application |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |
