"""
FinTalk Feishu Bot — Financial data analysis bot for Feishu/Lark.

Uses WebSocket long-connection mode — no public IP or ngrok needed.

Usage:
    pip install lark-oapi requests
    export FEISHU_APP_ID=cli_a9466001417a9cd2
    export FEISHU_APP_SECRET=your-app-secret
    export DEEPSEEK_API_KEY=your-deepseek-key
    python feishu_bot.py
"""

import os
import json
import logging
import re
import tempfile
from pathlib import Path

import requests
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    GetMessageResourceRequest,
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)

# ================================================================
# Config
# ================================================================

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("feishu-bot")

# ================================================================
# Initialize FinTalk (reuse core classes from mcp_server.py)
# ================================================================

PROJECT_ROOT = Path(__file__).parent

from mcp_server import FinTalkDatabase, FinancialAnalyzer, DeepSeekAnalyzer

DATA_DIR = PROJECT_ROOT / "data"
db = FinTalkDatabase(DATA_DIR)
fin = FinancialAnalyzer(db)
ds = DeepSeekAnalyzer(DEEPSEEK_API_KEY) if DEEPSEEK_API_KEY else None

# Lark API client (for sending replies)
lark_client = (
    lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()
)

# Track recently uploaded tables for context
_recent_tables: list[str] = []


# ================================================================
# Tool Routing (DeepSeek-powered intent parsing)
# ================================================================

TOOL_SYSTEM_PROMPT = """You are a tool router for FinTalk, a financial data analysis system covering 999 fintech companies.

Given a user query, decide which tool to call and extract parameters. Respond with JSON only.

Available tools:
1. get_company_info(company_name) — Full profile for a company
2. get_top_shareholders(company_name, top_n=3) — Top N shareholders with ownership %
3. calculate_ratio(company_name, ratio_name) — Financial ratio. ratio_name options: executive_director_ratio, non_executive_director_ratio, independent_director_ratio, shareholder_concentration, management_to_employee_ratio
4. compare_companies(company1, company2, metric) — Compare two companies. metric uses same names as ratio_name
5. query_data(sql) — SQL query. Tables: companies (name, employee_size, status, founder_name, ceoname, company_tag, ...), management (management_name, management_title, director_type), shareholders (shareholder_name, share_percentage, shareholder_tag). All joined by company_sort_id.
6. list_companies() — List all companies
7. ai_analyze(question, context) — Open-ended financial analysis

Response format:
{"tool": "tool_name", "params": {"key": "value"}}

For greetings or casual chat:
{"tool": "chat", "params": {"reply": "your friendly response in the same language as the user"}}

Important:
- Always respond in the same language as the user's query
- For Chinese company names, keep them in Chinese
- For ambiguous queries, prefer query_data with SQL for flexibility
- When the user mentions "this file", "the file", "this table", "这个文件", "这个表格", "刚才的数据" etc., they are referring to recently uploaded data. Use query_data with the table name provided in the context below."""


def route_query(query: str) -> dict:
    if not DEEPSEEK_API_KEY:
        return {"tool": "chat", "params": {"reply": "DeepSeek API key not configured."}}

    # Build dynamic system prompt with context about uploaded tables
    system_prompt = TOOL_SYSTEM_PROMPT
    if _recent_tables:
        table_context = "\n\nRecently uploaded tables (user may refer to these as 'this file/table/数据'):\n"
        for tname in _recent_tables[-3:]:
            info = db.describe_table(tname)
            cols = ", ".join(c["name"] for c in info.get("columns", [])[:10])
            table_context += f"- Table '{tname}' ({info.get('rows', 0)} rows): columns [{cols}]\n"
        system_prompt += table_context

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Route error: {e}")
        return {"tool": "chat", "params": {"reply": f"Sorry, I couldn't understand that: {e}"}}


def execute_tool(tool_call: dict) -> str:
    tool = tool_call.get("tool", "")
    params = tool_call.get("params", {})

    try:
        if tool == "chat":
            return params.get("reply", "")

        if tool == "get_company_info":
            result = fin.get_company_info(params["company_name"])
        elif tool == "get_top_shareholders":
            result = fin.get_top_shareholders(
                params["company_name"], int(params.get("top_n", 3))
            )
        elif tool == "calculate_ratio":
            result = fin.calculate_ratio(params["company_name"], params["ratio_name"])
        elif tool == "compare_companies":
            result = fin.compare_companies(
                params["company1"], params["company2"], params["metric"]
            )
        elif tool == "query_data":
            result = db.execute_query(params["sql"])
        elif tool == "list_companies":
            result = fin.list_companies()
        elif tool == "ai_analyze":
            if ds:
                return ds.analyze(params.get("question", ""), params.get("context", ""))
            return "AI analysis is not available (no API key)."
        else:
            return f"Unknown tool: {tool}"

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return f"Error executing {tool}: {e}"


def summarize_result(query: str, tool_name: str, raw_result: str) -> str:
    """Use DeepSeek to turn raw JSON into a readable reply."""
    if tool_name == "chat" or not DEEPSEEK_API_KEY:
        return raw_result

    # Always summarize through DeepSeek for natural language output
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are FinTalk AI, a financial data analyst. "
                            "The user asked a question and we retrieved data. "
                            "Summarize the result clearly and concisely. "
                            "Use the same language as the user's question. "
                            "Use bullet points for clarity. Keep it under 500 characters."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"User question: {query}\n\nData:\n{raw_result[:3000]}",
                    },
                ],
                "temperature": 0.3,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return raw_result[:2000]


# ================================================================
# Reply via Lark SDK
# ================================================================


def _fetch_recent_file_from_chat(chat_id: str) -> dict | None:
    """Look through recent chat messages to find the latest CSV file."""
    try:
        token = lark_client.config.app_settings.app_id  # just to check client exists
        import time
        # Get messages from last 10 minutes
        start_time = str(int((time.time() - 600) * 1000))
        resp = requests.get(
            f"{FEISHU_BASE}/im/v1/messages",
            headers={"Authorization": f"Bearer {_get_tenant_token()}"},
            params={
                "container_id_type": "chat",
                "container_id": chat_id,
                "start_time": start_time,
                "page_size": 20,
                "sort_type": "ByCreateTimeDesc",
            },
        )
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"Fetch messages failed: {data}")
            return None

        for item in data.get("data", {}).get("items", []):
            if item.get("msg_type") == "file":
                content = json.loads(item.get("body", {}).get("content", "{}"))
                filename = content.get("file_name", "")
                if filename.lower().endswith(".csv"):
                    return {
                        "message_id": item.get("message_id"),
                        "file_key": content.get("file_key"),
                        "file_name": filename,
                    }
    except Exception as e:
        logger.error(f"Fetch recent file error: {e}")
    return None


def _get_tenant_token() -> str:
    """Get tenant access token for API calls."""
    import time as _time
    now = _time.time()
    if _token_cache["token"] and now < _token_cache["expires"]:
        return _token_cache["token"]
    resp = requests.post(
        f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
    )
    data = resp.json()
    token = data.get("tenant_access_token", "")
    _token_cache["token"] = token
    _token_cache["expires"] = now + data.get("expire", 7200) - 60
    return token

_token_cache = {"token": "", "expires": 0}

FEISHU_BASE = "https://open.feishu.cn/open-apis"


def reply_message(message_id: str, text: str):
    # Use interactive card for markdown rendering
    card = {
        "elements": [
            {"tag": "markdown", "content": text}
        ]
    }
    req = (
        ReplyMessageRequest.builder()
        .message_id(message_id)
        .request_body(
            ReplyMessageRequestBody.builder()
            .msg_type("interactive")
            .content(json.dumps(card))
            .build()
        )
        .build()
    )
    resp = lark_client.im.v1.message.reply(req)
    if not resp.success():
        logger.error(f"Reply failed: code={resp.code}, msg={resp.msg}")


# ================================================================
# Event Handler
# ================================================================


def _clean_mention(text: str) -> str:
    """Remove @mention tags from group chat messages."""
    return re.sub(r"@_user_\d+\s*", "", text).strip()


def _download_file(message_id: str, file_key: str, filename: str) -> str:
    """Download a file from Feishu and return the local path."""
    req = (
        GetMessageResourceRequest.builder()
        .message_id(message_id)
        .file_key(file_key)
        .type("file")
        .build()
    )
    resp = lark_client.im.v1.message_resource.get(req)
    if not resp.success():
        raise RuntimeError(f"Download failed: {resp.msg}")

    tmp_dir = Path(tempfile.gettempdir()) / "fintalk_uploads"
    tmp_dir.mkdir(exist_ok=True)
    filepath = tmp_dir / filename
    filepath.write_bytes(resp.file.read())
    logger.info(f"Downloaded file: {filepath}")
    return str(filepath)


