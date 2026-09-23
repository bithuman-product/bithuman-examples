"""Real-time microphone input driving a self-hosted bitHuman Essence avatar.

Captures audio from your microphone, detects speech vs silence,
and animates the avatar in real time with optional audio echo.

Usage:
    python microphone.py --model avatar.imx
    python microphone.py --model avatar.imx --echo   # hear yourself back
"""

import argparse
import asyncio
import os
import sys
import threading
import time

import cv2
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from loguru import logger

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


# A small pacer so the window is refreshed at the avatar's own frame rate
# rather than as fast as frames arrive.
class FPSController:
    def __init__(self, target_fps: int = 25, window: int = 50):
        self._target_dt = 1.0 / float(target_fps)
        self._next_t = time.monotonic()
        self._window = window
        self._ticks: list[float] = []

    def wait_next_frame(self, sleep: bool = True) -> float:
        now = time.monotonic()
        wait = self._next_t - now
        if wait > 0 and sleep:
            time.sleep(wait)
        return max(wait, 0.0)

    def update(self) -> None:
        now = time.monotonic()
        self._next_t += self._target_dt
        if self._next_t < now - self._target_dt:
            self._next_t = now + self._target_dt
        self._ticks.append(now)
        if len(self._ticks) > self._window:
            self._ticks.pop(0)

    @property
    def average_fps(self) -> float:
        if len(self._ticks) < 2:
            return 0.0
        span = self._ticks[-1] - self._ticks[0]
        return (len(self._ticks) - 1) / span if span > 0 else 0.0
# --- end inline FPSController ---

load_dotenv()
logger.remove()
logger.add(sys.stdout, level="INFO")

SAMPLE_RATE = 16000
MIC_CHUNK = 160       # 10ms at 16kHz
SILENCE_TIMEOUT = 3.0  # seconds of silence before draining stale audio


async def read_and_push_audio(
    runtime: AsyncBithuman,
    audio_queue: asyncio.Queue,
    volume: float = 1.0,
    silent_threshold_db: int = -40,
):
    """Read mic audio from queue and push to bitHuman runtime with silence detection."""
    last_speech_time = asyncio.get_running_loop().time()

    while True:
        audio_data, rms_db = await audio_queue.get()
        now = asyncio.get_running_loop().time()

        if rms_db > silent_threshold_db:
            last_speech_time = now
        elif now - last_speech_time > SILENCE_TIMEOUT:
            while audio_queue.qsize() > 10:
                audio_queue.get_nowait()

        if volume != 1.0:
            samples = np.frombuffer(audio_data, dtype=np.int16)
            samples = np.clip(samples * volume, -32768, 32767).astype(np.int16)
            audio_data = samples.tobytes()

        await runtime.push_audio(audio_data, SAMPLE_RATE, last_chunk=False)


async def main():
    parser = argparse.ArgumentParser(description="bitHuman Essence -- microphone input")
    parser.add_argument("--model", default=os.getenv("BITHUMAN_MODEL_PATH"),
                        help="Path to .imx avatar model")
    parser.add_argument("--api-secret", default=os.getenv("BITHUMAN_API_SECRET"))
    parser.add_argument("--volume", type=float, default=1.0, help="Mic volume multiplier")
    parser.add_argument("--silent-threshold-db", type=int, default=-40)
    parser.add_argument("--echo", action="store_true", help="Play avatar audio back through speakers")
    args = parser.parse_args()

    if not args.model:
        print("Error: Provide --model or set BITHUMAN_MODEL_PATH")
        print("Download .imx models from https://www.bithuman.ai")
        return

    # Before the model loads, before the credential is held, before anything bills.
    require_window()

    runtime = await AsyncBithuman.create(
        model_path=args.model, api_secret=args.api_secret, input_buffer_size=5,
    )

    width, height = runtime.frame_width, runtime.frame_height
    cv2.resizeWindow(WINDOW, width, height)

    loop = asyncio.get_running_loop()
    audio_queue: asyncio.Queue = asyncio.Queue()
    speaker_buf = bytearray()
    speaker_lock = threading.Lock()

    def mic_callback(indata, frames, time_info, status):
        samples = indata[:, 0].copy()
        int16 = (samples * 32767).astype(np.int16)
        rms = np.sqrt(np.mean(samples ** 2))
        db = 20 * np.log10(rms + 1e-9)
        asyncio.run_coroutine_threadsafe(audio_queue.put((int16.tobytes(), db)), loop)

    def speaker_callback(outdata, frames, time_info, status):
        n_bytes = frames * 2
        with speaker_lock:
            avail = min(len(speaker_buf), n_bytes)
            outdata[:avail // 2, 0] = np.frombuffer(speaker_buf[:avail], dtype=np.int16)
            outdata[avail // 2:, 0] = 0
            del speaker_buf[:avail]

    mic_stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="float32",
        blocksize=MIC_CHUNK, callback=mic_callback,
    )
    speaker_stream = None
    if args.echo:
        speaker_stream = sd.OutputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16",
            blocksize=640, callback=speaker_callback,
        )
        speaker_stream.start()

    mic_stream.start()
    logger.info("Microphone started -- press Q in the video window to quit")

    mic_task = asyncio.create_task(
        read_and_push_audio(runtime, audio_queue, args.volume, args.silent_threshold_db)
    )

    fps = FPSController(target_fps=25)
    try:
        async for frame in runtime.run():
            sleep_time = fps.wait_next_frame(sleep=False)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            if frame.has_image:
                cv2.imshow(WINDOW, frame.bgr_image)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if args.echo and frame.audio_chunk:
                with speaker_lock:
                    speaker_buf.extend(frame.audio_chunk.array.tobytes())

            fps.update()
    finally:
        mic_task.cancel()
        mic_stream.stop()
        if speaker_stream:
            speaker_stream.stop()
        cv2.destroyAllWindows()
        # shutdown(), not stop(): stop() halts the frame producer but keeps the
        # model loaded and the credential held. shutdown() frees both.
        await runtime.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
