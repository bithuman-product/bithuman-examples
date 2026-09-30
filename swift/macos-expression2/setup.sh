#!/bin/bash
# Fetch the three files the example needs into Model/. The default identity is in
# the public showcase, so these downloads are anonymous; rendering needs your API secret.
#
#   ./setup.sh                                      # Wise Pup, the showcase identity
#   BITHUMAN_API_SECRET=… ./setup.sh <AGENT_CODE>   # your own agent
set -euo pipefail
cd "$(dirname "$0")"

# Never stop half-way in silence: say which step failed and what to do.
trap 'echo >&2; echo "setup.sh stopped: \"$BASH_COMMAND\" failed (line $LINENO). Nothing after it ran — fix the error above and run ./setup.sh again." >&2' ERR

SHOWCASE=A23WJF0199          # wise-pup, expression-2, public showcase
CODE="${1:-$SHOWCASE}"
mkdir -p Model

AUTH=()
if [ -n "${BITHUMAN_API_SECRET:-}" ]; then
  AUTH=(-H "api-secret: $BITHUMAN_API_SECRET")
elif [ "$CODE" != "$SHOWCASE" ]; then
  echo "set BITHUMAN_API_SECRET to fetch your own agent ($CODE), or run with no argument for the showcase identity" >&2
  exit 2
fi

# fetch <out> <url> [curl args…]: download, and on an HTTP error print what the
# server said (plain `curl -f` hides it) instead of just exiting.
fetch() {
  local out=$1 url=$2; shift 2
  if curl -L --fail-with-body --progress-bar "$@" -o "$out" "$url"; then return 0; fi
  echo "error: download failed: $url" >&2
  if [ -s "$out" ] && [ "$(wc -c <"$out")" -lt 4096 ]; then
    echo "the server said: $(cat "$out")" >&2
  fi
  rm -f "$out"
  case "$url" in *api.bithuman.ai*)
    echo "hint: a 401/403 means this avatar is not public — set BITHUMAN_API_SECRET to a key of the account that owns it." >&2 ;;
  esac
  return 1
}

# 1. the identity (about 188 MB). A showcase identity and your own agent come
#    through the same door; the only difference is whether a credential rides
#    along. It answers 302 to a signed URL that expires in an hour.
echo "==> $CODE.imx"
fetch Model/agent.imx \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?model=expression-2" \
  "${AUTH[@]+"${AUTH[@]}"}"

# 2. the shared engine graphs (about 165 MB) — one artifact per platform, not
#    one per identity. Anonymous, and the same file for every agent you open.
echo "==> shared engine"
fetch Model/shared-engine.imx \
  "https://github.com/bithuman-product/homebrew-bithuman/releases/download/expression2-engine-mac-arm64-1.0.0/mac-arm64-1.0.0.engine"

# 3. something for it to say — 16 kHz mono, out of the identity's own bundle.
echo "==> speech16k.wav"
fetch Model/speech16k.wav \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?model=expression-2&member=demo_speech_16k.wav" \
  "${AUTH[@]+"${AUTH[@]}"}"

# Both downloads are IMX containers and the first four bytes say so. A file
# that fails this is a truncated or redirected download, not a model.
for f in Model/agent.imx Model/shared-engine.imx; do
  head -c 4 "$f" | grep -q 'IMX' || { echo "$f is not an IMX container — re-run" >&2; exit 1; }
done

echo "==> Model is ready:"
du -h Model/*
echo "Next: export BITHUMAN_API_SECRET=… and run  swift run -c release MacOSExpression2"
