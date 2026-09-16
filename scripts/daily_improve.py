#!/usr/bin/env python3
"""
FinTalk.v self-evolution loop — runs every 2 hours via GitHub Actions.

Each run:
  1. Builds a context pack: project brief, file tree, recent commits, the
     evolution log (what was done before, what to do next), and 1-3 focus files.
  2. Asks DeepSeek for ONE meaningful, self-contained improvement as JSON.
  3. Applies it, then gates it: every touched .py must parse, the whole repo
     must parse, and any test file touched this round must pass with
     `python -m unittest` (stdlib + light deps only, no network).
  4. Records the step in docs/EVOLUTION.md and commits + pushes.

If the API fails, the AI skips, or the change fails the gate, the run still
lands a commit: a "reflection" entry in docs/EVOLUTION.md describing what was
attempted and why it did not land, so the next run can pick up from there.
Code is never polluted with filler.

Local debugging:
  EVOLVE_MOCK_RESPONSE_FILE=resp.json  use a canned API response instead of DeepSeek
  EVOLVE_NO_PUSH=1                     apply + log, but do not commit or push
"""

from __future__ import annotations

import ast
import datetime as _dt
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ───────────────────────────── configuration ─────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

GIT_NAME = "boris-dotv"
GIT_EMAIL = "1322553126@qq.com"

LOG_REL = "docs/EVOLUTION.md"
LOG_PATH = REPO_ROOT / LOG_REL

# Directories the AI may never touch (any path part).
PROTECTED_PARTS = {".git", ".github", "OSWorld", "__pycache__", "scripts", "assets", "cache", "data"}
# Individual files the AI may never touch.
PROTECTED_FILES = {"scripts/daily_improve.py", ".github/workflows/daily-improve.yml", LOG_REL, "docs/index.html"}
# Where the AI may create new files.
NEW_FILE_DIRS = ("tests/", "docs/")
EDITABLE_SUFFIXES = {".py", ".md"}

# Light third-party packages installed in CI (see .github/workflows/daily-improve.yml).
LIGHT_DEPS = ("loguru", "requests", "python-dotenv", "pyyaml")

# Files we prefer to show the AI (core logic) vs. demos/data generation.
CORE_HINTS = ("enhanced_core/", "formula.py", "mcp_server.py", "enhanced_fintalk.py",
              "feishu_bot.py", "mcp_integration/", "config/", "run.py")

MAX_EDITS = 4
MAX_NEW_FILES = 2
MAX_FOCUS_FILES = 3
MAX_FILE_CHARS = 28_000       # per focus file sent to the model
MAX_BRIEF_CHARS = 2_500       # README / STRUCTURE excerpt
LOG_ENTRIES_IN_PROMPT = 12
API_TIMEOUT_S = 120
TEST_TIMEOUT_S = 180

# ───────────────────────────── small helpers ─────────────────────────────


def sh(*args: str, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), cwd=REPO_ROOT, check=check, capture_output=True, text=True, timeout=timeout)


def rel(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT)).replace(os.sep, "/")


def is_protected(relpath: str) -> bool:
    if relpath in PROTECTED_FILES:
        return True
    return any(part in PROTECTED_PARTS for part in Path(relpath).parts)


def eligible_files() -> list[str]:
    """All files the AI may edit, as repo-relative paths."""
    out = []
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in EDITABLE_SUFFIXES:
            continue
        r = rel(p)
        if not is_protected(r):
            out.append(r)
    return sorted(out)


def python_files() -> list[str]:
    return [f for f in eligible_files() if f.endswith(".py")]


def parse_ok(path: Path) -> str | None:
    """Return None if the file parses, else a short error string."""
    try:
        ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        return None
    except SyntaxError as e:
        return f"{rel(path)}:{e.lineno}: {e.msg}"


def repo_parses() -> list[str]:
    errs = []
    for p in REPO_ROOT.rglob("*.py"):
        if any(part in (".git", "OSWorld", "__pycache__") for part in p.parts):
            continue
        e = parse_ok(p)
        if e:
            errs.append(e)
    return errs


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ───────────────────────────── evolution log ─────────────────────────────

