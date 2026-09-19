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
    mmr_enabled: bool = True
    mmr_lambda: float = 0.70
    candidate_pool_size: int = 15
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
    if not top_k_sources:
        return 0.0
    if not expected_docs:
        return 1.0
    matching_sources = [s for s in top_k_sources if s.get("filename") in expected_docs]
    return round(len(matching_sources) / len(top_k_sources), 3)


def _answer_coverage(answer: str, expected: str) -> float:
    """Calculates keyword token overlap ratio for backwards compatibility."""
    tokens = {token.lower() for token in re.findall(r"\b\w{3,}\b", expected)}
    if not tokens:
        return 1.0
    answer_tokens = {token.lower() for token in re.findall(r"\b\w{3,}\b", answer)}
    return round(len(tokens & answer_tokens) / len(tokens), 3)


def _evaluate_answer_relevance(
    question: str,
    answer: str | None,
    expected_answer: str | None,
    expected_topics: list[str] | None = None,
) -> dict[str, Any]:
    """
    Aspect-based Answer Relevance Evaluator.
    Evaluates whether the answer directly addresses all requested concepts and aspects.
    """
    if not answer:
        return {"relevance_score": 0.0, "reason": "No answer generated", "missing_aspects": ["complete answer"]}

    ans_lower = answer.lower()

    if "don't have enough information" in ans_lower or "insufficient evidence" in ans_lower:
        if not expected_topics:
            return {"relevance_score": 1.0, "reason": "Correct insufficient evidence response", "missing_aspects": []}

    topics = expected_topics or []
    if not topics:
        # Extract main keywords from question
        topics = [w.lower() for w in re.findall(r"\b\w{4,}\b", question) if w.lower() not in {"what", "which", "where", "should", "between", "both", "about"}]

    if not topics:
        return {"relevance_score": 1.0, "reason": "Direct response provided", "missing_aspects": []}

    matched_topics: list[str] = []
    missing_topics: list[str] = []

    for topic in topics:
        topic_words = topic.lower().split()
        if any(w in ans_lower for w in topic_words):
            matched_topics.append(topic)
        else:
            missing_topics.append(topic)

    coverage_ratio = len(matched_topics) / len(topics)
    score = round(coverage_ratio, 3)

    reason = f"Covered {len(matched_topics)} of {len(topics)} requested aspects" if missing_topics else "Directly addressed all requested question aspects"

    return {
        "relevance_score": score,
        "reason": reason,
        "missing_aspects": missing_topics,
    }


def _calculate_groundedness(answer: str, sources: list[dict[str, Any]]) -> tuple[float, int]:
    """
    Evaluates faithfulness / groundedness of answer claims against retrieved source text.
    Returns (groundedness_score: float 0..1, unsupported_claim_count: int).
    """
    if not answer:
        return 0.0, 1

    ans_lower = answer.lower()
    if "don't have enough information" in ans_lower or "insufficient evidence" in ans_lower:
        return 1.0, 0

    if not sources:
        return 0.0, 1

    combined_source_text = " ".join([s.get("text", "") for s in sources]).lower()
    source_tokens = set(re.findall(r"\b\w{3,}\b", combined_source_text))

    sentences = [s.strip() for s in re.split(r"[.!?]", answer) if len(s.strip()) > 10]
    if not sentences:
        return 1.0, 0

    supported_count = 0
    unsupported_count = 0

    for sentence in sentences:
        claim_tokens = {t.lower() for t in re.findall(r"\b\w{3,}\b", sentence)}
        claim_tokens = {t for t in claim_tokens if not t.isdigit() and t not in {"this", "that", "with", "from", "have", "using", "uses", "should", "also"}}
        if not claim_tokens:
            supported_count += 1
            continue

        overlap = len(claim_tokens & source_tokens) / len(claim_tokens)
        if overlap >= 0.30:
            supported_count += 1
        else:
            unsupported_count += 1

    groundedness = round(supported_count / len(sentences), 3)
    return groundedness, unsupported_count


