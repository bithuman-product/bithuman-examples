# Local CI (replaces GitHub Actions)

## Why

Owner directive, 2026-09-29 (~04:45Z): "disable Actions altogether as github is
charging way too much" · "please also remove all github actions" · "instead we
should run local tests for validation". GitHub Actions is disabled for this repo
and no status checks are required on `main`.

## How to run

```bash
ci/run-local.sh            # the PR suite (what the old PR/push workflows enforced)
ci/run-local.sh --list     # steps, tiers, and the manual (host/secret) jobs
ci/run-local.sh --only <step>
ci/run-local.sh --full     # + slower non-PR jobs that can run locally
ci/run-local.sh --no-cap   # skip the systemd-run MemoryMax=8G/CPUQuota=400% + nice wrapper
ci/run-local.sh --base origin/main   # diff base for change-scoped checks
```

Each step prints one `PASS`/`FAIL`/`SKIP` line (SKIP = a tool or host is missing,
with the reason; it is not a pass). The last line is
`LOCAL CI <PASS|FAIL> sha=<git sha> steps=<n> ...`. Logs go to a temp dir named
on that line. Heavy steps run under
`systemd-run --user --scope -p MemoryMax=8G -p MemorySwapMax=0 -p CPUQuota=400% nice -n 19`
when systemd-run is available (never run suites uncapped on a prod host).

## Evidence convention (merge rule)

Before merging, run `ci/run-local.sh` on the exact PR head and post a PR comment
with the command, the sha and the PASS/FAIL lines. **Red = no merge.** A SKIP on a
step your change touches means run it on a host that has the tool.

## Where the old workflows live

`ci/github-workflows-disabled/*.yml` — kept verbatim as the recipe (they no longer
run: GitHub only executes `.github/workflows/`). Jobs that need secrets, macOS/
Windows hosts, GPUs, deploys, releases or live services are listed under
`ci/run-local.sh --list` as manual, with the command/runbook pointer.

## This repo

- Default: `claims`, `links`, `published-versions` (network: Maven Central, PyPI,
  the tap), `realtime-model-rules`, `python-self-host` (one Python), `dev-levers`,
  `flutter-test` and `android-examples` (SKIP without Flutter / JDK 17 + Android SDK).
- `--full`: `python-matrix` (3.10/3.11/3.13/3.14), `release-ignores-dev-levers`;
  on a Mac also `swift-typecheck-ios` and `swift-build-packages`.
- `links` and `published-versions` also ran daily; run them periodically.

## Known reds

None on the first local run (2026-09-29, Linux host): 6 PASS, 2 SKIP (flutter-test,
android-examples: no Flutter / JDK 17 + Android SDK on that host). A SKIP is not a PASS:
run those on a host that has the toolchain when you touch flutter/ or android/.
