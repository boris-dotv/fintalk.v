#!/usr/bin/env python3
"""
Daily autonomous code improvement for FinTalk.v.
Called by GitHub Actions. Reads the codebase, picks a file,
asks DeepSeek for one improvement, applies it, commits, pushes.
"""

import os
import sys
import random
import subprocess
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

API_KEY = os.environ["DEEPSEEK_API_KEY"]
API_URL = "https://api.deepseek.com/chat/completions"
REPO_ROOT = Path(__file__).resolve().parent.parent

# Files eligible for improvement (exclude data, logs, .git, assets)
PYTHON_FILES = [
    str(p.relative_to(REPO_ROOT))
    for p in REPO_ROOT.rglob("*.py")
    if ".git" not in p.parts
    and "OSWorld" not in p.parts  # skip vendored OSWorld
    and "__pycache__" not in p.parts
]

SYSTEM_PROMPT = """You are a senior software engineer. Review the given code and suggest ONE small, concrete improvement. Output in this exact format:

FILE: <relative path to the file to modify>
OLD: <exact lines to replace>
NEW: <replacement lines>

Rules:
- ONE change only, small and safe
- OLD must match the file exactly (copy-paste from the provided code)
- Prioritize: bug fixes > error handling > type hints > refactoring > docstrings
- Do NOT change logic or APIs
- If you see nothing worth changing, output: SKIP"""


def call_deepseek(prompt: str) -> str:
    """Call DeepSeek API and return the response text."""
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }).encode()
    req = Request(API_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    })
    try:
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except URLError as e:
        print(f"API error: {e}")
        sys.exit(1)


def pick_files() -> list[Path]:
    """Pick 1-3 Python files to send for review."""
    if not PYTHON_FILES:
        print("No Python files found")
        sys.exit(0)
    n = min(random.randint(1, 3), len(PYTHON_FILES))
    picked = random.sample(PYTHON_FILES, n)
    print(f"Reviewing {n} file(s): {picked}")
    return [REPO_ROOT / p for p in picked]


def build_prompt(files: list[Path]) -> str:
    """Build the prompt with file contents."""
    parts = []
    for fp in files:
        rel = fp.relative_to(REPO_ROOT)
        content = fp.read_text(encoding="utf-8", errors="replace")
        parts.append(f"=== {rel} ===\n{content}")
    return "\n\n".join(parts)


def parse_response(response: str) -> tuple[str | None, str | None, str | None]:
    """Parse FILE/OLD/NEW from AI response. Returns (file, old, new) or (None, None, None)."""
    if "SKIP" in response.upper().split("\n")[0]:
        return None, None, None

    import re
    file_match = re.search(r"FILE:\s*(.+)", response)
    old_match = re.search(r"OLD:\s*\n?(.*?)(?=\nNEW:|\Z)", response, re.DOTALL)
    new_match = re.search(r"NEW:\s*\n?(.*?)(?=\n\w+:|\Z)", response, re.DOTALL)

    if not (file_match and old_match and new_match):
        print("Could not parse AI response:")
        print(response[:500])
        return None, None, None

    return (
        file_match.group(1).strip(),
        old_match.group(1).strip(),
        new_match.group(1).strip(),
    )


def apply_change(file_path: str, old_text: str, new_text: str) -> bool:
    """Apply the change to the file. Returns True on success."""
    fp = REPO_ROOT / file_path
    if not fp.exists():
        print(f"File not found: {file_path}")
        return False

    content = fp.read_text(encoding="utf-8")
    if old_text not in content:
        print(f"OLD text not found in {file_path}")
        print(f"Looking for:\n{old_text[:200]}")
        return False

    new_content = content.replace(old_text, new_text, 1)
    fp.write_text(new_content, encoding="utf-8")
    print(f"Applied change to {file_path}")
    return True


def main():
    os.chdir(REPO_ROOT)

    # 1. Pick files
    files = pick_files()

    # 2. Build prompt & call AI
    prompt = build_prompt(files)
    print(f"Prompt size: {len(prompt)} chars")
    response = call_deepseek(prompt)
    print(f"AI response:\n{response[:500]}")

    # 3. Parse response
    file_path, old_text, new_text = parse_response(response)
    if file_path is None:
        print("AI chose to skip — nothing to improve today")
        sys.exit(0)

    # 4. Skip if no actual change (AI hallucinated identical OLD/NEW)
    if old_text == new_text:
        print("AI returned identical OLD/NEW — no real change, skipping")
        sys.exit(0)

    # 5. Apply change
    if not apply_change(file_path, old_text, new_text):
        print("Failed to apply change, exiting")
        sys.exit(1)

    # 6. Commit & push
    subprocess.run(["git", "config", "user.name", "fintalk-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@fintalk.ai"], check=True)
    subprocess.run(["git", "add", file_path], check=True)

    # Verify there's actually a diff
    diff_check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True,
    )
    if diff_check.returncode == 0:
        print("No diff to commit — skipping")
        sys.exit(0)

    # Build sanitized commit message (first meaningful line, no quotes/brackets)
    desc = new_text.strip().split("\n")[0][:60] if new_text else "minor improvement"
    # Strip problematic characters for git commit messages
    desc = desc.replace('"', "'").replace("`", "'").replace("\\", "")
    msg = f"auto: {file_path} - {desc}"
    subprocess.run(["git", "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)

    print(f"✅ Committed & pushed: {msg}")


if __name__ == "__main__":
    main()
