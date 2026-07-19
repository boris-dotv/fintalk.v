#!/usr/bin/env python3
"""
FinTalk.AI - Complex Query Demo
Demonstrates multi-step SQL queries + Formula calculation

Example Query: "What is the executive_director_ratio for ZA Bank?"

This requires:
1. SQL 1: Find ZA Bank's company_sort_id
2. SQL 2: Count Executive Directors for ZA Bank
3. SQL 3: Count all Directors for ZA Bank
4. Formula: executive_director_ratio = (Executive Directors) / (Total Directors)
"""

import os
import sys
import json
import requests
import pandas as pd
import sqlite3
from typing import Dict, Any, List

# Setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from formula import find_formula_for_query, calculate_from_expression
from common.db import default_csv_files, load_csv_tables
from common.llm import chat_completion

# Code is not just logic — it is clarity, discipline, and respect for the next reader.
# API Configuration
API_URL = "https://qianfan.baidubce.com/v2/chat/completions"
API_KEY = os.environ["QIANFAN_API_KEY"]
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# Database Schema
DB_SCHEMA = """
CREATE TABLE companies (
    company_sort_id INT PRIMARY KEY,
    name VARCHAR(255),
    employee_size INT,
    size_category VARCHAR(50)
);

CREATE TABLE management (
    management_id INT PRIMARY KEY,
    company_sort_id INT,
    management_name VARCHAR(255),
    management_title VARCHAR(255),
    management_department VARCHAR(100),
    director_type VARCHAR(100)
);

CREATE TABLE shareholders (
    shareholder_id INT PRIMARY KEY,
    company_sort_id INT,
    shareholder_name VARCHAR(255),
    share_percentage VARCHAR(20),
    shareholder_tag VARCHAR(50)
);
"""

def call_llm(prompt: str, temperature: float = 0.3) -> str:
    """Call LLM API."""
    try:
        return chat_completion(
            [{"role": "user", "content": prompt}],
            api_url=API_URL,
            headers=HEADERS,
            model="deepseek-v3.2-think",
            temperature=temperature,
            timeout=30,
            web_search={"enable": False},
            raise_on_error=True,
        )
    except Exception as e:
        print(f"❌ API Error: {e}")
        return ""


def setup_database():
    """Load CSV data into SQLite."""
    conn = sqlite3.connect(':memory:')
    csv_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    csv_files = default_csv_files(csv_dir)
    # Validate that all CSV files exist before attempting to load them
    missing = [name for name, path in csv_files.items() if not os.path.exists(path)]
    if missing:
        print(f"❌ Missing CSV files: {', '.join(missing)}")
        sys.exit(1)

    for table_name, rows in load_csv_tables(conn, csv_files).items():
        print(f"✅ Loaded {rows} rows into '{table_name}'")

    return conn


def execute_sql(conn, sql: str) -> List[Dict]:
    """Execute SQL and return results."""
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ SQL Error: {e}")
        return []


# ============== COMPLEX QUERY DEMO ==============
def complex_query_demo(conn):
    """Demonstrate a complex query that requires multiple SQL calls + formula."""

    print("\n" + "="*70)
    print("🎯 COMPLEX QUERY DEMO: Multi-Step SQL + Formula Calculation")
    print("="*70)

    user_query = "What is the executive_director_ratio for ZA Bank?"

    print(f"\n👤 User Query: \"{user_query}\"")
    print("\n" + "-"*70)
    print("📋 Step-by-Step Execution:")
    print("-"*70)

    # Step 1: Find ZA Bank's company_sort_id
    print("\n📍 Step 1: Find ZA Bank's company_sort_id")
    print("   Orchestrator: I need to find ZA Bank's ID first.")

    sql_1 = "SELECT company_sort_id FROM companies WHERE name LIKE '%ZA Bank%'"
    print(f"   SQL: {sql_1}")

    result_1 = execute_sql(conn, sql_1)
    print(f"   Result: {result_1}")

    if not result_1 or len(result_1) == 0:
        print("   ❌ Company not found!")
        return

    company_id = result_1[0]['company_sort_id']
    print(f"   ✅ Found company_sort_id: {company_id}")

    # Step 2: Count Executive Directors
    print(f"\n📍 Step 2: Count Executive Directors for company_id = {company_id}")
    print("   Orchestrator: Now I need to count the executive directors.")

    sql_2 = f"""
    SELECT COUNT(*) as executive_count
    FROM management
    WHERE company_sort_id = {company_id}
      AND director_type LIKE '%Executive Director%'
    """
    print(f"   SQL: {sql_2}")

    result_2 = execute_sql(conn, sql_2)
    print(f"   Result: {result_2}")

    executive_count = result_2[0]['executive_count']
    print(f"   ✅ Executive Directors count: {executive_count}")

    # Step 3: Count all Directors
    print(f"\n📍 Step 3: Count all Directors for company_id = {company_id}")
    print("   Orchestrator: Now I need the total number of directors.")

    sql_3 = f"""
    SELECT COUNT(*) as total_directors
    FROM management
    WHERE company_sort_id = {company_id}
      AND director_type IS NOT NULL
      AND director_type != ''
    """
    print(f"   SQL: {sql_3}")

    result_3 = execute_sql(conn, sql_3)
    print(f"   Result: {result_3}")

    total_directors = result_3[0]['total_directors']
    print(f"   ✅ Total Directors count: {total_directors}")

    # Step 4: Calculate using formula
    print(f"\n📍 Step 4: Calculate executive_director_ratio using Formula Library")
    print("   Orchestrator: I have all the data. Now I'll use the formula library.")

    formula_name = "executive_director_ratio"
    values = {
        "Count of Executive Directors": executive_count,
        "Total Count of Directors": total_directors
    }

    name, expression, variables = find_formula_for_query(formula_name)
    print(f"   Formula: {name}")
    print(f"   Expression: {expression}")
    print(f"   Values: {values}")

    result = calculate_from_expression(expression, values)
    print(f"   ✅ Calculation Result: {result:.4f} (or {result:.2%})")

    # Step 5: Generate final answer
    print(f"\n📍 Step 5: Generate natural language answer")
    print("   Orchestrator: Let me compose the final answer.")

    final_prompt = f"""
Based on the database query and calculation results:
- Company: ZA Bank
- Executive Directors: {executive_count}
- Total Directors: {total_directors}
- Executive Director Ratio: {result:.2%}

Provide a clear, professional answer to the user's question: "{user_query}"
"""

    final_answer = call_llm(final_prompt, temperature=0.7)
    print(f"   ✅ Final Answer: {final_answer}")

    print("\n" + "="*70)
    print("🎉 Complex Query Completed Successfully!")
    print("="*70)

    return {
        "company": "ZA Bank",
        "executive_directors": executive_count,
        "total_directors": total_directors,
        "ratio": result
    }


