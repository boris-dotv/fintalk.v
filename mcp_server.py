# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.0.0",
#     "requests>=2.31.0",
#     "loguru>=0.7.0",
# ]
# ///
"""
FinTalk MCP Server — Financial data analysis tools for AI agents.

Exposes financial analysis capabilities as MCP tools that can be used
by Claude Code, Cursor, and other MCP-compatible AI agents.

Usage:
    uv run --script mcp_server.py
    # or
    python mcp_server.py

Configure in Claude Code (~/.claude/settings.json):
    {
      "mcpServers": {
        "fintalk": {
          "command": "uv",
          "args": ["run", "--script", "/path/to/mcp_server.py"],
          "env": { "DEEPSEEK_API_KEY": "sk-xxx" }
        }
      }
    }
"""

import os
import sys
import csv
import json
import sqlite3
import re
import logging
from pathlib import Path
from typing import Optional

# Log to stderr — stdout is the MCP transport
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("fintalk-mcp")

# Add project root so we can import formula.py
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from formula import (
        get_financial_formulas,
        find_formula_for_query,
        calculate_from_expression,
    )
except ImportError:
    logger.warning("formula.py not found — ratio helpers disabled")

    def get_financial_formulas():
        return []

    def find_formula_for_query(_q):
        return None, None, None

    def calculate_from_expression(_e, _v):
        return float("nan")


from mcp.server.fastmcp import FastMCP


# ================================================================
# Database Layer
# ================================================================


