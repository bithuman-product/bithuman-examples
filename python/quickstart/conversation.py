"""AI voice conversation (OpenAI Realtime) with a bitHuman avatar rendered on this machine.

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
    # Linux wheels of sounddevice do not carry the PortAudio library.
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

NO_DISPLAY = """No display, so there is no window to draw the avatar in.

This example is live: it drives the avatar from your microphone, so there is
no audio file to render instead. On a machine with no display, use
../self-host/ (the avatar in a browser page served by your own LiveKit
server). On a desktop with a display, this example opens a window as written."""

NO_GUI_BUILD = """This OpenCV cannot open a window: it was built without GUI support.

The display is fine — the problem is which OpenCV got installed. `bithuman`
depends on `opencv-python-headless`, and requirements.txt here also asks for
`opencv-python`, the GUI build. Both land, they own the same `cv2/` package,
and whichever pip writes LAST is the one you get. Here the headless build won.

This puts the GUI build back and leaves everything else alone:

    pip install --force-reinstall --no-deps opencv-python"""


def require_window() -> None:
    """Stop before the model loads if this machine cannot show a window.

    Two checks, in this order:
      1. Is a display named at all? The GUI build of OpenCV does not raise when
         there is none: Qt aborts the process (SIGABRT) with nothing to catch.
         So the environment is checked before cv2 opens anything.
      2. Can this OpenCV open a window? If the headless build won the install,
         `namedWindow` raises here (NO_GUI_BUILD says how to fix it), before
         anything loads or bills.
    """
    if sys.platform not in ("darwin", "win32") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        sys.exit(NO_DISPLAY)
    try:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    except cv2.error:
        sys.exit(NO_GUI_BUILD)

# Only this folder's .env: a bare load_dotenv() also searches every parent folder.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
logger.remove()
logger.add(sys.stdout, level="INFO")
logging.getLogger("numba").setLevel(logging.WARNING)

OPENAI_SAMPLE_RATE = 24000  # OpenAI Realtime requires 24kHz PCM16
AVATAR_SAMPLE_RATE = 16000  # bitHuman outputs at 16kHz
MIC_CHUNK = 240             # 10ms at 24kHz


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="bitHuman -- AI conversation")
    parser.add_argument("--model", default=os.getenv("BITHUMAN_MODEL_PATH"),
                        help="Path to .imx avatar model")
    parser.add_argument("--voice", default=os.getenv("OPENAI_VOICE", "coral"),
                        help="OpenAI voice (alloy, coral, echo, etc.)")
    args = parser.parse_args()
    # Your API secret, from the environment only — a value on the command line
    # is readable by anyone who can run `ps`.
    args.api_secret = os.getenv("BITHUMAN_API_SECRET")

    model_path = args.model
    api_secret = args.api_secret
    openai_key = os.getenv("OPENAI_API_KEY")

    if not model_path:
        print("Error: Set --model or BITHUMAN_MODEL_PATH")
        print("Download .imx models from https://www.bithuman.ai")
        return
    if not api_secret:
        print("Error: set BITHUMAN_API_SECRET (your API secret, from https://www.bithuman.ai/developer/api-keys)")
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
        # gpt-realtime-2.1-mini on the GA Realtime API (client.realtime); the older
        # preview models and the beta API were shut down by OpenAI on 2026-05-07.
        async with client.realtime.connect(model="gpt-realtime-2.1-mini") as conn:
            await conn.session.update(session={
                "type": "realtime",
                "instructions": "You are a friendly AI assistant. Keep responses concise.",
                "output_modalities": ["audio"],
                "audio": {
                    "input": {"format": {"type": "audio/pcm", "rate": OPENAI_SAMPLE_RATE},
                              "turn_detection": {"type": "server_vad"}},
                    "output": {"format": {"type": "audio/pcm", "rate": OPENAI_SAMPLE_RATE},
                               "voice": args.voice},
                },
            })
            logger.info("Connected to OpenAI Realtime -- speak now (press Q to quit)")

            async def send_mic():
                while True:
                    data = await mic_queue.get()
                    await conn.input_audio_buffer.append(audio=base64.b64encode(data).decode())

            send_task = asyncio.create_task(send_mic())
            try:
                async for event in conn:
                    if event.type == "response.output_audio.delta":
                        await ai_audio_queue.put(base64.b64decode(event.delta))
                    elif event.type == "response.output_audio.done":
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
