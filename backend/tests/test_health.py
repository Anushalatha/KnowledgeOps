from fastapi.testclient import TestClient

from app.main import app
from app.storage import load_documents, save_document

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "knowledgeops-api"}


def test_service_health_endpoint() -> None:
    response = client.get("/health/services")

    assert response.status_code == 200
    assert response.json()["api"] == "operational"
    assert "qdrant" in response.json()


def test_upload_pdf_document() -> None:
    response = client.post(
        "/documents",
        files={"file": ("sample.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "sample.pdf"
    assert payload["file_type"] == "pdf"
    assert payload["status"] == "uploaded"
    assert payload["file_size"] > 0
    assert "document_id" in payload
    assert "created_at" in payload


def test_rejects_non_pdf_upload() -> None:
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400


def test_extracts_text_from_uploaded_pdf() -> None:
    response = client.post(
        "/documents",
        files={"file": ("summary.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", "application/pdf")},
    )

    document_id = response.json()["document_id"]
    content_response = client.get(f"/documents/{document_id}/content")

    assert content_response.status_code == 200
    payload = content_response.json()
    assert payload["document_id"] == document_id
    assert "text" in payload
    assert payload["word_count"] > 0


def test_chunks_uploaded_document() -> None:
    response = client.post(
        "/documents",
        files={"file": ("chunked.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", "application/pdf")},
    )

    document_id = response.json()["document_id"]
    chunks_response = client.get(
        f"/documents/{document_id}/chunks",
        params={"chunk_size": 10, "overlap": 2},
    )

    assert chunks_response.status_code == 200
    payload = chunks_response.json()
    assert payload["chunk_count"] > 0
    assert payload["chunks"][0]["chunk_id"].startswith(document_id)


def test_rejects_invalid_chunk_parameters() -> None:
    upload_response = client.post(
        "/documents",
        files={"file": ("invalid-chunks.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", "application/pdf")},
    )

    document_id = upload_response.json()["document_id"]
    response = client.get(
        f"/documents/{document_id}/chunks",
        params={"chunk_size": 10, "overlap": 10},
    )

    assert response.status_code == 400


def test_embeddings_require_configuration(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    upload_response = client.post(
        "/documents",
        files={"file": ("embedding-config.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", "application/pdf")},
    )

    document_id = upload_response.json()["document_id"]
    response = client.post(f"/documents/{document_id}/embeddings")

    assert response.status_code == 503


def test_search_requires_embedding_configuration(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    response = client.post("/search", json={"query": "retrieval architecture"})

    assert response.status_code == 503


def test_ask_requires_embedding_configuration(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    response = client.post("/ask", json={"query": "What is retrieval?"})

    assert response.status_code == 503


def test_document_storage_round_trip(monkeypatch, tmp_path) -> None:
    database = tmp_path / "documents.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    document = {
        "document_id": "persistent-document",
        "filename": "persistent.pdf",
        "file_type": "pdf",
        "file_size": 42,
        "status": "uploaded",
        "created_at": "2026-09-18T00:00:00+00:00",
        "content": "Persistent extracted content.",
    }

    save_document(document)

    assert load_documents() == [document]


def test_delete_document() -> None:
    response = client.post(
        "/documents",
        files={"file": ("delete-me.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )
    document_id = response.json()["document_id"]

    delete_response = client.delete(f"/documents/{document_id}")

    assert delete_response.status_code == 204
    assert client.get(f"/documents/{document_id}/content").status_code == 404


def test_query_metric_persists(monkeypatch, tmp_path) -> None:
    from app.storage import get_metric, increment_metric

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "metrics.db"))

    assert increment_metric("queries") == 1
    assert increment_metric("queries") == 2
    assert get_metric("queries") == 2


def test_collections_endpoint() -> None:
    response = client.get("/collections")

    assert response.status_code == 200
    assert "collections" in response.json()


def test_index_pending_requires_embedding_configuration(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    response = client.post("/documents/index-pending")

    assert response.status_code == 503


def test_monitoring_endpoint() -> None:
    response = client.get("/monitoring")

    assert response.status_code == 200
    payload = response.json()
    assert "documents" in payload
    assert "collection" in payload
    assert "health" in payload


def test_evaluations_endpoint_lists_runs() -> None:
    response = client.get("/evaluations")

    assert response.status_code == 200
    payload = response.json()
    assert "runs" in payload


def test_evaluation_service_calculates_retrieval_metrics() -> None:
    import asyncio
    from app.evaluations import EvaluationRunRequest, run_evaluation

    async def retrieve(question: str, limit: int) -> list[dict]:
        return [
            {"document_id": "other", "filename": "other.pdf", "chunk_id": "other:0", "score": 0.9},
            {"document_id": "target", "filename": "guide.pdf", "chunk_id": "target:0", "score": 0.8},
        ]

    async def generate(question: str, sources: list[dict]) -> str:
        return "A supported answer [1]."

    result = asyncio.run(run_evaluation(
        EvaluationRunRequest(cases=[{"question": "How?", "relevant_filename": "guide.pdf"}]),
        retrieve,
        generate,
    ))

    assert result["summary"]["retrieval_hit_rate"] == 1.0
    assert result["summary"]["mean_reciprocal_rank"] == 0.5
    assert result["cases"][0]["relevant_rank"] == 2


def test_reranker_blends_vector_and_lexical_scores() -> None:
    from app.reranking import rerank

    results, latency_ms = rerank(
        "deployment checklist",
        [
            {"chunk_id": "a", "score": 0.9, "text": "General platform overview."},
            {"chunk_id": "b", "score": 0.8, "text": "Deployment checklist for release."},
        ],
        final_count=1,
    )

    assert results[0]["chunk_id"] == "b"
    assert results[0]["retrieval_score"] == 0.8
    assert results[0]["reranking_score"] > results[0]["retrieval_score"]
    assert latency_ms >= 0


def test_evaluation_dataset_storage_round_trip(monkeypatch, tmp_path) -> None:
    from app.storage import load_evaluation_datasets, save_evaluation_dataset

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "evaluations.db"))
    dataset = {
        "dataset_id": "dataset-1",
        "name": "Release documentation",
        "created_at": "2026-09-18T00:00:00+00:00",
        "cases": [{"question": "What is the release process?", "relevant_filename": "guide.pdf"}],
    }
    save_evaluation_dataset(dataset)

    assert load_evaluation_datasets() == [dataset]


def test_request_metrics_track_errors_and_latency(monkeypatch, tmp_path) -> None:
    from app.storage import get_request_metrics, save_request_event

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "requests.db"))
    save_request_event({
        "request_id": "ok", "method": "GET", "path": "/health", "status_code": 200,
        "latency_ms": 10.0, "created_at": "2026-09-18T00:00:00+00:00",
    })
    save_request_event({
        "request_id": "bad", "method": "POST", "path": "/ask", "status_code": 502,
        "latency_ms": 30.0, "created_at": "2026-09-18T00:00:00+00:00",
    })

    assert get_request_metrics() == {"requests": 2, "errors": 1, "success_rate": 0.5, "average_latency_ms": 20.0}
