from __future__ import annotations

import hashlib
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import backfill_metadata, main, vector_store
from app.chunking import chunk_pages
from app.metadata import document_chunks
from app.vector_store import build_metadata_filter, search_document_chunks


class MemoryQdrant:
    def __init__(self) -> None:
        self.points = [
            SimpleNamespace(
                id="point-alpha-1",
                score=0.9,
                payload={
                    "document_id": "doc-alpha-1",
                    "document_name": "alpha.pdf",
                    "filename": "alpha.pdf",
                    "chunk_id": "doc-alpha-1:0",
                    "text": "Alpha project evidence.",
                    "project_name": "alpha",
                    "category": "architecture",
                    "source_type": "pdf",
                    "page_number": 1,
                },
            ),
            SimpleNamespace(
                id="point-beta",
                score=0.8,
                payload={
                    "document_id": "doc-beta",
                    "document_name": "beta.pdf",
                    "filename": "beta.pdf",
                    "chunk_id": "doc-beta:0",
                    "text": "Beta project evidence.",
                    "project_name": "beta",
                    "category": "architecture",
                    "source_type": "pdf",
                    "page_number": 2,
                },
            ),
            SimpleNamespace(
                id="point-alpha-2",
                score=0.7,
                payload={
                    "document_id": "doc-alpha-2",
                    "document_name": "alpha-notes.pdf",
                    "filename": "alpha-notes.pdf",
                    "chunk_id": "doc-alpha-2:0",
                    "text": "Additional alpha evidence.",
                    "project_name": "alpha",
                    "category": "guide",
                    "source_type": "pdf",
                    "page_number": 1,
                },
            ),
            SimpleNamespace(
                id="point-legacy",
                score=0.6,
                payload={
                    "document_id": "legacy-doc",
                    "filename": "legacy.pdf",
                    "chunk_id": "legacy-doc:0",
                    "text": "Legacy point without optional metadata.",
                },
            ),
        ]
        self.last_query_filter: Any = None

    def collection_exists(self, name: str) -> bool:
        assert name == "knowledgeops_documents"
        return True

    def query_points(self, **kwargs: Any) -> SimpleNamespace:
        self.last_query_filter = kwargs["query_filter"]
        conditions = self.last_query_filter.must if self.last_query_filter else []
        results = []
        for point in self.points:
            payload = point.payload
            matches = True
            for condition in conditions:
                match = condition.match
                if hasattr(match, "any"):
                    matches = matches and payload.get(condition.key) in match.any
                else:
                    matches = matches and payload.get(condition.key) == match.value
            if matches:
                results.append(point)
        return SimpleNamespace(points=results[: kwargs["limit"]])


@pytest.fixture
def memory_qdrant(monkeypatch: pytest.MonkeyPatch) -> MemoryQdrant:
    client = MemoryQdrant()
    monkeypatch.setattr(vector_store, "get_client", lambda: client)
    monkeypatch.setattr(vector_store, "collection_name", lambda: "knowledgeops_documents")
    return client


def test_global_retrieval_returns_points_from_all_projects_and_legacy(
    memory_qdrant: MemoryQdrant,
) -> None:
    results = search_document_chunks([0.1, 0.2], limit=10)

    assert len(results) == 4
    assert {result["document_id"] for result in results} == {
        "doc-alpha-1",
        "doc-beta",
        "doc-alpha-2",
        "legacy-doc",
    }
    assert memory_qdrant.last_query_filter is None


def test_project_filter_matches_normalized_project_name(
    memory_qdrant: MemoryQdrant,
) -> None:
    results = search_document_chunks([0.1], project_name="  ALPHA  ")

    assert {result["document_id"] for result in results} == {"doc-alpha-1", "doc-alpha-2"}


def test_multi_project_filter_returns_all_requested_projects(
    memory_qdrant: MemoryQdrant,
) -> None:
    results = search_document_chunks([0.1], project_names=["alpha", " BETA "])

    assert {result["document_id"] for result in results} == {
        "doc-alpha-1",
        "doc-alpha-2",
        "doc-beta",
    }


def test_document_filter_returns_only_requested_document(
    memory_qdrant: MemoryQdrant,
) -> None:
    results = search_document_chunks([0.1], document_id="doc-beta")

    assert [result["document_id"] for result in results] == ["doc-beta"]


