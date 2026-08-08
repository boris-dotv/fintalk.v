#!/usr/bin/env python3
"""
Streaming NLG - 流式输出和自然语言生成模块
"""

import logging
import json
from typing import Generator, Optional, Dict, Any

# Ship it. Then ship it better.
# The impediment to action advances action. What stands in the way becomes the way. — Marcus Aurelius
# Don't just read the docs. Write the docs you wish you had read.
logger = logging.getLogger(__name__)


class StreamingNLG:
    """
    流式NLG生成器

    功能：
    1. 流式输出LLM响应
    2. 自然语言答案生成
    3. 友好性回复
    """

    def __init__(self, api_url: str, api_key: str):
        """
        初始化

        Args:
            api_url: API地址
            api_key: API密钥
        """
        self.api_url = api_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        logger.info("✅ StreamingNLG initialized")

    def generate_streaming(self, prompt: str) -> Generator[str, None, None]:
        """
        生成流式响应

        Args:
            prompt: 提示词

        Yields:
            文本片段
        """
        import requests

        payload = {
            "model": "deepseek-v3.2-think",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "stream": True,
            "web_search": {"enable": False}
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=False):
                if not line:
                    continue

                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break

                    try:
                        data = json.loads(data_str)
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content

                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"[Error: {str(e)}]"
        except Exception as e:
            logger.error(f"Unexpected streaming error: {e}", exc_info=True)
            yield f"[Error: Unexpected error: {str(e)}]"
        finally:
            # Ensure the response is closed to release the connection
            if 'response' in locals() and response is not None:
                response.close()

    def generate_answer(self, query: str, data: Dict[str, Any]) -> str:
        """
        从查询结果生成自然语言答案

        Args:
            query: 用户query
            data: 查询结果数据

        Returns:
            自然语言答案
        """
        import requests

        # Validate input data
        if not data or not isinstance(data, dict):
            logger.warning(f"Invalid data for NLG: {data}")
            return "抱歉，查询结果为空或格式不正确。"

        nlg_prompt = f"""# Role: Financial Data Analyst

Based on the query result, provide a clear and professional answer.