from __future__ import annotations

import pytest
from app.evaluations import (
    _answer_coverage,
    _calculate_groundedness,
    _calculate_precision_at_k,
    _calculate_recall_at_k,
    _evaluate_answer_relevance,
    _verify_citations,
)


def test_01_single_part_question_answered_completely():
    question = "What does rightsizing mean in cloud infrastructure?"
    answer = "Rightsizing means matching instance types and capacity to workload requirements at the lowest cost. [1]"
    expected_topics = ["rightsizing", "capacity", "lowest cost"]

    eval_res = _evaluate_answer_relevance(question, answer, None, expected_topics)
    assert eval_res["relevance_score"] == 1.0
    assert eval_res["missing_aspects"] == []


def test_02_multi_part_question_answered_completely():
    question = "What practices should be used to protect the API, make the pipeline retry-safe, and monitor failures?"
    answer = (
        "Protect the API using TLS encryption and rate limiting. [1] "
        "Make the pipeline retry-safe using idempotent job execution. [2] "
        "Monitor failures with dead-letter queue metrics and alert thresholds. [3]"
    )
    expected_topics = ["protect the API", "retry-safe", "monitor failures"]

    eval_res = _evaluate_answer_relevance(question, answer, None, expected_topics)
    assert eval_res["relevance_score"] == 1.0
    assert eval_res["missing_aspects"] == []


def test_03_multi_document_question():
    answer = "DNS translates domains to IPs [1]. Idempotent retries prevent duplicates [2]."
    sources = [
        {"filename": "05_networking_fundamentals.pdf", "text": "DNS translates domains"},
        {"filename": "03_data_engineering_pipeline.pdf", "text": "Idempotent retries prevent duplicates"},
    ]
    expected_docs = ["05_networking_fundamentals.pdf", "03_data_engineering_pipeline.pdf"]

    cit_res = _verify_citations(answer, sources, expected_docs)
    assert cit_res["valid"] is True


def test_04_missing_evidence():
    question = "What quantum encryption algorithm is used by KnowledgeOps?"
    answer = "I don't have enough information in the provided knowledge base to answer this."

    eval_res = _evaluate_answer_relevance(question, answer, None, expected_topics=[])
    assert eval_res["relevance_score"] == 1.0

    cit_res = _verify_citations(answer, [], expected_docs=[])
    assert cit_res["valid"] is True


def test_05_irrelevant_retrieved_chunk():
    sources = [
        {"filename": "01_cloud_cost_optimization.pdf", "text": "Rightsizing cloud instances reduces costs."},
        {"filename": "06_machine_learning_evaluation.pdf", "text": "Accuracy is misleading for imbalanced datasets."},
    ]
    expected_docs = ["01_cloud_cost_optimization.pdf"]

    prec = _calculate_precision_at_k(sources, expected_docs, k=2)
    assert prec == 0.5


def test_06_unsupported_claim():
    answer = "Rightsizing reduces cloud costs [1]. KnowledgeOps uses quantum computers to process data instantly."
    sources = [
        {"filename": "01_cloud_cost_optimization.pdf", "text": "Rightsizing cloud instances reduces costs."}
    ]

    groundedness, unsupported_count = _calculate_groundedness(answer, sources)
    assert unsupported_count >= 1
    assert groundedness < 1.0


def test_07_multiple_citations():
    answer = "System reliability requires idempotent handlers [1] and explicit request timeouts [2]."
    sources = [
        {"filename": "03_data_engineering_pipeline.pdf", "text": "idempotent handlers"},
        {"filename": "05_networking_fundamentals.pdf", "text": "explicit request timeouts"},
    ]

    cit_res = _verify_citations(answer, sources)
    assert cit_res["valid"] is True


def test_08_wrong_citation():
    answer = "Rightsizing reduces cloud costs [5]."
    sources = [
        {"filename": "01_cloud_cost_optimization.pdf", "text": "Rightsizing cloud instances"}
    ]

    cit_res = _verify_citations(answer, sources)
    assert cit_res["valid"] is False
    assert "out of bounds" in cit_res["reason"]


def test_09_missing_citation():
    answer = "Rightsizing reduces cloud costs."
    sources = [
        {"filename": "01_cloud_cost_optimization.pdf", "text": "Rightsizing cloud instances"}
    ]

    cit_res = _verify_citations(answer, sources)
    assert cit_res["valid"] is False
    assert "Missing required inline citations" in cit_res["reason"]


def test_10_empty_retrieval():
    sources = []
    expected_docs = ["01_cloud_cost_optimization.pdf"]

    rec = _calculate_recall_at_k(sources, expected_docs, k=5)
    assert rec == 0.0


def test_11_conflicting_evidence():
    sources = [
        {"filename": "doc1.pdf", "text": "Doc 1 recommends a 30 second timeout for network requests."},
        {"filename": "doc2.pdf", "text": "Doc 2 specifies a 5 second timeout for network requests."},
    ]
    answer = "Doc 1 recommends a 30 second timeout [1], whereas Doc 2 specifies a 5 second timeout [2]."

    groundedness, unsupported = _calculate_groundedness(answer, sources)
    assert groundedness == 1.0
    assert unsupported == 0


def test_12_long_context():
    long_text = "Word " * 500
    sources = [{"filename": "doc_long.pdf", "text": long_text}]
    answer = "Summary of long context. [1]"

    cit_res = _verify_citations(answer, sources)
    assert cit_res["valid"] is True


def test_13_short_context():
    short_text = "Idempotency prevents duplicates."
    sources = [{"filename": "doc_short.pdf", "text": short_text}]
    answer = "Idempotency prevents duplicates. [1]"

    groundedness, unsupported = _calculate_groundedness(answer, sources)
    assert groundedness == 1.0
    assert unsupported == 0