def test_category_and_source_type_filters_are_applied_together(
    memory_qdrant: MemoryQdrant,
) -> None:
    results = search_document_chunks(
        [0.1],
        category=" ARCHITECTURE ",
        source_type=" PDF ",
    )

    assert {result["document_id"] for result in results} == {"doc-alpha-1", "doc-beta"}


def test_missing_metadata_is_included_globally_but_not_in_filtered_results(
    memory_qdrant: MemoryQdrant,
) -> None:
    global_results = search_document_chunks([0.1], limit=10)
    alpha_results = search_document_chunks([0.1], project_name="alpha")

    assert any(result["document_id"] == "legacy-doc" for result in global_results)
    assert all(result["document_id"] != "legacy-doc" for result in alpha_results)
    assert build_metadata_filter() is None


def test_page_chunking_preserves_page_attribution() -> None:
    pages = [
        {"page_number": 1, "text": "one two three four"},
        {"page_number": 2, "text": "five six seven eight"},
    ]

    assert chunk_pages(pages, chunk_size=2, overlap=0) == [
        ("one two", 1),
        ("three four", 1),
        ("five six", 2),
        ("seven eight", 2),
    ]
    assert document_chunks({"content": "legacy content"}, 10, 0) == (
        ["legacy content"],
        [None],
    )


def test_pdf_upload_stores_project_metadata_and_page_attribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self.text = text

        def extract_text(self) -> str:
            return self.text

    class FakeReader:
        def __init__(self, _file: Any) -> None:
            self.pages = [FakePage("alpha beta gamma"), FakePage(""), FakePage("delta epsilon")]

    monkeypatch.setattr(main, "PdfReader", FakeReader)
    client = TestClient(main.app)
    response = client.post(
        "/documents",
        files={"file": ("sample.pdf", b"pdf-bytes", "application/pdf")},
        data={"project_name": "My Project", "category": "Reference Docs"},
    )
    document_id = response.json()["document_id"]
    try:
        assert response.status_code == 200
        assert response.json()["project_name"] == "my project"
        assert response.json()["category"] == "reference docs"
        assert "page_texts" not in response.json()

        chunks_response = client.get(
            f"/documents/{document_id}/chunks",
            params={"chunk_size": 2, "overlap": 0},
        )
        chunks = chunks_response.json()["chunks"]
        assert [chunk["page_number"] for chunk in chunks] == [1, 1, 3]
        assert all(chunk["page_number"] is not None for chunk in chunks)
        assert all(
            "page_texts" not in document
            for document in client.get("/documents").json()
            if document["document_id"] == document_id
        )
    finally:
        main.DOCUMENTS.pop(document_id, None)


def test_backfill_updates_only_existing_payloads_and_preserves_unknowns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BackfillClient:
        def __init__(self) -> None:
            self.points = [
                SimpleNamespace(
                    id="existing-1",
                    payload={
                        "document_id": "known",
                        "filename": "known.pdf",
                        "chunk_id": "known:0",
                        "text": "known chunk",
                    },
                ),
                SimpleNamespace(
                    id="existing-2",
                    payload={
                        "document_id": "unmatched",
                        "filename": "unmatched.pdf",
                        "chunk_id": "unmatched:0",
                        "text": "unmatched chunk",
                    },
                ),
            ]
            self.updated: list[tuple[str, dict[str, Any]]] = []

        def collection_exists(self, name: str) -> bool:
            return name == "knowledgeops_documents"

        def scroll(self, **kwargs: Any) -> tuple[list[Any], None]:
            assert kwargs["with_vectors"] is False
            return self.points, None

        def set_payload(self, **kwargs: Any) -> None:
            for point_id in kwargs["points"]:
                self.updated.append((point_id, kwargs["payload"]))
                point = next(point for point in self.points if point.id == point_id)
                point.payload.update(kwargs["payload"])

    client = BackfillClient()
    monkeypatch.setattr(backfill_metadata, "get_client", lambda: client)
    monkeypatch.setattr(backfill_metadata, "collection_name", lambda: "knowledgeops_documents")
    summary = backfill_metadata.backfill_collection_metadata(
        [
            {
                "document_id": "known",
                "filename": "known.pdf",
                "file_type": "pdf",
                "created_at": "2026-10-01T00:00:00+00:00",
            }
        ]
    )

    assert summary["scanned_points"] == 2
    assert summary["updated_points"] == 2
    assert len(client.updated) == 2
    assert all("project_name" in point.payload for point in client.points)
    assert all("category" in point.payload for point in client.points)
    assert all("page_number" in point.payload for point in client.points)
    assert client.points[0].payload["uploaded_at"] == "2026-10-01T00:00:00+00:00"
    assert client.points[1].payload["uploaded_at"] == "unknown"
    assert client.points[0].payload["project_name"] == "unknown"
    assert client.points[0].payload["page_number"] == "unknown"
    assert client.points[0].payload["content_hash"] == hashlib.sha256(
        b"known chunk"
    ).hexdigest()
    assert summary["unavailable_values"]["project_name"] == 2
    assert summary["unavailable_values"]["page_number"] == 2
    assert summary["unavailable_values"]["uploaded_at"] == 1
    recovered_page = backfill_metadata._document_value(
        {"text": "unique text on page 2"},
        {
            "page_texts": [
                {"page_number": 1, "text": "content on page one"},
                {"page_number": 2, "text": "unique text on page 2"},
            ]
        },
        "page_number",
    )
    assert recovered_page == 2
    assert (
        backfill_metadata._document_value(
            {"text": "foo"},
            {"page_texts": [{"page_number": 1, "text": "foobar"}]},
            "page_number",
        )
        is None
    )
    assert (
        backfill_metadata._document_value(
            {"text": "repeated chunk"},
            {
                "page_texts": [
                    {"page_number": 1, "text": "repeated chunk"},
                    {"page_number": 2, "text": "repeated chunk"},
                ]
            },
            "page_number",
        )
        is None
    )
    second_run = backfill_metadata.backfill_collection_metadata(
        [
            {
                "document_id": "known",
                "filename": "known.pdf",
                "file_type": "pdf",
                "created_at": "2026-10-01T00:00:00+00:00",
            }
        ]
    )
    assert second_run["updated_points"] == 0


