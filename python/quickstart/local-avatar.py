"""Local avatar -- load a .imx model, push audio, display video frames.

Setup:
    export BITHUMAN_API_SECRET=your_secret
    pip install -r requirements.txt

Usage:
    python local-avatar.py                              # auto-downloads a sample model
    python local-avatar.py --model avatar.imx           # use your own model
    python local-avatar.py --model avatar.imx --audio speech.wav
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf

from bithuman import AsyncAvatar


# --- Inline replacements for bithuman.audio (removed in SDK 2.3 slim wheel). ---
# These helpers were tiny leaf utilities; we inline them so examples have no
# dependency on internal SDK helpers that may move between releases.
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

def display_available() -> bool:
    """True only when a window server is actually reachable from this process.

    ★Two different failures hide behind `cv2.imshow`, and only ONE of them is
    catchable, so the window server is checked from the environment BEFORE cv2
    is asked to open anything:

      * `opencv-python-headless` — which `bithuman` itself depends on — has no
        GUI compiled in at all. `imshow` raises `cv2.error: The function is not
        implemented. Rebuild the library with ... GTK+ 2.x or Cocoa support`.
      * full `opencv-python` on a box with no DISPLAY does not raise: the Qt
        plugin calls abort(), and the process dies on SIGABRT with no traceback
        and no chance to fall back.

    So "just pip install opencv-python" is not the fix — it trades a catchable
    error for an uncatchable one on exactly the machines (SSH, Docker, CI) where
    this example is most often run.
    """
    if sys.platform in ("darwin", "win32"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
# --- end inline helpers ---

# The sample identity: "Sofia Ramirez" (A52DHS2219), an Essence 2 agent in the
# free gallery -- `bithuman list` shows the whole gallery, and every entry there
# downloads with no account.
#
# ★FETCHED THROUGH THE DOWNLOAD DOOR, NOT FROM A BUCKET PATH. This used to name
# an object in the public Supabase bucket directly. A raw bucket URL is a second
# distribution channel for the same weights with none of the first one's rules:
# it never expires, is not rate-limited, records nothing about who fetched it,
# and cannot be closed without breaking whoever copied the link. It also pinned
# this file to one object's name, which is why the old comment here said
# changing the sample "requires a coordinated repo + Supabase update".
#
# The door answers 302 to a 1-hour signed URL, needs no credential for a
# gallery identity, and re-asks the permission check on every fetch -- so the
# sample can change without touching this file, and a future ruling that closes
# an identity actually closes it. `urlretrieve` follows the redirect.
SAMPLE_MODEL_CODE = "A52DHS2219"
SAMPLE_MODEL_URL = (
    f"https://api.bithuman.ai/v1/agent/{SAMPLE_MODEL_CODE}/model/download?model=essence-2"
)
SAMPLE_MODEL_NAME = f"{SAMPLE_MODEL_CODE}.imx"


def download_sample_model() -> str:
    """Download the sample .imx model if not already cached."""
    cache_dir = Path.home() / ".cache" / "bithuman" / "models"
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / SAMPLE_MODEL_NAME

    if model_path.exists():
        print(f"Using cached sample model: {model_path}")
        return str(model_path)

    print(f"Downloading sample avatar model (~148 MB, one-time)...")
    print(f"  Source: free-gallery agent {SAMPLE_MODEL_CODE} (Sofia Ramirez, Essence 2)")
    print(f"  Saving: {model_path}")

    import urllib.request

    is_tty = sys.stdout.isatty()
    last_pct = -1

    def _progress(block_num, block_size, total_size):
        nonlocal last_pct
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, downloaded * 100 // total_size)
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            if is_tty:
                print(f"\r  [{pct:3d}%] {mb:.0f} / {total_mb:.0f} MB", end="", flush=True)
            elif pct >= last_pct + 25:  # print at 0%, 25%, 50%, 75%, 100% for CI/logs
                print(f"  [{pct}%] {mb:.0f} / {total_mb:.0f} MB")
                last_pct = pct

    urllib.request.urlretrieve(SAMPLE_MODEL_URL, model_path, reporthook=_progress)
    if is_tty:
        print()  # newline after progress
    print(f"  Done!")
    return str(model_path)


async def main():
    p = argparse.ArgumentParser(description="bitHuman local avatar quickstart")
    p.add_argument("--model", help="Path to .imx model file (auto-downloads sample if omitted)")
    p.add_argument("--audio", default="speech.wav", help="Path to WAV/MP3 audio file (default: speech.wav)")
    p.add_argument(
        "--out",
        default="avatar.mp4",
        help="Where to write the MP4 when there is no display (default: avatar.mp4)",
    )
    args = p.parse_args()

    # Validate API secret
    secret = os.environ.get("BITHUMAN_API_SECRET")
    if not secret:
        print("Error: BITHUMAN_API_SECRET not set.")
        print()
        print("  1. Go to https://www.bithuman.ai → Developer → API Keys")
        print("  2. Copy your API secret")
        print("  3. Run: export BITHUMAN_API_SECRET='your_secret_here'")
        sys.exit(1)

    # Get model path (download sample if not specified)
    model_path = args.model or download_sample_model()
    if not Path(model_path).exists():
        print(f"Error: Model file not found: {model_path}")
        print("  Download one from https://www.bithuman.ai/#explore (click ... → Download)")
        sys.exit(1)

    # Check audio file
    if not Path(args.audio).exists():
        print(f"Error: Audio file not found: {args.audio}")
        print("  A sample speech.wav is included in this directory.")
        sys.exit(1)

    # Load the avatar runtime
    print(f"Loading model: {model_path}")
    print("  (First run may take 30s for format conversion — this is a one-time cost)")
    runtime = await AsyncAvatar.create(model_path=model_path, api_secret=secret)
    # AsyncAvatar starts its frame producer inside .create(); no explicit
    # .start() call needed.
    print("  Model loaded!")

    # Push audio
    print(f"Playing audio: {args.audio}")
    pcm, sr = load_audio(args.audio)
    pcm = float32_to_int16(pcm)
    chunk = sr // 100
    for i in range(0, len(pcm), chunk):
        await runtime.push_audio(pcm[i : i + chunk].tobytes(), sr, last_chunk=False)
    await runtime.flush()

    # Show the frames in a window when there is one, write an MP4 when there is not.
    # A render that reached a file is the same proof as a render that reached a
    # window — and on a headless box only one of the two is available.
    windowed = display_available()
    if windowed:
        # The second gate: a window SERVER exists, but this OpenCV build may still
        # have no GUI compiled in. `namedWindow` raises exactly where `imshow`
        # would, before any frame is in hand — so the fallback is chosen once,
        # not discovered mid-stream.
        try:
            cv2.namedWindow("bitHuman Avatar", cv2.WINDOW_AUTOSIZE)
        except cv2.error:
            print("This OpenCV build has no GUI (opencv-python-headless).")
            windowed = False

    writer = None
    n = 0

    if windowed:
        print("Displaying avatar (press 'q' to quit)...")
    else:
        print(f"No window available — writing {args.out} instead.")

    # ★A FILE NEEDS AN END AND A WINDOW DOES NOT. `runtime.run()` does not stop
    # when the pushed audio runs out — it goes on yielding the idle loop, which
    # is exactly right behind a window you close with 'q'. Writing that to disk
    # instead just grows a file until something kills it. `audio_chunk` is None
    # once the runtime is back in its idle loop, so the first idle frame AFTER
    # we have seen speech is the end of what we pushed.
    spoke = False

    async for frame in runtime.run():
        if frame.audio_chunk is not None:
            spoke = True
        elif spoke and not windowed:
            break
        if not frame.has_image:
            continue
        n += 1
        if windowed:
            cv2.imshow("bitHuman Avatar", frame.bgr_image)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            if writer is None:
                h, w = frame.bgr_image.shape[:2]
                writer = cv2.VideoWriter(
                    args.out, cv2.VideoWriter_fourcc(*"mp4v"), runtime.fps, (w, h)
                )
                if not writer.isOpened():
                    print(f"Error: could not open {args.out} for writing.")
                    sys.exit(1)
            writer.write(frame.bgr_image)

    if writer is not None:
        writer.release()
        print(f"Wrote {args.out} — {n} frames at {runtime.fps} fps.")
    else:
        cv2.destroyAllWindows()

    await runtime.stop()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