def on_message(event: P2ImMessageReceiveV1) -> None:
    msg = event.event.message
    msg_type = msg.message_type
    message_id = msg.message_id

    # Handle CSV file uploads
    if msg_type == "file":
        content = json.loads(msg.content)
        file_key = content.get("file_key", "")
        filename = content.get("file_name", "upload.csv")

        if not filename.lower().endswith(".csv"):
            reply_message(message_id, "Only CSV files are supported. Please send a .csv file.")
            return

        try:
            filepath = _download_file(message_id, file_key, filename)
            table_name = Path(filename).stem.lower().replace(" ", "_").replace("-", "_")
            result = db.load_external_csv(filepath, table_name)
            if "error" in result:
                reply_message(message_id, f"Failed to load CSV: {result['error']}")
            else:
                _recent_tables.append(result["table"])
                # Auto-analyze: get table info and summarize
                info = db.describe_table(result["table"])
                cols = [c["name"] for c in info.get("columns", [])]
                sample = info.get("sample", [])

                summary = (
                    f"CSV loaded: {result['table']} ({result['rows_loaded']} rows, {len(cols)} columns)\n"
                    f"Columns: {', '.join(cols[:15])}"
                )
                if len(cols) > 15:
                    summary += f" ... +{len(cols)-15} more"
                summary += "\n\nSample data:\n"
                for i, row in enumerate(sample[:3]):
                    row_str = " | ".join(f"{k}: {v}" for k, v in list(row.items())[:5])
                    summary += f"  {i+1}. {row_str}\n"
                summary += f"\nYou can now ask me questions about this data, e.g.:\n"
                summary += f'  "How many rows are in {result["table"]}?"\n'
                summary += f'  "Show the top 5 entries"'
                reply_message(message_id, summary)
        except Exception as e:
            logger.error(f"CSV upload error: {e}")
            reply_message(message_id, f"Error processing CSV: {e}")
        return

    if msg_type != "text":
        reply_message(message_id, "I support text messages and CSV file uploads.")
        return

    content = json.loads(msg.content)
    text = _clean_mention(content.get("text", ""))

    if not text:
        return

    logger.info(f"Received: {text}")

    # If user mentions a file/table but we have no context, try to find it in chat history
    file_keywords = ["表格", "表", "文件", "csv", "file", "table", "数据"]
    if not _recent_tables and any(kw in text.lower() for kw in file_keywords):
        chat_id = msg.chat_id if hasattr(msg, "chat_id") else ""
        if chat_id:
            logger.info(f"No recent tables, searching chat {chat_id} for CSV files...")
            file_info = _fetch_recent_file_from_chat(chat_id)
            if file_info:
                try:
                    filepath = _download_file(
                        file_info["message_id"], file_info["file_key"], file_info["file_name"]
                    )
                    table_name = Path(file_info["file_name"]).stem.lower().replace(" ", "_").replace("-", "_")
                    result = db.load_external_csv(filepath, table_name)
                    if "error" not in result:
                        _recent_tables.append(result["table"])
                        logger.info(f"Auto-loaded CSV from chat: {result['table']} ({result['rows_loaded']} rows)")
                except Exception as e:
                    logger.error(f"Auto-load CSV error: {e}")

    tool_call = route_query(text)
    logger.info(f"Routed to: {tool_call.get('tool')}")
    raw_result = execute_tool(tool_call)
    response = summarize_result(text, tool_call.get("tool", ""), raw_result)
    reply_message(message_id, response)


# ================================================================
# Entry Point — WebSocket Long Connection
# ================================================================

handler = (
    lark.EventDispatcherHandler.builder("", "")
    .register_p2_im_message_receive_v1(on_message)
    .build()
)

if __name__ == "__main__":
    if not APP_ID or not APP_SECRET:
        print("ERROR: Set FEISHU_APP_ID and FEISHU_APP_SECRET environment variables")
        print("  export FEISHU_APP_ID=cli_a9466001417a9cd2")
        print("  export FEISHU_APP_SECRET=your-secret-here")
        exit(1)
    if not DEEPSEEK_API_KEY:
        print("WARNING: DEEPSEEK_API_KEY not set — intent parsing won't work")

    print("FinTalk Feishu Bot starting (WebSocket long-connection mode)...")
    print("No public IP or ngrok needed. Bot connects to Feishu directly.")

    from lark_oapi.ws import Client as WsClient

    ws_client = WsClient(
        APP_ID,
        APP_SECRET,
        event_handler=handler,
        log_level=lark.LogLevel.INFO,
    )
    ws_client.start()
