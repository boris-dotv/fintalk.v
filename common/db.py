"""Shared helpers for loading the FinTalk CSV data into SQLite.

The main app, the OSWorld adapters and every demo used to repeat the same
"open an in-memory SQLite database, read company/management/shareholder CSVs
with a utf-8 -> latin-1 fallback, and ``to_sql`` them" logic. These helpers
consolidate that pattern.
"""

import logging
import os
import sqlite3
from typing import Dict, Mapping, Optional

import pandas as pd

# Logical table name -> CSV file name used throughout the project.
DEFAULT_TABLE_FILES: Dict[str, str] = {
    "companies": "company.csv",
    "management": "management.csv",
    "shareholders": "shareholder.csv",
}

_module_logger = logging.getLogger(__name__)


def read_csv_safe(file_path: str) -> pd.DataFrame:
    """Read a CSV as utf-8, falling back to latin-1 on decode/parse errors."""
    try:
        return pd.read_csv(file_path, encoding="utf-8", encoding_errors="ignore")
    except (UnicodeDecodeError, pd.errors.ParserError):
        return pd.read_csv(file_path, encoding="latin-1")


def default_csv_files(data_dir: str) -> Dict[str, str]:
    """Map each logical table name to its CSV path under ``data_dir``."""
    return {
        table: os.path.join(data_dir, filename)
        for table, filename in DEFAULT_TABLE_FILES.items()
    }


def load_csv_tables(
    conn: sqlite3.Connection,
    csv_files: Mapping[str, str],
    *,
    logger: Optional[logging.Logger] = None,
    if_exists: str = "replace",
) -> Dict[str, int]:
    """Load ``{table_name: csv_path}`` into ``conn``.

    Missing files are skipped. Returns a mapping of loaded table name to the
    number of rows loaded (useful for callers that want to log/print results).
    """
    log = logger or _module_logger
    loaded: Dict[str, int] = {}
    for table_name, file_path in csv_files.items():
        if not os.path.exists(file_path):
            log.warning(f"CSV not found: {file_path}")
            continue
        df = read_csv_safe(file_path)
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)
        loaded[table_name] = len(df)
        log.info(f"Loaded {len(df)} rows into '{table_name}'")
    return loaded


def build_memory_db(
    data_dir: str,
    *,
    logger: Optional[logging.Logger] = None,
    connect_kwargs: Optional[dict] = None,
) -> sqlite3.Connection:
    """Create an in-memory SQLite DB with the standard FinTalk tables loaded."""
    conn = sqlite3.connect(":memory:", **(connect_kwargs or {}))
    load_csv_tables(conn, default_csv_files(data_dir), logger=logger)
    return conn