class FinTalkDatabase:
    """In-memory SQLite database loaded from CSV files."""

    PROTECTED_TABLES = frozenset(
        {"companies", "management", "shareholders", "employee_notech"}
    )
    DEFAULT_CSVS = {
        "companies": "company.csv",
        "management": "management.csv",
        "shareholders": "shareholder.csv",
        "employee_notech": "employee_noTech.csv",
    }

    def __init__(self, data_dir: Path):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.company_map: dict[str, int] = {}

        for table_name, filename in self.DEFAULT_CSVS.items():
            filepath = data_dir / filename
            if filepath.exists():
                rows = self._load_csv_to_table(filepath, table_name)
                logger.info(f"Loaded {table_name}: {rows} rows from {filename}")

        self._build_company_map()

    # ---- CSV loading ----

    def _load_csv_to_table(self, filepath: Path, table_name: str) -> int:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return 0

            # Deduplicate column names (e.g. company.csv has two "digital_bank_license")
            seen: dict[str, int] = {}
            fields = []
            for col in header:
                col = col.strip()
                if not col:
                    col = f"_col{len(fields)}"
                if col in seen:
                    seen[col] += 1
                    fields.append(f"{col}_{seen[col]}")
                else:
                    seen[col] = 0
                    fields.append(col)

            cols_def = ", ".join(f'"{c}" TEXT' for c in fields)
            self.conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            self.conn.execute(f'CREATE TABLE "{table_name}" ({cols_def})')

            placeholders = ", ".join(["?"] * len(fields))
            insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'

            batch: list[tuple] = []
            for row in reader:
                # Pad or truncate row to match column count
                padded = row + [""] * (len(fields) - len(row))
                batch.append(tuple(padded[: len(fields)]))

            self.conn.executemany(insert_sql, batch)
            self.conn.commit()
            return len(batch)

    # ---- Company map ----

    def _build_company_map(self):
        try:
            cur = self.conn.execute("SELECT company_sort_id, name FROM companies")
            for row in cur:
                name = row[1]
                if name:
                    self.company_map[name.lower().strip()] = int(row[0])
        except Exception:
            pass

    def get_company_id(self, company_name: str) -> Optional[int]:
        key = company_name.lower().strip()
        if key in self.company_map:
            return self.company_map[key]
        for known, cid in self.company_map.items():
            if key in known or known in key:
                return cid
        return None

    # ---- Introspection ----

    def list_tables(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        result = []
        for (tname,) in cur:
            cnt = self.conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
            result.append({"table": tname, "rows": cnt})
        return result

    def describe_table(self, table_name: str) -> dict:
        exists = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        if not exists:
            return {"error": f"Table '{table_name}' not found"}

        columns = []
        for col in self.conn.execute(f'PRAGMA table_info("{table_name}")'):
            columns.append({"name": col[1], "type": col[2]})

        cnt = self.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

        cur = self.conn.execute(f'SELECT * FROM "{table_name}" LIMIT 3')
        col_names = [d[0] for d in cur.description]
        samples = [dict(zip(col_names, r)) for r in cur]

        return {
            "table": table_name,
            "columns": columns,
            "rows": cnt,
            "sample": samples,
        }

    # ---- Query ----

    def execute_query(self, sql: str) -> list[dict]:
        stripped = sql.strip()
        if not stripped.upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")

        cur = self.conn.execute(stripped)
        col_names = [d[0] for d in cur.description]
        return [dict(zip(col_names, r)) for r in cur.fetchall()]

    # ---- External CSV ----

    def load_external_csv(self, file_path: str, table_name: Optional[str] = None):
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        if path.suffix.lower() != ".csv":
            return {"error": "Only .csv files are supported"}

        tname = table_name or path.stem.lower().replace(" ", "_").replace("-", "_")
        if tname in self.PROTECTED_TABLES:
            return {"error": f"Cannot overwrite built-in table '{tname}'"}

        rows = self._load_csv_to_table(path, tname)
        return {"status": "success", "table": tname, "rows_loaded": rows}

    # ---- Schema overview ----

    def get_schema_overview(self) -> str:
        lines = ["# FinTalk Database Schema\n"]
        for t in self.list_tables():
            lines.append(f"## {t['table']} ({t['rows']} rows)")
            info = self.describe_table(t["table"])
            for col in info["columns"]:
                lines.append(f"  - {col['name']} ({col['type']})")
            lines.append("")
        return "\n".join(lines)


# ================================================================
# Financial Analysis Layer
# ================================================================


class FinancialAnalyzer:
    """Financial analysis functions (ported from function_registry.py)."""

    def __init__(self, db: FinTalkDatabase):
        self.db = db

    def list_companies(self) -> list[dict]:
        try:
            return self.db.execute_query(
                "SELECT company_sort_id, name, website, employee_size, "
                "status, company_tag FROM companies ORDER BY company_sort_id"
            )
        except Exception as e:
            return [{"error": str(e)}]

    def get_company_info(self, company_name: str) -> dict:
        cid = self.db.get_company_id(company_name)
        if cid is None:
            return {"error": f"Company not found: {company_name}"}
        rows = self.db.execute_query(
            f"SELECT * FROM companies WHERE company_sort_id = {cid}"
        )
        if rows:
            return {"company": company_name, "info": rows[0], "status": "success"}
        return {"error": f"No data for {company_name}"}

    def get_top_shareholders(self, company_name: str, top_n: int = 3) -> dict:
        cid = self.db.get_company_id(company_name)
        if cid is None:
            return {"error": f"Company not found: {company_name}"}
        rows = self.db.execute_query(
            f"SELECT shareholder_name, share_percentage, shareholder_tag "
            f"FROM shareholders WHERE company_sort_id = {cid} "
            f"AND share_percentage NOT LIKE '%/%' "
            f"ORDER BY CAST(REPLACE(share_percentage, '%', '') AS REAL) DESC "
            f"LIMIT {int(top_n)}"
        )
        return {
            "company": company_name,
            "top_n": top_n,
            "shareholders": rows,
            "count": len(rows),
            "status": "success",
        }

    # ---- Ratio calculations ----

    @staticmethod
    def _parse_pct(val) -> float:
        if not val or val == "/":
            return 0.0
        try:
            return float(str(val).replace("%", "").strip())
        except (ValueError, TypeError):
            return 0.0

    def calculate_ratio(self, company_name: str, ratio_name: str) -> dict:
        cid = self.db.get_company_id(company_name)
        if cid is None:
            return {"error": f"Company not found: {company_name}"}

        key = ratio_name.lower().replace(" ", "_").replace("-", "_")

        if "executive_director" in key and "non" not in key:
            return self._director_ratio(cid, company_name, "Executive")
        if "non_executive_director" in key:
            return self._director_ratio(cid, company_name, "Non-Executive")
        if "independent_director" in key:
            return self._director_ratio(cid, company_name, "Independent")
        if "shareholder_concentration" in key or "concentration" in key:
            n = 5 if "5" in ratio_name else 3
            return self._concentration(company_name, n)
        if "management_to_employee" in key:
            return self._mgmt_employee_ratio(cid, company_name)

        # Fall back to formula.py
        name, expression, variables = find_formula_for_query(ratio_name)
        if name:
            return {
                "ratio_name": name,
                "expression": expression,
                "required_variables": variables,
                "note": "Formula found. Use query_data to fetch variable values, then compute.",
            }
        return {
            "error": f"Unknown ratio: {ratio_name}",
            "available": [
                "executive_director_ratio",
                "non_executive_director_ratio",
                "independent_director_ratio",
                "shareholder_concentration",
                "management_to_employee_ratio",
            ],
        }

    def _director_ratio(self, cid: int, name: str, dtype: str) -> dict:
        type_count = self.db.execute_query(
            f"SELECT COUNT(*) as cnt FROM management "
            f"WHERE company_sort_id = {cid} AND director_type LIKE '%{dtype}%'"
        )
        total_count = self.db.execute_query(
            f"SELECT COUNT(*) as cnt FROM management "
            f"WHERE company_sort_id = {cid} "
            f"AND director_type IS NOT NULL AND director_type != ''"
        )
        tc = int(type_count[0]["cnt"]) if type_count else 0
        total = int(total_count[0]["cnt"]) if total_count else 0
        if total == 0:
            return {"error": f"No director data for {name}"}
        ratio = tc / total
        return {
            "company": name,
            "ratio_name": f"{dtype.lower()}_director_ratio",
            f"{dtype.lower()}_directors": tc,
            "total_directors": total,
            "ratio": round(ratio, 4),
            "percentage": f"{ratio:.2%}",
            "status": "success",
        }

    def _mgmt_employee_ratio(self, cid: int, name: str) -> dict:
        mgmt = self.db.execute_query(
            f"SELECT COUNT(*) as cnt FROM management WHERE company_sort_id = {cid}"
        )
        emp = self.db.execute_query(
            f"SELECT employee_size FROM companies WHERE company_sort_id = {cid}"
        )
        mc = int(mgmt[0]["cnt"]) if mgmt else 0
        emp_str = emp[0]["employee_size"] if emp else "0"
        m = re.search(r"(\d[\d,]*)", str(emp_str).replace(",", ""))
        ec = int(m.group(1)) if m else 0
        if ec == 0:
            return {"error": f"No employee data for {name}"}
        ratio = mc / ec
        return {
            "company": name,
            "managers": mc,
            "employees": ec,
            "ratio": round(ratio, 4),
            "status": "success",
        }

    def _concentration(self, company_name: str, top_n: int) -> dict:
        data = self.get_top_shareholders(company_name, top_n)
        if "error" in data:
            return data
        total = sum(self._parse_pct(s.get("share_percentage")) for s in data["shareholders"])
        return {
            "company": company_name,
            "top_n": top_n,
            "concentration": round(total, 2),
            "concentration_pct": f"{total:.2f}%",
            "shareholders": data["shareholders"],
            "status": "success",
        }

    def compare_companies(self, c1: str, c2: str, metric: str) -> dict:
        r1 = self.calculate_ratio(c1, metric)
        r2 = self.calculate_ratio(c2, metric)
        if "error" in r1 or "error" in r2:
            return {
                "error": "Comparison failed",
                "details": {c1: r1.get("error"), c2: r2.get("error")},
            }
        v1 = r1.get("ratio") or r1.get("concentration") or 0
        v2 = r2.get("ratio") or r2.get("concentration") or 0
        return {
            "metric": metric,
            c1: r1,
            c2: r2,
            "higher": c1 if v1 > v2 else c2,
            "status": "success",
        }


# ================================================================
# DeepSeek AI Layer (optional)
# ================================================================


class DeepSeekAnalyzer:
    def __init__(self, api_key: str, api_url: str = "", model: str = ""):
        self.api_key = api_key
        self.api_url = api_url or "https://api.deepseek.com/chat/completions"
        self.model = model or "deepseek-chat"

    def analyze(self, question: str, context: str = "") -> str:
        import requests

        user_content = question
        if context:
            user_content = f"Data context:\n{context}\n\nQuestion: {question}"

        try:
            resp = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are FinTalk AI, a professional financial data analyst. "
                                "Analyze the provided data and answer accurately. "
                                "Show calculations when relevant. Be concise but thorough."
                            ),
                        },
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.3,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"AI analysis error: {e}"


