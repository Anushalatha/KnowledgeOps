from __future__ import annotations

import re
from time import perf_counter
from typing import Any


def reranker_name() -> str:
    return "lexical-vector-v1"


def rerank(query: str, candidates: list[dict[str, Any]], final_count: int) -> tuple[list[dict[str, Any]], float]:
    """A local, replaceable reranker that blends vector and query-term relevance."""
    if final_count < 1:
        raise ValueError("final_count must be at least 1.")
    started = perf_counter()
    query_terms = set(re.findall(r"\b\w{3,}\b", query.lower()))
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        text_terms = set(re.findall(r"\b\w{3,}\b", str(candidate.get("text", "")).lower()))
        lexical_score = len(query_terms & text_terms) / len(query_terms) if query_terms else 0.0
        retrieval_score = float(candidate.get("score", 0.0))
        reranking_score = round(0.75 * retrieval_score + 0.25 * lexical_score, 6)
        ranked.append({
            **candidate,
            "retrieval_score": retrieval_score,
            "reranking_score": reranking_score,
        })
    ranked.sort(key=lambda item: item["reranking_score"], reverse=True)
    return ranked[:final_count], round((perf_counter() - started) * 1000, 2)
