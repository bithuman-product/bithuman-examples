#!/usr/bin/env python3
"""check_claims — this public repository makes no claim the product cannot back.

Every example here is copied into real apps, and every README is read by people
and by coding agents deciding what bitHuman does. A sentence such as "a free key",
"idle is free" or "100% internet-free" stops being true while nobody edits the file
(the plan, the billing rule and the offline license all changed in September 2026),
so the words themselves are graded on every pull request, on every push to main,
and once a day.

WHAT IS REFUSED (case-insensitive, any tracked text file):

  C1  free key / free account / free tier / free SDK      API and SDK use needs the
                                                           Creator plan or higher
  C2  "no API secret" / "no account" / "no credits"       the same rule, said the
                                                           other way round
  C3  idle is free                                         sessions bill active
  C4  talking time only                                    session time, talking
  C5  meters the talking time                              or idle
  C6  short-lived token                                    the on-device engines
                                                           take an API secret
  C7  therapy / therapist                                  not a medical product
  C8  care for loneliness
  C9  100% on-device                                       the engines report usage
  C10 internet-free                                        offline is a Business /
  C11 100% offline                                         Enterprise license for
                                                           Linux PCs and terminals
  C12 homebrew-bithuman/tree/main/Examples                 that path is gone
  C13 bitHumanKit                                          legacy; allowed only on a
                                                           line that says so, or in
                                                           the legacy examples
  C14 instant replies / instant responses                  no latency promises

HOW A LINE IS ALLOWED — three ways, all narrow:

  * C13 on a line that also says "legacy", or anywhere under a legacy example's own
    directory (LEGACY_DIRS below; each of those READMEs opens with the notice).
  * An entry in ci/claims-allow.json: a file, a rule id, a substring of the line
    and a reason. An entry that matches nothing is itself a failure (STALE), so the
    list can only shrink.
  * `claims-check-ignore: <reason>` on the line itself.

    check_claims.py                     grade the tracked tree; exit 1 on a finding
    check_claims.py --prove-by-mutation every rule must turn RED on a planted line,
                                        and every allow entry must be load-bearing

Exit 0 = clean. Exit 1 = a finding (or a stale allow entry). Exit 2 = harness error.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ALLOW_FILE = Path("ci/claims-allow.json")
SELF = {Path("scripts/check_claims.py"), ALLOW_FILE}
SKIP_NAMES = {"package-lock.json"}
MAX_BYTES = 2_000_000

RULES: list[tuple[str, str, str]] = [
    ("C1", r"\bfree[- ](key|account|tier|sdk)s?\b", "a free key, account, tier or SDK"),
    ("C2", r"\bno (api secret|account|credits)\b", "'no API secret / account / credits'"),
    ("C3", r"\bidle is free\b", "'idle is free'"),
    ("C4", r"\btalking[- ]time only\b", "'talking time only'"),
    ("C5", r"\bmeters the talking time\b", "'meters the talking time'"),
    ("C6", r"\bshort-lived tokens?\b", "'short-lived token' for the on-device SDKs"),
    ("C7", r"\btherap(y|ies|ist|ists)\b", "therapy / therapist"),
    ("C8", r"\bcare for loneliness\b", "'care for loneliness'"),
    ("C9", r"100% on-device", "'100% on-device'"),
    ("C10", r"\binternet-free\b", "'internet-free'"),
    ("C11", r"100% offline", "'100% offline'"),
    ("C12", r"homebrew-bithuman/(?:-/)?tree/main/Examples", "the deleted tap Examples/ path"),
    ("C13", r"bitHumanKit", "bitHumanKit outside a legacy notice"),
    ("C14", r"\binstant (repl|respons)", "instant replies / responses"),
]
COMPILED = [(rid, re.compile(rx, re.I), desc) for rid, rx, desc in RULES]

LEGACY_RULE = "C13"
LEGACY_DIRS = ("swift/hello-voice-chat/", "swift/macos-voice/", "swift/ios-avatar/")
INLINE_ESCAPE = "claims-check-ignore:"

# One planted line per rule, for the mutation proof.
PLANTS = {
    "C1": "Get a free key at the dashboard.",
    "C2": "The sample needs no account.",
    "C3": "The engine bills talking time; idle is free.",
    "C4": "Sessions bill talking time only.",
    "C5": "The engine meters the talking time it renders.",
    "C6": "Ship sign-in so the app obtains a short-lived token.",
    "C7": "A companion for therapy sessions.",
    "C8": "Apps that care for loneliness.",
    "C9": "Runs 100% on-device.",
    "C10": "An offline license for internet-free operation.",
    "C11": "A 100% offline Mac stack.",
    "C12": "See https://github.com/bithuman-product/homebrew-bithuman/tree/main/Examples/swift",
    "C13": "Most apps want bitHumanKit.",
    "C14": "Instant replies on any phone.",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def tracked_files(root: Path) -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"HARNESS ERROR: git ls-files failed in {root}: {out.stderr.decode()}")
    return [Path(p) for p in out.stdout.decode().split("\0") if p]


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None  # binary
    return data.decode("utf-8", "replace")


def load_allow(root: Path) -> list[dict]:
    p = root / ALLOW_FILE
    if not p.exists():
        return []
    doc = json.loads(p.read_text("utf-8"))
    entries = doc.get("allow", [])
    for e in entries:
        for k in ("file", "rule", "contains", "reason"):
            if not str(e.get(k, "")).strip():
                raise SystemExit(f"HARNESS ERROR: allow entry without '{k}': {e}")
        if e["rule"] not in {r[0] for r in RULES}:
            raise SystemExit(f"HARNESS ERROR: allow entry names an unknown rule: {e}")
    return entries


def scan(root: Path, files: list[Path] | None = None) -> tuple[list[str], list[str]]:
    """Return (findings, stale allow entries)."""
    allow = load_allow(root)
    used = [0] * len(allow)
    findings: list[str] = []
    for rel in files if files is not None else tracked_files(root):
        if rel in SELF or rel.name in SKIP_NAMES:
            continue
        text = read_text(root / rel)
        if text is None:
            continue
        posix = rel.as_posix()
        for n, line in enumerate(text.splitlines(), 1):
            for rid, rx, desc in COMPILED:
                if not rx.search(line):
                    continue
                if INLINE_ESCAPE in line:
                    continue
                if rid == LEGACY_RULE and ("legacy" in line.lower() or posix.startswith(LEGACY_DIRS)):
                    continue
                hit = False
                for i, e in enumerate(allow):
                    if e["file"] == posix and e["rule"] == rid and e["contains"] in line:
                        used[i] += 1
                        hit = True
                        break
                if hit:
                    continue
                findings.append(f"{posix}:{n}: {rid} {desc}: {line.strip()[:160]}")
    stale = [f"STALE allow entry (matches nothing, delete it): {json.dumps(e)}"
             for i, e in enumerate(allow) if used[i] == 0]
    return findings, stale


def grade(root: Path) -> int:
    findings, stale = scan(root)
    for f in findings:
        log(f"::error::{f}")
    for s in stale:
        log(f"::error::{s}")
    if findings or stale:
        log(f"RED: {len(findings)} claim(s), {len(stale)} stale allow entr(y/ies)")
        return 1
    log(f"GREEN: no refused claim in the tracked tree ({len(RULES)} rules, "
        f"{len(load_allow(root))} allow entries, every one in use)")
    return 0


def copy_tree(root: Path, dst: Path) -> list[Path]:
    files = tracked_files(root)
    for rel in files:
        src = root / rel
        if not src.is_file():
            continue
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst / rel)
    return files


def prove_by_mutation(root: Path) -> int:
    missing = [r[0] for r in RULES if r[0] not in PLANTS]
    if missing:
        log(f"HARNESS ERROR: rules with no mutation arm: {missing}")
        return 2
    tmp = Path(tempfile.mkdtemp(prefix="claims-proof-"))
    try:
        files = copy_tree(root, tmp)
        base, stale = scan(tmp, files)
        if base or stale:
            log("HARNESS ERROR: the unmutated tree is already RED, so no arm can prove anything:")
            for f in base + stale:
                log(f"    {f}")
            return 2
        log("  control: the unmutated tree .......................... GREEN [required]")
        bad = 0
        target = Path("README.md")
        original = (tmp / target).read_text("utf-8")
        for rid, _, desc in RULES:
            (tmp / target).write_text(original + "\n" + PLANTS[rid] + "\n", "utf-8")
            found, _ = scan(tmp, files)
            if any(f.startswith(f"{target.as_posix()}:") and f" {rid} " in f for f in found):
                log(f"  [{rid}] plant \"{PLANTS[rid][:50]}\" ... RED as required")
            else:
                log(f"  [{rid}] plant \"{PLANTS[rid][:50]}\" ... STAYED GREEN — the rule is blind")
                bad += 1
        (tmp / target).write_text(original, "utf-8")
        # C13's legacy exemption must be exactly as wide as a line that says so.
        (tmp / target).write_text(original + "\nThe legacy bitHumanKit package is frozen.\n", "utf-8")
        found, _ = scan(tmp, files)
        if found:
            log("  [C13] a line that says legacy ... went RED — the exemption is broken")
            bad += 1
        else:
            log("  [C13] a line that says legacy ... GREEN as required")
        (tmp / target).write_text(original, "utf-8")
        # Every allow entry must be load-bearing: remove each, the tree must go RED.
        allow_path = tmp / ALLOW_FILE
        if allow_path.exists():
            doc = json.loads(allow_path.read_text("utf-8"))
            entries = doc.get("allow", [])
            for i, e in enumerate(entries):
                trimmed = dict(doc)
                trimmed["allow"] = entries[:i] + entries[i + 1:]
                allow_path.write_text(json.dumps(trimmed, indent=2), "utf-8")
                found, _ = scan(tmp, files)
                if found:
                    log(f"  [allow {i}] without {e['file']} {e['rule']} ... RED as required")
                else:
                    log(f"  [allow {i}] without {e['file']} {e['rule']} ... STAYED GREEN — the entry is dead")
                    bad += 1
            allow_path.write_text(json.dumps(doc, indent=2), "utf-8")
            # A stale entry must fail too.
            doc2 = dict(doc)
            doc2["allow"] = entries + [{"file": "README.md", "rule": "C1",
                                        "contains": "zz-nothing-matches-this-zz", "reason": "control"}]
            allow_path.write_text(json.dumps(doc2, indent=2), "utf-8")
            _, stale = scan(tmp, files)
            if stale:
                log("  [stale] an allow entry that matches nothing ... RED as required")
            else:
                log("  [stale] an allow entry that matches nothing ... STAYED GREEN")
                bad += 1
        if bad:
            log(f"MUTATION PROOF FAILED: {bad} arm(s) stayed green")
            return 1
        log(f"MUTATION PROOF PASSED: {len(RULES)} rules, each RED on its planted line")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prove-by-mutation", action="store_true")
    ap.add_argument("--root", default=str(REPO))
    a = ap.parse_args()
    root = Path(a.root)
    if a.prove_by_mutation:
        return prove_by_mutation(root)
    return grade(root)


if __name__ == "__main__":
    sys.exit(main())
