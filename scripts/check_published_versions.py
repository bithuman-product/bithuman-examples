#!/usr/bin/env python3
"""check_published_versions — a version a README advertises must be one the
registry actually serves.

★WHY THIS EXISTS.  On 2026-09-22 `android/README.md` carried a column literally
headed `latest` that read:

    | essence-2    | `ai.bithuman:essence2-android`   | 0.2.0 |
    | expression-2 | `ai.bithuman:expression2-android`| 0.3.0 |

Maven Central was serving **0.5.12** and **0.4.8** — thirteen and five releases
on.  Nobody edited that file wrongly; the file stopped being true while it sat
still, because THE REGISTRY MOVED AND NOTHING IN THIS REPOSITORY WAS LOOKING.
A developer who copied those two lines got an engine a quarter of a year old
that still compiles, still renders, and renders differently.

So the durable fix is not a correction, it is an INSTRUMENT, and it has to hold
four properties or it will rot the same way:

  1. IT READS THE PUBLISHED REGISTRY, NEVER A CHECKOUT.  Maven Central's
     `maven-metadata.xml`, PyPI's JSON API, and the tag list of the public tap
     (`git ls-remote`, one round trip, no auth, no rate limit).  A local clone
     can be behind; a registry cannot be behind itself.

  2. IT FAILS CLOSED AND LOUD.  Every finding names the file, the line, the
     version claimed and the version served.  ★AND A REGISTRY IT COULD NOT
     REACH IS A FAILURE, NOT A SKIP — "I could not look" is UNKNOWN, never
     PASS.  `--selftest` proves that arm by pointing the fetcher at a dead host
     and requiring a non-zero exit.

  3. IT CARRIES A POSITIVE CONTROL.  A green that has never been shown to go
     red is not evidence.  `--selftest` builds a fixture that claims a stale
     version and requires this checker to REJECT it, then builds a fixture from
     the live registry values and requires it to ACCEPT that.  The passing
     fixture is generated from the registry at run time, so the control itself
     can never go stale — the failure mode it guards against cannot reach it.

  4. IT RUNS ON A CLOCK, NOT ONLY ON A DIFF.  The bug above landed with ZERO
     commits to the offending file.  A check that only runs on pull requests
     cannot see registry drift, so the workflow also runs daily.

★THE RULES ARE DELIBERATELY TWO-TIER, because not every version in a document
is the same kind of statement:

  LATEST  — a Maven coordinate in a document is a line a developer COPIES.
            `implementation("ai.bithuman:essence2-android:0.2.0")` and a table
            row headed `latest` are both instructions, and an instruction that
            names anything but the current release is wrong.
  EXISTS  — a deliberate pin (`ref: flutter-plugin-v2.6.8`, a release asset
            URL, a SwiftPM `from:` floor, a `pip` pin) is allowed to name an
            older version — that is what pinning IS — but the version it names
            MUST STILL BE SERVED.  A pin to a tag that does not exist breaks
            `flutter pub get` and `swift build` outright, and no compiler in
            this repository would notice.

Escape hatches, both narrow and both visible:

  * `<!-- version-check-ignore: reason -->` on the same line, or on the line
    immediately above, suppresses that line.  For a DATED MEASUREMENT — a table
    recording what 0.3.0 did on a particular day — the old number is the point,
    and the owning lane can say so in its own file without touching this one.
  * `.github/version-waivers.json` waives a (file, coordinate) pair across a
    lane boundary, and every entry MUST carry an owner, a reason and an
    `expires` date.  ★An expired waiver is a hard failure and a waiver whose
    claim has become correct is a hard failure: the list can only shrink, the
    same way `swift-examples.yml`'s KNOWN_BROKEN can only shrink.  A waiver is
    a receipt for a known defect with a deadline on it, not a place to hide.

Usage
    python3 scripts/check_published_versions.py            # grade this repo
    python3 scripts/check_published_versions.py --selftest # prove it can fail
    python3 scripts/check_published_versions.py --root DIR # grade a fixture

Exit codes: 0 clean · 1 a claim is wrong · 2 a registry could not be read.
Stdlib only, no pip install, ~2 s of network.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# ── where the truth lives ────────────────────────────────────────────────────
# Overridable ONLY so --selftest can aim the fetcher at a dead host and prove
# that an unreachable registry fails instead of passing.
MAVEN_BASE = os.environ.get("BH_VERSION_CHECK_MAVEN_BASE", "https://repo1.maven.org/maven2")
PYPI_BASE = os.environ.get("BH_VERSION_CHECK_PYPI_BASE", "https://pypi.org/pypi")
TAP_URL = os.environ.get(
    "BH_VERSION_CHECK_TAP_URL", "https://github.com/bithuman-product/homebrew-bithuman.git"
)

# Maven artifacts under the ai.bithuman group that documents may name.
MAVEN_GROUP = "ai.bithuman"
MAVEN_ARTIFACTS = ("sdk", "essence2-android", "expression2-android")
# These two are unambiguous enough to be recognised without the group prefix;
# `sdk` is not, so it is only matched as `ai.bithuman:sdk`.
BARE_OK = ("essence2-android", "expression2-android")

PYPI_PROJECT = "bithuman"
# Other PyPI projects a document may pin. ★`livekit-plugins-bithuman` ENDS IN
# `bithuman`, so a naive match reads `livekit-plugins-bithuman>=1.4` as a claim
# about `bithuman` — it is a different project with a different version line.
# The left boundary below is what keeps those apart (this checker's own first
# run made that mistake, which is why it is written down here).
PYPI_PROJECTS = ("bithuman", "livekit-plugins-bithuman")

# Tag families published on the tap. A reference to any of them must resolve.
TAP_TAG_PREFIXES = ("flutter-plugin-v", "cli-v", "essence2-v", "expression2-v")

SKIP_DIRS = {".git", "node_modules", ".dart_tool", "build", ".gradle", "Pods", "xcf", ".venv"}
SKIP_NAMES = {"package-lock.json", "yarn.lock", "Podfile.lock", "pubspec.lock"}
# ★THIS FILE GRADES EVERY FILE BUT ITSELF.  It quotes `0.2.0` and
# `flutter-plugin-v9.9.9` deliberately — in the docstring that records the
# defect it was written for, and in the controls that must be REJECTED for the
# gate to be trustworthy. Grading its own fixtures would make a working checker
# permanently red, and a permanently red check is one somebody deletes.
# Nothing here is a line a developer copies into a build file.
SELF = "check_published_versions.py"
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".wav", ".mp4",
    ".imx", ".so", ".dylib", ".a", ".jar", ".whl", ".ico", ".ttf", ".otf",
}

SEMVER = r"\d+\.\d+\.\d+"
IGNORE_RE = re.compile(r"version-check-ignore\s*:", re.I)


# ── registry access ──────────────────────────────────────────────────────────
class RegistryUnreachable(RuntimeError):
    """We could not look. That is UNKNOWN, and UNKNOWN is not a pass."""


def _get(url: str, *, tries: int = 3, timeout: int = 20) -> bytes:
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bithuman-examples-version-check"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 — every failure mode is the same verdict
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                raise RegistryUnreachable(f"{url} -> HTTP 404") from e
            if n + 1 < tries:
                time.sleep(1.5 * (n + 1))
    raise RegistryUnreachable(f"{url} -> {last}")


class Registry:
    """Every published fact this checker grades against, fetched once."""

    def __init__(self) -> None:
        self.maven: dict[str, dict] = {}
        self.pypi: dict[str, dict] = {}
        self.tap_tags: set[str] = set()
        self.sources: list[str] = []

    def load(self) -> None:
        for art in MAVEN_ARTIFACTS:
            path = f"{MAVEN_GROUP.replace('.', '/')}/{art}/maven-metadata.xml"
            url = f"{MAVEN_BASE}/{path}"
            root = ET.fromstring(_get(url).decode("utf-8", "replace"))
            versioning = root.find("versioning")
            if versioning is None:
                raise RegistryUnreachable(f"{url} -> no <versioning>")
            rel = versioning.findtext("release") or versioning.findtext("latest")
            vers = [v.text for v in versioning.iterfind("versions/version") if v.text]
            if not rel or not vers:
                raise RegistryUnreachable(f"{url} -> empty metadata")
            self.maven[art] = {"latest": rel, "versions": set(vers)}
            self.sources.append(f"maven {MAVEN_GROUP}:{art} latest={rel} ({len(vers)} versions) <- {url}")

        for proj in PYPI_PROJECTS:
            url = f"{PYPI_BASE}/{proj}/json"
            d = json.loads(_get(url).decode("utf-8", "replace"))
            self.pypi[proj] = {"latest": d["info"]["version"], "versions": set(d["releases"])}
            self.sources.append(
                f"pypi {proj} latest={self.pypi[proj]['latest']} "
                f"({len(self.pypi[proj]['versions'])} releases) <- {url}"
            )

        # One round trip, unauthenticated, no API rate limit. This IS the
        # registry SwiftPM and `flutter pub get` resolve a git ref against.
        try:
            out = subprocess.run(
                ["git", "ls-remote", "--tags", TAP_URL],
                capture_output=True, text=True, timeout=60, check=True,
            ).stdout
        except Exception as e:  # noqa: BLE001
            raise RegistryUnreachable(f"git ls-remote {TAP_URL} -> {e}") from e
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) == 2:
                self.tap_tags.add(parts[1].removeprefix("refs/tags/").removesuffix("^{}"))
        if not self.tap_tags:
            raise RegistryUnreachable(f"git ls-remote {TAP_URL} -> zero tags")
        self.sources.append(f"tap tags: {len(self.tap_tags)} <- {TAP_URL}")


# ── claim extraction ─────────────────────────────────────────────────────────
class Claim:
    __slots__ = ("file", "line", "text", "kind", "registry", "coord", "version", "rule")

    def __init__(self, file, line, text, kind, registry, coord, version, rule):
        self.file, self.line, self.text = file, line, text
        self.kind, self.registry, self.coord, self.version, self.rule = kind, registry, coord, version, rule

    def __repr__(self) -> str:
        return f"{self.file}:{self.line} {self.coord}={self.version} [{self.kind}/{self.rule}]"


_RE_MAVEN_DEP = re.compile(
    rf"(?:{re.escape(MAVEN_GROUP)}:)?(?P<art>{'|'.join(BARE_OK)}):(?P<ver>{SEMVER})"
)
_RE_MAVEN_SDK_DEP = re.compile(rf"{re.escape(MAVEN_GROUP)}:(?P<art>sdk):(?P<ver>{SEMVER})")
_RE_MAVEN_BARE_COORD = re.compile(
    rf"{re.escape(MAVEN_GROUP)}:(?P<art>{'|'.join(MAVEN_ARTIFACTS)})\b(?!:)"
)
_RE_SEMVER = re.compile(SEMVER)
_RE_TAP_TAG = re.compile(rf"\b(?P<tag>(?:{'|'.join(p.rstrip('v') + 'v' for p in TAP_TAG_PREFIXES)}){SEMVER})\b")
_RE_TAP_DL = re.compile(r"homebrew-bithuman/releases/download/(?P<tag>[^/\s\"')]+)/")
_RE_TAP_SPM = re.compile(r'from:\s*"?(?P<ver>' + SEMVER + r')"?')
_RE_PYPI_PIN = re.compile(
    r"(?<![\w.-])(?P<proj>" + "|".join(sorted(PYPI_PROJECTS, key=len, reverse=True)) + r")"
    r"(?:\[[^\]]*\])?\s*(?P<op>==|>=)\s*(?P<ver>" + SEMVER + r")(?![\w.])"
)


def _iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.name == SELF or p.name in SKIP_NAMES or p.suffix.lower() in SKIP_SUFFIXES:
            continue
        if p.name.startswith("._"):
            continue
        try:
            if p.stat().st_size > 2_000_000:
                continue
            yield p, p.read_text("utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue


def extract(root: Path) -> list[Claim]:
    claims: list[Claim] = []
    for path, lines in _iter_files(root):
        rel = str(path.relative_to(root))
        tap_window = 0  # lines remaining in which a `from:` belongs to the tap
        for i, line in enumerate(lines, 1):
            prev = lines[i - 2] if i >= 2 else ""
            if IGNORE_RE.search(line) or IGNORE_RE.search(prev):
                if "homebrew-bithuman" in line:
                    tap_window = 0
                continue

            # ── Maven: an exact coordinate in a document is a copy-me line.
            for m in list(_RE_MAVEN_DEP.finditer(line)) + list(_RE_MAVEN_SDK_DEP.finditer(line)):
                claims.append(Claim(rel, i, line.strip(), "LATEST", "maven",
                                    m.group("art"), m.group("ver"), "maven-dep"))
            # ── Maven: a table row naming the coordinate and the version apart.
            for m in _RE_MAVEN_BARE_COORD.finditer(line):
                for v in _RE_SEMVER.finditer(line):
                    claims.append(Claim(rel, i, line.strip(), "LATEST", "maven",
                                        m.group("art"), v.group(0), "maven-table"))

            # ── the tap: pins may be old, but they must resolve.
            for m in _RE_TAP_TAG.finditer(line):
                claims.append(Claim(rel, i, line.strip(), "EXISTS", "tap",
                                    "tag", m.group("tag"), "tap-tag"))
            for m in _RE_TAP_DL.finditer(line):
                claims.append(Claim(rel, i, line.strip(), "EXISTS", "tap",
                                    "tag", m.group("tag"), "tap-release-asset"))
            if "homebrew-bithuman" in line:
                tap_window = 4
            if tap_window:
                for m in _RE_TAP_SPM.finditer(line):
                    claims.append(Claim(rel, i, line.strip(), "EXISTS", "tap",
                                        "tag", "v" + m.group("ver"), "tap-swiftpm-floor"))
                tap_window -= 1

            # ── PyPI: a pin or a floor must name a release that exists.
            for m in _RE_PYPI_PIN.finditer(line):
                # `==` to a version PyPI never published breaks `pip install`
                # on the spot; `>=` to one still resolves forward, so it is a
                # documentation defect and is reported, not failed.
                claims.append(Claim(rel, i, line.strip(),
                                    "EXISTS" if m.group("op") == "==" else "SHOULD_EXIST",
                                    "pypi", m.group("proj"), m.group("ver"),
                                    "pypi-pin" if m.group("op") == "==" else "pypi-floor"))

    # de-duplicate identical (file, line, coord, version, kind)
    seen, out = set(), []
    for c in claims:
        k = (c.file, c.line, c.registry, c.coord, c.version, c.kind)
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out


# ── waivers ──────────────────────────────────────────────────────────────────
def load_waivers(root: Path, enabled: bool) -> list[dict]:
    if not enabled:
        return []
    f = root / ".github" / "version-waivers.json"
    if not f.exists():
        return []
    data = json.loads(f.read_text("utf-8"))
    for w in data.get("waivers", []):
        for key in ("file", "coordinate", "reason", "owner", "expires"):
            if key not in w:
                raise SystemExit(
                    f"::error file=.github/version-waivers.json::waiver missing '{key}': {w!r} — "
                    "every waiver names a file, a coordinate, a reason, an owner and an expiry"
                )
    return data.get("waivers", [])


# ── grading ──────────────────────────────────────────────────────────────────
def grade(claims: list[Claim], reg: Registry, waivers: list[dict], today: _dt.date):
    errors: list[str] = []
    warnings: list[str] = []
    used_waivers: set[int] = set()

    def waiver_for(c: Claim):
        for idx, w in enumerate(waivers):
            if w["file"] == c.file and w["coordinate"] in (c.coord, f"{MAVEN_GROUP}:{c.coord}"):
                return idx, w
        return None, None

    for c in claims:
        served = None
        wrong = None
        if c.registry == "maven":
            info = reg.maven.get(c.coord)
            if info is None:
                errors.append(
                    f"::error file={c.file},line={c.line}::UNKNOWN COORDINATE — "
                    f"'{MAVEN_GROUP}:{c.coord}' is not published on Maven Central. Line: {c.text}"
                )
                continue
            served = info["latest"]
            if c.version not in info["versions"]:
                wrong = (f"names {c.coord} {c.version}, which Maven Central has NEVER served "
                         f"(latest is {served})")
            elif c.kind == "LATEST" and c.version != served:
                wrong = (f"advertises {MAVEN_GROUP}:{c.coord}:{c.version}; "
                         f"Maven Central serves {served}")
        elif c.registry == "pypi":
            info = reg.pypi.get(c.coord)
            if info is None:
                continue
            served = info["latest"]
            if c.version not in info["versions"]:
                wrong = (f"names {c.coord} {c.version}, which PyPI has never published "
                         f"(latest is {served})")
        elif c.registry == "tap":
            served = "(tag set)"
            if c.version not in reg.tap_tags:
                wrong = (f"references tag '{c.version}', which does not exist in "
                         f"{TAP_URL} ({len(reg.tap_tags)} tags read)")

        if wrong is not None and c.kind == "SHOULD_EXIST":
            warnings.append(
                f"::warning file={c.file},line={c.line}::{c.file}:{c.line} {wrong}. "
                f"A `>=` floor at a version that was never published still resolves, so this "
                f"does not break an install — but it means nobody has read this line against "
                f"the registry. Line: {c.text}"
            )
            continue

        if wrong is None:
            # A waiver whose claim is now correct must be deleted, or the list
            # stops being a list of real defects and becomes decoration.
            idx, w = waiver_for(c)
            if w is not None and c.kind == "LATEST" and c.registry == "maven":
                used_waivers.add(idx)
            continue

        idx, w = waiver_for(c)
        if w is not None:
            exp = _dt.date.fromisoformat(w["expires"])
            if exp < today:
                errors.append(
                    f"::error file=.github/version-waivers.json::WAIVER EXPIRED {w['expires']} "
                    f"({w['owner']}) — {c.file}:{c.line} still {wrong}. "
                    f"Fix the file or renew the waiver with a new date and a reason."
                )
            else:
                used_waivers.add(idx)
                warnings.append(
                    f"::warning file={c.file},line={c.line}::WAIVED until {w['expires']} "
                    f"(owner: {w['owner']}) — {c.file}:{c.line} {wrong}. Reason: {w['reason']}"
                )
            continue

        errors.append(f"::error file={c.file},line={c.line}::{c.file}:{c.line} {wrong}. Line: {c.text}")

    for idx, w in enumerate(waivers):
        if idx not in used_waivers:
            errors.append(
                f"::error file=.github/version-waivers.json::STALE WAIVER — "
                f"{w['file']} / {w['coordinate']} is no longer wrong (or no longer present). "
                f"Delete this entry; the waiver list can only shrink."
            )
    return errors, warnings


def run(root: Path, use_waivers: bool, reg: Registry, quiet: bool = False) -> int:
    claims = extract(root)
    waivers = load_waivers(root, use_waivers)
    errors, warnings = grade(claims, reg, waivers, _dt.date.today())
    if not quiet:
        print(f"scanned {root} — {len(claims)} version claims, {len(waivers)} waiver(s)")
        for w in warnings:
            print(w)
        for e in errors:
            print(e)
        if errors:
            print(f"\nFAILED: {len(errors)} version claim(s) do not match what the registry serves.")
        else:
            print("OK: every version claim matches a version the registry actually serves.")
    return 1 if errors else 0


# ── controls ─────────────────────────────────────────────────────────────────
def selftest(reg: Registry) -> int:
    """Show this gate going red before trusting it green.

    Four arms.  Each is a way this checker could be blind, and each must be
    demonstrated to fire.
    """
    failures: list[str] = []

    def arm(name: str, body: str, expect_fail: bool) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "README.md").write_text(body, "utf-8")
            rc = run(d, use_waivers=False, reg=reg, quiet=True)
            ok = (rc != 0) if expect_fail else (rc == 0)
            verdict = "fires" if expect_fail else "passes"
            print(f"  [{'OK ' if ok else 'BAD'}] control {verdict}: {name} (rc={rc})")
            if not ok:
                failures.append(name)

    e2, x2 = reg.maven["essence2-android"]["latest"], reg.maven["expression2-android"]["latest"]
    # ★`flutter-plugin-vendor-v1` also starts with "flutter-plugin-v"; require
    # a real semver suffix or this control crashes instead of grading.
    _plugin = re.compile(r"^flutter-plugin-v(\d+)\.(\d+)\.(\d+)$")
    newest_plugin = max(
        (t for t in reg.tap_tags if _plugin.match(t)),
        key=lambda t: tuple(int(g) for g in _plugin.match(t).groups()),
    )

    print("controls:")
    # 1. NEGATIVE — a real-but-superseded Maven version must be rejected. This
    #    is the exact shape of the defect that motivated the file.
    arm("a superseded Maven version in a copy-me line",
        f'implementation("{MAVEN_GROUP}:essence2-android:0.2.0")\n', expect_fail=True)
    # 2. NEGATIVE — a version nobody ever published must be rejected.
    arm("a Maven version that was never published",
        f'| essence-2 | `{MAVEN_GROUP}:essence2-android` | 9.9.9 |\n', expect_fail=True)
    # 3. NEGATIVE — a pin to a tag that does not exist must be rejected.
    arm("a pin to a tap tag that does not exist",
        "    ref: flutter-plugin-v9.9.9\n", expect_fail=True)
    # 4. POSITIVE — the same shapes, built FROM THE LIVE REGISTRY so the
    #    control cannot itself go stale, must pass.
    arm("the live values, read from the registry seconds ago",
        f'implementation("{MAVEN_GROUP}:essence2-android:{e2}")\n'
        f'| expression-2 | `{MAVEN_GROUP}:expression2-android` | {x2} |\n'
        f'    ref: {newest_plugin}\n'
        f'bithuman=={reg.pypi["bithuman"]["latest"]}\n', expect_fail=False)
    # 5. The ignore marker must actually suppress — otherwise lanes cannot
    #    record a dated measurement and will delete the check instead.
    arm("an ignore marker suppresses the line it names",
        f'implementation("{MAVEN_GROUP}:essence2-android:0.2.0")  <!-- version-check-ignore: fixture -->\n',
        expect_fail=False)

    # 6. "I COULD NOT LOOK" IS NOT A PASS.  Aim the fetcher at a dead host and
    #    require a non-zero exit — a checker that silently skips an unreachable
    #    registry reports green on a repository it never graded.
    env = dict(os.environ, BH_VERSION_CHECK_MAVEN_BASE="https://127.0.0.1:9/maven2")
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--root", tempfile.gettempdir(), "--registries-only"],
        capture_output=True, text=True, env=env, timeout=300,
    )
    ok = proc.returncode == 2
    print(f"  [{'OK ' if ok else 'BAD'}] control fires: an unreachable registry exits 2, "
          f"not 0 (rc={proc.returncode})")
    if not ok:
        failures.append("unreachable registry must not pass")

    if failures:
        print("\n::error::SELFTEST FAILED — this gate cannot be trusted: " + "; ".join(failures))
        return 1
    print("\nselftest OK: this gate has been shown to go red, so a green means something.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent.parent
    ap.add_argument("--root", default=str(here), help="tree to grade (default: this repository)")
    ap.add_argument("--selftest", action="store_true", help="prove the gate can fail, then grade nothing")
    ap.add_argument("--no-waivers", action="store_true",
                    help="ignore .github/version-waivers.json — shows the unvarnished state")
    ap.add_argument("--registries-only", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    reg = Registry()
    try:
        reg.load()
    except RegistryUnreachable as e:
        print(f"::error::COULD NOT READ A PUBLISHED REGISTRY: {e}")
        print("::error::'I could not look' is UNKNOWN, never PASS — failing closed.")
        return 2
    for s in reg.sources:
        print(f"  registry: {s}")

    if args.registries_only:
        return 0
    if args.selftest:
        return selftest(reg)
    return run(Path(args.root).resolve(), use_waivers=not args.no_waivers, reg=reg)


if __name__ == "__main__":
    sys.exit(main())
