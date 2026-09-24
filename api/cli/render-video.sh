#!/usr/bin/env bash
# Render a lip-synced MP4 from a model + audio with `bithuman render`.
# Get your API secret at https://www.bithuman.ai (Developer section).
#
# ── WHERE THIS ACTUALLY WORKS (measured 2026-09-04, CLI 2.5.1) ───────────────
# This script is validated for ONE combination: expression-2 on Linux x86_64.
# It was run end-to-end there and produced 60 frames of h264+aac that decode
# cleanly. The other combinations do NOT work today:
#
#   expression-2 · Linux x86_64   ✓ verified (this script)
#   expression-2 · macOS arm64    ✗ engine under-produces (53 of 60 frames),
#                                   exits non-zero — and STILL leaves the
#                                   truncated mp4 at -o. Do not trust
#                                   "the file exists" as success.
#   essence-1    · Linux x86_64   ✗ "audio_decode: avformat_open_input failed"
#                                   for wav/mp3/m4a/flac alike.
#   essence-1    · macOS arm64    ✗ "video encoder unavailable on macOS in this
#                                   libessence build".
#   essence-2    · Linux x86_64   ✗ the Linux tarball ships no lible_core.so.
#                                   Use the Python SDK instead:
#                                     pip install 'bithuman[offline]'
#                                     python -c "from bithuman.offline \
#                                       import render_offline; \
#                                       print(render_offline(imx, wav, out_mp4=out))"
#                                   Gate on stats["borrow_state"] == "borrowed",
#                                   never on the frame count.
#
# The previous version of this file claimed render "is implemented on Linux
# only", which reads as "all families work on Linux". Only expression-2 does.
set -euo pipefail

export BITHUMAN_API_SECRET="${BITHUMAN_API_SECRET:?Set BITHUMAN_API_SECRET first}"

# Install the CLI (the curl installer is the channel that works on Linux; the
# CLI is not on PyPI — `pip install bithuman-cli` 404s):
#   curl -fsSL https://raw.githubusercontent.com/bithuman-product/homebrew-bithuman/main/install.sh | sh
#   brew install bithuman-product/bithuman/bithuman-cli      # macOS

MODEL="${1:?Usage: ./render-video.sh <expression-2 model.imx>}"
OUT="${2:-demo.mp4}"

# ★`-f` IS LOAD-BEARING, and the missing `-f` is why this mattered. Without it
# curl writes the server's error BODY to the file and still exits 0. This line
# pointed into `homebrew-bithuman/Examples/`, a tree that has been retired, so a
# fresh run produced a 14-byte `speech.wav` whose contents were the text
# `404: Not Found` — and the render then failed on a corrupt WAV, one step away
# from the real cause. Measured 2026-09-22: that URL answers 404, `curl -sO`
# exits 0, and the file it leaves behind is 14 bytes.
if [ ! -f speech.wav ]; then
  curl -fsSLo speech.wav \
    https://raw.githubusercontent.com/bithuman-product/bithuman-examples/main/python/local-essence/speech.wav
fi

# A WAV is 44 bytes of header before a single sample, so anything this small is
# not audio however it got here. The check is the floor that makes the next dead
# URL an error instead of a puzzle.
if [ "$(wc -c < speech.wav)" -lt 1024 ]; then
  echo "speech.wav is $(wc -c < speech.wav) bytes — that is not audio. Delete it and re-run." >&2
  exit 1
fi

bithuman render "$MODEL" speech.wav -o "$OUT"

# ★Verify the artifact rather than trusting the exit code alone — a truncated
# render can leave a decodable file behind.
frames=$(ffprobe -v error -count_frames -select_streams v:0 \
           -show_entries stream=nb_read_frames -of csv=p=0 "$OUT")
echo "Done: $OUT — ${frames} video frames decoded."
