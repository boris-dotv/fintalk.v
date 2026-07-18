#!/usr/bin/env python3
"""
MCP Integration Module - 集成Model Context Protocol
使用真实API，无Mock数据
"""

import os
import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import requests

# Don't just read the docs. Write the docs you wish you had read.
# Done is better than perfect, but thoughtful is better than done.
logger = logging.getLogger(__name__)


class MCPLogger:
    """MCP通信日志记录器"""

    def __init__(self, log_dir: str = "mcp_integration/logs"):
        """初始化日志记录器"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"mcp_session_{timestamp}.jsonl"

        self.session_id = str(uuid.uuid4())[:8]
        self.message_count = 0

        logger.info(f"✅ MCP Logger initialized: {self.log_file}")

    def log(self, direction: str, message_type: str, data: Dict[str, Any]):
        """记录MCP消息"""
        self.message_count += 1

        log_entry = {
            "session_id": self.session_id,
            "message_id": self.message_count,
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "type": message_type,
            "data": data
        }

        # 写入文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        # 控制台输出
        arrow = "➡️  " if direction == "out" else "⬅️  "
        logger.debug(f"{arrow} MCP [{message_type}]: {json.dumps(data, ensure_ascii=False)[:200]}...")

    def get_summary(self) -> Dict[str, Any]:
        """获取日志摘要"""
        return {
            "session_id": self.session_id,
            "log_file": str(self.log_file),
            "message_count": self.message_count
        }


class MCPClient:
    """
    MCP客户端 - 使用真实API，无Mock数据
    """

    def __init__(self, log_dir: str = "mcp_integration/logs"):
        """初始化MCP客户端"""
        self.logger = MCPLogger(log_dir)
        self.tools = {}

        # 加载API密钥
        self._load_api_keys()

        # 注册内置工具
        self._register_tools()

        logger.info("✅ MCP Client initialized (Real APIs - No Mock)")

    def _load_api_keys(self):
        """从环境变量加载API密钥"""
        # Google Search API
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")

        # Alpha Vantage (股票数据)
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_KEY")

        # NewsAPI
        self.news_api_key = os.getenv("NEWS_API_KEY")

        # GitHub Token (可选，提高限额)
        self.github_token = os.getenv("GITHUB_TOKEN")

        logger.info("📝 API Keys loaded from environment")

    def _register_tools(self):
        """注册工具"""

        # 1. GitHub搜索 - 公开API，不需要token
        self.register_tool({
            "name": "search_github",
            "description": "搜索GitHub代码仓库 (使用GitHub REST API)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询"
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言过滤 (可选)"
                    }
                },
                "required": ["query"]
            }
        })

        # 2. Google搜索 - 需要API Key
        if self.google_api_key and self.google_cse_id:
            self.register_tool({
                "name": "web_search",
                "description": "Google搜索 (需要GOOGLE_API_KEY和GOOGLE_CSE_ID)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "返回结果数量，默认10",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            })

        # 3. Alpha Vantage股票价格 - 需要API Key
        if self.alpha_vantage_key:
            self.register_tool({
                "name": "get_stock_price",
                "description": "获取股票实时价格 (使用Alpha Vantage API)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "股票代码，如 03863.HK"
                        }
                    },
                    "required": ["symbol"]
                }
            })

        # 4. NewsAPI新闻 - 需要API Key
        if self.news_api_key:
            self.register_tool({
                "name": "get_financial_news",
                "description": "获取金融相关新闻 (使用NewsAPI)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "新闻关键词"
                        },
                        "days": {
                            "type": "integer",
                            "description": "最近N天，默认7",
                            "default": 7
                        }
                    },
                    "required": ["query"]
                }
            })

        # 5. GitHub仓库管理 - 需要GitHub Token
        if self.github_token:
            self.register_tool({
                "name": "github_repo_manager",
                "description": "GitHub仓库管理 - 创建/修改文件、提交代码、创建issue等",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "操作类型: get_file, create_file, update_file, create_issue, create_branch",
                            "enum": ["get_file", "create_file", "update_file", "create_issue", "create_branch"]
                        },
                        "owner": {
                            "type": "string",
                            "description": "仓库所有者 (默认: boris-dotv)"
                        },
                        "repo": {
                            "type": "string",
                            "description": "仓库名称 (默认: fintalk.ai)"
                        },
                        "path": {
                            "type": "string",
                            "description": "文件路径 (如: demos/new_demo.py)"
                        },
                        "content": {
                            "type": "string",
                            "description": "文件内容 (用于create_file/update_file)"
                        },
                        "message": {
                            "type": "string",
                            "description": "提交消息"
                        },
                        "branch": {
                            "type": "string",
                            "description": "分支名 (用于create_branch)"
                        },
                        "title": {
                            "type": "string",
                            "description": "Issue标题"
                        },
                        "body": {
                            "type": "string",
                            "description": "Issue内容"
                        }
                    },
                    "required": ["action"]
                }
            })

        logger.info(f"✅ Registered {len(self.tools)} MCP tools (Real APIs)")

    def register_tool(self, tool_def: Dict[str, Any]):
        """注册工具"""
        tool_name = tool_def["name"]
        self.tools[tool_name] = tool_def
        logger.debug(f"   Registered tool: {tool_name}")

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具"""
        return list(self.tools.values())

    def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        # 记录调用请求
        self.logger.log("out", "tool_call", {
            "tool": tool_name,
            "parameters": parameters
        })

        # 执行工具
        result = self._execute_tool(tool_name, parameters)

        # 记录调用响应
        self.logger.log("in", "tool_response", {
            "tool": tool_name,
            "result": result
        })

        return result

    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具（真实API调用）"""

        if tool_name == "search_github":
            return self._github_search(parameters.get("query", ""),
                                      parameters.get("language", ""))

        elif tool_name == "web_search":
            return self._google_search(parameters.get("query", ""),
                                       parameters.get("num_results", 10))

        elif tool_name == "get_stock_price":
            return self._alpha_vantage_price(parameters.get("symbol", ""))

        elif tool_name == "get_financial_news":
            return self._newsapi_search(parameters.get("query", ""),
                                        parameters.get("days", 7))

        elif tool_name == "github_repo_manager":
            return self._github_repo_manager(parameters)

        else:
            return {
                "error": f"Unknown tool: {tool_name}",
                "status": "failed"
            }

    # ============== GitHub API ==============

    def _github_search(self, query: str, language: str = "") -> Dict[str, Any]:
        """GitHub代码搜索 - 使用GitHub REST API"""
        try:
            url = "https://api.github.com/search/repositories"
            params = {
                "q": f"{query}{' language:' + language if language else ''}",
                "sort": "stars",
                "order": "desc",
                "per_page": 10
            }

            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"

            logger.info(f"🔍 GitHub API: {url}?q={params['q']}")

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            return {
                "status": "success",
                "query": query,
                "language": language,
                "total_count": data.get("total_count", 0),
                "results": [
                    {
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "url": repo["html_url"],
                        "description": repo.get("description", ""),
                        "stars": repo["stargazers_count"],
                        "language": repo.get("language", "")
                    }
                    for repo in data.get("items", [])
                ]
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "GitHub API请求失败，请检查网络连接"
            }

    # ============== Google Custom Search API ==============

    def _google_search(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Google搜索 - 使用Google Custom Search API"""
        if not self.google_api_key or not self.google_cse_id:
            return {
                "status": "error",
                "error": "Missing API credentials",
                "message": "请设置环境变量 GOOGLE_API_KEY 和 GOOGLE_CSE_ID。获取方式: https://developers.google.com/custom-search/v1/overview"
            }

        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cse_id,
                "q": query,
                "num": min(num_results, 10)
            }

            logger.info(f"🔍 Google API: {query}")

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            return {
                "status": "success",
                "query": query,
                "total_results": data.get("searchInformation", {}).get("totalResults", "0"),
                "results": [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    }
                    for item in data.get("items", [])
                ]
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Google API error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Google API请求失败"
            }

    # ============== Alpha Vantage API ==============

    def _alpha_vantage_price(self, symbol: str) -> Dict[str, Any]:
        """获取股票价格 - 使用Alpha Vantage API"""
        if not self.alpha_vantage_key:
            return {
                "status": "error",
                "error": "Missing API credentials",
                "message": "请设置环境变量 ALPHA_VANTAGE_KEY。获取免费API Key: https://www.alphavantage.co/support/#api-key"
            }

        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.alpha_vantage_key
            }

            logger.info(f"📈 Alpha Vantage API: {symbol}")

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if "Global Quote" in data:
                quote = data["Global Quote"]
                return {
                    "status": "success",
                    "symbol": symbol,
                    "price": float(quote.get("05. price", "0.00")),
                    "change": quote.get("09. change", "N/A"),
                    "change_percent": quote.get("10. change percent", "N/A"),
                    "high": quote.get("03. high", "N/A"),
                    "low": quote.get("04. low", "N/A"),
                    "volume": quote.get("06. volume", "N/A"),
                    "timestamp": quote.get("07. latest trading day", "N/A")
                }
            else:
                return {
                    "status": "error",
                    "error": "Invalid response",
                    "message": f"无法获取股票 {symbol} 的数据"
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Alpha Vantage API error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Alpha Vantage API请求失败"
            }

    # ============== NewsAPI ==============

    def _newsapi_search(self, query: str, days: int = 7) -> Dict[str, Any]:
        """获取金融新闻 - 使用NewsAPI"""
        if not self.news_api_key:
            return {
                "status": "error",
                "error": "Missing API credentials",
                "message": "请设置环境变量 NEWS_API_KEY。获取免费API Key: https://newsapi.org/register"
            }

        try:
            from datetime import timedelta

            url = "https://newsapi.org/v2/everything"
            params = {
                "apiKey": self.news_api_key,
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "from": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
                "pageSize": 10
            }

            logger.info(f"📰 NewsAPI: {query}")

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            return {
                "status": "success",
                "query": query,
                "total_results": data.get("totalResults", 0),
                "articles": [
                    {
                        "title": article.get("title", ""),
                        "source": article.get("source", {}).get("name", ""),
                        "url": article.get("url", ""),
                        "published_at": article.get("publishedAt", ""),
                        "description": article.get("description", "")
                    }
                    for article in data.get("articles", [])
                ]
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"NewsAPI error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "NewsAPI请求失败"
            }

    # ============== GitHub Repository Manager ==============

    def _github_repo_manager(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """GitHub仓库管理 - 完整的CRUD操作"""
        import base64

        action = params.get("action")
        owner = params.get("owner", "boris-dotv")
        repo = params.get("repo", "fintalk.ai")

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.github_token}"
        }

        try:
            # 1. 获取文件内容
            if action == "get_file":
                path = params.get("path")
                if not path:
                    return {"status": "error", "error": "Missing 'path' parameter"}

                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
                logger.info(f"📄 GitHub API: GET {url}")

                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                data = response.json()
                if "content" in data:
                    content = base64.b64decode(data["content"]).decode('utf-8')
                    return {
                        "status": "success",
                        "path": path,
                        "content": content,
                        "sha": data.get("sha"),
                        "url": data.get("html_url")
                    }
                else:
                    return {"status": "error", "error": "File not found"}

            # 2. 创建文件
            elif action == "create_file":
                path = params.get("path")
                content = params.get("content")
                message = params.get("message", f"Create {path}")

                if not path or content is None:
                    return {"status": "error", "error": "Missing 'path' or 'content' parameter"}

                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
                logger.info(f"📝 GitHub API: PUT {url}")

                payload = {
                    "message": message,
                    "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
                }

                response = requests.put(url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()

                data = response.json()
                return {
                    "status": "success",
                    "action": "created",
                    "path": path,
                    "url": data.get("content", {}).get("html_url"),
                    "sha": data.get("content", {}).get("sha")
                }

            # 3. 更新文件
            elif action == "update_file":
                path = params.get("path")
                content = params.get("content")
                message = params.get("message", f"Update {path}")
                sha = params.get("sha")

                if not path or content is None:
                    return {"status": "error", "error": "Missing 'path' or 'content' parameter"}

                # 如果没有提供sha，先获取
                if not sha:
                    get_result = self._github_repo_manager({
                        "action": "get_file",
                        "owner": owner,
                        "repo": repo,
                        "path": path
                    })
                    if get_result.get("status") != "success":
                        return get_result
                    sha = get_result.get("sha")

                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
                logger.info(f"✏️  GitHub API: PUT {url}")

                payload = {
                    "message": message,
                    "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
                    "sha": sha
                }

                response = requests.put(url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()

                data = response.json()
                return {
                    "status": "success",
                    "action": "updated",
                    "path": path,
                    "url": data.get("content", {}).get("html_url"),
                    "sha": data.get("content", {}).get("sha")
                }

            # 4. 创建Issue
            elif action == "create_issue":
                title = params.get("title")
                body = params.get("body", "")

                if not title:
                    return {"status": "error", "error": "Missing 'title' parameter"}

                url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                logger.info(f"🐛 GitHub API: POST {url}")

                payload = {
                    "title": title,
                    "body": body
                }

                response = requests.post(url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()

                data = response.json()
                return {
                    "status": "success",
                    "action": "issue_created",
                    "issue_number": data.get("number"),
                    "url": data.get("html_url"),
                    "title": title
                }

            # 5. 创建分支
            elif action == "create_branch":
                branch = params.get("branch")
                if not branch:
                    return {"status": "error", "error": "Missing 'branch' parameter"}

                # 获取默认分支的SHA
                url = f"https://api.github.com/repos/{owner}/{repo}"
                logger.info(f"🌿 GitHub API: GET {url}")

                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                default_branch = response.json().get("default_branch")
                sha = response.json().get("default_branch_sha")

                # 获取默认分支的最新commit SHA
                refs_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{default_branch}"
                refs_response = requests.get(refs_url, headers=headers, timeout=10)
                refs_response.raise_for_status()
                sha = refs_response.json().get("object", {}).get("sha")

                # 创建新分支
                create_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
                logger.info(f"🌿 GitHub API: POST {create_url}")

                payload = {
                    "ref": f"refs/heads/{branch}",
                    "sha": sha
                }

                create_response = requests.post(create_url, headers=headers, json=payload, timeout=10)
                create_response.raise_for_status()

                return {
                    "status": "success",
                    "action": "branch_created",
                    "branch": branch,
                    "from": default_branch
                }

            else:
                return {
                    "status": "error",
                    "error": f"Unknown action: {action}"
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "GitHub API请求失败"
            }

    def get_logs_summary(self) -> str:
        """获取日志摘要"""
        summary = self.logger.get_summary()

        # 读取日志文件内容
        if self.logger.log_file.exists():
            with open(self.logger.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            return f"""
📋 MCP Session Summary:
  Session ID: {summary['session_id']}
  Log File: {summary['log_file']}
  Messages: {summary['message_count']}

  Latest messages:
  {''.join(lines[-5:])}
"""
        return f"No logs yet. Session: {summary['session_id']}"

    def view_logs(self) -> str:
        """查看完整日志"""
        if not self.logger.log_file.exists():
            return "No logs available."

        with open(self.logger.log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return f"""
{'='*80}
MCP Communication Log (Real API Calls)
{'='*80}
File: {self.logger.log_file}
Session: {self.logger.session_id}

{content}
{'='*80}
"""


class MCPFunctionRegistry:
    """将MCP工具集成到FinTalk.AI的Function Registry"""

    def __init__(self, mcp_client: MCPClient):
        """初始化"""
        self.mcp_client = mcp_client
        self.functions = self._convert_to_openai_functions()
        logger.info(f"✅ MCP Function Registry initialized with {len(self.functions)} functions")

    def _convert_to_openai_functions(self) -> List[Dict]:
        """转换MCP工具为OpenAI Function格式"""
        openai_functions = []
        for tool in self.mcp_client.get_tools():
            openai_functions.append({
                "type": "function",
                "function": tool
            })
        return openai_functions

    def execute(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行MCP函数"""
        return self.mcp_client.call_tool(function_name, parameters)

    def get_functions(self) -> List[Dict]:
        """获取所有函数"""
        return self.functions