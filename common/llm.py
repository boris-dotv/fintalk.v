"""Shared helper for OpenAI-style chat-completion HTTP calls.

Almost every module in the project used to hand-roll the same
``requests.post(url, headers={Authorization: Bearer ...}, json={model, messages,
...})`` call followed by ``response.json()["choices"][0]["message"]["content"]``
parsing. ``chat_completion`` centralises that boilerplate while remaining
flexible enough to cover every call site (different endpoints, models, extra
payload fields such as ``top_p``/``web_search``/``response_format`` and
different error-handling policies).
"""

import logging
from typing import Any, Dict, List, Optional

import requests

DEFAULT_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"

_module_logger = logging.getLogger(__name__)


def build_headers(api_key: str) -> Dict[str, str]:
    """Build the standard JSON + Bearer auth headers for a chat request."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def chat_completion(
    messages: List[Dict[str, str]],
    *,
    api_url: str = DEFAULT_API_URL,
    api_key: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    timeout: int = 60,
    logger: Optional[logging.Logger] = None,
    default: Any = None,
    raise_on_error: bool = False,
    **extra_payload: Any,
) -> Any:
    """Send a chat-completion request and return the assistant message content.

    Args:
        messages: OpenAI-style ``[{"role": ..., "content": ...}]`` list.
        api_url: Chat-completions endpoint.
        api_key: Bearer token; ignored when ``headers`` is supplied.
        headers: Explicit headers (overrides ``api_key``).
        model: Model name.
        temperature: Sampling temperature.
        timeout: Request timeout in seconds.
        logger: Logger used to report failures (defaults to this module's).
        default: Value returned on error / missing ``choices`` when
            ``raise_on_error`` is False.
        raise_on_error: Re-raise the underlying exception instead of returning
            ``default``.
        **extra_payload: Additional payload fields (e.g. ``top_p``,
            ``max_tokens``, ``response_format``, ``web_search``).

    Returns:
        The response content string, or ``default`` on failure.
    """
    log = logger or _module_logger
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        **extra_payload,
    }

    try:
        response = requests.post(
            api_url,
            headers=headers if headers is not None else build_headers(api_key),
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices")
        if not choices:
            log.error(f"LLM response missing 'choices': {data}")
            if raise_on_error:
                raise ValueError("LLM response missing 'choices'")
            return default
        return choices[0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 - callers choose the policy
        log.error(f"LLM API error: {exc}")
        if raise_on_error:
            raise
        return default