LOG_HEADER = """# FinTalk.v Evolution Log

This file is maintained automatically by `scripts/daily_improve.py`, which runs
every 2 hours. Each entry records one autonomous improvement (or a reflection on
why none landed) plus the ideas queued for the next run. The AI reads the most
recent entries before deciding what to do, so this file is the project's memory.

Newest entries are at the bottom.

"""


def read_log_entries() -> list[str]:
    if not LOG_PATH.exists():
        return []
    body = LOG_PATH.read_text(encoding="utf-8")
    entries = re.split(r"(?m)^(?=## )", body)
    return [e.strip() for e in entries if e.strip().startswith("## ")]


def append_log(entry_md: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text(LOG_HEADER, encoding="utf-8")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(entry_md.rstrip() + "\n\n")


def fmt_list(items: list[str] | None) -> str:
    items = [str(i).strip() for i in (items or []) if str(i).strip()]
    return "; ".join(items) if items else "—"


# ───────────────────────────── context pack ─────────────────────────────


def project_brief() -> str:
    parts = []
    for name in ("README.md", "STRUCTURE.md"):
        p = REPO_ROOT / name
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="replace")
            txt = re.sub(r"<[^>]+>", "", txt)              # drop html badges
            txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
            parts.append(f"=== {name} (excerpt) ===\n{txt[:MAX_BRIEF_CHARS]}")
    return "\n\n".join(parts)


def file_tree() -> str:
    lines = []
    for f in python_files():
        try:
            n = sum(1 for _ in (REPO_ROOT / f).open(encoding="utf-8", errors="replace"))
        except OSError:
            n = 0
        lines.append(f"{f}  ({n} lines)")
    return "\n".join(lines)


def recent_commits(n: int = 12) -> str:
    try:
        return sh("git", "log", f"-{n}", "--format=%ad %s", "--date=short").stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def pick_focus_files(entries: list[str]) -> list[str]:
    """Prefer files named in the latest 'Next' ideas; otherwise weighted random."""
    pool = python_files()
    if not pool:
        return []
    mentioned: list[str] = []
    for e in reversed(entries[-3:]):
        for m in re.finditer(r"[\w./-]+\.py", e):
            cand = m.group(0).lstrip("./")
            if cand in pool and cand not in mentioned:
                mentioned.append(cand)
    picked = mentioned[:MAX_FOCUS_FILES]
    if not picked or random.random() < 0.4:
        weights = [3 if any(f.startswith(h) or f == h for h in CORE_HINTS) else 1 for f in pool]
        target = max(len(picked) + 1, random.randint(1, MAX_FOCUS_FILES))
        while len(picked) < min(target, len(pool)):
            c = random.choices(pool, weights=weights, k=1)[0]
            if c not in picked:
                picked.append(c)
    return picked[:MAX_FOCUS_FILES]


def build_user_prompt(entries: list[str], focus: list[str]) -> str:
    recent = "\n\n".join(entries[-LOG_ENTRIES_IN_PROMPT:]) if entries else "(empty — this is the first run)"
    tests_dir = REPO_ROOT / "tests"
    tests = sorted(rel(p) for p in tests_dir.glob("*.py")) if tests_dir.exists() else []
    focus_blocks = []
    for f in focus:
        txt = (REPO_ROOT / f).read_text(encoding="utf-8", errors="replace")
        if len(txt) > MAX_FILE_CHARS:
            txt = txt[:MAX_FILE_CHARS] + "\n# ... (truncated) ..."
        focus_blocks.append(f"=== FILE: {f} ===\n{txt}")
    nl = "\n"
    return f"""# Project brief
{project_brief()}

# Python files you may edit
{file_tree()}

# Existing tests
{nl.join(tests) or '(none)'}

# Recent commits
{recent_commits()}

# Evolution log (most recent entries; continue from the 'Next' ideas when sensible)
{recent}

# Focus files for this run (full contents)
{nl.join(focus_blocks)}

Now decide on ONE improvement and respond with the JSON object described in your instructions.
"""


