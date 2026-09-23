"""AI voice conversation with a self-hosted bitHuman Essence avatar.

Speak into your mic, hear the AI respond via OpenAI Realtime,
and watch the avatar lip-sync in real time. No LiveKit server needed.

Usage:
    python conversation.py
    python conversation.py --model avatar.imx --voice alloy
"""

import asyncio
import base64
import logging
import os
import sys
import threading

import cv2
import numpy as np
try:
    import sounddevice as sd
except OSError:
    # ★`pip install` gets the sounddevice package but not the PortAudio
    # library it loads: its Linux wheels do not carry one (macOS and Windows
    # wheels do). Measured 2026-09-23 on a stock Ubuntu 24.04 with a display
    # and a sound server: `OSError: PortAudio library not found` at this
    # import, before anything else in the script ran. Say what to install.
    sys.exit(
        "sounddevice needs the PortAudio library, which pip cannot install.\n\n"
        "    sudo apt install libportaudio2      # Debian, Ubuntu\n"
        "    sudo dnf install portaudio          # Fedora\n\n"
        "then run this again. (macOS needs nothing: the wheel carries it.)"
    )
from dotenv import load_dotenv
from loguru import logger
from openai import AsyncOpenAI

from bithuman import AsyncBithuman


WINDOW = "bitHuman"

# Why there is no MP4 writer here: the frame rate belongs to the avatar
# (essence-2 renders at 25 fps, expression-2 at 20), so an example that wrote
# its own file would have to guess it or reach past the taught surface. The
# supported paths already exist, so the message points at them instead.
NO_DISPLAY = """No display, so there is no window to draw the avatar in.

This example is LIVE — it drives the avatar from your microphone as you speak,
so there is no audio file to render instead. To use a headless machine, run
the Docker stack in this directory and watch the avatar in a browser:

    docker compose up          # then open http://localhost:4202

If that stack is on a remote box, README.md → "Scenario B" has the ssh tunnel.
On a desktop with a display, this example opens a window as written."""

NO_GUI_BUILD = """This OpenCV cannot open a window: it was built without GUI support.

The display is fine — the problem is which OpenCV got installed. `bithuman`
depends on `opencv-python-headless`, and requirements.txt here also asks for
`opencv-python`, the GUI build. Both land, they own the same `cv2/` package,
and whichever pip writes LAST is the one you get. Here the headless build won.

This puts the GUI build back and leaves everything else alone:

    pip install --force-reinstall --no-deps opencv-python"""


def require_window() -> None:
    """Refuse before the model loads if this machine cannot show a window.

    ★THE ORDER OF THESE TWO GATES IS THE WHOLE POINT, because only the second
    failure is catchable and the first one kills the process.

      1. The GUI build of OpenCV on a box with no display does NOT raise. Qt
         fails to load its xcb platform plugin and calls abort(): the process
         dies on SIGABRT with no traceback and no except clause that can help.
         Measured 2026-09-22 on a headless Linux box with this directory's own
         requirements.txt — `cv2.namedWindow` exited 134. So the environment is
         read FIRST, and cv2 is not asked to open anything until it passes.
      2. Only then can `namedWindow` be called safely. It raises exactly where
         `imshow` would if this OpenCV has no GUI compiled in, and raising here
         means the answer is known BEFORE a frame is rendered rather than
         discovered mid-stream.

    The two gates fail for DIFFERENT reasons and say so separately. Gate 2 is
    not "no display" — there is one; it is "the headless build won the
    install", which is a live possibility in this directory because `bithuman`
    depends on `opencv-python-headless` while requirements.txt also asks for
    `opencv-python`. Telling a developer with a working display that they have
    no display would send them to fix the wrong thing.

    Both gates run before `AsyncBithuman.create()`, so a machine that cannot
    show the avatar is told so without loading the model, holding the
    credential, or billing a render. Before this gate existed the process
    reached `create()` and THEN died — the developer paid, waited, and got
    exit 134 with nothing to read.

    This is also where the window is created, so the `namedWindow` call that
    used to sit beside `resizeWindow` is gone: this IS that call, moved to
    where it can still refuse cheaply.

    The limit, stated rather than papered over: gate 1 reads whether a display
    is NAMED, not whether it answers. `DISPLAY=:0` pointing at nothing still
    reaches Qt and still aborts. Covering that honestly means probing the
    display from a subprocess, which is more machinery than an example should
    carry — and the shapes these scripts land in (ssh, Docker, CI) name no
    display at all.
    """
    if sys.platform not in ("darwin", "win32") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        sys.exit(NO_DISPLAY)
    try:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    except cv2.error:
        sys.exit(NO_GUI_BUILD)

