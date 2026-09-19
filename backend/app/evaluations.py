from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    expected_answer: str | None = Field(default=None, max_length=5000)
    relevant_document_id: str | None = None
    relevant_filename: str | None = None
    relevant_chunk_id: str | None = None


class EvaluationRunRequest(BaseModel):
    dataset_name: str = Field(default="ad-hoc", min_length=1, max_length=100)
    cases: list[EvaluationCase] = Field(min_length=1, max_length=100)
    limit: int = Field(default=5, ge=1, le=50)
    generate_answers: bool = False


class EvaluationDatasetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    cases: list[EvaluationCase] = Field(min_length=1, max_length=100)


def _targeted(case: EvaluationCase) -> bool:
    return any((case.relevant_document_id, case.relevant_filename, case.relevant_chunk_id))


def _matches_target(source: dict[str, Any], case: EvaluationCase) -> bool:
    return (
        (not case.relevant_document_id or source.get("document_id") == case.relevant_document_id)
        and (not case.relevant_filename or source.get("filename") == case.relevant_filename)
        and (not case.relevant_chunk_id or source.get("chunk_id") == case.relevant_chunk_id)
    )


def _answer_coverage(answer: str, expected: str) -> float:
    tokens = {token.lower() for token in re.findall(r"\b\w{3,}\b", expected)}
    if not tokens:
        return 1.0
    answer_tokens = {token.lower() for token in re.findall(r"\b\w{3,}\b", answer)}
    return round(len(tokens & answer_tokens) / len(tokens), 3)


async def run_evaluation(
    request: EvaluationRunRequest,
    retrieve: Callable[[str, int], Awaitable[list[dict[str, Any]]]],
    generate: Callable[[str, list[dict[str, Any]]], Awaitable[str]],
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case in request.cases:
        started = perf_counter()
        sources = await retrieve(case.question, request.limit)
        retrieval_ms = round((perf_counter() - started) * 1000, 1)
        rank = next((index for index, source in enumerate(sources, 1) if _matches_target(source, case)), None)
        answer: str | None = None
        answer_ms: float | None = None
        if request.generate_answers and sources:
            started = perf_counter()
            answer = await generate(case.question, sources)
            answer_ms = round((perf_counter() - started) * 1000, 1)
        citations = [int(value) for value in re.findall(r"\[(\d+)\]", answer or "")]
        valid_citations = all(1 <= citation <= len(sources) for citation in citations)
        results.append({
            "question": case.question,
            "retrieved_chunks": len(sources),
            "relevant_rank": rank,
            "retrieval_hit": rank is not None if _targeted(case) else None,
            "reciprocal_rank": round(1 / rank, 3) if rank else 0.0,
            "answer": answer,
            "answer_relevance": _answer_coverage(answer, case.expected_answer) if answer and case.expected_answer else None,
            "citation_correctness": valid_citations if answer else None,
            "retrieval_latency_ms": retrieval_ms,
            "answer_latency_ms": answer_ms,
            "sources": [{key: source.get(key) for key in ("document_id", "filename", "chunk_id", "score")} for source in sources],
        })

    targeted = [item for item in results if item["retrieval_hit"] is not None]
    answer_scores = [item["answer_relevance"] for item in results if item["answer_relevance"] is not None]
    citation_scores = [item["citation_correctness"] for item in results if item["citation_correctness"] is not None]
    return {
        "run_id": str(uuid4()),
        "dataset_name": request.dataset_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {"limit": request.limit, "generate_answers": request.generate_answers},
        "summary": {
            "case_count": len(results),
            "retrieval_hit_rate": round(sum(item["retrieval_hit"] for item in targeted) / len(targeted), 3) if targeted else None,
            "mean_reciprocal_rank": round(sum(item["reciprocal_rank"] for item in targeted) / len(targeted), 3) if targeted else None,
            "answer_relevance": round(sum(answer_scores) / len(answer_scores), 3) if answer_scores else None,
            "citation_correctness": round(sum(citation_scores) / len(citation_scores), 3) if citation_scores else None,
            "average_retrieval_latency_ms": round(sum(item["retrieval_latency_ms"] for item in results) / len(results), 1),
        },
        "cases": results,
    }