SYSTEM_PROMPT = f"""You are the autonomous maintainer of FinTalk.v, an agent-ready financial data analysis
system (NL2SQL over ~999 companies, MCP server, multi-agent orchestration, Feishu bot).
You run every 2 hours with no human in the loop. Each run you make exactly ONE meaningful,
self-contained improvement and leave notes for your future self. Over many runs the project
must become more correct, more robust, better tested and better documented, and gain small
useful capabilities that fit its purpose. That accumulation is the evolution.

Priorities, highest first:
1. Fix a real bug you can actually see in the focus files (wrong logic, unhandled None,
   bad edge case, resource leak, inconsistent return types).
2. Add unit tests for pure logic (e.g. formula.py, enhanced_core/rejection_detector.py,
   enhanced_core/conversation_manager.py, parsing helpers). Tests go in tests/test_*.py and
   use the standard library `unittest`. The test environment has ONLY the standard library
   plus {", ".join(LIGHT_DEPS)}. Tests must not need network, API keys, or heavy dependencies
   (torch, transformers, openai, pandas...). If a module pulls heavy deps at import time,
   stub them via `sys.modules` in the test or pick a smaller pure function instead.
   Tests are run from the repo root, so `from formula import ...` works.
3. Robustness: input validation, clearer error handling, timeouts, logging that helps debugging.
4. Documentation: docstrings, type hints, README/STRUCTURE/API_REFERENCE corrections.
5. A small feature that the README/roadmap implies and that can be finished in one run.

Use the evolution log: continue a 'Next' idea when it is still valid, and never redo something
already logged as done. Vary the area you work on across runs. If a previous attempt was
rejected by the gate, read the reason and do it correctly this time or move on.

Hard rules:
- Every edit is an exact, unique substring replacement. `old` must be copied verbatim from the
  focus file and occur exactly once. Keep each run under ~100 changed lines total.
- Do not change public function signatures or observable behaviour that callers depend on.
- No new third-party dependencies. No filler: never add quotes, mottos, or decorative comments.
- Never touch: scripts/, .github/, OSWorld/, assets/, data/, cache/, docs/EVOLUTION.md, docs/index.html.
- New files only under tests/ or docs/ (Markdown or Python).
- Only edit files whose full contents you were shown, unless the edit is a new file.
- Tests must actually pass against the current code. Do not assert behaviour you have not
  verified by reading the implementation.

Respond with ONLY a JSON object (no prose, no code fences) in one of these two shapes:

{{
  "type": "bugfix | tests | robustness | docs | feature | refactor",
  "summary": "one line, imperative, <= 70 chars, e.g. 'Guard formula.calc against empty input'",
  "rationale": "2-4 sentences: what was wrong or missing and why this change is the right one",
  "edits": [
    {{"file": "relative/path.py", "old": "exact existing text", "new": "replacement text"}}
  ],
  "new_files": [
    {{"file": "tests/test_something.py", "content": "full file content"}}
  ],
  "next_ideas": ["concrete follow-ups for future runs, mention file paths"]
}}

or, only if nothing in the focus files is worth changing:

{{"skip": true, "reason": "why", "next_ideas": ["what to look at instead, with file paths"]}}

`edits` may be empty when `new_files` is non-empty and vice versa. Max {MAX_EDITS} edits and
{MAX_NEW_FILES} new files. Output valid JSON only.
"""

# ───────────────────────────── model call ─────────────────────────────


class ApiError(Exception):
    pass


def call_deepseek(user_prompt: str) -> str:
    mock = os.environ.get("EVOLVE_MOCK_RESPONSE_FILE")
    if mock:
        print(f"[mock] using canned response from {mock}")
        return Path(mock).read_text(encoding="utf-8")
    if not API_KEY:
        raise ApiError("DEEPSEEK_API_KEY is not set")
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 8000,
        "response_format": {"type": "json_object"},
    }).encode()
    req = Request(API_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    })
    try:
        with urlopen(req, timeout=API_TIMEOUT_S) as resp:
            data = json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        raise ApiError(f"HTTP {e.code}: {body}") from e
    except (URLError, TimeoutError, OSError) as e:
        raise ApiError(str(e)) from e
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ApiError(f"unexpected response shape: {str(data)[:300]}") from e


