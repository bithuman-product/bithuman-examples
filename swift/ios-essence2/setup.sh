#!/bin/bash
# setup.sh — fetch everything the app needs. No account, no key.
#   ./setup.sh              # warm-clear-professional-presenter
#   ./setup.sh A52DHS2219   # any code from the table in README.md
set -euo pipefail
cd "$(dirname "$0")"
CODE="${1:-A21SKT4314}"
REL=https://github.com/bithuman-product/homebrew-bithuman/releases/download/essence2-v1.14.1
mkdir -p Sources/Model Sources/EngineResources

# 1 · the identity. One URL, no credential: the door answers 302 to a one-hour
#     signed URL and curl -L follows it.
echo "==> downloading $CODE.imx"
curl -fL --progress-bar \
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
echo "==> downloading the engine's three runtime files (the release Essence2Kit pins)"
for f in w2v_ess_fp16_v1.onnx audio_encoder_fp16_window_trunk.onnx audio_encoder_fp16_window_head.onnx; do
  curl -fL --progress-bar -o "Sources/EngineResources/$f"      "$REL/$f"
  curl -fL                -o "Sources/EngineResources/$f.sha256" "$REL/$f.sha256"
  (cd Sources/EngineResources && shasum -a 256 -c "$f.sha256" && rm -f "$f.sha256")
done

echo "==> making speech16k.wav"
say -o /tmp/e2-speech.aiff \
  "Hello. Every frame you are watching was rendered on this phone."
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/e2-speech.aiff Sources/Model/speech16k.wav

echo "==> ready:"
du -sh Sources/Model Sources/EngineResources
