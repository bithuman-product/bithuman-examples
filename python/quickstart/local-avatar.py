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


def sample_model() -> str:
    """Download the sample avatar on first use; reuse it afterwards."""
    path = Path.home() / ".cache" / "bithuman" / "models" / f"{SAMPLE_CODE}.imx"
    if path.exists():
        return str(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading the sample avatar (~148 MB, once) to {path}")
    urllib.request.urlretrieve(SAMPLE_URL, path)
    return str(path)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", help="a .imx avatar (default: download the sample)")
    p.add_argument("--audio", default="speech.wav", help="any audio file (default: speech.wav)")
    args = p.parse_args()

    if not os.environ.get("BITHUMAN_API_SECRET"):
        sys.exit(
            "Set BITHUMAN_API_SECRET first — it is free at\n"
            "https://www.bithuman.ai → Developer → API Keys:\n\n"
            "    export BITHUMAN_API_SECRET='your_key'"
        )
    if not Path(args.audio).exists():
        sys.exit(f"No audio file at {args.audio}")

    model = args.model or sample_model()

    # The whole surface: open an avatar, render audio through it. Each frame is
    # a (height, width, 3) uint8 array in RGB; OpenCV wants BGR, hence the flip.
    # Leaving the `with` block frees the model.
    with bithuman.open(model) as avatar:
        for frame in avatar.render(args.audio):
            cv2.imshow("bitHuman avatar", frame[:, :, ::-1])
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
