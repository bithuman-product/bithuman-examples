#!/bin/bash
# Fetch the three files the example needs into Model/. Nothing here needs an
# account, a key or credits: the default identity is in the free showcase.
#
#   ./setup.sh                                      # Wise Pup, the showcase identity
#   BITHUMAN_API_SECRET=… ./setup.sh <AGENT_CODE>   # your own agent
set -euo pipefail
cd "$(dirname "$0")"

SHOWCASE=A23WJF0199          # wise-pup, expression-2, free showcase
CODE="${1:-$SHOWCASE}"
mkdir -p Model

AUTH=()
if [ -n "${BITHUMAN_API_SECRET:-}" ]; then
  AUTH=(-H "api-secret: $BITHUMAN_API_SECRET")
elif [ "$CODE" != "$SHOWCASE" ]; then
  echo "set BITHUMAN_API_SECRET to fetch your own agent ($CODE), or run with no argument for the showcase identity" >&2
  exit 2
fi

# 1. the identity (about 188 MB). A showcase identity and your own agent come
#    through the same door; the only difference is whether a credential rides
#    along. It answers 302 to a signed URL that expires in an hour.
echo "==> $CODE.imx"
curl -fL --progress-bar "${AUTH[@]+"${AUTH[@]}"}" \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?model=expression-2" \
  -o Model/agent.imx

# 2. the shared engine graphs (about 165 MB) — one artifact per platform, not
#    one per identity. Anonymous, and the same file for every agent you open.
echo "==> shared engine"
curl -fL --progress-bar \
  "https://tmoobjxlwcwvxvjeppzq.supabase.co/storage/v1/object/public/web/engines/expression-2/mac-arm64-1.0.0.engine" \
  -o Model/shared-engine.imx

# 3. something for it to say — 16 kHz mono, out of the identity's own bundle.
echo "==> speech16k.wav"
curl -fL --progress-bar "${AUTH[@]+"${AUTH[@]}"}" \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?model=expression-2&member=demo_speech_16k.wav" \
  -o Model/speech16k.wav

# Both downloads are IMX containers and the first four bytes say so. A file
# that fails this is a truncated or redirected download, not a model.
for f in Model/agent.imx Model/shared-engine.imx; do
  head -c 4 "$f" | grep -q 'IMX' || { echo "$f is not an IMX container — re-run" >&2; exit 1; }
done

echo "==> Model is ready:"
du -h Model/*
