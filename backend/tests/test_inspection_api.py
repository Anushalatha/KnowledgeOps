from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main, vector_store


client = TestClient(main.app)


def test_collection_points_endpoint_returns_payload_without_vectors(monkeypatch) -> None:
    expected_point = {
        "point_id": "point-1",
        "document_id": "doc-1",
        "chunk_id": "doc-1:0",
        "text": "Stored chunk text.",
    }
    monkeypatch.setattr(main, "collection_name", lambda: "knowledgeops_documents")
    monkeypatch.setattr(
        main,
        "scroll_collection_points",
        lambda **kwargs: {"points": [expected_point], "next_offset": "point-next"},
    )

    response = client.get("/collections/knowledgeops_documents/points?limit=1")

    assert response.status_code == 200
    assert response.json() == {
        "collection": "knowledgeops_documents",
        "points": [expected_point],
        "next_offset": "point-next",
    }
    assert "vector" not in response.text


def test_collection_points_supports_search_filter_and_filtered_pagination(monkeypatch) -> None:
    points = [
        {"point_id": "point-1", "document_id": "doc-1", "category": "guide", "text": "RAG ingestion"},
        {"point_id": "point-2", "document_id": "doc-2", "category": "guide", "text": "RAG query"},
    ]
    monkeypatch.setattr(main, "collection_name", lambda: "knowledgeops_documents")
    monkeypatch.setattr(
        main,
        "scroll_collection_points",
        lambda **kwargs: {"points": points, "next_offset": None},
    )
    monkeypatch.setattr(
        vector_store,
        "scroll_collection_points",
        lambda **kwargs: {"points": points, "next_offset": None},
    )

    first_page = client.get(
        "/collections/knowledgeops_documents/points",
        params={"point_query": "rag", "filter_field": "category", "filter_value": "guide", "limit": 1},
    )
    second_page = client.get(
        "/collections/knowledgeops_documents/points",
        params={"point_query": "rag", "filter_field": "category", "filter_value": "guide", "limit": 1, "offset": "1"},
    )

    assert first_page.status_code == 200
    assert first_page.json()["points"] == [points[0]]
    assert first_page.json()["total"] == 2
    assert first_page.json()["next_offset"] == "1"
    assert second_page.status_code == 200
    assert second_page.json()["points"] == [points[1]]
    assert second_page.json()["next_offset"] is None


def test_filtered_collection_points_rejects_qdrant_cursor_offsets(monkeypatch) -> None:
    monkeypatch.setattr(main, "collection_name", lambda: "knowledgeops_documents")
    response = client.get(
        "/collections/knowledgeops_documents/points",
        params={"point_query": "text", "offset": "qdrant-cursor"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Filtered point pages require a numeric offset."


def test_collection_points_rejects_incomplete_payload_filters(monkeypatch) -> None:
    monkeypatch.setattr(main, "collection_name", lambda: "knowledgeops_documents")
    response = client.get(
        "/collections/knowledgeops_documents/points",
        params={"filter_value": "guide"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Payload field and value filters must be provided together."


def test_unmatched_collection_points_include_missing_document_ids(monkeypatch) -> None:
    points = [
        {"point_id": "point-known", "document_id": "known"},
        {"point_id": "point-missing", "document_id": "missing"},
        {"point_id": "point-no-id"},
    ]
    monkeypatch.setattr(main, "collection_name", lambda: "knowledgeops_documents")
    monkeypatch.setattr(main, "DOCUMENTS", {"known": {}})
    monkeypatch.setattr(
        main,
        "scroll_collection_points",
        lambda **kwargs: {"points": points, "next_offset": None},
    )
    monkeypatch.setattr(
        vector_store,
        "scroll_collection_points",
        lambda **kwargs: {"points": points, "next_offset": None},
    )

    response = client.get("/collections/knowledgeops_documents/unmatched-points")

    assert response.status_code == 200
    body = response.json()
    assert [point["point_id"] for point in body["points"]] == ["point-missing", "point-no-id"]
    assert all("unmatched_reason" in point for point in body["points"])
    assert body["total"] == 2


def test_collection_details_reports_unmatched_points(monkeypatch) -> None:
    monkeypatch.setattr(main, "collection_name", lambda: "knowledgeops_documents")
    monkeypatch.setattr(
        main,
        "get_collection_details",
        lambda: {"name": "knowledgeops_documents", "scanned_points": 2},
    )
    pages = iter([
        {"points": [{"document_id": "known"}, {"document_id": "missing"}], "next_offset": None},
    ])
    monkeypatch.setattr(main, "scroll_collection_points", lambda **kwargs: next(pages))
    monkeypatch.setattr(main, "DOCUMENTS", {"known": {}})

    response = client.get("/collections/knowledgeops_documents/details")

    assert response.status_code == 200
    assert response.json()["unmatched_points"] == 1
    assert response.json()["sqlite_document_count"] == 1


def test_collection_details_counts_payload_presence_unknown_values_and_types(monkeypatch) -> None:
    payloads = [
        {"project_name": "unknown", "category": None, "page_number": 1},
        {"project_name": "Project A", "page_number": 2},
    ]

    class FakeClient:
        def collection_exists(self, name):
            return True

        def get_collection(self, name):
            vector_config = SimpleNamespace(
                size=3,
                distance=SimpleNamespace(value="Cosine"),
            )
            config = SimpleNamespace(
                params=SimpleNamespace(vectors=vector_config),
                optimizer_config=None,
                hnsw_config=None,
            )
            return SimpleNamespace(config=config, points_count=2, payload_schema={})

        def scroll(self, **kwargs):
            return ([SimpleNamespace(payload=payload) for payload in payloads], None)

    monkeypatch.setattr(vector_store, "get_client", FakeClient)
    monkeypatch.setattr(vector_store, "collection_name", lambda: "knowledgeops_documents")

    details = vector_store.get_collection_details()

    assert details["scanned_points"] == 2
    assert details["payload_field_statistics"]["project_name"] == {
        "present_points": 2,
        "missing_points": 0,
        "unknown_points": 1,
        "known_points": 1,
        "completeness_percent": 50.0,
        "types": ["str"],
    }
    assert details["payload_field_statistics"]["category"] == {
        "present_points": 1,
        "missing_points": 2,
        "unknown_points": 0,
        "known_points": 0,
        "completeness_percent": 0.0,
        "types": [],
    }
    assert details["payload_field_statistics"]["page_number"]["types"] == ["int"]


def test_indexed_document_chunks_uses_stored_point_ids(monkeypatch) -> None:
    monkeypatch.setattr(main, "DOCUMENTS", {"doc-1": {"filename": "source.pdf"}})
    monkeypatch.setattr(main, "count_document_points", lambda document_id: 1)
    monkeypatch.setattr(
        main,
        "scroll_collection_points",
        lambda **kwargs: {
            "points": [{
                "point_id": "stored-point",
                "document_id": "doc-1",
                "chunk_id": "doc-1:7",
                "chunk_index": 7,
                "text": "Existing payload text",
            }],
            "next_offset": None,
        },
    )

    response = client.get("/documents/doc-1/indexed-chunks")

    assert response.status_code == 200
    body = response.json()
    assert body["total_chunk_count"] == 1
    assert body["chunks"][0]["point_id"] == "stored-point"
    assert body["chunks"][0]["chunk_id"] == "doc-1:7"
    assert body["chunks"][0]["text"] == "Existing payload text"


def test_search_response_includes_point_id_and_inspection_metadata(monkeypatch) -> None:
    async def mock_embed_texts(*args, **kwargs):
        return [[0.1, 0.2]]

    candidate = {
        "point_id": "stored-point",
        "document_id": "doc-1",
        "chunk_id": "doc-1:0",
        "text": "Existing text",
        "score": 0.8,
    }
    monkeypatch.setattr(main, "increment_metric", lambda name: 1)
    monkeypatch.setattr(main, "embed_texts", mock_embed_texts)
    monkeypatch.setattr(main, "search_document_chunks", lambda *args, **kwargs: [candidate])
    monkeypatch.setattr(main, "rerank", lambda *args, **kwargs: ([candidate], 1.25))
    operation_events = []
    monkeypatch.setattr(main, "save_operation_event", operation_events.append)

    response = client.post("/search", json={"query": "find source", "limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["point_id"] == "stored-point"
    assert body["results"][0]["chunk_id"] == "doc-1:0"
    assert response.headers["x-retrieval-method"] == "dense_vector"
    assert float(response.headers["x-retrieval-latency-ms"]) >= 0
    assert body["candidate_count"] == 1
    assert body["reranking_latency_ms"] == 1.25
    assert len(operation_events) == 1
    assert operation_events[0]["request_id"] == response.headers["x-request-id"]
    assert operation_events[0]["operation"] == "search"
    assert operation_events[0]["embedding_latency_ms"] >= 0
    assert operation_events[0]["vector_retrieval_latency_ms"] >= 0


def test_settings_response_does_not_expose_secrets(monkeypatch, tmp_path) -> None:
    secrets = {
        "LLM_API_KEY": "llm-secret-value",
        "EMBEDDING_API_KEY": "embedding-secret-value",
        "QDRANT_API_KEY": "qdrant-secret-value",
        "QDRANT_URL": "https://user:password@example.test:6333",
        "DATABASE_PATH": str(tmp_path / "private" / "database.sqlite"),
    }
    for key, value in secrets.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(main, "database_status", lambda: "unavailable")

    response = client.get("/settings")

    assert response.status_code == 200
    for secret in secrets.values():
        assert secret not in response.text
    settings = response.json()
    assert settings["llm"]["credentials"] == "Configured"
    assert settings["vector_database"]["host"] == "example.test"
    assert settings["database"]["configured"] == "yes"
    assert settings["database"]["status"] == "unavailable"


def test_settings_report_runtime_embedding_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")

    response = client.get("/settings")

    assert response.status_code == 200
    settings = response.json()
    assert settings["llm"]["provider"] == "gemini"
    assert settings["embeddings"]["provider"] == "gemini"


def test_human_judgments_validate_identifiers_without_claiming_provenance(monkeypatch, tmp_path) -> None:
    judgment_path = tmp_path / "judgement.json"
    judgment_path.write_text(json.dumps({
        "query_id": "Q001",
        "query": "Example question?",
        "relevant_chunks": {"doc-1:0": 3},
    }), encoding="utf-8")
    monkeypatch.setenv("HUMAN_JUDGMENTS_PATH", str(judgment_path))
    monkeypatch.setattr(
        main,
        "get_point_by_chunk_id",
        lambda chunk_id: {
            "point_id": "point-1",
            "document_id": "doc-1",
            "chunk_id": chunk_id,
            "text": "Supporting source text",
        },
    )

    response = client.get("/evaluations/human-judgments")

    assert response.status_code == 200
    body = response.json()
    assert body["identifier_validation"] == "passed"
    assert body["human_review_provenance"] == "not_recorded_in_file"
    assert body["relevant_chunks"][0]["point_id"] == "point-1"
    assert body["relevant_chunks"][0]["relevance_grade"] == 3