# ============== EVEN MORE COMPLEX: Comparison Query ==============
def comparison_query_demo(conn):
    """Demonstrate comparing two companies."""

    print("\n" + "="*70)
    print("🎯 BONUS: Multi-Company Comparison Query")
    print("="*70)

    user_query = "Compare the executive_director_ratio between ZA Bank and WeLab Bank"

    print(f"\n👤 User Query: \"{user_query}\"")
    print("\n" + "-"*70)

    companies_to_compare = ["ZA Bank", "WeLab Bank"]
    results = []

    for company_name in companies_to_compare:
        print(f"\n📍 Processing {company_name}:")

        # Find company ID
        sql = f"SELECT company_sort_id FROM companies WHERE name LIKE '%{company_name}%'"
        result = execute_sql(conn, sql)
        if not result or len(result) == 0:
            print(f"   ⚠️  {company_name} not found, skipping.")
            continue

        company_id = result[0]['company_sort_id']

        # Count Executive Directors
        sql_exec = f"""
        SELECT COUNT(*) as count FROM management
        WHERE company_sort_id = {company_id}
          AND director_type LIKE '%Executive Director%'
        """
        exec_result = execute_sql(conn, sql_exec)
        exec_count = exec_result[0]['count'] if exec_result else 0

        # Count Total Directors
        sql_total = f"""
        SELECT COUNT(*) as count FROM management
        WHERE company_sort_id = {company_id}
          AND director_type IS NOT NULL
        """
        total_result = execute_sql(conn, sql_total)
        total_count = total_result[0]['count'] if total_result else 0

        # Calculate ratio
        ratio = exec_count / total_count if total_count > 0 else 0

        results.append({
            "company": company_name,
            "executive_directors": exec_count,
            "total_directors": total_count,
            "ratio": ratio
        })

        print(f"   Executive Directors: {exec_count}")
        print(f"   Total Directors: {total_count}")
        print(f"   Ratio: {ratio:.2%}")

    # Generate comparison answer
    print(f"\n📍 Generating comparison...")

    comparison_prompt = f"""
Compare the executive director ratios for these companies:

{json.dumps(results, indent=2)}

Provide a clear comparison answering: "{user_query}"
"""

    comparison_answer = call_llm(comparison_prompt, temperature=0.7)
    print(f"\n🤖 Comparison Result:\n{comparison_answer}")

    print("\n" + "="*70)


# ============== MAIN ==============
def main():
    """Run the demo."""

    print("\n" + "="*70)
    print("🚀 FinTalk.AI - Complex Query Demo")
    print("   Demonstrating Multi-Step SQL + Formula Calculation")
    print("="*70)

    # Setup database
    print("\n📊 Setting up database...")
    conn = setup_database()

    # Run complex query demo
    complex_query_demo(conn)

    # Run comparison demo
    comparison_query_demo(conn)

    print("\n\n✅ Demo completed! Your FinTalk.AI system can:")
    print("   1. Break down complex queries into multiple steps")
    print("   2. Execute multiple SQL queries sequentially")
    print("   3. Use formula library for calculations")
    print("   4. Compare results across multiple companies")
    print("   5. Generate natural language answers")


if __name__ == "__main__":
    main()