def test_backfill_refuses_to_target_another_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RefusingClient:
        def collection_exists(self, name: str) -> bool:
            raise AssertionError("A mismatched collection must not be accessed.")

    monkeypatch.setattr(backfill_metadata, "get_client", lambda: RefusingClient())
    monkeypatch.setattr(backfill_metadata, "collection_name", lambda: "different_collection")

    with pytest.raises(vector_store.VectorStoreError, match="expected the existing"):
        backfill_metadata.backfill_collection_metadata([])


@pytest.mark.parametrize(
    ("path", "request_body", "expected_keys"),
    [
        (
            "/search",
            {"query": "find alpha", "project_names": ["Alpha", "Beta"]},
            {"query", "count", "candidate_count", "reranker", "reranking_latency_ms", "results"},
        ),
        (
            "/ask",
            {"query": "find alpha", "document_name": "alpha.pdf"},
            {
                "question",
                "answer",
                "model",
                "request_id",
                "retrieved_chunks",
                "candidate_count",
                "reranker",
                "latency",
                "citations",
                "retrieved_sources",
            },
        ),
        (
            "/search",
            {"query": "global retrieval"},
            {"query", "count", "candidate_count", "reranker", "reranking_latency_ms", "results"},
        ),
    ],
)
def test_existing_retrieval_apis_forward_optional_filters_without_changing_response_shape(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    request_body: dict[str, Any],
    expected_keys: set[str],
) -> None:
    captured_filters: list[dict[str, Any]] = []

    async def fake_embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
        return [[0.1, 0.2]]

    def fake_search(vector: list[float], limit: int, **filters: Any) -> list[dict[str, Any]]:
        captured_filters.append(filters)
        return [
            {
                "document_id": "doc-alpha-1",
                "filename": "alpha.pdf",
                "document_name": "alpha.pdf",
                "chunk_id": "doc-alpha-1:0",
                "text": "Alpha evidence.",
                "score": 0.9,
            }
        ]

    def fake_rerank(query: str, candidates: list[dict[str, Any]], limit: int):
        return candidates[:limit], 0.1

    async def fake_generate(question: str, sources: list[dict[str, Any]]) -> str:
        return "Grounded answer [1]."

    monkeypatch.setattr(main, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(main, "search_document_chunks", fake_search)
    monkeypatch.setattr(main, "rerank", fake_rerank)
    monkeypatch.setattr(main, "generate_grounded_answer", fake_generate)

    response = TestClient(main.app).post(path, json=request_body)

    assert response.status_code == 200
    assert set(response.json()) == expected_keys
    if path == "/search":
        if "project_names" in request_body:
            assert captured_filters[0]["project_names"] == ["alpha", "beta"]
        else:
            assert captured_filters[0] == {}
    else:
        assert captured_filters[0]["document_name"] == "alpha.pdf"
