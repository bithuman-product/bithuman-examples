"""Play an audio file through a self-hosted bitHuman Essence avatar.

Loads a local .imx model on CPU, streams audio in, shows the avatar in a
window, plays the synchronized audio back through the default speaker.

Usage:
    python quickstart.py --model avatar.imx --audio-file speech.wav
"""

import argparse
import asyncio
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
import soundfile as sf
from dotenv import load_dotenv

from bithuman import AsyncBithuman


WINDOW = "bitHuman"

# Why there is no MP4 writer here: the frame rate belongs to the avatar
# (essence-2 renders at 25 fps, expression-2 at 20), so an example that wrote
# its own file would have to guess it or reach past the taught surface. The
# supported paths already exist, so the message points at them instead.
NO_DISPLAY = """No display, so there is no window to draw the avatar in.

This example plays an audio FILE through the avatar, and the SDK already does
that to a file in one command:

    python -m bithuman <avatar> <audio>        # writes <avatar>.mp4

Pass the same model and audio file you would have passed here. On a desktop
with a display, this example opens a window as written."""

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


# push_audio() wants 16 kHz mono int16; these two turn any audio file into that.
def load_audio(path: str, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """Load WAV/MP3/FLAC/etc., downmix to mono, resample to target_sr.

    Returns (float32 array in [-1, 1], sample_rate).
    """
    audio, sr = sf.read(path, dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != target_sr:
        n_out = int(round(len(audio) * target_sr / sr))
        audio = np.interp(
            np.linspace(0, len(audio), n_out, endpoint=False),
            np.arange(len(audio)),
            audio,
        ).astype(np.float32)
        sr = target_sr
    return audio, sr


def float32_to_int16(arr: np.ndarray) -> np.ndarray:
    """Clip + scale float32 [-1, 1] to int16 PCM."""
    return (np.clip(arr, -1.0, 1.0) * 32767.0).astype(np.int16)

load_dotenv()


def make_speaker(sample_rate: int = 16_000):
    """Return (output_stream, append_pcm). append_pcm(int16_bytes) is thread-safe."""
    buf, lock = bytearray(), threading.Lock()

    def callback(outdata, frames, _time, _status):
        n = frames * 2  # int16 = 2 bytes
        with lock:
            take = min(len(buf), n)
            outdata[: take // 2, 0] = np.frombuffer(buf[:take], dtype=np.int16)
            outdata[take // 2 :, 0] = 0
            del buf[:take]

    stream = sd.OutputStream(
        samplerate=sample_rate, channels=1, dtype="int16", blocksize=640, callback=callback
    )

    def append(pcm: bytes):
        with lock:
            buf.extend(pcm)

    return stream, append


async def stream_audio(runtime: AsyncBithuman, audio_file: str) -> None:
    pcm, sr = load_audio(audio_file)
    pcm = float32_to_int16(pcm)
    chunk = sr // 100  # 10 ms
    for i in range(0, len(pcm), chunk):
        await runtime.push_audio(pcm[i : i + chunk].tobytes(), sr, last_chunk=False)
    await runtime.flush()


async def main() -> None:
    p = argparse.ArgumentParser(description="bitHuman Essence — play audio through a local avatar")
    p.add_argument("--model", default=os.getenv("BITHUMAN_MODEL_PATH"), help="Path to .imx model")
    p.add_argument("--audio-file", required=True, help="Path to WAV/MP3/FLAC/M4A")
    p.add_argument("--api-secret", default=os.getenv("BITHUMAN_API_SECRET"))
    args = p.parse_args()

    if not args.model:
        raise SystemExit("Provide --model or set BITHUMAN_MODEL_PATH (download .imx from https://www.bithuman.ai)")
    if not args.api_secret:
        raise SystemExit("Set BITHUMAN_API_SECRET")

    # Before the model loads, before the credential is held, before anything bills.
    require_window()

    runtime = await AsyncBithuman.create(model_path=args.model, api_secret=args.api_secret)
    w, h = runtime.frame_width, runtime.frame_height
    cv2.resizeWindow(WINDOW, w, h)

    speaker, append_pcm = make_speaker()
    speaker.start()
    pusher = asyncio.create_task(stream_audio(runtime, args.audio_file))
    try:
        async for frame in runtime.run():
            if frame.has_image:
                cv2.imshow(WINDOW, frame.bgr_image)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            if frame.audio_chunk:
                append_pcm(frame.audio_chunk.array.tobytes())
    finally:
        pusher.cancel()
        speaker.stop()
        cv2.destroyAllWindows()
        # shutdown(), not stop(): stop() halts the frame producer but keeps the
        # model loaded and the credential held. shutdown() frees both.
        await runtime.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
