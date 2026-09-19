from __future__ import annotations

import asyncio
from app.benchmark_dataset_v2 import BENCHMARK_CASES_V2, BENCHMARK_DOCUMENTS_V2
from app.evaluations import (
    EvaluationCase,
    EvaluationRunRequest,
    _calculate_groundedness,
    _calculate_precision_at_k,
    _calculate_recall_at_k,
    _verify_citations,
    run_evaluation,
)


def test_benchmark_v2_dataset_loading() -> None:
    """Verifies that Benchmark Dataset v2 loads 30 cases and 6 domain documents."""
    assert len(BENCHMARK_CASES_V2) == 30
    assert len(BENCHMARK_DOCUMENTS_V2) == 6

    for case in BENCHMARK_CASES_V2:
        assert "id" in case
        assert "question" in case
        assert "expected_documents" in case
        assert "category" in case
        assert "difficulty" in case


def test_hit_rate_and_mrr_calculation() -> None:
    """Verifies Hit Rate, Recall@K, and Precision@K calculation metrics."""
    sources = [
        {"filename": "01_cloud_cost_optimization.pdf", "text": "Rightsizing cloud infrastructure."},
        {"filename": "02_cybersecurity_basics.pdf", "text": "Least privilege principles."},
        {"filename": "03_data_engineering_pipeline.pdf", "text": "Idempotent pipeline retries."},
    ]

    expected = ["01_cloud_cost_optimization.pdf"]

    recall_3 = _calculate_recall_at_k(sources, expected, k=3)
    precision_3 = _calculate_precision_at_k(sources, expected, k=3)

    assert recall_3 == 1.0
    assert precision_3 == round(1 / 3, 3)


def test_groundedness_evaluation_supported_vs_unsupported() -> None:
    """Verifies groundedness score calculation and unsupported claim detection."""
    sources = [
        {"filename": "01_cloud_cost_optimization.pdf", "text": "Rightsizing matches instance types to workload capacity at lowest cost."}
    ]

    # Grounded answer
    grounded_ans = "Rightsizing matches instance types to workload capacity. [1]"
    score, unsupported = _calculate_groundedness(grounded_ans, sources)
    assert score >= 0.8
    assert unsupported == 0

    # Fallback answer when evidence is insufficient
    fallback_ans = "I don't have enough information in the provided knowledge base to answer this."
    fb_score, fb_unsupported = _calculate_groundedness(fallback_ans, sources)
    assert fb_score == 1.0
    assert fb_unsupported == 0


def test_citation_verification_valid_wrong_missing() -> None:
    """Verifies citation correctness detection for valid, wrong, and missing citations."""
    sources = [
        {"filename": "01_cloud_cost_optimization.pdf", "text": "Cloud cost optimization."},
        {"filename": "02_cybersecurity_basics.pdf", "text": "Least privilege security."},
    ]

    # Valid citation
    assert _verify_citations("Rightsizing reduces costs. [1]", sources, ["01_cloud_cost_optimization.pdf"])["valid"] is True

    # Wrong document citation (cites [2] which is cybersecurity when expected is cloud)
    assert _verify_citations("Rightsizing reduces costs. [2]", sources, ["01_cloud_cost_optimization.pdf"])["valid"] is False

    # Missing citation when expected
    assert _verify_citations("Rightsizing reduces costs without any citation.", sources, ["01_cloud_cost_optimization.pdf"])["valid"] is False

    # Out of bounds citation
    assert _verify_citations("Rightsizing reduces costs. [99]", sources, ["01_cloud_cost_optimization.pdf"])["valid"] is False


def test_full_benchmark_run_evaluation_metrics() -> None:
    """Executes a full evaluation run with mock retrieval and generation callbacks."""
    async def _async_test() -> None:
        case = EvaluationCase(
            id="test_case_1",
            question="What does rightsizing mean in cloud infrastructure?",
            expected_documents=["01_cloud_cost_optimization.pdf"],
            category="direct_retrieval",
            difficulty="easy",
        )

        request = EvaluationRunRequest(
            dataset_name="Test Benchmark",
            cases=[case],
            limit=3,
            generate_answers=True,
        )

        async def mock_retrieve(q: str, limit: int) -> list[dict]:
            return [
                {"filename": "01_cloud_cost_optimization.pdf", "chunk_id": "c1", "text": "Rightsizing matches instance types.", "score": 0.9}
            ]

        async def mock_generate(q: str, sources: list[dict]) -> str:
            return "Rightsizing matches instance types to workload capacity. [1]"

        result = await run_evaluation(request, mock_retrieve, mock_generate)

        assert result["summary"]["case_count"] == 1
        assert result["summary"]["retrieval_hit_rate"] == 1.0
        assert result["summary"]["mean_reciprocal_rank"] == 1.0
        assert result["summary"]["groundedness"] == 1.0
        assert result["summary"]["citation_correctness"] == 1.0

    asyncio.run(_async_test())
