#!/bin/bash
# setup.sh — fetch everything the app needs. A sample avatar downloads anonymously.
#   ./setup.sh              # warm-clear-professional-presenter
#   ./setup.sh A52DHS2219   # any code from the table in README.md
#   BITHUMAN_API_SECRET=… ./setup.sh <AGENT_CODE>   # your own agent
set -euo pipefail
cd "$(dirname "$0")"

# Never stop half-way in silence: say which step failed and what to do.
trap 'echo >&2; echo "setup.sh stopped: \"$BASH_COMMAND\" failed (line $LINENO). Nothing after it ran — fix the error above and run ./setup.sh again." >&2' ERR

CODE="${1:-A21SKT4314}"
# The Essence 2 runtime files of the release the Swift package pins
# (Essence2Resources.releaseTag in Swift package 2.20.1). Raise it with the package.
ESSENCE2_TAG=essence2-v1.15.3   # keep equal to the tag in REL below
REL=https://github.com/bithuman-product/homebrew-bithuman/releases/download/essence2-v1.15.4
mkdir -p Sources/Model Sources/EngineResources
AUTH=()
if [ -n "${BITHUMAN_API_SECRET:-}" ]; then AUTH=(-H "api-secret: $BITHUMAN_API_SECRET"); fi

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

# 1 · the identity. One URL; a sample needs no credential, your own agent sends
#     BITHUMAN_API_SECRET. The door answers 302 to a one-hour signed URL.
echo "==> downloading $CODE.imx"
fetch Sources/Model/agent.imx \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?model=essence-2" \
  "${AUTH[@]+"${AUTH[@]}"}"

# 2 · prove it is the container this engine opens BEFORE you open Xcode.
#     An error page and a truncated download both look like a file.
python3 - <<'PY'
import struct, sys
p = "Sources/Model/agent.imx"
b = open(p, "rb")
head = b.read(8)
if head[:4] != b"IMX\0":
    sys.exit(f"{p} does not start with IMX\\0 — got {head[:4]!r}. Re-run ./setup.sh")
ver, n = struct.unpack("<HH", head[4:8])
if ver != 2:
    sys.exit(f"{p} is an IMX v{ver} container; this engine opens v2.")
names, blob = [], b.read(1 << 16)
off = 0
for _ in range(n):
    (ln,) = struct.unpack_from("<H", blob, off); off += 2
    names.append(blob[off:off + ln].decode("utf-8", "replace")); off += ln + 16
if "manifest.json" not in names:
    sys.exit(f"{p} has no manifest.json member — this is not an essence-2 bundle.")
print(f"OK: IMX v2, {n} members, manifest.json present")
PY

# 3 · the shared engine resources, checksum-verified against the sidecar
#     published beside them.
echo "==> downloading the engine's three runtime files ($ESSENCE2_TAG)"
for f in w2v_ess_fp16_v1.onnx audio_encoder_fp16_window_trunk.onnx audio_encoder_fp16_window_head.onnx; do
  fetch "Sources/EngineResources/$f"        "$REL/$f"
  fetch "Sources/EngineResources/$f.sha256" "$REL/$f.sha256" --silent --show-error
  (cd Sources/EngineResources && shasum -a 256 -c "$f.sha256" && rm -f "$f.sha256")
done

echo "==> making speech16k.wav"
TMP_AIFF="$(mktemp -t e2-speech).aiff"
say -o "$TMP_AIFF" \
  "Hello. Every frame you are watching was rendered on this phone."
afconvert -f WAVE -d LEI16@16000 -c 1 "$TMP_AIFF" Sources/Model/speech16k.wav
rm -f "$TMP_AIFF"

echo "==> ready:"
du -sh Sources/Model Sources/EngineResources
echo "Next: open IOSEssence2.xcodeproj, set BITHUMAN_API_SECRET in the scheme, pick your team and your iPhone, Run."
