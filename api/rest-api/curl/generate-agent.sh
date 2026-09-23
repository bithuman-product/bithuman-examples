#!/usr/bin/env bash
# Generate a new avatar agent and poll until it is ready.
# Usage: ./generate-agent.sh ["Your system prompt here"]
# Model: BITHUMAN_MODEL=essence-2 | expression-2 (default) | auto.
# Creation is a one-time credit charge: https://docs.bithuman.ai/guides/pricing
# A second-generation agent takes about 2 to 2.5 hours to create.
set -euo pipefail

API_SECRET="${BITHUMAN_API_SECRET:?Set BITHUMAN_API_SECRET first (get yours at https://www.bithuman.ai/developer/api-keys)}"
BASE="https://api.bithuman.ai"

PROMPT="${1:-You are a friendly AI assistant.}"
MODEL="${BITHUMAN_MODEL:-expression-2}"

echo "Starting agent generation..."
echo "  Prompt: $PROMPT"
echo "  Model:  $MODEL"
echo ""

# 1. Start generation
RESPONSE=$(curl -s -X POST "$BASE/v1/agent/generate" \
  -H "Content-Type: application/json" \
  -H "api-secret: $API_SECRET" \
  -d "{\"prompt\": \"$PROMPT\", \"model\": \"$MODEL\", \"aspect_ratio\": \"16:9\"}")

echo "$RESPONSE" | python3 -m json.tool

# Extract agent_id from response
AGENT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('agent_id', ''))")

if [ -z "$AGENT_ID" ]; then
  echo "Error: No agent_id in response. Check the output above."
  exit 1
fi

echo ""
echo "Agent ID: $AGENT_ID"
echo "Polling status (a second-generation agent takes about 2 to 2.5 hours)..."
echo ""

# 2. Poll until ready or failed
while true; do
  STATUS_RESPONSE=$(curl -s "$BASE/v1/agent/status/$AGENT_ID" \
    -H "Content-Type: application/json" \
    -H "api-secret: $API_SECRET")

  STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('status', 'unknown'))")
  PROGRESS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; p = json.load(sys.stdin).get('data', {}).get('progress'); print(f'{int(round(p * 100))}%' if p is not None else 'N/A')")

  echo "  Status: $STATUS  Progress: $PROGRESS"

  if [ "$STATUS" = "ready" ]; then
    echo ""
    echo "Agent is ready!"
    echo "$STATUS_RESPONSE" | python3 -m json.tool
    break
  fi

  if [ "$STATUS" = "failed" ]; then
    echo ""
    echo "Generation failed."
    echo "$STATUS_RESPONSE" | python3 -m json.tool
    exit 1
  fi

  sleep 30
done
