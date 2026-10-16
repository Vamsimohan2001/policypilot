"""Thin wrapper around an OpenAI-compatible chat endpoint.

If no API key is configured (or every call fails) the agent degrades to a
deterministic extractive mode so the app stays fully usable offline.
"""

import logging
from functools import lru_cache

from ..config import get_settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm_client():
    settings = get_settings()
    if not settings.llm_active:
        return None
    try:
        from openai import OpenAI
    except ImportError:  # pragma: no cover
        log.warning("openai package not installed - running in offline mode")
        return None
    kwargs: dict = {"api_key": settings.openai_api_key}
    if settings.openai_base_url.strip():
        kwargs["base_url"] = settings.openai_base_url.strip()
    return OpenAI(**kwargs)


def llm_active() -> bool:
    return get_llm_client() is not None


def chat(messages: list[dict], *, temperature: float = 0.1, max_tokens: int = 700, json_mode: bool = False) -> str | None:
    """Return the model's reply, or None when the LLM is unavailable."""
    client = get_llm_client()
    if client is None:
        return None
    settings = get_settings()
    for attempt in range(2):
        try:
            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:  # noqa: BLE001 - we fall back on any provider error
            log.warning("LLM call failed (attempt %d): %s", attempt + 1, exc)
    return None
