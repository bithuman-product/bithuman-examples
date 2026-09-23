"""Play an audio file through an avatar running on this machine, in a window.

Nothing is sent anywhere to make a frame: the model runs in this process.

    export BITHUMAN_API_SECRET=...        # free at https://www.bithuman.ai
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

# "Sofia Ramirez" — an Essence 2 avatar in the free gallery, so this download
# needs no account. `bithuman list` shows the rest of the gallery.
SAMPLE_CODE = "A52DHS2219"
SAMPLE_URL = f"https://api.bithuman.ai/v1/agent/{SAMPLE_CODE}/model/download?model=essence-2"

WINDOW = "bitHuman avatar"

# This example is about the window. When there is no window, the SDK already
# ships the one-liner that writes a file instead, so there is nothing for this
# example to reimplement — and it cannot reimplement it honestly anyway: the
# frame rate belongs to the avatar (essence-2 renders at 25 fps, expression-2
# at 20), and `Avatar` deliberately publishes one method, so an example that
# wrote its own MP4 would have to guess the rate or reach past the taught
# surface to find it.
NO_WINDOW = """No display, so there is no window to draw the avatar in.

To render to a file instead, the SDK does it in one command:

    python -m bithuman <avatar> <audio>        # writes <avatar>.mp4

Pass the same avatar and audio you would have passed here. On a desktop with
a display, this example opens a window as written."""


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
    """Refuse before the render if this machine cannot show one.

    ★THE ORDER OF THESE TWO GATES IS THE WHOLE POINT, because only the second
    failure is catchable and the first one kills the process.

      1. The GUI build of OpenCV on a box with no display does NOT raise. Qt
         fails to load its xcb platform plugin and calls abort(): the process
         dies on SIGABRT with no traceback and no except clause that can help.
         Measured 2026-09-22 on a headless Linux box with this directory's own
         requirements.txt — `cv2.imshow` exited 134. So the environment is
         read FIRST, and cv2 is not asked to open anything until it passes.
      2. Only then can `namedWindow` be called safely. It raises exactly where
         `imshow` would if this OpenCV has no GUI compiled in
         (`opencv-python-headless`, which `bithuman` itself depends on), and
         raising here means the answer is known BEFORE a frame is rendered
         rather than discovered mid-stream.

    Both gates run before `bithuman.open()`, so a machine that cannot show the
    avatar is told so without downloading 148 MB or billing a render.

    The limit, stated rather than papered over: gate 1 reads whether a display
    is NAMED, not whether it answers. `DISPLAY=:0` pointing at nothing still
    reaches Qt and still aborts. Covering that honestly means probing the
    display from a subprocess, which is more machinery than a quickstart should
    carry — and the shapes this example actually lands in (ssh, Docker, CI)
    name no display at all.
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
            "Set BITHUMAN_API_SECRET first — it is free at\n"
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
            cv2.imshow(WINDOW, frame[:, :, ::-1])
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