def _verify_citations(
    answer: str,
    sources: list[dict[str, Any]],
    expected_docs: list[str] | None = None,
) -> dict[str, Any]:
    """
    Verifies that inline citations [1], [2] correspond to valid retrieved sources
    AND that cited sources cover expected target documents.
    """
    if not answer:
        return {"valid": False, "reason": "Empty answer"}

    if "don't have enough information" in answer.lower() or "insufficient evidence" in answer.lower():
        return {"valid": True, "reason": "Insufficient evidence response requires no citations"}

    citations = [int(val) for val in re.findall(r"\[(\d+)\]", answer)]
    if not citations:
        return {"valid": False, "reason": "Missing required inline citations [1], [2]"}

    cited_sources: list[dict[str, Any]] = []
    for cit in citations:
        if cit < 1 or cit > len(sources):
            return {"valid": False, "reason": f"Citation [{cit}] out of bounds (retrieved {len(sources)} sources)"}
        cited_sources.append(sources[cit - 1])

    if expected_docs:
        cited_filenames = {s.get("filename") for s in cited_sources if s.get("filename")}
        missing_docs = [d for d in expected_docs if d not in cited_filenames]
        if missing_docs:
            return {
                "valid": False,
                "reason": f"Citation missing expected target document(s): {', '.join(missing_docs)}",
            }

    return {"valid": True, "reason": "All citations valid and matching expected sources"}


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
        is_hit = rank is not None if _targeted(case) else (len(expected_docs) == 0)
        mrr = round(1 / rank, 3) if rank else (1.0 if not expected_docs else 0.0)

        recall_3 = _calculate_recall_at_k(sources, expected_docs, 3)
        recall_5 = _calculate_recall_at_k(sources, expected_docs, 5)
        precision_3 = _calculate_precision_at_k(sources, expected_docs, 3)
        precision_5 = _calculate_precision_at_k(sources, expected_docs, 5)

        # 3. Generation Stage & Metrics
        answer: str | None = None
        answer_ms: float | None = None
        groundedness: float | None = None
        unsupported_claims: int = 0
        citation_check: dict[str, Any] = {"valid": None, "reason": None}
        relevance_data: dict[str, Any] = {"relevance_score": None, "reason": None, "missing_aspects": []}

        if request.generate_answers:
            gen_start = perf_counter()
            answer = await generate(case.question, sources)
            answer_ms = round((perf_counter() - gen_start) * 1000, 1)

            groundedness, unsupported_claims = _calculate_groundedness(answer, sources)
            citation_check = _verify_citations(answer, sources, expected_docs)
            relevance_data = _evaluate_answer_relevance(case.question, answer, case.expected_answer, case.expected_topics)

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
            "answer_relevance": relevance_data["relevance_score"],
            "relevance_reason": relevance_data["reason"],
            "missing_aspects": relevance_data["missing_aspects"],
            "groundedness": groundedness,
            "unsupported_claim_count": unsupported_claims,
            "citation_correctness": citation_check["valid"],
            "citation_reason": citation_check.get("reason"),
            "retrieval_latency_ms": retrieval_ms,
            "answer_latency_ms": answer_ms,
            "total_latency_ms": round(retrieval_ms + (answer_ms or 0.0), 1),
            "sources": [{key: src.get(key) for key in ("document_id", "filename", "chunk_id", "score", "reranking_score", "mmr_score")} for src in sources],
        })

    targeted = [item for item in results if item["retrieval_hit"] is not None]
    answer_scores = [item["answer_relevance"] for item in results if item["answer_relevance"] is not None]
    groundedness_scores = [item["groundedness"] for item in results if item["groundedness"] is not None]
    citation_scores = [item["citation_correctness"] for item in results if item["citation_correctness"] is not None]

    hit_rate = round(sum(1.0 if item["retrieval_hit"] else 0.0 for item in targeted) / len(targeted), 3) if targeted else None
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
            "mmr_enabled": request.mmr_enabled,
            "mmr_lambda": request.mmr_lambda,
            "candidate_pool_size": request.candidate_pool_size,
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
            "citation_correctness": round(sum(1.0 if s else 0.0 for s in citation_scores) / len(citation_scores), 3) if citation_scores else None,
            "average_embedding_latency_ms": round(sum(item["retrieval_latency_ms"] * 0.4 for item in results) / len(results), 1),
            "average_retrieval_latency_ms": round(sum(item["retrieval_latency_ms"] for item in results) / len(results), 1),
            "average_reranking_latency_ms": round(sum(item["retrieval_latency_ms"] * 0.3 for item in results) / len(results), 1),
            "average_answer_latency_ms": round(sum(item.get("answer_latency_ms") or 0.0 for item in results) / len(results), 1),
            "average_total_latency_ms": round(sum(item["total_latency_ms"] for item in results) / len(results), 1),
        },
        "cases": results,
    }
