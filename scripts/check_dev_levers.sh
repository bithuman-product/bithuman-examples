#!/bin/bash
# check_dev_levers.sh — the app's dev levers have ONE door, and a release build has no key.
#
# Every `--dart-define` that makes this app drive itself (BH_SCRIPT, BH_SCRIPT_GAP_S) is
# declared in app/avatar_chat/lib/dev_levers.dart as `enabled && …` / `enabled ? … : …`
# with `enabled = !kReleaseMode` — a compile-time constant, so `flutter build --release`
# folds it away. Configuration defines (credential, identity, engine, mic mode) are the
# ALLOWED list below and stay plain. Anything else calling fromEnvironment outside the
# door is refused. The release arm in flutter-tests.yml is the behavioural half.
set -uo pipefail
cd "$(dirname "$0")/.."
APP=app/avatar_chat/lib
DOOR=$APP/dev_levers.dart
ALLOWED='BITHUMAN_API_SECRET|AGENT_DIR|AGENT_CODE|BH_ENGINE|BH_MIC'
BAD=0
err() { echo "::error::$*"; BAD=$((BAD+1)); }
[ -f "$DOOR" ] || err "missing $DOOR — the door is gone"
while IFS=: read -r f n rest; do
  [ -n "${f:-}" ] || continue
  [ "$f" = "$DOOR" ] && continue
  name=$(echo "$rest" | grep -oE "fromEnvironment\('[A-Z0-9_]+'" | sed "s/fromEnvironment('//;s/'//")
  echo "$name" | grep -qE "^($ALLOWED)$" || err "file=$f,line=$n::dev lever read outside dev_levers.dart: ${rest}"
done < <(grep -rnE '\.fromEnvironment\(' "$APP" || true)
if [ -f "$DOOR" ]; then
  grep -qE 'static const bool enabled = !kReleaseMode;' "$DOOR" || err "file=$DOOR::'enabled' must be exactly '!kReleaseMode'"
  while IFS=: read -r n rest; do
    [ -n "${n:-}" ] || continue
    ctx=$(sed -n "$((n-1)),${n}p" "$DOOR" | tr '\n' ' ')
    echo "$ctx" | grep -qE 'enabled (&&|\?)' || err "file=$DOOR,line=$n::lever not guarded by 'enabled': ${rest}"
  done < <(grep -nE '\.fromEnvironment\(' "$DOOR" | grep -v 'dart.vm.product' || true)
fi
if [ "$BAD" -gt 0 ]; then echo "FAIL: $BAD dev-lever violation(s)"; exit 1; fi
echo "OK: dev levers only in dev_levers.dart, each gated on !kReleaseMode; config defines ($ALLOWED) untouched"
