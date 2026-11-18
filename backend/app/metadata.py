from __future__ import annotations

from typing import Any

from app.chunking import chunk_pages, chunk_text

UNKNOWN_VALUE = "unknown"


def normalize_label(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).casefold()
    return normalized or None


def document_chunks(
    document: dict[str, Any],
    chunk_size: int,
    overlap: int,
) -> tuple[list[str], list[int | None]]:
    pages = document.get("page_texts")
    if isinstance(pages, list) and pages:
        valid_pages = [
            page
            for page in pages
            if isinstance(page, dict) and isinstance(page.get("text"), str)
        ]
        page_chunks = chunk_pages(valid_pages, chunk_size, overlap)
        return [chunk for chunk, _ in page_chunks], [page for _, page in page_chunks]

    chunks = chunk_text(document.get("content") or "", chunk_size, overlap)
    return chunks, [None] * len(chunks)
