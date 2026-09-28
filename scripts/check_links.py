#!/usr/bin/env python3
"""check_links — every bitHuman link and every relative link in this repository resolves.

docs.bithuman.ai was reorganised on 2026-09-27/28 (/sdk/* became /platforms/*,
/guides/* moved under /deploy, /build and /pricing). Old URLs mostly redirect today,
and anchors do not: a link to `/sdk/android#pin-the-version` lands on a page with
no such section. The docs move without a commit here, so this runs on every pull
request, on every push to main, and once a day.

WHAT IS CHECKED
  * Every absolute URL on docs.bithuman.ai, www.bithuman.ai or bithuman.ai in any
    tracked text file: fetched with redirects followed; the final answer must be 200.
    A #fragment on a docs.bithuman.ai page must exist as an id on that page.
  * Every relative link in a Markdown file (`[text](path)`): the path must exist in
    this repository, resolved from the file's own directory.
  URLs holding a placeholder (<CODE>, {id}, $VAR, YOUR_…, …) are skipped; so is
  api.bithuman.ai, whose endpoints need a credential or a POST.

    check_links.py                      grade the tracked tree
    check_links.py --prove-by-mutation  plant a 404, a missing anchor and a broken
                                        relative link; each must turn RED

Exit 0 = every link resolves. Exit 1 = a broken link. Exit 2 = harness error (for
example the docs site itself unreachable: that is not a green).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urldefrag, urlparse

REPO = Path(__file__).resolve().parent.parent
HOSTS = {"docs.bithuman.ai", "www.bithuman.ai", "bithuman.ai"}
URL_RX = re.compile(r"https?://(?:docs\.|www\.)?bithuman\.ai[^\s)\]\"'<>`*|,]*")
MD_LINK_RX = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
PLACEHOLDER_RX = re.compile(r"[<>{}$…]|YOUR_|AGENT_CODE|AGENT_ID|\.\.\.")
SKIP_NAMES = {"package-lock.json"}
MAX_BYTES = 2_000_000
UA = "Mozilla/5.0 (bithuman-examples link check)"
TIMEOUT = 15
ATTEMPTS = 3


def log(msg: str) -> None:
    print(msg, flush=True)


def tracked_files(root: Path) -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(2)
    return [Path(p) for p in out.stdout.decode().split("\0") if p]


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", "replace")


def clean(url: str) -> str:
    return url.rstrip(".,;:!?'\"")


def collect(root: Path, files: list[Path]) -> tuple[dict[str, list[str]], list[str]]:
    """Return ({url: [where]}, [broken relative link findings])."""
    urls: dict[str, list[str]] = {}
    broken_rel: list[str] = []
    for rel in files:
        if rel.name in SKIP_NAMES or rel == Path("scripts/check_links.py"):
            continue
        text = read_text(root / rel)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in URL_RX.finditer(line):
                u = clean(m.group(0))
                if PLACEHOLDER_RX.search(u):
                    continue
                urls.setdefault(u, []).append(f"{rel.as_posix()}:{n}")
            if rel.suffix.lower() != ".md":
                continue
            for m in MD_LINK_RX.finditer(line):
                target = m.group(1)
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                    continue
                path = target.split("#", 1)[0].split("?", 1)[0]
                if not path or PLACEHOLDER_RX.search(path):
                    continue
                resolved = (root / rel.parent / path).resolve()
                try:
                    resolved.relative_to(root.resolve())
                except ValueError:
                    broken_rel.append(f"{rel.as_posix()}:{n}: relative link leaves the repository: {target}")
                    continue
                if not resolved.exists():
                    broken_rel.append(f"{rel.as_posix()}:{n}: relative link to a missing path: {target}")
    return urls, broken_rel


_page_cache: dict[str, tuple[int, str, str]] = {}


def fetch(url: str) -> tuple[int, str, str]:
    """(status, final url, body) — status 0 means the network never answered."""
    if url in _page_cache:
        return _page_cache[url]
    last = (0, url, "")
    for i in range(ATTEMPTS):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read(3_000_000).decode("utf-8", "replace")
                last = (r.status, r.geturl(), body)
                break
        except urllib.error.HTTPError as e:
            last = (e.code, url, "")
            if e.code < 500 and e.code != 429:
                break
        except Exception:  # noqa: BLE001 — DNS, TLS, timeout: retry, then report 0
            last = (0, url, "")
        time.sleep(1.5 * (i + 1))
    _page_cache[url] = last
    return last


def check_url(url: str) -> str | None:
    base, frag = urldefrag(url)
    status, final, body = fetch(base)
    if status != 200:
        return f"HTTP {status or 'no answer'}"
    if frag and urlparse(final).hostname == "docs.bithuman.ai":
        if not re.search(r'id="%s"' % re.escape(frag), body):
            return f"no #{frag} on {final}"
    return None


def grade_tree(root: Path, files: list[Path]) -> tuple[list[str], int]:
    urls, findings = collect(root, files)
    bases = sorted({urldefrag(u)[0] for u in urls})
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(fetch, bases))
    for u, where in sorted(urls.items()):
        err = check_url(u)
        if err:
            findings.append(f"{where[0]}: {u} -> {err}" + (f" (and {len(where) - 1} more)" if len(where) > 1 else ""))
    return findings, len(urls)


def instrument_check() -> bool:
    """The docs site must answer, and a page that cannot exist must NOT be 200."""
    ok, _, _ = fetch("https://docs.bithuman.ai/")
    bogus, _, _ = fetch("https://docs.bithuman.ai/this-page-does-not-exist-zz9")
    if ok != 200:
        log(f"HARNESS ERROR: docs.bithuman.ai did not answer 200 (got {ok}); no link can be graded")
        return False
    if bogus == 200:
        log("HARNESS ERROR: a page that cannot exist answered 200; a 200 here proves nothing")
        return False
    return True


def grade(root: Path) -> int:
    if not instrument_check():
        return 2
    findings, n = grade_tree(root, tracked_files(root))
    for f in findings:
        log(f"::error::{f}")
    if findings:
        log(f"RED: {len(findings)} broken link(s)")
        return 1
    log(f"GREEN: {n} bitHuman URLs answer 200 (anchors checked on docs pages); every relative link resolves")
    return 0


def prove_by_mutation(root: Path) -> int:
    if not instrument_check():
        return 2
    tmp = Path(tempfile.mkdtemp(prefix="links-proof-"))
    try:
        files = tracked_files(root)
        for rel in files:
            if (root / rel).is_file():
                (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / rel, tmp / rel)
        base, _ = grade_tree(tmp, files)
        if base:
            log("HARNESS ERROR: the unmutated tree is already RED:")
            for f in base:
                log(f"    {f}")
            return 2
        log("  control: the unmutated tree ........................ GREEN [required]")
        arms = [
            ("a docs page that 404s", "[gone](https://docs.bithuman.ai/sdk/this-page-was-removed-zz9)"),
            ("an anchor the page does not have", "[pin](https://docs.bithuman.ai/platforms/android#no-such-section-zz9)"),
            ("a relative link to a missing path", "[old](swift/no-such-example-zz9/)"),
        ]
        target = tmp / "README.md"
        original = target.read_text("utf-8")
        bad = 0
        for desc, plant in arms:
            target.write_text(original + "\n" + plant + "\n", "utf-8")
            found, _ = grade_tree(tmp, files)
            if any(f.startswith("README.md:") and "zz9" in f for f in found):
                log(f"  [{desc}] ... RED as required")
            else:
                log(f"  [{desc}] ... STAYED GREEN — the check is blind to it")
                bad += 1
        target.write_text(original, "utf-8")
        if bad:
            log(f"MUTATION PROOF FAILED: {bad} arm(s) stayed green")
            return 1
        log(f"MUTATION PROOF PASSED: {len(arms)}/{len(arms)} arms RED")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prove-by-mutation", action="store_true")
    ap.add_argument("--root", default=str(REPO))
    a = ap.parse_args()
    root = Path(a.root)
    return prove_by_mutation(root) if a.prove_by_mutation else grade(root)


if __name__ == "__main__":
    sys.exit(main())
