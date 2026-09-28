# bitHuman Visual Agent App - a local conversation brain on macOS

An avatar agent on Apple M2+/M3/M4 Macs whose conversation runs on the Mac: Apple Speech Recognition (STT), an Ollama language model, Apple Voices/Siri (TTS) and LiveKit all run locally, and the bitHuman SDK renders the avatar locally.

**It needs the internet for bitHuman.** The avatar checks your API secret when a session starts and reports usage (never audio, video or conversation text). Offline licenses are for Linux PCs and terminals, Business and Enterprise only; a Mac stays online. See [Fully offline](https://docs.bithuman.ai/deploy/offline).

## What You Need

**For M2+/M3/M4 macOS devices:**
- Docker and Docker Compose (**We strongly recommend [OrbStack](https://orbstack.dev/) for better performance and easier management**)
- `BITHUMAN_MASTER_SECRET` — your API secret (Creator plan or higher from 12 October 2026)
- `.imx` model files (place in `./models/` directory)
- Python 3.10+ for bitHuman's Apple plugin
- [Ollama](https://ollama.com/) for local LLM

## Local Setup Steps

### 1. Install bitHuman's Apple Plugin

Install bitHuman's Apple STT (Speech Recognition) and TTS (Siri/Apple voices) plugin for LiveKit:

> **Preview — private distribution.** The `bithuman-voice` wheel is not currently published publicly. This example won't run end-to-end without it. Reach out on [Discord](https://discord.gg/ES953n7bPA) or through [bitHuman support](https://bithuman.ai) to request access.

Once you have the wheel, install it:

```bash
pip install bithuman_voice-1.3.2-py3-none-any.whl
```

### 2. Configure Apple Voices

Configure Apple voices by going to System Settings. We recommend either **Siri voices** or **Apple's premium voices**. You need to download them first.

- Go to System Settings > Accessibility > Spoken Content > System Voice
- Download Siri voices or premium Apple voices

### 3. Start bitHuman's Apple TTS/STT Services

Start the bitHuman Apple voice services:

```bash
bithuman-voice serve --port 8000
```

This provides both STT and TTS endpoints at port 8000.

### 4. Install and Run Ollama (Local LLM)

Follow the instructions at [https://ollama.com/](https://ollama.com/) to install Ollama, then download a lightweight LLM model:

```bash
ollama run llama3.2:1b
```

For slightly better performance (if you have sufficient RAM):
```bash
ollama run llama3.2:3b
```

Ollama serves on port 11434 by default.

### 5. Configure Environment

**Get your bitHuman API secret** from [Developer → API Secrets](https://www.bithuman.ai/developer/api-keys).

Create a `.env` file:

```bash
# Your API secret. A LiveKit worker never gets BITHUMAN_API_SECRET: livekit-plugins-bithuman 1.8.4
# and older reads that name by itself and, for a cloud avatar, copies it into the room.
BITHUMAN_MASTER_SECRET=<your API secret>
# The local LiveKit server's secret — any long random string, e.g. `openssl rand -hex 32`.
# docker-compose.yml hands it to the server, the agent and the web UI.
LIVEKIT_API_SECRET=<a long random string>
```

Optional environment variables for custom service URLs:

```bash
APPLE_SPEECH_URL=http://host.docker.internal:8000/v1   # Apple STT/TTS endpoint
OLLAMA_URL=http://host.docker.internal:11434/v1         # Ollama LLM endpoint
OLLAMA_MODEL=llama3.2:1b                                # Ollama model name
```

### 6. Add Models

Place your `.imx` files in the `models/` directory:

```bash
# Example - models/ directory should contain:
models/
└── YourModel.imx
```

**Download .imx models from bitHuman** at [https://www.bithuman.ai](https://www.bithuman.ai).

### 7. Start Services

```bash
docker compose up
```

Wait for all services to start (first run takes a few minutes).

### 8. Access the App

Open http://localhost:4202 in your browser.

## That's It!

Now you have an avatar agent whose conversation runs on your Mac. The system includes:

**Local Services:**
- **Apple Speech Recognition**: Local STT via bitHuman's Apple plugin
- **Apple Voices/Siri**: Local TTS via bitHuman's Apple plugin
- **Ollama LLM**: Local language model (Llama 3.2:1b or 3b)
- **LiveKit**: Local WebRTC communication server
- **Agent**: AI conversation handler with local components
- **Frontend**: Web interface
- **Redis**: Message broker

**What needs the internet:**
- **The avatar**: your API secret is checked when a session starts, and usage is reported (no audio, video or conversation text). A session keeps rendering through a network drop of up to 5 minutes.
- **Everything else** (speech recognition, the language model, the voice, LiveKit) runs on the Mac.

## Development

**Edit agent code:**
```bash
vim agent.py
docker compose restart agent
```

**View logs:**
```bash
docker compose logs -f agent
```

**Stop everything:**
```bash
docker compose down
```

## Troubleshooting

**Services won't start?**
- Check `.env` file exists with valid `BITHUMAN_MASTER_SECRET`
- Ensure models/ directory contains `.imx` files
- Verify bitHuman voice service is running on port 8000: `bithuman-voice serve --port 8000`
- Check Ollama is running and model is downloaded: `ollama list`
- Run `docker compose logs [service]` to see errors

**Port conflicts?**
- Frontend uses port 4202
- LiveKit uses ports 17880-17881 and UDP 50700-50720
- bitHuman voice service uses port 8000
- Ollama typically uses port 11434

**Voice/Speech issues?**
- Ensure Apple voices are downloaded in System Settings
- Check bitHuman voice service is running: `ps aux | grep bithuman-voice`
- Verify microphone permissions are granted to your terminal/browser

**Ollama model issues?**
- Check if model is downloaded: `ollama list`
- Try downloading again: `ollama pull llama3.2:1b`
- Ensure sufficient RAM for the model size

**Clean restart:**
```bash
# Stop bitHuman voice service (Ctrl+C if running in terminal)
# Stop Ollama if needed
docker compose down -v
docker compose up --build
# Restart bitHuman voice service: bithuman-voice serve --port 8000
```