load_dotenv()
logger.remove()
logger.add(sys.stdout, level="INFO")
logging.getLogger("numba").setLevel(logging.WARNING)

OPENAI_SAMPLE_RATE = 24000  # OpenAI Realtime requires 24kHz PCM16
AVATAR_SAMPLE_RATE = 16000  # bitHuman outputs at 16kHz
MIC_CHUNK = 240             # 10ms at 24kHz


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="bitHuman Essence -- AI conversation")
    parser.add_argument("--model", default=os.getenv("BITHUMAN_MODEL_PATH"),
                        help="Path to .imx avatar model")
    parser.add_argument("--api-secret", default=os.getenv("BITHUMAN_API_SECRET"))
    parser.add_argument("--voice", default=os.getenv("OPENAI_VOICE", "coral"),
                        help="OpenAI voice (alloy, coral, echo, etc.)")
    args = parser.parse_args()

    model_path = args.model
    api_secret = args.api_secret
    openai_key = os.getenv("OPENAI_API_KEY")

    if not model_path:
        print("Error: Set --model or BITHUMAN_MODEL_PATH")
        print("Download .imx models from https://www.bithuman.ai")
        return
    if not api_secret:
        print("Error: Set --api-secret or BITHUMAN_API_SECRET")
        return
    if not openai_key:
        print("Error: Set OPENAI_API_KEY in your .env")
        return

    # Before the model loads, before the credential is held, before anything bills.
    require_window()

    runtime = await AsyncBithuman.create(model_path=model_path, api_secret=api_secret)
    width, height = runtime.frame_width, runtime.frame_height
    cv2.resizeWindow(WINDOW, width, height)

    loop = asyncio.get_running_loop()
    mic_queue: asyncio.Queue[bytes] = asyncio.Queue()
    ai_audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    speaker_buf = bytearray()
    speaker_lock = threading.Lock()

    def mic_callback(indata, frames, time_info, status):
        samples = (indata[:, 0] * 32767).astype(np.int16)
        asyncio.run_coroutine_threadsafe(mic_queue.put(samples.tobytes()), loop)

    def speaker_callback(outdata, frames, time_info, status):
        n_bytes = frames * 2
        with speaker_lock:
            avail = min(len(speaker_buf), n_bytes)
            outdata[:avail // 2, 0] = np.frombuffer(speaker_buf[:avail], dtype=np.int16)
            outdata[avail // 2:, 0] = 0
            del speaker_buf[:avail]

    mic_stream = sd.InputStream(
        samplerate=OPENAI_SAMPLE_RATE, channels=1, dtype="float32",
        blocksize=MIC_CHUNK, callback=mic_callback,
    )
    speaker_stream = sd.OutputStream(
        samplerate=AVATAR_SAMPLE_RATE, channels=1, dtype="int16",
        blocksize=640, callback=speaker_callback,
    )
    mic_stream.start()
    speaker_stream.start()

    async def run_openai():
        client = AsyncOpenAI(api_key=openai_key)
        async with client.beta.realtime.connect(model="gpt-4o-mini-realtime-preview") as conn:
            await conn.session.update(session={
                "instructions": "You are a friendly AI assistant. Keep responses concise.",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {"type": "server_vad"},
                "voice": args.voice,
            })
            logger.info("Connected to OpenAI Realtime -- speak now (press Q to quit)")

            async def send_mic():
                while True:
                    data = await mic_queue.get()
                    await conn.input_audio_buffer.append(audio=base64.b64encode(data).decode())

            send_task = asyncio.create_task(send_mic())
            try:
                async for event in conn:
                    if event.type == "response.audio.delta":
                        await ai_audio_queue.put(base64.b64decode(event.delta))
                    elif event.type == "response.audio.done":
                        await ai_audio_queue.put(None)
            finally:
                send_task.cancel()

    async def push_to_bithuman():
        while True:
            data = await ai_audio_queue.get()
            if data is None:
                await runtime.flush()
            else:
                await runtime.push_audio(data, OPENAI_SAMPLE_RATE, last_chunk=False)

    openai_task = asyncio.create_task(run_openai())
    bithuman_task = asyncio.create_task(push_to_bithuman())

    try:
        async for frame in runtime.run():
            if frame.has_image:
                cv2.imshow(WINDOW, frame.bgr_image)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if frame.audio_chunk:
                with speaker_lock:
                    speaker_buf.extend(frame.audio_chunk.array.tobytes())
    finally:
        openai_task.cancel()
        bithuman_task.cancel()
        mic_stream.stop()
        speaker_stream.stop()
        cv2.destroyAllWindows()
        # shutdown(), not stop(): stop() halts the frame producer but keeps the
        # model loaded and the credential held. shutdown() frees both.
        await runtime.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
