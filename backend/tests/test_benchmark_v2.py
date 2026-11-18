from __future__ import annotations

import asyncio
from app.benchmark_dataset_v2 import BENCHMARK_CASES_V2, BENCHMARK_DOCUMENTS_V2
from app import main as main_module
from app.embeddings import EmbeddingConfigurationError
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


def test_unjudged_document_metrics_are_not_scored_as_perfect() -> None:
    sources = [{"filename": "unrelated.pdf", "text": "No expected target."}]

    assert _calculate_recall_at_k(sources, [], k=5) is None
    assert _calculate_precision_at_k(sources, [], k=5) is None


def test_multidocument_recall_requires_all_documents_but_hit_requires_any() -> None:
    async def _async_test() -> None:
        case = EvaluationCase(
            id="multi-document",
            question="Compare two sources",
            expected_documents=["first.pdf", "second.pdf"],
            category="cross_document",
        )

        async def mock_retrieve(question: str, limit: int) -> list[dict]:
            return [{"filename": "first.pdf", "chunk_id": "first:0", "text": "First source"}]

        async def mock_generate(question: str, sources: list[dict]) -> str:
            return "A response."

        result = await run_evaluation(
            EvaluationRunRequest(cases=[case], generate_answers=False),
            mock_retrieve,
            mock_generate,
        )

        case_result = result["cases"][0]
        assert case_result["retrieval_hit"] is True
        assert case_result["relevant_rank"] == 1
        assert case_result["reciprocal_rank"] == 1.0
        assert case_result["recall_at_5"] == 0.5
        assert case_result["precision_at_5"] == 1.0
        assert result["evaluation_version"] == "document-match-v2"
        assert result["summary"]["expected_document_case_count"] == 1

    asyncio.run(_async_test())


def test_insufficient_evidence_case_has_no_retrieval_match_scores() -> None:
    async def _async_test() -> None:
        case = EvaluationCase(
            id="insufficient",
            question="What unsupported technology is used?",
            category="insufficient_evidence",
        )

        async def mock_retrieve(question: str, limit: int) -> list[dict]:
            return [{"filename": "unrelated.pdf", "chunk_id": "other:0", "text": "Unrelated content"}]

        async def mock_generate(question: str, sources: list[dict]) -> str:
            return "Unsupported factual answer."

        result = await run_evaluation(
            EvaluationRunRequest(cases=[case], generate_answers=True),
            mock_retrieve,
            mock_generate,
        )

        case_result = result["cases"][0]
        assert case_result["retrieval_hit"] is None
        assert case_result["relevant_rank"] is None
        assert case_result["reciprocal_rank"] is None
        assert case_result["recall_at_5"] is None
        assert case_result["precision_at_5"] is None
        assert case_result["insufficient_evidence_correctness"] is False
        assert case_result["answer_relevance"] is None
        assert case_result["groundedness"] is None
        assert case_result["citation_correctness"] is None
        assert result["summary"]["retrieval_hit_rate"] is None
        assert result["summary"]["insufficient_evidence_correctness"] == 0.0

    asyncio.run(_async_test())


def test_insufficient_evidence_abstention_is_scored_separately() -> None:
    async def _async_test() -> None:
        case = EvaluationCase(
            question="What unsupported technology is used?",
            category="insufficient_evidence",
        )

        async def mock_retrieve(question: str, limit: int) -> list[dict]:
            return [{"filename": "unrelated.pdf", "chunk_id": "other:0", "text": "Unrelated content"}]

        async def mock_generate(question: str, sources: list[dict]) -> str:
            return "I don't have enough information in the provided knowledge base to answer this."

        result = await run_evaluation(
            EvaluationRunRequest(cases=[case], generate_answers=True),
            mock_retrieve,
            mock_generate,
        )

        assert result["cases"][0]["insufficient_evidence_correctness"] is True
        assert result["summary"]["insufficient_evidence_correctness"] == 1.0

    asyncio.run(_async_test())


def test_benchmark_endpoint_versions_run_and_records_actual_sources(monkeypatch) -> None:
    candidates = [
        {
            "filename": filename,
            "document_id": filename.removesuffix(".pdf"),
            "chunk_id": f"{filename}:0",
            "text": "Mock benchmark source content.",
        }
        for filename in BENCHMARK_DOCUMENTS_V2
    ]
    saved_runs = []

    async def mock_embed_texts(texts: list[str], task_type: str | None = None) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    def mock_rerank(*, candidates: list[dict], final_count: int, **kwargs):
        return candidates[:final_count], 0.0

    async def mock_generate(question: str, sources: list[dict]) -> str:
        return "Mock generated answer."

    async def unavailable_embeddings(
        texts: list[str],
        task_type: str | None = None,
    ) -> list[list[float]]:
        raise EmbeddingConfigurationError("Embeddings are unavailable for this test.")

    async def unavailable_generation(question: str, sources: list[dict]) -> str:
        from app.llm import LLMConfigurationError

        raise LLMConfigurationError("Generation is unavailable for this test.")

    monkeypatch.setattr(main_module, "embed_texts", mock_embed_texts)
    monkeypatch.setattr(main_module, "search_document_chunks", lambda vector, limit: candidates)
    monkeypatch.setattr(main_module, "rerank", mock_rerank)
    monkeypatch.setattr(main_module, "generate_grounded_answer", mock_generate)
    monkeypatch.setattr(main_module, "save_evaluation_run", saved_runs.append)

    live_result = asyncio.run(
        main_module.run_benchmark_v2_endpoint(
            top_k=5,
            generate_answers=True,
            mmr_enabled=True,
            mmr_lambda=0.7,
            candidate_pool_size=15,
        )
    )
    assert live_result["evaluation_version"] == "document-match-v2"
    assert live_result["retrieval_source_counts"] == {"qdrant": len(BENCHMARK_CASES_V2)}
    assert live_result["answer_source_counts"] == {"llm": len(BENCHMARK_CASES_V2)}
    assert live_result["cases"][0]["retrieval_source"] == "qdrant"
    assert live_result["cases"][0]["answer_source"] == "llm"

    monkeypatch.setattr(main_module, "embed_texts", unavailable_embeddings)
    monkeypatch.setattr(main_module, "generate_grounded_answer", unavailable_generation)
    fallback_result = asyncio.run(
        main_module.run_benchmark_v2_endpoint(
            top_k=5,
            generate_answers=True,
            mmr_enabled=True,
            mmr_lambda=0.7,
            candidate_pool_size=15,
        )
    )
    assert fallback_result["retrieval_source_counts"] == {
        "benchmark_fallback": len(BENCHMARK_CASES_V2),
    }
    assert fallback_result["answer_source_counts"] == {
        "benchmark_fallback": len(BENCHMARK_CASES_V2),
    }
    assert fallback_result["cases"][0]["retrieval_source"] == "benchmark_fallback"
    assert fallback_result["cases"][0]["answer_source"] == "benchmark_fallback"
    assert saved_runs == [live_result, fallback_result]


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