def parse_plan(text: str) -> dict:
    """Extract the JSON object from the model output."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            raise ValueError(f"no JSON object in response: {t[:200]!r}")
        obj = json.loads(m.group(0))
    if not isinstance(obj, dict):
        raise ValueError("response JSON is not an object")
    return obj


# ───────────────────────────── apply + gate ─────────────────────────────


class Rejected(Exception):
    pass


def _norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.splitlines())


def validate_and_apply(plan: dict) -> tuple[list[str], list[str]]:
    """Apply edits/new_files. Returns (changed_files, created_files). Raises Rejected."""
    edits = plan.get("edits") or []
    new_files = plan.get("new_files") or []
    if not isinstance(edits, list) or not isinstance(new_files, list):
        raise Rejected("edits/new_files must be lists")
    if not edits and not new_files:
        raise Rejected("plan contains no edits and no new files")
    if len(edits) > MAX_EDITS or len(new_files) > MAX_NEW_FILES:
        raise Rejected(f"too many changes ({len(edits)} edits, {len(new_files)} new files)")

    pending: dict[str, str] = {}   # relpath -> new content
    created: list[str] = []

    for i, e in enumerate(edits):
        if not isinstance(e, dict):
            raise Rejected(f"edit {i}: not an object")
        f, old, new = (e.get("file") or "").strip().lstrip("./"), e.get("old"), e.get("new")
        if not f or not isinstance(old, str) or not isinstance(new, str):
            raise Rejected(f"edit {i}: missing file/old/new")
        if is_protected(f) or Path(f).suffix not in EDITABLE_SUFFIXES:
            raise Rejected(f"edit {i}: {f} is not editable")
        p = REPO_ROOT / f
        if not p.is_file():
            raise Rejected(f"edit {i}: {f} does not exist")
        if not old.strip():
            raise Rejected(f"edit {i}: empty 'old'")
        if old == new:
            raise Rejected(f"edit {i}: old == new (no-op)")
        content = pending.get(f) or p.read_text(encoding="utf-8")
        n = content.count(old)
        if n == 0:
            # tolerate trailing-whitespace drift on each line
            c2, o2 = _norm(content), _norm(old)
            if c2.count(o2) == 1:
                content, old, n = c2, o2, 1
        if n != 1:
            raise Rejected(f"edit {i}: 'old' occurs {n} times in {f} (need exactly 1)")
        pending[f] = content.replace(old, new, 1)

    for i, nf in enumerate(new_files):
        if not isinstance(nf, dict):
            raise Rejected(f"new_file {i}: not an object")
        f, content = (nf.get("file") or "").strip().lstrip("./"), nf.get("content")
        if not f or not isinstance(content, str) or not content.strip():
            raise Rejected(f"new_file {i}: missing file/content")
        if not f.startswith(NEW_FILE_DIRS) or Path(f).suffix not in EDITABLE_SUFFIXES or is_protected(f):
            raise Rejected(f"new_file {i}: {f} is not an allowed location")
        if (REPO_ROOT / f).exists() or f in pending:
            raise Rejected(f"new_file {i}: {f} already exists")
        pending[f] = content if content.endswith("\n") else content + "\n"
        created.append(f)

    # Syntax-check everything in memory before touching disk.
    for f, content in pending.items():
        if f.endswith(".py"):
            try:
                ast.parse(content, filename=f)
            except SyntaxError as e:
                raise Rejected(f"{f}:{e.lineno}: {e.msg} (change would break syntax)")

    for f, content in pending.items():
        p = REPO_ROOT / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return list(pending.keys()), created


def run_gate(changed: list[str]) -> None:
    """Raise Rejected if the applied change fails any check."""
    errs = repo_parses()
    if errs:
        raise Rejected("repo no longer parses: " + "; ".join(errs[:3]))

    tests = [f for f in changed if f.startswith("tests/") and Path(f).name.startswith("test") and f.endswith(".py")]
    for t in tests:
        try:
            r = sh(sys.executable, "-m", "unittest", "-v", t, check=False, timeout=TEST_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise Rejected(f"{t}: tests timed out after {TEST_TIMEOUT_S}s")
        tail = [ln for ln in (r.stderr or r.stdout).strip().splitlines() if ln.strip()][-6:]
        print(f"[gate] unittest {t} -> rc={r.returncode}\n  " + "\n  ".join(tail))
        if r.returncode != 0:
            raise Rejected(f"{t} failed: " + " | ".join(tail[-3:]))

    if sh("git", "status", "--porcelain", check=False).stdout.strip() == "":
        raise Rejected("no effective change after applying plan")


def revert(changed: list[str], created: list[str]) -> None:
    """Undo this round's changes only (never touches unrelated working-tree files)."""
    for f in created:
        try:
            (REPO_ROOT / f).unlink()
        except FileNotFoundError:
            pass
    tracked = [f for f in changed if f not in created]
    if tracked:
        sh("git", "checkout", "--", *tracked, check=False)


