#!/bin/bash
# setup.sh — fetch everything the app needs. A sample avatar needs no account.
#   ./setup.sh              # warm-clear-professional-presenter
#   ./setup.sh A52DHS2219   # any code from the table in README.md
#   BITHUMAN_API_SECRET=… ./setup.sh <AGENT_CODE>   # your own agent
set -euo pipefail
cd "$(dirname "$0")"
CODE="${1:-A21SKT4314}"
REL=https://github.com/bithuman-product/homebrew-bithuman/releases/download/essence2-v1.14.0
ASSET=libessence2-resources.zip   # the release asset's frozen legacy name
mkdir -p Sources/Model Sources/EngineResources
AUTH=()
if [ -n "${BITHUMAN_API_SECRET:-}" ]; then AUTH=(-H "api-secret: $BITHUMAN_API_SECRET"); fi

# 1 · the identity. One URL; a sample needs no credential, your own agent sends
#     BITHUMAN_API_SECRET. The door answers 302 to a one-hour signed URL.
echo "==> downloading $CODE.imx"
curl -fL --progress-bar "${AUTH[@]+"${AUTH[@]}"}" \
  "https://api.bithuman.ai/v1/agent/$CODE/model/download?model=essence-2" \
  -o Sources/Model/agent.imx

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
echo "==> downloading the engine resources"
curl -fL --progress-bar -o "$ASSET"        "$REL/$ASSET"
curl -fL                -o "$ASSET.sha256" "$REL/$ASSET.sha256"
shasum -a 256 -c "$ASSET.sha256"
unzip -o -q "$ASSET" -d Sources/EngineResources

# 4 · something for it to say. `say` and `afconvert` ship with macOS.
echo "==> making speech16k.wav"
say -o /tmp/e2-speech.aiff \
  "Hello. Every frame you are watching was rendered on this phone."
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/e2-speech.aiff Sources/Model/speech16k.wav

echo "==> ready:"
du -sh Sources/Model Sources/EngineResources
