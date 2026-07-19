"""Shared utilities for FinTalk.AI.

Consolidates duplicated code patterns that previously appeared across the
main app, demos and data-generation scripts:

* ``common.llm`` - OpenAI-style chat-completion HTTP calls.
* ``common.db``  - loading the FinTalk CSV files into an in-memory SQLite DB.
"""

from common.db import (
    DEFAULT_TABLE_FILES,
    build_memory_db,
    default_csv_files,
    load_csv_tables,
    read_csv_safe,
)
from common.llm import DEFAULT_API_URL, DEFAULT_MODEL, build_headers, chat_completion

__all__ = [
    "DEFAULT_TABLE_FILES",
    "build_memory_db",
    "default_csv_files",
    "load_csv_tables",
    "read_csv_safe",
    "DEFAULT_API_URL",
    "DEFAULT_MODEL",
    "build_headers",
    "chat_completion",
]
