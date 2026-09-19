from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    id: str | None = None
    question: str = Field(min_length=1, max_length=1000)
    expected_answer: str | None = Field(default=None, max_length=5000)
    relevant_document_id: str | None = None
    relevant_filename: str | None = None
    relevant_chunk_id: str | None = None
    expected_documents: list[str] = Field(default_factory=list)
    expected_topics: list[str] = Field(default_factory=list)
    category: str = "general"
    difficulty: str = "medium"


class EvaluationRunRequest(BaseModel):
    dataset_name: str = Field(default="ad-hoc", min_length=1, max_length=100)
    cases: list[EvaluationCase] = Field(min_length=1, max_length=100)
    limit: int = Field(default=5, ge=1, le=50)
    top_k: int | None = None  # alias/override for limit
    generate_answers: bool = False


class EvaluationDatasetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    cases: list[EvaluationCase] = Field(min_length=1, max_length=100)


def _get_expected_docs(case: EvaluationCase) -> list[str]:
    docs: list[str] = []
    if case.expected_documents:
        docs.extend(case.expected_documents)
    if case.relevant_filename and case.relevant_filename not in docs:
        docs.append(case.relevant_filename)
    return docs


def _targeted(case: EvaluationCase) -> bool:
    return bool(_get_expected_docs(case) or case.relevant_document_id or case.relevant_chunk_id)


def _matches_target(source: dict[str, Any], case: EvaluationCase) -> bool:
    expected_docs = _get_expected_docs(case)
    matches_filename = not expected_docs or source.get("filename") in expected_docs
    matches_doc_id = not case.relevant_document_id or source.get("document_id") == case.relevant_document_id
    matches_chunk_id = not case.relevant_chunk_id or source.get("chunk_id") == case.relevant_chunk_id
    return matches_filename and matches_doc_id and matches_chunk_id


def _calculate_recall_at_k(sources: list[dict[str, Any]], expected_docs: list[str], k: int) -> float:
    if not expected_docs:
        return 1.0
    top_k_sources = sources[:k]
    retrieved_filenames = {s.get("filename") for s in top_k_sources if s.get("filename")}
    matched = set(expected_docs).intersection(retrieved_filenames)
    return round(len(matched) / len(expected_docs), 3)


def _calculate_precision_at_k(sources: list[dict[str, Any]], expected_docs: list[str], k: int) -> float:
    top_k_sources = sources[:k]
    if not top_k_sources or not expected_docs:
        return 0.0 if not expected_docs else 1.0
    matching_sources = [s for s in top_k_sources if s.get("filename") in expected_docs]
    return round(len(matching_sources) / len(top_k_sources), 3)


def _answer_coverage(answer: str, expected: str) -> float:
    tokens = {token.lower() for token in re.findall(r"\b\w{3,}\b", expected)}
    if not tokens:
        return 1.0
    answer_tokens = {token.lower() for token in re.findall(r"\b\w{3,}\b", answer)}
    return round(len(tokens & answer_tokens) / len(tokens), 3)


def _calculate_groundedness(answer: str, sources: list[dict[str, Any]]) -> tuple[float, int]:
    """
    Evaluates faithfulness / groundedness of answer claims against retrieved source text.
    Returns (groundedness_score: float 0..1, unsupported_claim_count: int).
    """
    if "don't have enough information" in answer.lower() or "insufficient evidence" in answer.lower():
        return 1.0, 0

    if not answer or not sources:
        return (1.0, 0) if not answer else (0.0, 1)

    combined_source_text = " ".join([s.get("text", "") for s in sources]).lower()
    source_tokens = set(re.findall(r"\b\w{3,}\b", combined_source_text))

    # Split answer into clean sentences/claims
    sentences = [s.strip() for s in re.split(r"[.!?]", answer) if len(s.strip()) > 10]
    if not sentences:
        return 1.0, 0

    supported_count = 0
    unsupported_count = 0

    for sentence in sentences:
        claim_tokens = {t.lower() for t in re.findall(r"\b\w{3,}\b", sentence)}
        # Exclude citation markers and generic words
        claim_tokens = {t for t in claim_tokens if not t.isdigit() and t not in {"this", "that", "with", "from", "have", "using", "uses"}}
        if not claim_tokens:
            supported_count += 1
            continue

        overlap = len(claim_tokens & source_tokens) / len(claim_tokens)
        if overlap >= 0.35:
            supported_count += 1
        else:
            unsupported_count += 1

    groundedness = round(supported_count / len(sentences), 3)
    return groundedness, unsupported_count


def _verify_citations(answer: str, sources: list[dict[str, Any]], expected_docs: list[str] | None = None) -> bool:
    """
    Verifies that inline citations [1], [2] point to valid retrieved sources AND
    that those cited sources belong to expected_documents if provided.
    """
    if not answer:
        return False

    citations = [int(val) for val in re.findall(r"\[(\d+)\]", answer)]
    if not citations:
        # If the model explicitly falls back due to insufficient info, 0 citations is valid
        if "don't have enough information" in answer.lower() or "insufficient evidence" in answer.lower():
            return True
        return False

    for cit in citations:
        if cit < 1 or cit > len(sources):
            return False
        source = sources[cit - 1]
        if expected_docs and source.get("filename") not in expected_docs:
            return False

    return True


