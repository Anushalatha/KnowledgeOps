from __future__ import annotations

import pytest
from app.chunking import chunk_text
from app.evaluations import EvaluationCase, EvaluationRunRequest, _answer_coverage, _matches_target, run_evaluation
from app.reranking import rerank
from app.vector_store import VectorStoreConfigurationError, VectorStoreError


def test_chunking_preserves_text_and_overlap() -> None:
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = chunk_text(text, chunk_size=30, overlap=10)
    
    assert len(chunks) > 1
    assert "word0" in chunks[0]
    # Check overlap presence between chunk 0 and chunk 1
    chunk0_words = chunks[0].split()
    chunk1_words = chunks[1].split()
    overlap_words = set(chunk0_words[-10:]).intersection(set(chunk1_words[:10]))
    assert len(overlap_words) > 0


def test_answer_coverage_calculation() -> None:
    expected = "KnowledgeOps is an AI platform for document ingestion and retrieval."
    answer_exact = "KnowledgeOps is an AI platform for document ingestion and retrieval."
    answer_partial = "KnowledgeOps is an AI platform."
    answer_unrelated = "Python is a dynamic programming language."

    assert _answer_coverage(answer_exact, expected) == 1.0
    assert 0.0 < _answer_coverage(answer_partial, expected) < 1.0
    assert _answer_coverage(answer_unrelated, expected) == 0.0


def test_evaluation_case_target_matching() -> None:
    case = EvaluationCase(
        question="What is KnowledgeOps?",
        relevant_filename="architecture.pdf",
        relevant_chunk_id="doc1:chunk2",
    )

    matching_source = {"document_id": "doc1", "filename": "architecture.pdf", "chunk_id": "doc1:chunk2"}
    mismatched_source = {"document_id": "doc1", "filename": "architecture.pdf", "chunk_id": "doc1:chunk0"}

    assert _matches_target(matching_source, case) is True
    assert _matches_target(mismatched_source, case) is False


def test_reranker_sorts_by_combined_score() -> None:
    candidates = [
        {"chunk_id": "c1", "score": 0.95, "text": "This text discusses generic machine learning models."},
        {"chunk_id": "c2", "score": 0.85, "text": "RAG pipeline architecture includes vector retrieval, reranking, and LLM context generation."},
    ]
    query = "RAG pipeline architecture reranking"
    results, latency_ms = rerank(query, candidates, final_count=2)

    assert len(results) == 2
    # c2 matches query terms strongly, so reranking score should promote it to top position
    assert results[0]["chunk_id"] == "c2"
    assert results[0]["reranking_score"] > results[1]["reranking_score"]
    assert latency_ms >= 0


def test_full_evaluation_run_metrics() -> None:
    import asyncio

    cases = [
        EvaluationCase(
            question="What is Qdrant used for?",
            expected_answer="Qdrant is used as a vector database for semantic chunk retrieval.",
            relevant_filename="qdrant_guide.pdf",
        ),
        EvaluationCase(
            question="What is PyMuPDF used for?",
            expected_answer="PyMuPDF is used for PDF text extraction.",
            relevant_filename="extraction.pdf",
        ),
    ]

    async def mock_retrieve(question: str, limit: int) -> list[dict]:
        if "Qdrant" in question:
            return [
                {"document_id": "d1", "filename": "qdrant_guide.pdf", "chunk_id": "d1:0", "score": 0.92, "text": "Qdrant is used as a vector database for semantic chunk retrieval."},
                {"document_id": "d2", "filename": "other.pdf", "chunk_id": "d2:0", "score": 0.60, "text": "Other info."},
            ]
        return [
            {"document_id": "d3", "filename": "extraction.pdf", "chunk_id": "d3:0", "score": 0.88, "text": "PyMuPDF is used for PDF text extraction."},
        ]

    async def mock_generate(question: str, sources: list[dict]) -> str:
        if "Qdrant" in question:
            return "Qdrant is used as a vector database for semantic chunk retrieval [1]."
        return "PyMuPDF is used for PDF text extraction [1]."

    request = EvaluationRunRequest(
        dataset_name="unit-benchmark",
        cases=cases,
        limit=2,
        generate_answers=True,
    )

    run_result = asyncio.run(run_evaluation(request, mock_retrieve, mock_generate))

    assert run_result["summary"]["case_count"] == 2
    assert run_result["summary"]["retrieval_hit_rate"] == 1.0
    assert run_result["summary"]["mean_reciprocal_rank"] == 1.0
    assert run_result["summary"]["answer_relevance"] == 1.0
    assert run_result["summary"]["citation_correctness"] == 1.0
    assert run_result["summary"]["average_retrieval_latency_ms"] >= 0
