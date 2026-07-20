"""Shared pytest configuration for the FinTalk.AI test suite.

Ensures the project root is importable so tests can `import formula`,
`import enhanced_core...`, etc. regardless of the working directory.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# These are runnable demo scripts (not automated tests): they require a live
# GITHUB_TOKEN, network access, and third-party packages, so they are excluded
# from automated collection.
collect_ignore = ["test_github_mcp.py", "mcp_test.py"]
