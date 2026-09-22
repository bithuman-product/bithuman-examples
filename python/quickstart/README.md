# Quickstart — Your First bitHuman Avatar

Get a talking avatar running in about 5 minutes. You'll need an API key first.

## Step 1: Get your API key (30 seconds)

1. Go to [www.bithuman.ai](https://www.bithuman.ai) and create a free account
2. Click **Developer** → **API Keys**
3. Copy your API secret

```bash
export BITHUMAN_API_SECRET="paste_your_key_here"
```

## Step 2: Pick an example

| Example | What it does | Extra setup needed |
|---------|-------------|--------------------|
| **[local-avatar.py](local-avatar.py)** | Load an avatar model, play audio through it, see the animated face | None — auto-downloads a sample model on first run |
| **[cloud-avatar.py](cloud-avatar.py)** | Run a cloud-hosted avatar with AI conversation | LiveKit server + OpenAI API key |

**Recommended: start with `local-avatar.py`** — it has fewer dependencies.

## Step 3: Run it

### Option A: Local avatar (recommended first try)

```bash
# Install the SDK
pip install -r requirements.txt

# Run it — auto-downloads the free-gallery sample avatar (Sofia Ramirez, ~148 MB, one-time) if you don't specify one
python local-avatar.py

# Or use your own model:
python local-avatar.py --model your-avatar.imx --audio speech.wav
```

A window will open showing the avatar lip-syncing to the audio. Press `q` to quit.

> **First run is slow (up to 60 seconds).** The first time: the sample model downloads (~148 MB), then the SDK may convert it from legacy format to v2. Both are one-time costs — subsequent runs start in under 2 seconds.

> **The sample needs no account.** It is `A52DHS2219` ("Sofia Ramirez", Essence 2), one of the identities in the free gallery — `bithuman list` shows them all, and any of them can be fetched with `bithuman pull <SLUG>` or straight from `GET /v1/agent/<CODE>/model/download`, which needs no credential for a gallery identity. Your own agent's model does need `BITHUMAN_API_SECRET`, and so does running the avatar below.

> **Want to use your own avatar?** Download a `.imx` file from [bithuman.ai → Explore](https://www.bithuman.ai/#explore) (click the **...** menu on any agent → **Download**) and pass it with `--model your-file.imx`.

> **Sample audio included.** This directory ships a `speech.wav` file you can use for testing. No need to find your own audio.

> **macOS warning about AVFAudioReceiver / libavdevice?** Harmless — OpenCV and PyAV each ship their own FFmpeg libraries. It prints once at import and changes nothing.

> **Keep `opencv-python`, not `opencv-python-headless`.** `bithuman` depends on the headless build, but `cv2.imshow` is not compiled into it — a window example that gets the headless build fails with *"The function is not implemented"*. `requirements.txt` asks for the GUI build for exactly this reason. In a container, where there is no window, prefer headless (that is what the agent dockerfiles do).

### Option B: Cloud avatar (more setup, but no model download needed)

This requires a LiveKit server and OpenAI API key. See [.env.example](.env.example) for all required variables.

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your actual keys
python cloud-avatar.py dev
```

## What's next?

Once your first demo works, pick the path that matches what you're building:

| I want to build... | Go to |
|---|---|
| A web app with a talking avatar | [python/cloud-essence/](../cloud-essence/) |
| A server-side avatar (my own hardware) | [python/local-essence/](../local-essence/) |
| A Mac/iPad/iPhone app | [swift/](../../swift/) |
| Something without writing code | [cli/](../../api/cli/) |
| An integration in Java, Go, or another language | [rest-api/](../../api/rest-api/) |

## Files in this directory

| File | Purpose |
|------|---------|
| [local-avatar.py](local-avatar.py) | Opens an avatar, renders an audio file through it, shows the frames |
| [cloud-avatar.py](cloud-avatar.py) | LiveKit cloud agent with OpenAI voice chat |
| [speech.wav](speech.wav) | Sample audio for testing — 13.9 s, 16 kHz mono |
| [.env.example](.env.example) | Template for environment variables (copy to `.env` and fill in) |
| [requirements.txt](requirements.txt) | Python dependencies for both scripts |