# ================================================================
# Initialize
# ================================================================

DATA_DIR = PROJECT_ROOT / "data"
db = FinTalkDatabase(DATA_DIR)
fin = FinancialAnalyzer(db)

_ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
_ds_url = os.environ.get("DEEPSEEK_API_URL", "")
_ds_model = os.environ.get("DEEPSEEK_MODEL", "")
ai = DeepSeekAnalyzer(_ds_key, _ds_url, _ds_model) if _ds_key else None


# ================================================================
# MCP Server
# ================================================================

mcp = FastMCP(
    "fintalk",
    instructions=(
        "FinTalk is a financial data analysis server. "
        "It provides tools to query a database of 607+ companies "
        "including company profiles, management teams, and shareholders. "
        "Use list_tables and describe_table to explore the data, "
        "query_data for custom SQL, and the specialized financial tools "
        "for common analyses. You can also load external CSV files."
    ),
)


# ---- Database tools ----


@mcp.tool()
def list_tables() -> str:
    """List all database tables with their row counts."""
    return json.dumps(db.list_tables(), ensure_ascii=False, indent=2)


@mcp.tool()
def describe_table(table_name: str) -> str:
    """Get column names, types, row count, and 3 sample rows for a table.

    Use list_tables first to see available table names.
    """
    return json.dumps(db.describe_table(table_name), ensure_ascii=False, indent=2)


