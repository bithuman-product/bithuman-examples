"""Play an audio file through an avatar running on this machine, in a window.

The avatar renders in this process. What reaches bitHuman is the credential check,
the one-time model download and usage reports, never the audio or the frames.

    export BITHUMAN_API_SECRET=...        # from https://www.bithuman.ai/developer/api-keys
    pip install -r requirements.txt

    python local-avatar.py                                  # downloads a sample avatar
    python local-avatar.py --model your-avatar.imx          # or bring your own
    python local-avatar.py --model a.imx --audio speech.wav

Press q to quit.
"""

import argparse
import os
import sys
import urllib.request
from pathlib import Path

import cv2

import bithuman

# "Sofia Ramirez" — an Essence 2 avatar in the public gallery, so this download
# is anonymous. `bithuman list` shows the rest of the gallery.
SAMPLE_CODE = "A52DHS2219"
SAMPLE_URL = f"https://api.bithuman.ai/v1/agent/{SAMPLE_CODE}/model/download?model=essence-2"

WINDOW = "bitHuman avatar"
MAX_WINDOW_HEIGHT = 900  # Essence 2 frames are 1080x1920; scale them to fit a laptop screen

NO_WINDOW = """No display, so there is no window to draw the avatar in.

To render to an MP4 file instead, the SDK does it in one command:

    python -m bithuman render sofia-ramirez speech.wav     # writes sofia-ramirez.mp4
    python -m bithuman render your-avatar.imx speech.wav   # or your own avatar file

On a desktop with a display, this example opens a window as written."""


def sample_model() -> str:
    """Download the sample avatar on first use; reuse it afterwards."""
    path = Path.home() / ".cache" / "bithuman" / "models" / f"{SAMPLE_CODE}.imx"
    if path.exists():
        return str(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading the sample avatar (~148 MB, once) to {path}")
    urllib.request.urlretrieve(SAMPLE_URL, path)
    return str(path)


def require_window() -> None:
    """Stop before downloading or rendering anything if there is no window to draw in.

    Two checks, in this order:
      1. Is a display named at all? The GUI build of OpenCV does not raise when
         there is none: Qt aborts the process (SIGABRT) with nothing to catch.
         So the environment is checked before cv2 opens anything.
      2. Can this OpenCV open a window? `opencv-python-headless` (which
         `bithuman` depends on) raises here instead of later, mid-render.
    """
    if sys.platform not in ("darwin", "win32") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        sys.exit(NO_WINDOW)
    try:
        cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    except cv2.error:
        sys.exit(NO_WINDOW)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", help="a .imx avatar (default: download the sample)")
    p.add_argument("--audio", default="speech.wav", help="any audio file (default: speech.wav)")
    args = p.parse_args()

    if not os.environ.get("BITHUMAN_API_SECRET"):
        sys.exit(
            "Set BITHUMAN_API_SECRET first — create one at\n"
            "https://www.bithuman.ai → Developer → API Secrets:\n\n"
            "    export BITHUMAN_API_SECRET='your_key'"
        )
    if not Path(args.audio).exists():
        sys.exit(f"No audio file at {args.audio}")

    # Before the 148 MB download and before anything bills.
    require_window()

    model = args.model or sample_model()

    # The whole surface: open an avatar, render audio through it. Each frame is
    # a (height, width, 3) uint8 array in RGB; OpenCV wants BGR, hence the flip.
    # Leaving the `with` block frees the model.
    with bithuman.open(model) as avatar:
        for frame in avatar.render(args.audio):
            bgr = frame[:, :, ::-1]
            if bgr.shape[0] > MAX_WINDOW_HEIGHT:
                scale = MAX_WINDOW_HEIGHT / bgr.shape[0]
                bgr = cv2.resize(bgr, (round(bgr.shape[1] * scale), MAX_WINDOW_HEIGHT),
                                 interpolation=cv2.INTER_AREA)
            cv2.imshow(WINDOW, bgr)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
