# Quickstart — Your First bitHuman Avatar

Get a talking avatar running in about 5 minutes. You'll need an API secret first. From 12 October 2026, API and SDK use requires the Creator plan or higher.

## Step 1: Get your API secret (30 seconds)

1. Go to [www.bithuman.ai](https://www.bithuman.ai) and sign in (Creator plan or higher from 12 October 2026)
2. Click **Developer** → **API Secrets**
3. Copy your API secret

```bash
export BITHUMAN_API_SECRET="paste_your_key_here"
```

## Step 2: Pick an example

| Example | What it does | Extra setup needed |
|---------|-------------|--------------------|
| **[local-avatar.py](local-avatar.py)** | Load an avatar model, play audio through it, see the animated face | None — auto-downloads a sample model on first run |
| **[cloud-avatar.py](cloud-avatar.py)** | Run a cloud-hosted avatar with AI conversation | LiveKit server + OpenAI API key; your secret as `BITHUMAN_MASTER_SECRET` (Option B) |
| **[conversation.py](conversation.py)** | Talk to the avatar in a window: your mic → OpenAI Realtime → the avatar answers | OpenAI API key; Linux: `sudo apt install libportaudio2` |
| **[microphone.py](microphone.py)** | The avatar lip-syncs your own voice from the mic | Linux: `sudo apt install libportaudio2` |
| **[quickstart.py](quickstart.py)** | Play an audio file through an avatar file you pass with `--model`, with sound | Linux: `sudo apt install libportaudio2` |

**Recommended: start with `local-avatar.py`** — it has fewer dependencies.

## Step 3: Run it

### Option A: Local avatar (recommended first try)

```bash
# Install the SDK
pip install -r requirements.txt

# Run it — auto-downloads the public-gallery sample avatar (Sofia Ramirez, ~148 MB, one-time) if you don't specify one
python local-avatar.py

# Or use your own model:
python local-avatar.py --model your-avatar.imx --audio speech.wav
```

A window will open showing the avatar lip-syncing to the audio. Press `q` to quit.

> **No display (ssh, Docker, CI)?** The example says so and stops before it
> downloads anything or starts a render. To get an MP4 instead, use the SDK's
> own command, which downloads a showcase avatar by name:
>
> ```bash
> python -m bithuman render sofia-ramirez speech.wav     # writes sofia-ramirez.mp4
> python -m bithuman render wise-pup speech.wav          # Expression 2; needs bithuman[expression-2]
> ```

> **First run is slow (up to 60 seconds).** The first time: the sample model downloads (~148 MB), then the SDK may convert it from legacy format to v2. Both are one-time costs — subsequent runs start in under 2 seconds.

> **The sample downloads anonymously.** It is `A52DHS2219` ("Sofia Ramirez", Essence 2), one of the identities in the public gallery — `bithuman list` shows them all, and any of them can be fetched with `bithuman pull <SLUG>` or straight from `GET /v1/agent/<CODE>/model/download`, which needs no credential for a gallery identity. Running the avatar needs `BITHUMAN_API_SECRET` and bills active session time ([pricing](https://docs.bithuman.ai/pricing)); so does downloading your own agent's model.

> **Want to use your own avatar?** Download a `.imx` file from [bithuman.ai → Explore](https://www.bithuman.ai/#explore) (click the **...** menu on any agent → **Download**) and pass it with `--model your-file.imx`.

> **Sample audio included.** This directory ships a `speech.wav` file you can use for testing. No need to find your own audio.

> **macOS warning about AVFAudioReceiver / libavdevice?** Harmless — OpenCV and PyAV each ship their own FFmpeg libraries. It prints once at import and changes nothing.

> **Keep `opencv-python`, not `opencv-python-headless`.** `bithuman` depends on the headless build, but `cv2.imshow` is not compiled into it — a window example that gets the headless build fails with *"The function is not implemented"*. `requirements.txt` asks for the GUI build for exactly this reason. In a container, where there is no window, prefer headless (that is what the agent dockerfiles do).

### Option B: Cloud avatar (more setup, but no model download needed)

This requires a LiveKit server and an OpenAI API key. It is a LiveKit worker, so your API secret goes in `BITHUMAN_MASTER_SECRET`, not `BITHUMAN_API_SECRET`. The worker uses it for one thing: asking bitHuman for a one-hour token that can start only this agent's avatar in this room, and it gives the plugin only that token. The reason: `livekit-plugins-bithuman` 1.8.4 and older reads `BITHUMAN_API_SECRET` by itself and copies it into the room, where everyone who joins can read it. `cloud-avatar.py` refuses to start while `BITHUMAN_API_SECRET` is set. (`BITHUMAN_AGENT_CODE` works as another name for `BITHUMAN_AGENT_ID`.)

```bash
pip install -r requirements.txt
unset BITHUMAN_API_SECRET                          # a LiveKit worker never gets this name
export BITHUMAN_MASTER_SECRET="paste_your_key_here"
export BITHUMAN_AGENT_ID=A23WJF0199                # the public sample (wise-pup), or your own agent code
export LIVEKIT_URL=wss://your-project.livekit.cloud LIVEKIT_API_KEY=… LIVEKIT_API_SECRET=…
export OPENAI_API_KEY=…
python cloud-avatar.py dev
```

## What's next?

Once your first demo works, pick the path that matches what you're building:

| I want to build... | Go to |
|---|---|
| A web app with a talking avatar | [python/cloud-essence/](../cloud-essence/) |
| A voice agent on my own machine, in the browser (my own LiveKit server) | [python/self-host/](../self-host/) |
| A Mac/iPad/iPhone app | [swift/](../../swift/) |
| Something without writing code | [cli/](../../api/cli/) |
| An integration in Java, Go, or another language | [rest-api/](../../api/rest-api/) |

## Files in this directory

| File | Purpose |
|------|---------|
| [local-avatar.py](local-avatar.py) | Opens an avatar, renders an audio file through it, shows the frames |
| [cloud-avatar.py](cloud-avatar.py) | LiveKit cloud agent with OpenAI voice chat |
| [conversation.py](conversation.py) | Mic → OpenAI Realtime (`gpt-realtime-2.1-mini`) → the avatar speaks the answer, in a window |
| [microphone.py](microphone.py) | Mic → the avatar lip-syncs you, in a window |
| [quickstart.py](quickstart.py) | An audio file → the avatar, in a window |
| [speech.wav](speech.wav) | Sample audio for testing: 13.9 s, 16 kHz mono |
| [.env.example](.env.example) | Template for environment variables (copy to `.env` and fill in) |
| [requirements.txt](requirements.txt) | Python dependencies for every script here |
