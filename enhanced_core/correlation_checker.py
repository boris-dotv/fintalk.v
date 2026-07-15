#!/usr/bin/env python3
"""
Correlation Checker - 相关性判断模块
判断前后两个query是否相关（多轮对话）
"""

import logging

logger = logging.getLogger(__name__)


class CorrelationChecker:
    """相关性检查器"""

    def __init__(self, llm_caller):
        """
        初始化

        Args:
            llm_caller: LLM调用函数
        """
        self.llm_caller = llm_caller
        logger.info("✅ CorrelationChecker initialized")

    def is_correlated(self, prev_query: str, curr_query: str) -> bool:
        """
        判断两个query是否相关

        Args:
            prev_query: 前一个query
            curr_query: 当前query

        Returns:
            True if correlated, False otherwise
        """
        if not prev_query or not curr_query:
            return False

        prompt = f"""Are these two queries correlated in a multi-turn conversation?

Query 1: {prev_query}
Query 2: {curr_query}

Output ONLY: Yes or No"""

        result = (self.llm_caller(prompt, temperature=0.1) or "").strip().lower()[:3]
        is_correlated = "yes" in result

        logger.info(f"   🔗 Correlation check -> {is_correlated}")

        return is_correlated
