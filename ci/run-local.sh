#!/usr/bin/env bash
# ci/run-local.sh — local validation that replaces GitHub Actions.
# Owner directive 2026-09-29: "disable Actions altogether as github is charging way
# too much" / "please also remove all github actions" / "instead we should run local
# tests for validation". Old workflow YAML (the recipe): ci/github-workflows-disabled/.
#
# Usage: ci/run-local.sh [--list] [--only <step>] [--full] [--no-cap] [--base <ref>]
#   default   run the PR/push suite the old workflows enforced
#   --full    also run the slower non-PR jobs that can run locally (and, on a Mac, the Swift jobs)
#   --only S  run one step (any tier except manual)
#   --no-cap  do not wrap heavy steps in systemd-run MemoryMax/CPUQuota + nice
#   --base R  diff base for change-scoped checks (default: origin/main)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SELF="$ROOT/ci/run-local.sh"
BASE_REF="${BASE_REF:-origin/main}"
LIST=0; FULL=0; CAP=1; ONLY=""; INTERNAL=""

while [ $# -gt 0 ]; do
  case "$1" in
    --list) LIST=1 ;;
    --full) FULL=1 ;;
    --no-cap) CAP=0 ;;
    --only) ONLY="${2:?--only needs a step name}"; shift ;;
    --base) BASE_REF="${2:?--base needs a ref}"; shift ;;
    --_step) INTERNAL="${2:?}"; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

have() { command -v "$1" >/dev/null 2>&1; }
# skip_step <reason>: exit code 3 = SKIP (tool/host missing), reported, never PASS.
skip_step() { echo "SKIP-REASON: $*"; exit 3; }
first_python() { local v; for v in "$@"; do have "python$v" && { echo "python$v"; return 0; }; done; return 1; }

# ---------------------------------------------------------------- steps
# Registry: "name|tier|heavy|description"  tier = default | full | mac (runs with --full/--only on macOS)
STEPS=(
  "claims|default|0|claims-and-links.yml job claims: check_claims.py --prove-by-mutation, then grade the tree"
  "links|default|0|claims-and-links.yml job links: check_links.py --prove-by-mutation, then grade (network)"
  "published-versions|default|0|published-versions.yml: check_published_versions.py --selftest + grade vs maven.bithuman.ai/PyPI/tap (network)"
  "realtime-model-rules|default|0|python-examples.yml job realtime-model-rules: no gpt-4o realtime preview + turn_detection controls"
  "python-self-host|default|1|python-examples.yml job self-host-imports on ONE python (first of 3.13/3.11/3.10/3.14): venv + requirements + import agent + compileall"
  "dev-levers|default|0|flutter-tests.yml job dev-levers: check_dev_levers.sh + two negative controls"
  "flutter-test|default|1|flutter-tests.yml job avatar-chat: test census + flutter pub get + flutter test (SKIP without flutter)"
  "android-examples|default|1|android-examples.yml: assembleDebug + resolved-coordinate check for expression2-hello and essence2-hello (SKIP without JDK17 + Android SDK)"
  "python-matrix|full|1|python-examples.yml self-host-imports on every python the old matrix ran (3.10 3.11 3.13 3.14) that is installed"
  "release-ignores-dev-levers|full|1|flutter-tests.yml job release-ignores-dev-levers: scripts/prove_release_ignores_dev_levers.sh (flutter + JDK17 + Android SDK)"
  "swift-typecheck-ios|mac|1|swift-examples.yml job typecheck-ios (macOS + Xcode): pinned xcframeworks + swiftc -typecheck + negative control"
  "swift-build-packages|mac|1|swift-examples.yml job build-packages (macOS + Xcode): swift build every swift/*/Package.swift"
  "swift-xcodebuild-ios|mac|1|the COMMITTED ios-essence2 + ios-expression2 Xcode projects from a clean copy: setup.sh + xcodebuild for the generic Simulator and a device, unsigned (network, ~700 MB)"
)
MANUAL=(
  "swift-typecheck-ios / swift-build-packages / swift-xcodebuild-ios (macOS host + Xcode): on a Mac run ci/run-local.sh --full, or --only each of them (recipe: ci/github-workflows-disabled/swift-examples.yml)"
  "android-examples / release-ignores-dev-levers need JDK 17 + an Android SDK (ANDROID_HOME); on such a host ci/run-local.sh runs them, else they SKIP"
  "schedule: claims-and-links.yml and published-versions.yml also ran once a day (registry drift takes no commit): run ci/run-local.sh --only published-versions and --only links periodically"
)

run_all() {
  local c fails=0
  for c in "$@"; do
    echo "---- \$ $c"
    if bash -c "set -euo pipefail; $c"; then echo "---- ok: $c"; else echo "---- FAILED: $c"; fails=$((fails+1)); fi
  done
  echo "---- $fails of $# command(s) failed"
  [ $fails -eq 0 ]
}

step_claims() { run_all "python3 scripts/check_claims.py --prove-by-mutation" "python3 scripts/check_claims.py"; }
step_links()  { run_all "python3 scripts/check_links.py --prove-by-mutation" "python3 scripts/check_links.py"; }
step_published_versions() {
  run_all "python3 scripts/check_published_versions.py --selftest" "python3 scripts/check_published_versions.py"
  echo "---- unwaived state (informational):"; python3 scripts/check_published_versions.py --no-waivers 2>&1 || true
}
step_realtime_model_rules() {
  if grep -rnE 'gpt-4o(-mini)?-realtime-previe[w]' --exclude-dir=.git --exclude-dir=ci .; then
    echo "a shut-down OpenAI Realtime preview model is named above; use gpt-realtime-2.1-mini"; return 1
  fi
  run_all "python3 scripts/check_realtime_turn_detection.py --selftest" "python3 scripts/check_realtime_turn_detection.py ."
}
self_host_on() {   # $1 = python interpreter
  local py="$1" v; v="$(mktemp -d)/venv"
  echo "== $py ($($py --version 2>&1))"
  "$py" -m venv "$v" \
    && "$v/bin/pip" install --quiet --upgrade pip \
    && "$v/bin/pip" install --quiet -r python/self-host/requirements.txt \
    && (cd python/self-host && BITHUMAN_API_SECRET="" "$v/bin/python" -c "import agent; print('agent.py imports; server =', type(agent.server).__name__)") \
    && "$v/bin/python" -m compileall -q python
  local rc=$?; rm -rf "$(dirname "$v")"; return $rc
}
step_python_self_host() { local py; py="$(first_python 3.13 3.11 3.10 3.14)" || skip_step "no python3.10/3.11/3.13/3.14"; self_host_on "$py"; }
step_python_matrix() {
  local v n=0 fails=0
  for v in 3.10 3.11 3.13 3.14; do
    have "python$v" || { echo "== python$v not installed (not graded)"; continue; }
    n=$((n+1)); self_host_on "python$v" || { echo "FAILED on python$v"; fails=$((fails+1)); }
  done
  [ $n -gt 0 ] || skip_step "none of python3.10/3.11/3.13/3.14 installed"
  [ $fails -eq 0 ]
}
step_dev_levers() {
  local d; d="$(mktemp -d)"
  git worktree add -q --detach "$d/wt" HEAD   # controls mutate files: do it in a throwaway worktree
  trap 'git worktree remove --force "$d/wt" >/dev/null 2>&1; rm -rf "$d"' RETURN
  cd "$d/wt"; git -C "$ROOT" worktree prune
  ./scripts/check_dev_levers.sh
  red() { if ./scripts/check_dev_levers.sh >/dev/null 2>&1; then echo "control did NOT fire: $1 (the check is not looking)"; return 1; fi; echo "control fires: $1"; }
  local F=app/avatar_chat/lib/main.dart; cp "$F" "$d/c1"
  echo "const _stray = String.fromEnvironment('BH_SCRIPT');" >> "$F"; red "stray lever outside the door"; cp "$d/c1" "$F"
  F=app/avatar_chat/lib/dev_levers.dart; cp "$F" "$d/c2"
  sed -i.bak "s/enabled ? String.fromEnvironment('BH_SCRIPT') : ''/String.fromEnvironment('BH_SCRIPT')/" "$F"; rm -f "$F.bak"
  red "un-gated lever"; cp "$d/c2" "$F"
  ./scripts/check_dev_levers.sh
  cd "$ROOT"
}
step_flutter_test() {
  have flutter || skip_step "flutter not installed"
  cd app/avatar_chat
  local n; n=$(ls test/*_test.dart 2>/dev/null | wc -l | tr -d ' ')
  echo "test files: $n"; [ "$n" -ge 1 ] || { echo "no *_test.dart under app/avatar_chat/test"; return 1; }
  flutter --version; flutter pub get; flutter test --reporter expanded
}
android_ready() { have java && [ -n "${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}" ] && [ -d "${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}" ]; }
step_android_examples() {
  android_ready || skip_step "needs JDK 17 + an Android SDK (ANDROID_HOME)"
  if git ls-files android | grep -E '(^|/)local\.properties$'; then echo "a local.properties is committed (it holds the API secret)"; return 1; fi
  local p want
  for p in expression2-hello essence2-hello; do
    echo "== android/$p"
    (cd "android/$p" \
      && ./gradlew --no-daemon :app:assembleDebug \
      && want=$(grep -oE 'ai\.bithuman:[a-z0-9-]+:[0-9][0-9.]*' app/build.gradle.kts) \
      && ./gradlew -q --no-daemon :app:dependencies --configuration debugRuntimeClasspath | grep -F -- "--- $want" \
      && ls -l app/build/outputs/apk/debug/app-debug.apk)
  done
}
step_release_ignores_dev_levers() {
  have flutter && android_ready || skip_step "needs flutter + JDK 17 + an Android SDK"
  cd app/avatar_chat && bash ../../scripts/prove_release_ignores_dev_levers.sh
}
need_mac() { [ "$(uname -s)" = Darwin ] && have xcrun || skip_step "macOS host with Xcode needed"; }
step_swift_typecheck_ios() {
  need_mac
  python3 - "$ROOT/ci/github-workflows-disabled/swift-examples.yml" typecheck-ios > "$ROOT/.swift-ci.sh" <<'PY'
import sys, yaml
job = yaml.safe_load(open(sys.argv[1]))["jobs"][sys.argv[2]]
for s in job["steps"]:
    if "run" in s: print("( " + s["run"].replace("sudo xcode-select", "echo would: xcode-select") + " )")
PY
  bash -euo pipefail "$ROOT/.swift-ci.sh"; rm -f "$ROOT/.swift-ci.sh"; rm -rf "$ROOT/xcf"
}
step_swift_build_packages() {
  need_mac
  local p d n failed=""
  for p in swift/*/Package.swift; do
    d=$(dirname "$p"); n=$(basename "$d")
    [ "$n" = ios-avatar ] && { echo "skip $d (iOS-only)"; continue; }
    if (cd "$d" && swift build 2>&1 | tail -30); then echo "OK $d"; else echo "FAIL $d"; failed="$failed $d"; fi
  done
  [ -z "$failed" ] || { echo "packages failed to build:$failed"; return 1; }
}
step_swift_xcodebuild_ios() {
  need_mac
  # ★Builds what a newcomer opens, not a typecheck of the sources: on 2026-09-30 the
  # committed IOSEssence2.xcodeproj linked the wrong product and referenced two
  # bundles that no longer existed, while the typecheck step stayed green.
  local tmp p n dest failed=""
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/xcodebuild-ios.XXXXXX")
  git -C "$ROOT" archive HEAD swift/ios-essence2 swift/ios-expression2 | tar -x -C "$tmp"
  for p in ios-essence2:IOSEssence2 ios-expression2:IOSExpression2; do
    n=${p##*:}; p=${p%%:*}
    echo "== swift/$p: setup.sh"
    (cd "$tmp/swift/$p" && ./setup.sh >/dev/null) || { failed="$failed $p(setup)"; continue; }
    for dest in 'generic/platform=iOS Simulator' 'generic/platform=iOS'; do
      echo "== swift/$p: xcodebuild [$dest]"
      if (cd "$tmp/swift/$p" && xcodebuild -project "$n.xcodeproj" -scheme "$n" -destination "$dest" \
            -derivedDataPath "$tmp/dd" -clonedSourcePackagesDirPath "$tmp/spm" -packageCachePath "$tmp/spmcache" \
            CODE_SIGNING_ALLOWED=NO build 2>&1 | grep -E 'error:|BUILD (SUCCEEDED|FAILED)' | tail -5 | tee /dev/stderr | grep -q 'BUILD SUCCEEDED'); then
        echo "OK $p [$dest]"
      else failed="$failed $p[$dest]"; fi
    done
  done
  rm -rf "$tmp"
  [ -z "$failed" ] || { echo "failed:$failed"; return 1; }
}

# ---------------------------------------------------------------- runner
step_field() { local IFS='|'; set -- $1; eval "echo \"\${$2}\""; }

if [ -n "$INTERNAL" ]; then "step_${INTERNAL//-/_}"; exit $?; fi

if [ "$LIST" = 1 ]; then
  for s in "${STEPS[@]}"; do
    IFS='|' read -r n t h d <<<"$s"
    case "$t" in
      default) printf '%-26s default%s  %s\n' "$n" "$([ "$h" = 1 ] && echo ' (heavy)')" "$d" ;;
      full)    printf '%-26s --full%s   %s\n' "$n" "$([ "$h" = 1 ] && echo ' (heavy)')" "$d" ;;
      mac)     printf '%-26s mac-only   %s\n' "$n" "$d" ;;
    esac
  done
  echo; echo "manual (host/secret needed) — not run by this script:"
  for m in "${MANUAL[@]}"; do echo "  - $m"; done
  exit 0
