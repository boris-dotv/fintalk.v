#!/usr/bin/env python3
"""
Arbitrator - 仲裁机制模块
判断query类型：Task/Knowledge/SmallTalk/Invalid
"""

import logging
from typing import Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ArbitrationResult:
    """仲裁结果"""
    query_type: str  # task, knowledge, small_talk, invalid
    confidence: float
    reasoning: str


class QueryArbitrator:
    """Query仲裁器"""

    def __init__(self, llm_caller):
        """
        初始化

        Args:
            llm_caller: LLM调用函数
        """
        self.llm_caller = llm_caller
        logger.info("✅ QueryArbitrator initialized")

    def arbitrate(self, query: str, history: str = "") -> ArbitrationResult:
        """
        仲裁query类型

        Args:
            query: 用户query
            history: 对话历史

        Returns:
            ArbitrationResult
        """
        prompt = self._build_arbitration_prompt(query, history)
        result = self.llm_caller(prompt, temperature=0.1)

        # 解析结果 - handle potential None or non-string return
        if result is None or not isinstance(result, str):
            logger.warning(f"Unexpected LLM response type: {type(result)}, defaulting to 'A'")
            result = "A"
        else:
            result = result.strip().upper()
            if result not in ["A", "B", "C", "D"]:
                logger.warning(f"Unexpected arbitration result '{result}', defaulting to 'A'")
                result = "A"  # 默认任务类型
        logger.info(f"Arbitration result: {result}")
        logger.info(f"Arbitration result: {result}")

        type_map = {
            "A": ("task", "Data retrieval, calculation, or comparison"),
            "B": ("knowledge", "Explain concepts or how-to"),
            "C": ("small_talk", "Greeting, thanks, casual conversation"),
            "D": ("invalid", "Nonsense or incomplete input")
        }

        query_type, reasoning = type_map[result]

        logger.info(f"   🎯 Arbitration: {query[:50]}... -> {query_type}")

        return ArbitrationResult(
            query_type=query_type,
            confidence=0.8,
            reasoning=reasoning
        )

    def _build_arbitration_prompt(self, query: str, history: str) -> str:
        """构建仲裁prompt"""
        return f"""# Role: Financial Query Arbitration Expert

Classify the user's query type:

## A - Task-oriented
Data retrieval, calculation, comparison.
Examples: "What is ZA Bank's employee size?", "Calculate executive_director_ratio"

## B - Knowledge
Explain concepts or how-to.
Examples: "How is executive_director_ratio calculated?", "What does concentration mean?"

## C - Small Talk
Greetings, thanks, casual conversation.
Examples: "Hello", "Thank you", "How are you?"

## D - Invalid
Nonsense or incomplete input.

Context: {history if history else "No history"}

Query: {query}

Output ONLY the letter (A/B/C/D):"""
