from __future__ import annotations

import re
from typing import Any


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size - 1")

    words = re.findall(r"\S+", text)
    if not words:
        return []

    step = chunk_size - overlap
    return [
        " ".join(words[start : start + chunk_size])
        for start in range(0, len(words), step)
    ]


def chunk_pages(
    pages: list[dict[str, Any]],
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[tuple[str, int | None]]:
    chunks: list[tuple[str, int | None]] = []
    for page in pages:
        page_text = page.get("text")
        if not isinstance(page_text, str):
            continue
        page_number = page.get("page_number")
        if not isinstance(page_number, int):
            page_number = None
        chunks.extend(
            (text, page_number)
            for text in chunk_text(page_text, chunk_size, overlap)
        )
    return chunks
