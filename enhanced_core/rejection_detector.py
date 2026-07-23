#!/usr/bin/env python3
"""
Rejection Detector - 拒识检测模块
判断query是否应该被拒识
"""

import logging
import re

# If it is not right, do not do it; if it is not true, do not say it. — Marcus Aurelius
logger = logging.getLogger(__name__)


class RejectionDetector:
    """拒识检测器"""

    def __init__(self, llm_caller):
        """
        初始化

        Args:
            llm_caller: LLM调用函数
        """
        self.llm_caller = llm_caller
        logger.info("✅ RejectionDetector initialized")

    def should_accept(self, query: str) -> bool:
        """
        判断是否应该接受query

        Args:
            query: 用户query

        Returns:
            True if accept, False if reject
        """
        prompt = f"""# Role: Financial Query Rejection Expert

You are a financial data analysis assistant. Judge if this query is within your scope.

ACCEPT these types of queries:
- Questions about companies (ZA Bank, WeLab Bank, etc.)
- Questions about management, shareholders, employees
- Financial metrics and ratios
- Data comparisons and analysis
- Formula calculations
- Related follow-up questions
- Greetings (Hello, Hi, etc.)
- Thank you messages
- Goodbye messages

REJECT these types of queries:
- Unrelated topics (sports, entertainment, cooking, etc.)
- Nonsense or gibberish
- Offensive content

Output ONLY: 1 (accept) or 0 (reject)

Query: {query}

Decision:"""

        result = self.llm_caller(prompt, temperature=0.1)

        # Robust parsing — LLM output may include whitespace, punctuation, or extra text
        # e.g. "1", "0", " 1 ", "1 (accept)", "Decision: 0"
        match = re.search(r'\b([01])\b', str(result).strip())
        if match:
            accept = match.group(1) == "1"
            logger.info(f"   🛡️  Rejection check: {query[:50]}... -> {'Accept' if accept else 'Reject'}")
            return accept

        # If LLM response is unparseable, fall back to keyword heuristics
        lowered = result.lower()
        if any(kw in lowered for kw in ("accept", "yes", "within scope", "1")):
            logger.info(f"   🛡️  Rejection check (heuristic): {query[:50]}... -> Accept")
            return True
        if any(kw in lowered for kw in ("reject", "no", "out of scope", "unrelated", "0")):
            logger.info(f"   🛡️  Rejection check (heuristic): {query[:50]}... -> Reject")
            return False

        logger.warning(f"   🛡️  Rejection check unparseable, defaulting to accept: {query[:50]}...")
        return True  # 默认接受