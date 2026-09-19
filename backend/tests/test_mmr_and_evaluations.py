from __future__ import annotations

import asyncio
from app.evaluations import (
    EvaluationCase,
    EvaluationRunRequest,
    _calculate_groundedness,
    _evaluate_answer_relevance,
    _verify_citations,
    run_evaluation,
)
from app.reranking import calculate_chunk_similarity, rerank


def test_mmr_selects_relevant_and_diverse_chunks() -> None:
    """Verifies that MMR balances query relevance and document diversity."""
    candidates = [
        {"filename": "01_cloud.pdf", "text": "Cloud cost rightsizing matches capacity.", "score": 0.90},
        {"filename": "01_cloud.pdf", "text": "Cloud cost allocation tags provide visibility.", "score": 0.88},
        {"filename": "02_security.pdf", "text": "Least privilege security policies.", "score": 0.85},
    ]

    # MMR Enabled (lambda = 0.5 balances diversity)
    selected_mmr, _ = rerank("cloud and security", candidates, final_count=2, mmr_enabled=True, mmr_lambda=0.5)
    filenames_mmr = [item["filename"] for item in selected_mmr]
    assert "01_cloud.pdf" in filenames_mmr
    assert "02_security.pdf" in filenames_mmr


def test_mmr_does_not_force_unrelated_documents() -> None:
    """Verifies that single-document focused queries remain focused on relevant sources."""
    candidates = [
        {"filename": "04_analytics.pdf", "text": "Cohort analysis tracks user retention.", "score": 0.95},
        {"filename": "04_analytics.pdf", "text": "DAU/MAU stickiness ratio measures engagement.", "score": 0.90},
        {"filename": "06_ml.pdf", "text": "Cross-validation estimates fold error.", "score": 0.10},
    ]

    selected, _ = rerank("cohort analysis retention", candidates, final_count=2, mmr_enabled=True, mmr_lambda=0.8)
    assert selected[0]["filename"] == "04_analytics.pdf"
    assert selected[1]["filename"] == "04_analytics.pdf"


def test_multi_document_queries_retrieve_multiple_sources() -> None:
    """Verifies that multi-document queries return chunks from distinct target documents."""
    candidates = [
        {"filename": "03_data_engineering.pdf", "text": "Idempotent processing avoids duplicate retries.", "score": 0.90},
        {"filename": "05_networking.pdf", "text": "Explicit request timeouts prevent thread exhaustion.", "score": 0.88},
    ]

    selected, _ = rerank("pipeline retries and networking timeouts", candidates, final_count=2, mmr_enabled=True)
    assert len({item["filename"] for item in selected}) == 2


def test_citation_metadata_verification() -> None:
    """Verifies that every cited inline source exists in retrieved chunks."""
    sources = [
        {"filename": "01_cloud.pdf", "chunk_id": "c1"},
        {"filename": "02_security.pdf", "chunk_id": "c2"},
    ]

    # Valid citations
    res_valid = _verify_citations("Rightsizing lowers cost [1]. Least privilege protects APIs [2].", sources, ["01_cloud.pdf", "02_security.pdf"])
    assert res_valid["valid"] is True

    # Out of bounds citation [99]
    res_invalid = _verify_citations("Invalid citation test [99].", sources)
    assert res_invalid["valid"] is False


def test_insufficient_evidence_behavior() -> None:
    """Verifies that missing evidence triggers fallback response."""
    sources = [{"filename": "01_cloud.pdf", "text": "Cloud cost rightsizing."}]
    answer = "I don't have enough information in the provided knowledge base to answer this."

    score, unsupported = _calculate_groundedness(answer, sources)
    assert score == 1.0
    assert unsupported == 0

    relevance = _evaluate_answer_relevance("quantum satellite encryption", answer, None, [])
    assert relevance["relevance_score"] == 1.0


def test_relevance_evaluator_detects_incomplete_answers() -> None:
    """Verifies aspect-based relevance evaluator penalizes answers missing key requested topics."""
    answer = "Use TLS encryption for security."
    topics = ["TLS encryption", "idempotent processing", "monitoring metrics"]

    rel = _evaluate_answer_relevance("How to handle security, retries, and monitoring?", answer, None, topics)
    assert rel["relevance_score"] < 1.0
    assert "idempotent processing" in rel["missing_aspects"]


def test_full_benchmark_evaluator_integration() -> None:
    """End-to-end integration test running evaluation on sample cases."""
    async def _async_test() -> None:
        case = EvaluationCase(
            id="test_integration",
            question="What is rightsizing in cloud computing?",
            expected_documents=["01_cloud.pdf"],
            expected_topics=["rightsizing", "capacity"],
        )

        request = EvaluationRunRequest(
            dataset_name="Test Integration",
            cases=[case],
            limit=2,
            generate_answers=True,
        )

        async def mock_retrieve(q: str, limit: int) -> list[dict]:
            return [{"filename": "01_cloud.pdf", "chunk_id": "c1", "text": "Rightsizing matches capacity at lowest cost.", "score": 0.9}]

        async def mock_generate(q: str, sources: list[dict]) -> str:
            return "Rightsizing matches instance capacity at lowest cost. [1]"

        res = await run_evaluation(request, mock_retrieve, mock_generate)
        assert res["summary"]["retrieval_hit_rate"] == 1.0
        assert res["summary"]["groundedness"] == 1.0
        assert res["summary"]["citation_correctness"] == 1.0

    asyncio.run(_async_test())
