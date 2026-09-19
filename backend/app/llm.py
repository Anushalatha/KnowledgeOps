from __future__ import annotations

import os
from typing import Any

import httpx

from app.reliability import post_with_retry


class LLMConfigurationError(Exception):
    pass


class LLMProviderError(Exception):
    pass


def llm_api_key() -> str | None:
    return os.getenv("LLM_API_KEY")


def llm_model() -> str:
    return os.getenv("LLM_MODEL") or "gemini-2.5-flash"


def llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "gemini").lower()


async def generate_grounded_answer(question: str, sources: list[dict[str, Any]]) -> str:
    api_key = llm_api_key()
    if not api_key:
        raise LLMConfigurationError("LLM API key is not configured. Set LLM_API_KEY.")
    if llm_provider() != "gemini":
        raise LLMConfigurationError("Grounded generation currently supports LLM_PROVIDER=gemini.")

    source_context = "\n\n".join(
        f"[{index}] {source.get('filename', 'Unknown source')}\n{source.get('text', '')}"
        for index, source in enumerate(sources, start=1)
    )
    prompt = (
        "Answer the user's question using only the supplied sources. "
        "Cite supporting sources inline using [1], [2], etc. "
        "If the sources do not contain enough information, say so clearly. "
        "Do not invent facts or citations.\n\n"
        f"Sources:\n{source_context}\n\n"
        f"Question: {question}"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800},
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await post_with_retry(
                client,
                f"https://generativelanguage.googleapis.com/v1beta/models/{llm_model()}:generateContent",
                params={"key": api_key},
                json=payload,
            )
    except httpx.HTTPError as error:
        raise LLMProviderError("Gemini could not be reached.") from error

    if response.is_error:
        raise LLMProviderError(
            f"Gemini rejected the request with status {response.status_code}."
        )

    try:
        candidates = response.json()["candidates"]
        parts = candidates[0]["content"]["parts"]
        return "".join(part["text"] for part in parts)
    except (IndexError, KeyError, TypeError, ValueError) as error:
        raise LLMProviderError("Gemini returned an invalid answer response.") from error