@mcp.tool()
def query_data(sql: str) -> str:
    """Execute a read-only SQL SELECT query against the financial database.

    Only SELECT statements are allowed.
    Use describe_table to learn column names before writing queries.

    Example: SELECT name, employee_size FROM companies LIMIT 10
    """
    try:
        rows = db.execute_query(sql)
        return json.dumps(rows, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def load_csv(file_path: str, table_name: str = "") -> str:
    """Load a CSV file into the database as a new table.

    file_path: absolute path to a .csv file on this machine.
    table_name: optional name for the table (derived from filename if omitted).

    Built-in tables (companies, management, shareholders) cannot be overwritten.
    """
    return json.dumps(
        db.load_external_csv(file_path, table_name or None), ensure_ascii=False, indent=2
    )


# ---- Financial analysis tools ----


@mcp.tool()
def list_companies() -> str:
    """List all companies with basic info: name, website, employee_size, status."""
    return json.dumps(fin.list_companies(), ensure_ascii=False, indent=2)


@mcp.tool()
def get_company_info(company_name: str) -> str:
    """Get full profile for a company. Supports fuzzy name matching.

    Example: get_company_info("ZA Bank")
    """
    return json.dumps(fin.get_company_info(company_name), ensure_ascii=False, indent=2)


@mcp.tool()
def get_top_shareholders(company_name: str, top_n: int = 3) -> str:
    """Get the top N shareholders of a company with ownership percentages.

    Example: get_top_shareholders("ZA Bank", 5)
    """
    return json.dumps(
        fin.get_top_shareholders(company_name, top_n), ensure_ascii=False, indent=2
    )


@mcp.tool()
def calculate_ratio(company_name: str, ratio_name: str) -> str:
    """Calculate a financial ratio for a company.

    Available ratios:
      - executive_director_ratio
      - non_executive_director_ratio
      - independent_director_ratio
      - shareholder_concentration (top 3 or top 5)
      - management_to_employee_ratio

    Example: calculate_ratio("ZA Bank", "executive_director_ratio")
    """
    return json.dumps(
        fin.calculate_ratio(company_name, ratio_name), ensure_ascii=False, indent=2
    )


@mcp.tool()
def compare_companies(company1: str, company2: str, metric: str) -> str:
    """Compare two companies on a financial metric.

    Example: compare_companies("ZA Bank", "WeLab Bank", "shareholder_concentration")
    """
    return json.dumps(
        fin.compare_companies(company1, company2, metric), ensure_ascii=False, indent=2
    )


# ---- AI tool (conditional) ----

if ai:

    @mcp.tool()
    def ai_analyze(question: str, context: str = "") -> str:
        """Use DeepSeek AI to analyze financial data and answer complex questions.

        Provide relevant data as context for more accurate analysis.
        Requires DEEPSEEK_API_KEY environment variable.

        Example: ai_analyze("What trends do you see?", "ZA Bank: 87%, WeLab: 72%")
        """
        return ai.analyze(question, context)


# ---- Resources ----


@mcp.resource("fintalk://schema")
def schema_resource() -> str:
    """Complete database schema: all tables, columns, types, and row counts."""
    return db.get_schema_overview()


@mcp.resource("fintalk://formulas")
def formulas_resource() -> str:
    """All available financial formulas with their mathematical expressions."""
    formulas = get_financial_formulas()
    lines = ["# Available Financial Formulas\n"]
    for name, expression in formulas:
        lines.append(f"- **{name}** = {expression}")
    return "\n".join(lines)


# ---- Prompts ----


@mcp.prompt()
def analyze_company(company_name: str) -> str:
    """Comprehensive company analysis — guides the AI through a multi-step workflow
    using FinTalk tools to produce a structured financial report."""
    return (
        f"Perform a comprehensive financial analysis of {company_name} "
        f"using the FinTalk MCP tools.\n\n"
        f"Steps:\n"
        f"1. Call get_company_info(\"{company_name}\") for the company profile\n"
        f"2. Call get_top_shareholders(\"{company_name}\", 5) for ownership data\n"
        f"3. Call calculate_ratio(\"{company_name}\", \"executive_director_ratio\")\n"
        f"4. Call calculate_ratio(\"{company_name}\", \"shareholder_concentration\")\n"
        f"5. Synthesize findings into a report:\n"
        f"   - Company Overview\n"
        f"   - Governance Structure (director ratios)\n"
        f"   - Ownership Analysis (shareholder concentration)\n"
        f"   - Key Observations\n"
    )


# ================================================================
# Entry point
# ================================================================

if __name__ == "__main__":
    mcp.run()