# ───────────────────────────── commit ─────────────────────────────


def commit_and_push(message: str, paths: list[str]) -> None:
    paths = [p for p in paths if not is_protected(p) or p == LOG_REL]
    if os.environ.get("EVOLVE_NO_PUSH"):
        print(f"[dry-run] would commit {paths}: {message}")
        return
    sh("git", "config", "user.name", GIT_NAME)
    sh("git", "config", "user.email", GIT_EMAIL)
    sh("git", "add", "--", *paths)
    if sh("git", "diff", "--cached", "--quiet", check=False).returncode == 0:
        print("nothing staged, skipping commit")
        return
    sh("git", "commit", "-m", message)
    for attempt in range(3):
        r = sh("git", "push", check=False)
        if r.returncode == 0:
            print(f"pushed: {message}")
            return
        print(f"push failed (attempt {attempt + 1}): {r.stderr.strip()[:200]}")
        sh("git", "pull", "--rebase", "-q", check=False)
    raise RuntimeError("git push failed after 3 attempts")


def clean_msg(s: object, limit: int = 70) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip().replace('"', "'").replace("`", "'")
    return s[:limit]


# ───────────────────────────── main ─────────────────────────────


def land_reflection(attempted: str, blocked_by: str, next_ideas: list[str] | None) -> None:
    """Fallback commit: record why nothing landed so the next run learns from it."""
    entry = (
        f"## {now_utc()} — Reflection: no code change landed\n"
        f"- **Attempted:** {attempted or '—'}\n"
        f"- **Blocked by:** {blocked_by}\n"
        f"- **Next:** {fmt_list(next_ideas)}"
    )
    append_log(entry)
    commit_and_push(f"evolve(log): reflection — {clean_msg(blocked_by, 60)}", [LOG_REL])


def main() -> int:
    os.chdir(REPO_ROOT)
    random.seed()

    entries = read_log_entries()
    focus = pick_focus_files(entries)
    print(f"focus files: {focus}")
    user_prompt = build_user_prompt(entries, focus)
    print(f"prompt size: {len(user_prompt)} chars, {len(entries)} log entries")

    try:
        raw = call_deepseek(user_prompt)
    except ApiError as e:
        print(f"API error: {e}")
        land_reflection("call DeepSeek for an improvement", f"API error: {clean_msg(e, 200)}", [f"retry on {', '.join(focus)}"])
        return 0

    print("model output (head):\n" + raw[:800])
    try:
        plan = parse_plan(raw)
    except ValueError as e:
        print(f"unparseable plan: {e}")
        land_reflection("parse model plan", f"unparseable JSON: {clean_msg(e, 120)}", [f"retry on {', '.join(focus)}"])
        return 0

    if plan.get("skip"):
        reason = clean_msg(plan.get("reason", "model chose to skip"), 200)
        print(f"model skipped: {reason}")
        land_reflection(f"review {', '.join(focus)}", f"model skipped: {reason}", plan.get("next_ideas"))
        return 0

    summary = clean_msg(plan.get("summary") or "improvement")
    changed: list[str] = []
    created: list[str] = []
    try:
        changed, created = validate_and_apply(plan)
        run_gate(changed)
    except Rejected as e:
        print(f"REJECTED: {e}")
        revert(changed, created)
        land_reflection(summary, f"rejected by gate: {clean_msg(e, 200)}", plan.get("next_ideas"))
        return 0

    entry = (
        f"## {now_utc()} — {summary}\n"
        f"- **Type:** {clean_msg(plan.get('type', 'improvement'), 20)}\n"
        f"- **Files:** {', '.join(changed)}\n"
        f"- **Why:** {clean_msg(plan.get('rationale', ''), 600)}\n"
        f"- **Next:** {fmt_list(plan.get('next_ideas'))}"
    )
    append_log(entry)
    commit_and_push(f"evolve: {summary}", changed + [LOG_REL])
    return 0


if __name__ == "__main__":
    sys.exit(main())