fi

wrap=()
if [ "$CAP" = 1 ] && have systemd-run && systemd-run --user --scope -q true >/dev/null 2>&1; then
  wrap=(systemd-run --user --scope -q -p MemoryMax=8G -p MemorySwapMax=0 -p CPUQuota=400% nice -n 19)
fi

LOGDIR="${LOCAL_CI_LOGDIR:-$(mktemp -d "${TMPDIR:-/tmp}/local-ci.XXXXXX")}"
SHA="$(git rev-parse HEAD)"
git rev-parse --verify -q "$BASE_REF" >/dev/null || git fetch -q origin main 2>/dev/null || true
n=0; fails=0; skips=0; found=0
for s in "${STEPS[@]}"; do
  IFS='|' read -r name tier heavy desc <<<"$s"
  if [ -n "$ONLY" ]; then [ "$name" = "$ONLY" ] || continue
  elif [ "$tier" = full ] && [ "$FULL" != 1 ]; then continue
  elif [ "$tier" = mac ] && { [ "$FULL" != 1 ] || [ "$(uname -s)" != Darwin ]; }; then continue; fi
  found=1; n=$((n+1)); log="$LOGDIR/$name.log"; t0=$(date +%s)
  set +e
  if [ "$heavy" = 1 ] && [ ${#wrap[@]} -gt 0 ]; then
    BASE_REF="$BASE_REF" "${wrap[@]}" bash "$SELF" --_step "$name" --base "$BASE_REF" >"$log" 2>&1
  else
    bash "$SELF" --_step "$name" --base "$BASE_REF" >"$log" 2>&1
  fi
  rc=$?; set -e; dt=$(( $(date +%s) - t0 ))
  if [ $rc -eq 0 ]; then echo "PASS  $name  (${dt}s)"
  elif [ $rc -eq 3 ]; then skips=$((skips+1)); echo "SKIP  $name  ($(grep -m1 '^SKIP-REASON:' "$log" | cut -d' ' -f2-))"
  else fails=$((fails+1)); echo "FAIL  $name  (${dt}s, rc=$rc, log $log)"; tail -n 25 "$log" | sed 's/^/      | /'
  fi
done
[ "$found" = 1 ] || { echo "no such step: $ONLY (see --list)" >&2; exit 2; }
result=PASS; [ $fails -eq 0 ] || result=FAIL
echo "LOCAL CI $result sha=$SHA steps=$n${skips:+ skipped=$skips} logs=$LOGDIR"
[ $fails -eq 0 ]
