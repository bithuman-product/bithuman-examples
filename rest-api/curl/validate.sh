#!/usr/bin/env bash
# Validate your bitHuman API credentials.
# Prints {"valid": true|false}; exits 1 when the secret is not valid.
set -euo pipefail

API_SECRET="${BITHUMAN_API_SECRET:?Set BITHUMAN_API_SECRET first (get yours at https://www.bithuman.ai/developer/api-keys)}"
BASE="https://api.bithuman.ai"

RESP=$(curl -s -X POST "$BASE/v1/validate" \
  -H "Content-Type: application/json" \
  -H "api-secret: $API_SECRET")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | python3 -c 'import sys,json; sys.exit(0 if json.load(sys.stdin).get("valid") else 1)'
