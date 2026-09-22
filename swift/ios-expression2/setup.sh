#!/bin/bash
# Fetch the three things the app needs into Sources/Model/.
# Usage:  ./setup.sh                                   # the free showcase identity, no account
#         BITHUMAN_API_SECRET=… ./setup.sh <AGENT_CODE>  # your own agent
set -euo pipefail
cd "$(dirname "$0")"

# The default is Wise Pup (A23WJF0199), an expression-2 identity in the free
# gallery: `GET /v1/agent/<CODE>/model/download` serves a gallery identity to
# anyone, so the no-argument path needs no account, no key and no credits.
# `bithuman list` shows the whole gallery if you want a different face.
SHOWCASE_CODE="A23WJF0199"
CODE="${1:-$SHOWCASE_CODE}"
mkdir -p Sources/Model

# Step 2 below needs the bitHuman CLI, which is not a SwiftPM dependency and
# cannot be one. Say so HERE rather than after a 188 MB download: the script
# used to fail at `bithuman: command not found` with the identity already on
# disk and no clue what to install.
if ! command -v bithuman >/dev/null 2>&1; then
  echo "the bithuman CLI is not on PATH. Install it, then run this again:" >&2
  echo "    brew install bithuman-product/bithuman/bithuman-cli" >&2
  exit 3
fi

# 1. the per-identity avatar.
#
# ★ONE URL FOR BOTH ROUTES, WHICH IS THE POINT. The showcase identity and your
# own agent come through the SAME door; the only difference is whether a
# credential rides along. That door 302s to a 1-hour signed URL, rate-limits,
# and re-asks permission on every fetch. Do not replace it with a public bucket
# path — those never expire, record nothing, and cannot be closed.
AUTH=()
if [ -n "${BITHUMAN_API_SECRET:-}" ]; then
  AUTH=(-H "api-secret: $BITHUMAN_API_SECRET")
elif [ "$CODE" != "$SHOWCASE_CODE" ]; then
  echo "set BITHUMAN_API_SECRET to fetch your own agent ($CODE), or run with no argument for the free showcase identity"
  exit 2
fi
echo "==> downloading $CODE.avatar"
curl -fL --progress-bar "${AUTH[@]+"${AUTH[@]}"}" \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?model=expression-2" \
  -o Sources/Model/agent.avatar
ls -l Sources/Model/agent.avatar

# 2. the shared speech front-end the artifact does not carry
echo "==> installing the shared engine graphs"
bithuman engine install mac
rm -rf Sources/Model/shared_engine
cp -R "$HOME/.bithuman/engines/mac-1.0.0" Sources/Model/shared_engine

# 3. something for it to say. The identity's own bundle already carries a
#    16 kHz mono clip, so this needs no key and no TTS: `member=` asks the SAME
#    door as step 1 for ONE file out of the bundle instead of the whole
#    container, and takes the same credential (none, for a gallery identity).
echo "==> downloading speech16k.wav"
curl -fL --progress-bar "${AUTH[@]+"${AUTH[@]}"}" \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?member=demo_speech_16k.wav&model=expression-2" \
  -o Sources/Model/speech16k.wav

echo "==> Sources/Model is ready:"
du -sh Sources/Model/*
