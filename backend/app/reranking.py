from __future__ import annotations

import re
from time import perf_counter
from typing import Any


def reranker_name() -> str:
    return "lexical-vector-mmr-v2"


def _text_similarity(text1: str, text2: str) -> float:
    """Computes Jaccard word token similarity between two text snippets."""
    tokens1 = set(re.findall(r"\b\w{3,}\b", text1.lower()))
    tokens2 = set(re.findall(r"\b\w{3,}\b", text2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    union = tokens1 | tokens2
    return len(tokens1 & tokens2) / len(union)


def calculate_chunk_similarity(c1: dict[str, Any], c2: dict[str, Any]) -> float:
    """
    Calculates combined similarity between two chunks based on text overlap and document origin.
    If both chunks belong to the same document, adds a document similarity weight (0.4).
    """
    text_sim = _text_similarity(str(c1.get("text", "")), str(c2.get("text", "")))
    same_doc_penalty = 0.40 if (c1.get("filename") and c1.get("filename") == c2.get("filename")) else 0.0
    return min(1.0, text_sim + same_doc_penalty)


def rerank(
    query: str,
    candidates: list[dict[str, Any]],
    final_count: int,
    mmr_enabled: bool = True,
    mmr_lambda: float = 0.70,
    candidate_pool_size: int = 15,
) -> tuple[list[dict[str, Any]], float]:
    """
    Blends vector and query-term relevance with Maximal Marginal Relevance (MMR)
    for document diversity and chunk redundancy reduction.
    """
    if final_count < 1:
        raise ValueError("final_count must be at least 1.")

    started = perf_counter()
    query_terms = set(re.findall(r"\b\w{3,}\b", query.lower()))
    ranked_pool: list[dict[str, Any]] = []

    # 1. Base Reranking (Vector 75% + Lexical 25%)
    for candidate in candidates:
        text_terms = set(re.findall(r"\b\w{3,}\b", str(candidate.get("text", "")).lower()))
        lexical_score = len(query_terms & text_terms) / len(query_terms) if query_terms else 0.0
        retrieval_score = float(candidate.get("score", 0.0))
        reranking_score = round(0.75 * retrieval_score + 0.25 * lexical_score, 6)

        ranked_pool.append({
            **candidate,
            "retrieval_score": retrieval_score,
            "reranking_score": reranking_score,
        })

    ranked_pool.sort(key=lambda item: item["reranking_score"], reverse=True)

    # Limit initial candidate pool size
    pool = ranked_pool[: max(final_count, candidate_pool_size)]

    if not mmr_enabled or len(pool) <= final_count:
        final_list = pool[:final_count]
        for item in final_list:
            item["mmr_score"] = item["reranking_score"]
        return final_list, round((perf_counter() - started) * 1000, 2)

    # 2. Maximal Marginal Relevance (MMR) Selection
    # Normalize reranking scores in pool to 0..1 range
    max_score = max((item["reranking_score"] for item in pool), default=1.0)
    min_score = min((item["reranking_score"] for item in pool), default=0.0)
    score_range = max_score - min_score if max_score > min_score else 1.0

    selected: list[dict[str, Any]] = []
    unselected = list(pool)

    while unselected and len(selected) < final_count:
        best_candidate: dict[str, Any] | None = None
        best_mmr_score = -999.0

        for candidate in unselected:
            norm_rel = (candidate["reranking_score"] - min_score) / score_range

            if not selected:
                sim_to_selected = 0.0
            else:
                sim_to_selected = max(calculate_chunk_similarity(candidate, s) for s in selected)

            mmr_score = (mmr_lambda * norm_rel) - ((1.0 - mmr_lambda) * sim_to_selected)

            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                best_candidate = candidate

        if best_candidate:
            best_candidate["mmr_score"] = round(best_mmr_score, 6)
            selected.append(best_candidate)
            unselected.remove(best_candidate)
        else:
            break

    return selected, round((perf_counter() - started) * 1000, 2)
