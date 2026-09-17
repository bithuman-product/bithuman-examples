#!/bin/bash
# prove_release_ignores_dev_levers.sh — A RELEASE APK BUILT WITH EVERY DEV LEVER SET CARRIES NONE OF THEM.
#
# Builds app/avatar_chat twice with every dev lever set to a SENTINEL value: `--release`
# (what ships) and `--profile` (AOT too, but kReleaseMode is false — the control). The
# sentinel must be ABSENT from the release libapp.so and PRESENT in the profile one: the
# lever's value never entered the shipped snapshot, and the arm was looking.
#
# Two lever sets: this app's (BH_SCRIPT) and the plugin's (BH_MIC_FILE,
# BITHUMAN_REALTIME_WS_URL, BITHUMAN_TRANSPORT). The plugin half is graded only when the
# plugin ref resolved by `flutter pub get` carries its door (lib/src/dev_levers.dart);
# otherwise the arm SAYS the ref predates the door rather than reading green on a lever
# it did not grade.
set -euo pipefail
cd "$(dirname "$0")/../app/avatar_chat"
S=LEVER_SENTINEL_7f3a9c
APP_DEFS=(--dart-define=BH_SCRIPT="${S}_script|${S}_two" --dart-define=BH_SCRIPT_GAP_S=7)
PLUGIN_DEFS=(--dart-define=BH_MIC_FILE="${S}_mic" --dart-define=BITHUMAN_REALTIME_WS_URL="ws://${S}_ws" --dart-define=BITHUMAN_TRANSPORT="${S}_transport" --dart-define=BITHUMAN_DEV_STRESS=true)
flutter pub get >/dev/null
PLUGIN_DIR=$(python3 -c 'import json,sys,urllib.parse; d=json.load(open(".dart_tool/package_config.json")); p=[x for x in d["packages"] if x["name"]=="bithuman"][0]["rootUri"]; print(urllib.parse.unquote(p).replace("file://",""))')
if [ -f "$PLUGIN_DIR/lib/src/dev_levers.dart" ]; then GRADE_PLUGIN=1; echo "plugin ref carries lib/src/dev_levers.dart — plugin levers graded"; else GRADE_PLUGIN=0; echo "NOTE: plugin ref ($PLUGIN_DIR) predates lib/src/dev_levers.dart — plugin levers NOT graded here (they are ungated on this ref)"; fi
T=$(mktemp -d "${TMPDIR:-/tmp}/levers.XXXXXX"); trap 'rm -rf "$T"' EXIT
# macOS `strings` does not read stdin — extract the snapshot to a file first
count() { unzip -o -q "$1" lib/arm64-v8a/libapp.so -d "$T/$(basename "$1")" && strings "$T/$(basename "$1")/lib/arm64-v8a/libapp.so" | grep -c "$2" || true; }
echo "== release build, every lever set =="
flutter build apk --release --target-platform android-arm64 "${APP_DEFS[@]}" "${PLUGIN_DEFS[@]}" 2>&1 | tail -2
REL=build/app/outputs/flutter-apk/app-release.apk
echo "== profile build (control), same defines =="
flutter build apk --profile --target-platform android-arm64 "${APP_DEFS[@]}" "${PLUGIN_DEFS[@]}" 2>&1 | tail -2
PRO=build/app/outputs/flutter-apk/app-profile.apk
r_app=$(count "$REL" "${S}_script"); p_app=$(count "$PRO" "${S}_script")
r_plg=$(count "$REL" "${S}_mic\|${S}_ws\|${S}_transport"); p_plg=$(count "$PRO" "${S}_mic\|${S}_ws\|${S}_transport")
[ "$GRADE_PLUGIN" = 1 ] || [ "$r_plg" -eq 0 ] || echo "NOTE: the RELEASE build carries $r_plg plugin dev-lever value(s) — measured, not graded: this plugin ref has no door (bump the ref to a tag that carries lib/src/dev_levers.dart)"
echo "app levers   : release=$r_app  profile=$p_app  (sentinel occurrences in libapp.so)"
echo "plugin levers: release=$r_plg  profile=$p_plg"
[ "$p_app" -gt 0 ] || { echo "::error::the PROFILE build carries no sentinel — the arm is not looking (defines not reaching the snapshot)"; exit 1; }
[ "$r_app" -eq 0 ] || { echo "::error::the RELEASE build carries the app's dev-lever value $r_app time(s) — a release build honours BH_SCRIPT"; exit 1; }
if [ "$GRADE_PLUGIN" = 1 ]; then
  [ "$p_plg" -gt 0 ] || { echo "::error::profile build carries no plugin sentinel — not looking"; exit 1; }
  [ "$r_plg" -eq 0 ] || { echo "::error::the RELEASE build carries a plugin dev-lever value $r_plg time(s)"; exit 1; }
fi
echo "OK: release libapp.so carries 0 dev-lever values; profile carries them (app $p_app$([ "$GRADE_PLUGIN" = 1 ] && echo ", plugin $p_plg"))"