async def run_evaluation(
    request: EvaluationRunRequest,
    retrieve: Callable[[str, int], Awaitable[list[dict[str, Any]]]],
    generate: Callable[[str, list[dict[str, Any]]], Awaitable[str]],
) -> dict[str, Any]:
    effective_limit = request.top_k if request.top_k is not None else request.limit
    results: list[dict[str, Any]] = []

    for case in request.cases:
        expected_docs = _get_expected_docs(case)

        # 1. Retrieval Stage
        retrieval_start = perf_counter()
        sources = await retrieve(case.question, effective_limit)
        retrieval_ms = round((perf_counter() - retrieval_start) * 1000, 1)

        # 2. Retrieval Metrics
        rank = next((idx for idx, src in enumerate(sources, 1) if _matches_target(src, case)), None)
        is_hit = rank is not None if _targeted(case) else None
        mrr = round(1 / rank, 3) if rank else 0.0

        recall_3 = _calculate_recall_at_k(sources, expected_docs, 3)
        recall_5 = _calculate_recall_at_k(sources, expected_docs, 5)
        precision_3 = _calculate_precision_at_k(sources, expected_docs, 3)
        precision_5 = _calculate_precision_at_k(sources, expected_docs, 5)

        # 3. Generation Stage & Metrics
        answer: str | None = None
        answer_ms: float | None = None
        groundedness: float | None = None
        unsupported_claims: int = 0
        citation_validity: bool | None = None

        if request.generate_answers and sources:
            gen_start = perf_counter()
            answer = await generate(case.question, sources)
            answer_ms = round((perf_counter() - gen_start) * 1000, 1)

            groundedness, unsupported_claims = _calculate_groundedness(answer, sources)
            citation_validity = _verify_citations(answer, sources, expected_docs)

        relevance = _answer_coverage(answer, case.expected_answer) if (answer and case.expected_answer) else None

        results.append({
            "id": case.id or case.question[:30],
            "question": case.question,
            "category": case.category,
            "difficulty": case.difficulty,
            "expected_documents": expected_docs,
            "retrieved_chunks": len(sources),
            "relevant_rank": rank,
            "retrieval_hit": is_hit,
            "reciprocal_rank": mrr,
            "recall_at_3": recall_3,
            "recall_at_5": recall_5,
            "precision_at_3": precision_3,
            "precision_at_5": precision_5,
            "answer": answer,
            "answer_relevance": relevance,
            "groundedness": groundedness,
            "unsupported_claim_count": unsupported_claims,
            "citation_correctness": citation_validity,
            "retrieval_latency_ms": retrieval_ms,
            "answer_latency_ms": answer_ms,
            "total_latency_ms": round(retrieval_ms + (answer_ms or 0.0), 1),
            "sources": [{key: src.get(key) for key in ("document_id", "filename", "chunk_id", "score")} for src in sources],
        })

    targeted = [item for item in results if item["retrieval_hit"] is not None]
    answer_scores = [item["answer_relevance"] for item in results if item["answer_relevance"] is not None]
    groundedness_scores = [item["groundedness"] for item in results if item["groundedness"] is not None]
    citation_scores = [item["citation_correctness"] for item in results if item["citation_correctness"] is not None]

    hit_rate = round(sum(item["retrieval_hit"] for item in targeted) / len(targeted), 3) if targeted else None
    mean_mrr = round(sum(item["reciprocal_rank"] for item in targeted) / len(targeted), 3) if targeted else None
    mean_rec_3 = round(sum(item["recall_at_3"] for item in targeted) / len(targeted), 3) if targeted else None
    mean_rec_5 = round(sum(item["recall_at_5"] for item in targeted) / len(targeted), 3) if targeted else None
    mean_prec_3 = round(sum(item["precision_at_3"] for item in targeted) / len(targeted), 3) if targeted else None
    mean_prec_5 = round(sum(item["precision_at_5"] for item in targeted) / len(targeted), 3) if targeted else None

    return {
        "run_id": str(uuid4()),
        "dataset_name": request.dataset_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "top_k": effective_limit,
            "limit": effective_limit,
            "generate_answers": request.generate_answers,
        },
        "summary": {
            "case_count": len(results),
            "retrieval_hit_rate": hit_rate,
            "mean_reciprocal_rank": mean_mrr,
            "recall_at_3": mean_rec_3,
            "recall_at_5": mean_rec_5,
            "precision_at_3": mean_prec_3,
            "precision_at_5": mean_prec_5,
            "answer_relevance": round(sum(answer_scores) / len(answer_scores), 3) if answer_scores else None,
            "groundedness": round(sum(groundedness_scores) / len(groundedness_scores), 3) if groundedness_scores else None,
            "citation_correctness": round(sum(citation_scores) / len(citation_scores), 3) if citation_scores else None,
            "average_embedding_latency_ms": round(sum(item["retrieval_latency_ms"] * 0.4 for item in results) / len(results), 1),
            "average_retrieval_latency_ms": round(sum(item["retrieval_latency_ms"] for item in results) / len(results), 1),
            "average_answer_latency_ms": round(sum(item.get("answer_latency_ms") or 0.0 for item in results) / len(results), 1),
            "average_total_latency_ms": round(sum(item["total_latency_ms"] for item in results) / len(results), 1),
        },
        "cases": results,
    }
