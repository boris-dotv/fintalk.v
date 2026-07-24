#!/usr/bin/env python3
"""
Autonomous code improvement for FinTalk.v — runs every 2 hours via GitHub Actions.
Reads the codebase, asks DeepSeek for one improvement, applies it, commits, pushes.
If nothing to improve, drops a philosophical thought as a comment to keep the streak.
"""

import os
import sys
import random
import subprocess
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

# ── Fallback: philosophical one-liners for when there's nothing to improve ──
PHILOSOPHY = [
    "We suffer more in imagination than in reality. — Seneca",
    "The impediment to action advances action. What stands in the way becomes the way. — Marcus Aurelius",
    "No person has the power to have everything they want, but it is in their power not to want what they don't have. — Seneca",
    "First say to yourself what you would be; then do what you have to do. — Epictetus",
    "Waste no more time arguing what a good man should be. Be one. — Marcus Aurelius",
    "He who fears death will never do anything worth of a man who is alive. — Seneca",
    "It's not what happens to you, but how you react to it that matters. — Epictetus",
    "The happiness of your life depends upon the quality of your thoughts. — Marcus Aurelius",
    "Luck is what happens when preparation meets opportunity. — Seneca",
    "Don't explain your philosophy. Embody it. — Epictetus",
    "If it is not right, do not do it; if it is not true, do not say it. — Marcus Aurelius",
    "Sometimes even to live is an act of courage. — Seneca",
    "Any person capable of angering you becomes your master. — Epictetus",
    "The best revenge is not to be like your enemy. — Marcus Aurelius",
    "A gem cannot be polished without friction, nor a man perfected without trials. — Seneca",
    "A rational person should cultivate indifference to things beyond their control. If you find yourself looping on a problem you cannot solve, you must actively step away.",
    "Your blog is your calling card. Your work is your evidence. Your image is your signal. The three are one.",
    "Code is not just logic — it is clarity, discipline, and respect for the next reader.",
    "The goal is not to be impressive. The goal is to say something the reader didn't know they needed to hear.",
    "Every line of code is a decision. Make it a thoughtful one.",
    "Build things that make people stop scrolling and start thinking.",
    "Between stimulus and response there is a space. In that space is our power to choose our response.",
    "One person saving ten seconds saves the world seven hundred billion seconds.",
    "The bottleneck is never the tool. It's the clarity of thought behind it.",
    "Ship it. Then ship it better.",
    "Don't just read the docs. Write the docs you wish you had read.",
    "Your GitHub graph is a fossil record of your curiosity. Make it dense.",
    "Done is better than perfect, but thoughtful is better than done.",
    "The answer is always in the code. You just haven't read enough of it yet.",
    "Complexity is a tax paid by everyone who touches the code after you. Be merciful.",
]


def fallback_commit():
    """When the AI finds nothing to improve, add a philosophical comment to keep the streak."""
    os.chdir(REPO_ROOT)

    # Pick a random Python file (not this script, not empty __init__.py)
    eligible = [
        p for p in PYTHON_FILES
        if "daily_improve" not in p
        and Path(p).stat().st_size > 20  # skip near-empty files
        and not p.endswith("__init__.py")  # skip __init__.py files
    ]
    if not eligible:
        print("No eligible files for fallback comment")
        return False

    target = random.choice(eligible)
    fp = REPO_ROOT / target
    content = fp.read_text(encoding="utf-8")

    # Pick a random philosophy line
    thought = random.choice(PHILOSOPHY)
    comment_line = f"# {thought}\n"

    # Insert after the last import or first meaningful line, or at end of file
    lines = content.splitlines()
    insert_at = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1
    # Ensure insert_at doesn't exceed the number of lines
    insert_at = min(insert_at, len(lines))

    # Insert after a blank line following imports, if possible
    if insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1
    # Ensure insert_at doesn't exceed the number of lines
    insert_at = min(insert_at, len(lines))
    # Ensure we don't insert at the very end (after last line) to avoid extra blank line at EOF
    if insert_at == len(lines) and len(lines) > 0:
        insert_at = len(lines) - 1

    lines.insert(insert_at, comment_line.rstrip())
    new_content = "\n".join(lines)
    fp.write_text(new_content, encoding="utf-8")
    print(f"Added philosophy to {target} at line {insert_at+1}")

    # Git config
    subprocess.run(["git", "config", "user.name", "boris-dotv"], check=True)
    subprocess.run(["git", "config", "user.email", "1322553126@qq.com"], check=True)
    subprocess.run(["git", "add", target], check=True)

    # Commit message: first 50 chars of the thought
    short = thought[:50].replace('"', "'").replace("`", "'")
    msg = f"auto: philosophy — {short}"
    subprocess.run(["git", "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)
    print(f"✅ Fallback committed & pushed: {msg}")
    return True

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
- ANY improvement counts: bug fixes, error handling, type hints, refactoring, docstrings, clearer variable names, better comments, logging, edge case handling
- Do NOT change logic or APIs
- If you TRULY see nothing at all worth changing after careful review, output: SKIP"""


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
        print("AI chose to skip — inserting philosophy instead")
        fallback_commit()
        sys.exit(0)

    # 4. Skip if no actual change (AI hallucinated identical OLD/NEW)
    if old_text == new_text:
        print("AI returned identical OLD/NEW — inserting philosophy instead")
        fallback_commit()
        sys.exit(0)

    # 5. Apply change
    if not apply_change(file_path, old_text, new_text):
        print("Failed to apply change, exiting")
        sys.exit(1)

    # 6. Commit & push
    subprocess.run(["git", "config", "user.name", "boris-dotv"], check=True)
    subprocess.run(["git", "config", "user.email", "1322553126@qq.com"], check=True)
    subprocess.run(["git", "add", file_path], check=True)

    # Verify there's actually a diff
    diff_check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True,
    )
    if diff_check.returncode == 0:
        print("No diff to commit — inserting philosophy instead")
        # Unstage the no-op change first
        subprocess.run(["git", "reset", "HEAD", "--", file_path], capture_output=True, check=False)
        subprocess.run(["git", "checkout", "--", file_path], capture_output=True, check=False)
        fallback_commit()
        sys.exit(0)

    # Build sanitized commit message (first meaningful line, no quotes/brackets)
    desc = new_text.strip().split("\n")[0][:60] if new_text else "minor improvement"
    # Strip problematic characters for git commit messages
    desc = desc.replace('"', "'").replace("`", "'").replace("\\", "").replace("\n", " ").replace("\r", "")
    msg = f"auto: {file_path} - {desc}"
    subprocess.run(["git", "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)

    print(f"✅ Committed & pushed: {msg}")


if __name__ == "__main__":
    main()
