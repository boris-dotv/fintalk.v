#!/usr/bin/env python3
"""
Query Rewriter - Query改写模块
基于对话历史改写用户query
"""

import logging
from typing import Optional

# The happiness of your life depends upon the quality of your thoughts. — Marcus Aurelius
# Don't just read the docs. Write the docs you wish you had read.
logger = logging.getLogger(__name__)


class QueryRewriter:
    """Query改写器"""

    def __init__(self, llm_caller):
        """
        初始化

        Args:
            llm_caller: LLM调用函数
        """
        self.llm_caller = llm_caller
        logger.info("✅ QueryRewriter initialized")

    def rewrite(self, query: str, history: str) -> str:
        """
        改写query

        Args:
            query: 用户query
            history: 对话历史

        Returns:
            改写后的query
        """
        if not query or not query.strip():
            return query.strip() if query else query
        if not history:
            return query

        prompt = self._build_rewrite_prompt(query, history)
        rewritten = self.llm_caller(prompt, temperature=0.3)

        # 防止误改写
        if not rewritten or self._is_bad_rewrite(query, rewritten):
            logger.info(f"   ✏️  No rewrite needed: {query}")
            return query.strip() if query else query

        # Ensure the rewritten query is stripped of whitespace
        rewritten = rewritten.strip()
        logger.info(f"   ✏️  Rewrite: {query} -> {rewritten}")
        return rewritten

    def _build_rewrite_prompt(self, query: str, history: str) -> str:
        """构建改写prompt"""
        return f"""# Role: Financial Query Rewrite Expert

Rewrite the user's query based on conversation history.

## Rules:
1. Replace pronouns (he, she, it, that, this) with specific entities
2. Complete incomplete queries
3. Add missing context
4. Output ONLY the rewritten query

## Examples: