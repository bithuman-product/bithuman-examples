#!/bin/bash
# Fetch the three files the app needs into Sources/Model/. Nothing to install:
# three downloads, the same ones docs.bithuman.ai/platforms/ios "First frame" uses.
# Usage:  ./setup.sh                                     # the public showcase avatar, anonymous download
#         BITHUMAN_API_SECRET=… ./setup.sh <AGENT_CODE>  # your own agent
set -euo pipefail
cd "$(dirname "$0")"

# Never stop half-way in silence: say which step failed and what to do.
trap 'echo >&2; echo "setup.sh stopped: \"$BASH_COMMAND\" failed (line $LINENO). Nothing after it ran — fix the error above and run ./setup.sh again." >&2' ERR

# The default is Wise Pup (A23WJF0199), an expression-2 avatar in the public
# gallery: the download door serves a gallery avatar to anyone, so the
# no-argument download is anonymous. Rendering needs your API secret.
SHOWCASE_CODE="A23WJF0199"
CODE="${1:-$SHOWCASE_CODE}"
mkdir -p Sources/Model

AUTH=()
if [ -n "${BITHUMAN_API_SECRET:-}" ]; then
  AUTH=(-H "api-secret: $BITHUMAN_API_SECRET")
elif [ "$CODE" != "$SHOWCASE_CODE" ]; then
  echo "set BITHUMAN_API_SECRET to fetch your own agent ($CODE), or run with no argument for the public showcase avatar" >&2
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

# 1. the avatar (about 188 MB). The showcase avatar and your own agent come
#    through the SAME door; the only difference is whether a credential rides
#    along. It answers 302 to a signed URL that expires in an hour.
echo "==> downloading $CODE.imx"
fetch Sources/Model/agent.imx \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?model=expression-2" \
  "${AUTH[@]+"${AUTH[@]}"}"

# 2. the shared engine graphs (about 165 MB): one file for every avatar, not one
#    per avatar, anonymous. The `mac` engine file is the right one for iPhone too.
echo "==> downloading the shared engine"
fetch Sources/Model/shared-engine.imx \
  "https://downloads.bithuman.ai/homebrew-bithuman/expression2-engine-mac-arm64-1.0.0/mac-arm64-1.0.0.engine"

# 3. something for it to say: 16 kHz mono, one file out of the avatar's own
#    bundle (`member=`), through the same door and with the same credential.
echo "==> downloading speech16k.wav"
fetch Sources/Model/speech16k.wav \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?model=expression-2&member=demo_speech_16k.wav" \
  "${AUTH[@]+"${AUTH[@]}"}"

# Both big downloads are IMX containers and the first four bytes say so. A file
# that fails this is a truncated or redirected download, not a model.
for f in Sources/Model/agent.imx Sources/Model/shared-engine.imx; do
  head -c 4 "$f" | grep -q 'IMX' || { echo "$f is not an IMX container — re-run ./setup.sh" >&2; exit 1; }
done

echo "==> Sources/Model is ready:"
du -sh Sources/Model/*
echo "Next: open IOSExpression2.xcodeproj, set BITHUMAN_API_SECRET in the scheme, pick your team and device, Run."
