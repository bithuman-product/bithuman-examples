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

# 3. something for it to say — macOS makes this for you
echo "==> synthesising speech16k.wav"
say -o /tmp/ios-expression2.aiff \
  "Hello. I am a bit Human avatar, rendered on this phone, with no server in the loop."
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/ios-expression2.aiff Sources/Model/speech16k.wav
rm -f /tmp/ios-expression2.aiff

echo "==> Sources/Model is ready:"
du -sh Sources/Model/*
