from __future__ import annotations

import os
from typing import Any

import httpx

from app.reliability import post_with_retry


class EmbeddingConfigurationError(Exception):
    pass


class EmbeddingProviderError(Exception):
    pass


def embedding_model() -> str:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    default_model = "gemini-embedding-001" if provider == "gemini" else "text-embedding-3-small"
    return os.getenv("EMBEDDING_MODEL") or default_model


def embedding_api_key() -> str | None:
    return os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY")


def embedding_provider() -> str:
    return os.getenv("LLM_PROVIDER", "openai").lower()


async def embed_texts(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    api_key = embedding_api_key()
    if not api_key:
        raise EmbeddingConfigurationError(
            "Embedding API key is not configured. Set EMBEDDING_API_KEY or LLM_API_KEY."
        )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if embedding_provider() == "gemini":
                model = embedding_model()
                embeddings: list[list[float]] = []
                for text in texts:
                    response = await post_with_retry(
                        client,
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent",
                        params={"key": api_key},
                        json={
                            "model": f"models/{model}",
                            "content": {"parts": [{"text": text}]},
                            "taskType": task_type,
                        },
                    )
                    if response.is_error:
                        break
                    embeddings.append(response.json()["embedding"]["values"])
                if len(embeddings) == len(texts):
                    return embeddings
            else:
                payload = {"model": embedding_model(), "input": texts}
                response = await post_with_retry(
                    client,
                    "https://api.openai.com/v1/embeddings",
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
    except httpx.HTTPError as error:
        raise EmbeddingProviderError("Embedding provider could not be reached.") from error

    if response.is_error:
        raise EmbeddingProviderError(
            f"Embedding provider rejected the request with status {response.status_code}."
        )

    try:
        response_data = response.json()
        if embedding_provider() == "gemini":
            embeddings: list[dict[str, Any]] = response_data["embeddings"]
            return [item["values"] for item in embeddings]

        data: list[dict[str, Any]] = response_data["data"]
        return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
    except (KeyError, TypeError, ValueError) as error:
        raise EmbeddingProviderError("Embedding provider returned an invalid response.") from error
