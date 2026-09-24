#!/usr/bin/env python3
"""Every OpenAI Realtime model an example builds must choose its turn detection.

livekit-plugins-openai's RealtimeModel defaults to semantic VAD, which waits up
to ~4 s after you stop talking before it answers (measured on the raw API:
end of speech -> first reply audio 5.10 s with the default, 0.82 s with
server_vad at 500 ms of silence). An example that leaves the argument out
teaches the slow default to everyone who copies it. So every `RealtimeModel(`
call in the repo must pass `turn_detection=` (Python) or `turnDetection`
(JavaScript/TypeScript), in code files and in Markdown code snippets alike.

usage: check_realtime_turn_detection.py [--selftest] [root]
"""
import ast
import pathlib
import re
import sys

TEXT_SUFFIXES = {".md", ".mdx", ".js", ".mjs", ".ts", ".tsx", ".jsx"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "build", "dist"}


def python_misses(src: str, name: str) -> list[str]:
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [f"{name}:{e.lineno}: does not parse ({e.msg})"]
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        called = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if called != "RealtimeModel":
            continue
        kws = {k.arg for k in node.keywords}  # None = a **kwargs splat, which cannot be judged
        if "turn_detection" not in kws:
            out.append(f"{name}:{node.lineno}: RealtimeModel(...) without an explicit turn_detection=")
    return out


def text_misses(src: str, name: str) -> list[str]:
    out = []
    for m in re.finditer(r"RealtimeModel\s*\(", src):
        depth, i = 1, m.end()
        while i < len(src) and depth:
            depth += {"(": 1, ")": -1}.get(src[i], 0)
            i += 1
        args = src[m.end():i]
        if not re.search(r"turn_detection\s*=|turnDetection\s*:", args):
            out.append(f"{name}:{src.count(chr(10), 0, m.start()) + 1}: RealtimeModel(...) without turn detection")
    return out


def check_file(path: pathlib.Path, rel: str) -> list[str]:
    src = path.read_text(errors="ignore")
    if "RealtimeModel" not in src:
        return []
    return python_misses(src, rel) if path.suffix == ".py" else text_misses(src, rel)


def scan(root: pathlib.Path) -> list[str]:
    misses = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or SKIP_DIRS & set(p.relative_to(root).parts):
            continue
        if p.suffix == ".py" or p.suffix in TEXT_SUFFIXES:
            misses += check_file(p, str(p.relative_to(root)))
    return misses


def selftest() -> int:
    cases = [  # (suffix, source, must_flag)
        (".py", 'm = openai.realtime.RealtimeModel(voice="coral")', True),
        (".py", 'm = RealtimeModel(\n  voice="coral",\n  model="gpt-realtime-2.1-mini")', True),
        (".py", 'm = RealtimeModel(**opts)', True),
        (".py", 'm = openai.realtime.RealtimeModel(voice="coral",\n  turn_detection=ServerVad(type="server_vad"))', False),
        (".py", '# RealtimeModel( in a comment is not a call\nx = 1', False),
        (".md", '```python\nllm=openai.realtime.RealtimeModel(voice="alloy")\n```', True),
        (".md", '```python\nllm=openai.realtime.RealtimeModel(\n  voice="alloy", turn_detection=td)\n```', False),
        (".ts", 'new openai.realtime.RealtimeModel({ voice: "coral" })', True),
        (".ts", 'new openai.realtime.RealtimeModel({ voice: "coral", turnDetection: td })', False),
    ]
    bad = 0
    for i, (suffix, src, must_flag) in enumerate(cases, 1):
        got = python_misses(src, f"case{i}") if suffix == ".py" else text_misses(src, f"case{i}")
        ok = bool(got) == must_flag
        bad += not ok
        print(f"selftest {i}: {'ok' if ok else 'WRONG'} ({'must flag' if must_flag else 'must pass'}, flagged {len(got)})")
    print("selftest: " + ("all controls behave" if not bad else f"{bad} control(s) WRONG"))
    return 1 if bad else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest())
    root = pathlib.Path(args[0] if args else ".").resolve()
    misses = scan(root)
    for line in misses:
        print(f"::error::{line} (the plugin default, semantic VAD, answers up to ~4 s late; "
              "pass turn_detection=ServerVad(type=\"server_vad\", silence_duration_ms=500, ...))")
    print(f"{len(misses)} RealtimeModel call(s) without turn detection")
    sys.exit(1 if misses else 0)
