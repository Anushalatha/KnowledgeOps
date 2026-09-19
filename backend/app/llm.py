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

    if not sources:
        return "I don't have enough information in the provided knowledge base to answer this."

    source_context = "\n\n".join(
        f"[{index}]\n"
        f"Document: {source.get('filename', 'Unknown source')}\n"
        f"Chunk ID: {source.get('chunk_id', f'chunk_{index}')}\n"
        f"Relevance Score: {source.get('reranking_score') or source.get('score') or 0.0:.3f}\n"
        f"Content:\n{source.get('text', '').strip()}"
        for index, source in enumerate(sources, start=1)
    )
    prompt = (
        "You are an enterprise AI Knowledge Engine. Answer the user's question accurately using ONLY the supplied sources context.\n\n"
        "STRICT INSTRUCTIONS:\n"
        "1. Answer ALL requested parts of the user question explicitly.\n"
        "2. Provide a direct answer first, followed by concise supporting explanation.\n"
        "3. Cite supporting sources inline using [1], [2], etc. immediately after making factual claims.\n"
        "4. If multiple sources support a claim, cite all relevant sources together (e.g. [1][2]).\n"
        "5. Do NOT invent facts or citations. Use ONLY the supplied sources.\n"
        "6. If the sources do not contain enough information, respond strictly with: "
        "\"I don't have enough information in the provided knowledge base to answer this.\"\n\n"
        f"RETRIEVED SOURCES:\n{source_context}\n\n"
        f"QUESTION: {question}\n\n"
        "GROUNDED ANSWER:"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 800},
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
