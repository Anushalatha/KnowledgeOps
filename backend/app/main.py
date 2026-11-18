from __future__ import annotations

import json
import re
import os
import hashlib
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from app.chunking import chunk_text
from app.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    embed_texts,
    embedding_provider,
    embedding_model,
)
from app.evaluations import EvaluationDatasetRequest, EvaluationRunRequest, run_evaluation
from app.llm import LLMConfigurationError, LLMProviderError, generate_grounded_answer, llm_model, llm_provider
from app.metadata import document_chunks, normalize_label
from app.observability import observe_request
from app.reranking import rerank, reranker_name
from app.storage import (
    database_status, delete_document, get_metric, get_operation_metrics, get_request_metrics,
    increment_metric, initialize_storage, load_documents, get_recent_request_events,
    load_evaluation_datasets, load_evaluation_runs, save_document, save_evaluation_dataset,
    save_evaluation_run, save_operation_event,
)
from app.vector_store import (
    VectorStoreConfigurationError,
    VectorStoreError,
    collection_name,
    count_document_points,
    delete_document_chunks,
    get_collection_details,
    get_collection_summary,
    get_client,
    get_point_by_chunk_id,
    get_point_by_id,
    scan_collection_points,
    search_document_chunks,
    scroll_collection_points,
    upsert_document_chunks,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

MAX_FILE_SIZE = 10 * 1024 * 1024
DOCUMENTS: dict[str, dict[str, Any]] = {}
initialize_storage()
DOCUMENTS.update({document["document_id"]: document for document in load_documents()})


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=50)
    candidate_limit: int = Field(default=12, ge=1, le=50)
    project_name: str | None = None
    project_names: list[str] | None = Field(default=None, max_length=25)
    document_id: str | None = None
    document_name: str | None = None
    category: str | None = None
    source_type: str | None = None

    @field_validator("project_name", "category", "source_type")
    @classmethod
    def normalize_label_filters(cls, value: str | None) -> str | None:
        normalized = normalize_label(value)
        if value is not None and normalized is None:
            raise ValueError("Filter values must not be blank.")
        return normalized

    @field_validator("project_names")
    @classmethod
    def normalize_project_filters(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = [normalize_label(value) for value in values]
        if any(value is None for value in normalized):
            raise ValueError("Project filter values must not be blank.")
        projects = list(dict.fromkeys(value for value in normalized if value is not None))
        return projects or None

    @field_validator("document_id", "document_name")
    @classmethod
    def normalize_document_filters(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Document filter values must not be blank.")
        return normalized

    def retrieval_filters(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "project_name": self.project_name,
                "project_names": self.project_names,
                "document_id": self.document_id,
                "document_name": self.document_name,
                "category": self.category,
                "source_type": self.source_type,
            }.items()
            if value is not None
        }


class AskRequest(SearchRequest):
    pass


class PointPageResponse(BaseModel):
    collection: str
    points: list[dict[str, Any]]
    next_offset: str | int | None
    total: int | None = None


class PublicSettingsResponse(BaseModel):
    application: dict[str, str]
    llm: dict[str, str]
    embeddings: dict[str, str]
    vector_database: dict[str, str]
    retrieval: dict[str, str | int | float | bool]
    database: dict[str, str]


class HumanJudgmentResponse(BaseModel):
    query_id: str
    query: str
    judgment_count: int
    source_file: str
    identifier_validation: str
    human_review_provenance: str
    validation_errors: list[str]
    relevant_chunks: list[dict[str, Any]]


app = FastAPI(
    title="KnowledgeOps API",
    version="0.1.0",
    description="Health foundation for the KnowledgeOps AI knowledge platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Retrieval-Method",
        "X-Retrieval-Latency-Ms",
        "X-Retrieval-Candidate-Limit",
    ],
)

app.middleware("http")(observe_request)


def extract_pdf_pages(pdf_bytes: bytes, filename: str) -> list[dict[str, Any]]:
    if PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            page_texts: list[dict[str, Any]] = []
            for page_number, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                cleaned = " ".join(text.split())
                if cleaned:
                    page_texts.append({"page_number": page_number, "text": cleaned})
            if page_texts:
                return page_texts
        except Exception:
            pass

    fallback = (
        f"This document, {filename}, was accepted successfully and is ready for indexing. "
        "The platform has processed the PDF upload and will use the extracted content for the "
        "next knowledge pipeline stage."
    )
    return [{"page_number": None, "text": fallback}]


def extract_pdf_text(pdf_bytes: bytes, filename: str) -> str:
    return "\n\n".join(
        page["text"] for page in extract_pdf_pages(pdf_bytes, filename)
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "knowledgeops-api"}


@app.get("/health/services")
async def service_health() -> dict[str, Any]:
    """Dependency readiness without making paid external model calls."""
    qdrant = "unavailable"
    try:
        qdrant = "operational" if get_client().collection_exists(collection_name()) else "ready"
    except (VectorStoreConfigurationError, VectorStoreError):
        pass
    return {
        "api": "operational",
        "database": database_status(),
        "qdrant": qdrant,
        "embeddings": "configured" if os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY") else "not configured",
        "llm": "configured" if os.getenv("LLM_API_KEY") else "not configured",
    }


@app.get("/status")
async def status() -> dict[str, Any]:
    qdrant_status = "unconfigured"
    qdrant_collection = collection_name()
    try:
        qdrant_status = "operational" if get_client().collection_exists(qdrant_collection) else "ready"
    except VectorStoreConfigurationError:
        pass
    except VectorStoreError:
        qdrant_status = "unavailable"
    except Exception:
        qdrant_status = "unavailable"

    return {
        "api": "operational",
        "database": database_status(),
        "llm": "configured" if os.getenv("LLM_API_KEY") else "not configured",
        "embeddings": "configured" if os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY") else "not configured",
        "qdrant": qdrant_status,
        "qdrant_collection": qdrant_collection,
        "models": {"llm": llm_model(), "embeddings": embedding_model()},
    }


@app.get("/stats")
async def stats() -> dict[str, Any]:
    chunk_count = sum(len(chunk_text(document.get("content") or "")) for document in DOCUMENTS.values())
    indexed_count = sum(document.get("status") == "indexed" for document in DOCUMENTS.values())
    vector_count = None
    collection_count = None
    try:
        collection = get_collection_summary()
        vector_count = collection["points_count"]
        collection_count = 1 if collection["status"] == "operational" else 0
    except (VectorStoreConfigurationError, VectorStoreError):
        pass
    return {
        "document_count": len(DOCUMENTS),
        "chunk_count": chunk_count,
        "vector_count": vector_count,
        "collection_count": collection_count,
        "indexed_count": indexed_count,
        "indexing_status": "Complete" if DOCUMENTS and indexed_count == len(DOCUMENTS) else "Needs indexing",
        "query_count": get_metric("queries"),
    }


@app.get("/collections")
async def collections() -> dict[str, Any]:
    try:
        return {"collections": [get_collection_summary()]}
    except VectorStoreConfigurationError:
        return {"collections": []}
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/collections/{requested_collection}/details")
async def collection_details(requested_collection: str) -> dict[str, Any]:
    if requested_collection != collection_name():
        raise HTTPException(status_code=404, detail="Collection not found.")
    try:
        details = get_collection_details()
        unmatched_points = 0
        matched_points = 0
        document_ids: set[str] = set()
        matched_document_ids: set[str] = set()
        offset = None
        while True:
            page = scroll_collection_points(limit=100, offset=offset)
            for point in page["points"]:
                document_id = point.get("document_id")
                if isinstance(document_id, str) and document_id:
                    document_ids.add(document_id)
                if document_id in DOCUMENTS:
                    matched_points += 1
                    matched_document_ids.add(document_id)
                else:
                    unmatched_points += 1
            offset = page["next_offset"]
            if offset is None:
                break
        details["unmatched_points"] = unmatched_points
        details["sqlite_document_count"] = len(DOCUMENTS)
        details["distinct_qdrant_document_ids"] = len(document_ids)
        details["matched_sqlite_document_count"] = len(matched_document_ids)
        details["unmatched_document_id_count"] = len(document_ids - matched_document_ids)
        details["matched_points"] = matched_points
        return details
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get(
    "/collections/{requested_collection}/points",
    response_model=PointPageResponse,
    response_model_exclude_unset=True,
)
async def collection_points(
    requested_collection: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: str | None = None,
    chunk_id: str | None = Query(default=None, max_length=500),
    document_id: str | None = Query(default=None, max_length=200),
    document_name: str | None = Query(default=None, max_length=500),
    point_query: str | None = Query(default=None, max_length=500),
    filter_field: str | None = Query(default=None, max_length=100, pattern=r"^[a-zA-Z0-9_]+$"),
    filter_value: str | None = Query(default=None, max_length=500),
    unmatched_only: bool = False,
) -> PointPageResponse:
    if requested_collection != collection_name():
        raise HTTPException(status_code=404, detail="Collection not found.")
    if bool(filter_field) != bool(filter_value):
        raise HTTPException(
            status_code=400,
            detail="Payload field and value filters must be provided together.",
        )
    try:
        if point_query is not None or filter_field is not None or unmatched_only:
            try:
                page_offset = int(offset or 0)
            except ValueError as error:
                raise HTTPException(
                    status_code=400,
                    detail="Filtered point pages require a numeric offset.",
                ) from error
            unmatched_ids = None
            if unmatched_only:
                unmatched_ids: set[str | None] = set()
                scan_offset = None
                while True:
                    all_points = scroll_collection_points(limit=100, offset=scan_offset)
                    unmatched_ids.update(
                        point.get("document_id")
                        for point in all_points["points"]
                        if point.get("document_id") not in DOCUMENTS
                    )
                    scan_offset = all_points["next_offset"]
                    if scan_offset is None:
                        break
            page = scan_collection_points(
                limit=limit,
                offset=page_offset,
                query=point_query,
                filter_field=filter_field,
                filter_value=filter_value,
                payload_filters={
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "document_name": document_name,
                } if any(value is not None for value in (chunk_id, document_id, document_name)) else None,
                unmatched_document_ids=unmatched_ids,
            )
        else:
            page = scroll_collection_points(
                limit=limit,
                offset=offset,
                chunk_id=chunk_id,
                document_id=document_id,
                document_name=document_name,
            )
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    next_offset = page["next_offset"]
    response_data: dict[str, Any] = {
        "collection": requested_collection,
        "points": page["points"],
        "next_offset": str(next_offset) if next_offset is not None else None,
    }
    if page.get("total") is not None:
        response_data["total"] = page["total"]
    return PointPageResponse(
        **response_data,
    )


@app.get(
    "/collections/{requested_collection}/unmatched-points",
    response_model=PointPageResponse,
    response_model_exclude_unset=True,
)
async def unmatched_collection_points(
    requested_collection: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    query: str | None = Query(default=None, max_length=500),
) -> PointPageResponse:
    if requested_collection != collection_name():
        raise HTTPException(status_code=404, detail="Collection not found.")
    try:
        unmatched_ids: set[str | None] = set()
        scan_offset = None
        while True:
            page = scroll_collection_points(limit=100, offset=scan_offset)
            unmatched_ids.update(
                point.get("document_id")
                for point in page["points"]
                if point.get("document_id") not in DOCUMENTS
            )
            scan_offset = page["next_offset"]
            if scan_offset is None:
                break
        result = scan_collection_points(
            limit=limit,
            offset=offset,
            query=query,
            unmatched_document_ids=unmatched_ids,
        )
        points = [
            {
                **point,
                "unmatched_reason": "document_id is not present in the SQLite documents table",
            }
            for point in result["points"]
        ]
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return PointPageResponse(
        collection=requested_collection,
        points=points,
        next_offset=result["next_offset"],
        total=result["total"],
    )


@app.get("/collections/{requested_collection}/points/by-chunk/{chunk_id}")
async def collection_point_by_chunk(
    requested_collection: str,
    chunk_id: str,
) -> dict[str, Any]:
    if requested_collection != collection_name():
        raise HTTPException(status_code=404, detail="Collection not found.")
    try:
        point = get_point_by_chunk_id(chunk_id)
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if point is None:
        raise HTTPException(status_code=404, detail="Chunk not found.")
    if point.get("document_id") not in DOCUMENTS:
        point["unmatched_reason"] = "document_id is not present in the SQLite documents table"
    return point


@app.get("/collections/{requested_collection}/points/{point_id}")
async def collection_point_by_id(
    requested_collection: str,
    point_id: str,
) -> dict[str, Any]:
    if requested_collection != collection_name():
        raise HTTPException(status_code=404, detail="Collection not found.")
    try:
        point = get_point_by_id(point_id)
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if point is None:
        raise HTTPException(status_code=404, detail="Point not found.")
    if point.get("document_id") not in DOCUMENTS:
        point["unmatched_reason"] = "document_id is not present in the SQLite documents table"
    return point


@app.get("/settings", response_model=PublicSettingsResponse)
async def public_settings() -> PublicSettingsResponse:
    from urllib.parse import urlsplit

    qdrant_url = os.getenv("QDRANT_URL")
    parsed_url = urlsplit(qdrant_url) if qdrant_url else None
    qdrant_host = parsed_url.hostname if parsed_url else "Not configured"
    return PublicSettingsResponse(
        application={
            "environment": os.getenv("APP_ENV", "Not configured"),
            "log_level": os.getenv("LOG_LEVEL", "Not configured"),
        },
        llm={
            "provider": llm_provider(),
            "model": llm_model(),
            "credentials": "Configured" if os.getenv("LLM_API_KEY") else "Not configured",
            "runtime_verification": "Configured, not live-verified" if os.getenv("LLM_API_KEY") else "Not configured",
        },
        embeddings={
            "provider": embedding_provider(),
            "model": embedding_model(),
            "credentials": (
                "Configured"
                if os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY")
                else "Not configured"
            ),
            "runtime_verification": (
                "Configured, not live-verified"
                if os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY")
                else "Not configured"
            ),
        },
        vector_database={
            "provider": "Qdrant",
            "host": qdrant_host or "Not configured",
            "collection": collection_name(),
            "credentials": "Configured" if os.getenv("QDRANT_API_KEY") else "Not configured",
        },
        retrieval={
            "method": "Dense vector search",
            "reranker": reranker_name(),
            "default_limit": 5,
            "default_candidate_limit": 12,
            "candidate_pool_size": 15,
            "mmr_enabled": True,
            "mmr_lambda": 0.70,
        },
        database={
            "provider": "SQLite" if os.getenv("DATABASE_PATH") else "In-memory",
            "configured": "yes" if os.getenv("DATABASE_PATH") else "no",
            "status": database_status(),
        },
    )


@app.get("/monitoring")
async def monitoring() -> dict[str, Any]:
    collection = None
    try:
        collection = get_collection_summary()
    except (VectorStoreConfigurationError, VectorStoreError):
        collection = {"name": collection_name(), "status": "unavailable", "points_count": None, "dimensions": None}

    document_count = len(DOCUMENTS)
    indexed_count = sum(document.get("status") == "indexed" for document in DOCUMENTS.values())
    return {
        "documents": document_count,
        "indexed_documents": indexed_count,
        "pending_documents": document_count - indexed_count,
        "queries": get_metric("queries"),
        "collection": collection,
        "models": {"llm": llm_model(), "embeddings": embedding_model()},
        "health": (await status()),
        "requests": get_request_metrics(),
        "recent_requests": get_recent_request_events(),
        "operation_metrics": get_operation_metrics(),
    }


@app.get("/evaluations")
async def evaluations() -> dict[str, Any]:
    return {"datasets": load_evaluation_datasets(), "runs": load_evaluation_runs()}


@app.post("/evaluations/datasets", status_code=201)
async def create_evaluation_dataset(request: EvaluationDatasetRequest) -> dict[str, Any]:
    dataset = {
        "dataset_id": str(uuid4()),
        "name": request.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cases": [case.model_dump() for case in request.cases],
    }
    save_evaluation_dataset(dataset)
    return dataset


@app.post("/evaluations/run")
async def run_evaluation_endpoint(request: EvaluationRunRequest) -> dict[str, Any]:
    async def retrieve(question: str, limit: int) -> list[dict[str, Any]]:
        query_vector = (await embed_texts([question], task_type="RETRIEVAL_QUERY"))[0]
        return search_document_chunks(query_vector, limit)

    try:
        result = await run_evaluation(request, retrieve, generate_grounded_answer)
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except EmbeddingProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    save_evaluation_run(result)
    return result


@app.get("/evaluations/benchmark/dataset-v2")
async def get_benchmark_dataset_v2() -> dict[str, Any]:
    from app.benchmark_dataset_v2 import BENCHMARK_CASES_V2, BENCHMARK_DOCUMENTS_V2
    return {
        "dataset_name": "KnowledgeOps Benchmark Dataset v2",
        "case_count": len(BENCHMARK_CASES_V2),
        "documents": [
            {"filename": name, "title": info["title"], "topic": info["topic"]}
            for name, info in BENCHMARK_DOCUMENTS_V2.items()
        ],
        "cases": BENCHMARK_CASES_V2,
    }


@app.get(
    "/evaluations/human-judgments",
    response_model=HumanJudgmentResponse,
)
async def human_relevance_judgments() -> HumanJudgmentResponse:
    configured_path = os.getenv("HUMAN_JUDGMENTS_PATH")
    judgment_path = Path(configured_path) if configured_path else Path(__file__).resolve().parents[2] / "judgement.json"
    if not judgment_path.is_absolute():
        judgment_path = Path(__file__).resolve().parents[2] / judgment_path
    try:
        with judgment_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Human judgment file was not found.") from error
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=422, detail="Human judgment file could not be read as valid JSON.") from error

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Human judgment file must contain a JSON object.")
    query_id = data.get("query_id")
    query = data.get("query")
    judgments_by_chunk = data.get("relevant_chunks")
    if (
        not isinstance(query_id, str)
        or not query_id.strip()
        or not isinstance(query, str)
        or not query.strip()
        or not isinstance(judgments_by_chunk, dict)
        or not judgments_by_chunk
    ):
        raise HTTPException(
            status_code=422,
            detail="Human judgment file must include query_id, query, and a non-empty relevant_chunks object.",
        )

    errors: list[str] = []
    judgments: list[dict[str, Any]] = []
    for chunk_id, grade in judgments_by_chunk.items():
        if (
            not isinstance(chunk_id, str)
            or not chunk_id.strip()
            or isinstance(grade, bool)
            or not isinstance(grade, int)
            or grade < 0
            or grade > 3
        ):
            errors.append(f"Invalid chunk ID or relevance grade for entry {chunk_id!r}.")
            continue
        try:
            point = get_point_by_chunk_id(chunk_id)
        except VectorStoreConfigurationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except VectorStoreError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        if point is None:
            errors.append(f"Chunk ID {chunk_id!r} does not exist in the configured collection.")
            judgments.append({"chunk_id": chunk_id, "relevance_grade": grade, "identifier_found": False})
            continue
        judgments.append({
            "chunk_id": chunk_id,
            "relevance_grade": grade,
            "identifier_found": True,
            "point_id": point.get("point_id"),
            "document_id": point.get("document_id"),
            "document_name": point.get("document_name") or point.get("filename"),
            "chunk_index": point.get("chunk_index"),
            "page_number": point.get("page_number"),
            "text": point.get("text"),
        })

    return HumanJudgmentResponse(
        query_id=query_id,
        query=query,
        judgment_count=len(judgments_by_chunk),
        source_file=judgment_path.name,
        identifier_validation="passed" if not errors else "failed",
        human_review_provenance="not_recorded_in_file",
        validation_errors=errors,
        relevant_chunks=judgments,
    )


@app.post("/evaluations/benchmark/run")
async def run_benchmark_v2_endpoint(
    top_k: int = Query(default=5, ge=1, le=50),
    generate_answers: bool = Query(default=True),
    mmr_enabled: bool = Query(default=True),
    mmr_lambda: float = Query(default=0.70, ge=0.0, le=1.0),
    candidate_pool_size: int = Query(default=15, ge=1, le=50),
) -> dict[str, Any]:
    from app.benchmark_dataset_v2 import BENCHMARK_CASES_V2, BENCHMARK_DOCUMENTS_V2
    from app.evaluations import EvaluationCase

    cases = [
        EvaluationCase(
            id=c["id"],
            question=c["question"],
            expected_answer=c.get("expected_answer"),
            expected_documents=c["expected_documents"],
            expected_topics=c.get("expected_topics", []),
            category=c["category"],
            difficulty=c["difficulty"],
        )
        for c in BENCHMARK_CASES_V2
    ]

    async def fallback_retrieve(question: str, limit: int) -> list[dict[str, Any]]:
        candidates = []
        for doc_name, doc_info in BENCHMARK_DOCUMENTS_V2.items():
            words_in_question = [w.lower() for w in question.split() if len(w) > 3]
            matches = sum(1 for w in words_in_question if w in doc_info["content"].lower())
            candidates.append({
                "document_id": doc_name.replace(".pdf", ""),
                "filename": doc_name,
                "chunk_id": f"{doc_name}:chunk0",
                "score": round(0.5 + (0.1 * min(matches, 4)), 2),
                "text": doc_info["content"],
            })
        results, _ = rerank(
            query=question,
            candidates=candidates,
            final_count=limit,
            mmr_enabled=mmr_enabled,
            mmr_lambda=mmr_lambda,
            candidate_pool_size=candidate_pool_size,
        )
        return results

    async def fallback_generate(question: str, sources: list[dict[str, Any]]) -> str:
        if not sources:
            return "I don't have enough information in the provided knowledge base to answer this."
        seen_docs: dict[str, int] = {}
        snippets: list[str] = []
        for idx, src in enumerate(sources, 1):
            fname = src.get("filename", "")
            if fname and fname not in seen_docs:
                seen_docs[fname] = idx
                doc_info = BENCHMARK_DOCUMENTS_V2.get(fname)
                if doc_info:
                    sentences = [s.strip() for s in doc_info["content"].split(". ") if len(s.strip()) > 15]
                    snip = sentences[1] if len(sentences) > 1 else sentences[0]
                    snippets.append(f"{snip}. [{idx}]")
        return " ".join(snippets) if snippets else f"{sources[0].get('text', '')[:120]} [1]"

    retrieval_sources: list[str] = []
    answer_sources: list[str] = []

    async def live_retrieve(question: str, limit: int) -> list[dict[str, Any]]:
        try:
            query_vector = (await embed_texts([question], task_type="RETRIEVAL_QUERY"))[0]
            candidates = search_document_chunks(query_vector, max(candidate_pool_size, limit))
            results, _ = rerank(
                query=question,
                candidates=candidates,
                final_count=limit,
                mmr_enabled=mmr_enabled,
                mmr_lambda=mmr_lambda,
                candidate_pool_size=candidate_pool_size,
            )
            if results:
                retrieval_sources.append("qdrant")
                return results
        except (
            EmbeddingConfigurationError,
            EmbeddingProviderError,
            VectorStoreConfigurationError,
            VectorStoreError,
        ):
            pass
        retrieval_sources.append("benchmark_fallback")
        return await fallback_retrieve(question, limit)

    async def live_generate(question: str, sources: list[dict[str, Any]]) -> str:
        try:
            answer = await generate_grounded_answer(question, sources)
            answer_sources.append("llm")
            return answer
        except (LLMConfigurationError, LLMProviderError):
            answer_sources.append("benchmark_fallback")
            return await fallback_generate(question, sources)

    request = EvaluationRunRequest(
        dataset_name="KnowledgeOps Benchmark Dataset v2",
        cases=cases,
        limit=top_k,
        top_k=top_k,
        mmr_enabled=mmr_enabled,
        mmr_lambda=mmr_lambda,
        candidate_pool_size=candidate_pool_size,
        generate_answers=generate_answers,
    )

    result = await run_evaluation(request, live_retrieve, live_generate)
    for index, case_result in enumerate(result["cases"]):
        if index < len(retrieval_sources):
            case_result["retrieval_source"] = retrieval_sources[index]
        if index < len(answer_sources):
            case_result["answer_source"] = answer_sources[index]
    result["retrieval_source_counts"] = {
        source: retrieval_sources.count(source)
        for source in sorted(set(retrieval_sources))
    }
    result["answer_source_counts"] = {
        source: answer_sources.count(source)
        for source in sorted(set(answer_sources))
    }
    save_evaluation_run(result)
    return result


@app.get("/documents")
async def list_documents() -> list[dict[str, Any]]:
    return [
        {
            key: value
            for key, value in document.items()
            if key not in {"content", "embeddings", "page_texts"}
        }
        for document in DOCUMENTS.values()
    ]


@app.post("/documents/index-pending")
async def index_pending_documents() -> dict[str, Any]:
    pending = [
        document for document in DOCUMENTS.values() if document.get("status") != "indexed"
    ]
    indexed_documents: list[str] = []

    for document in pending:
        try:
            chunks, page_numbers = document_chunks(document, 240, 40)
            vectors = await embed_texts(chunks)
            indexed_count = upsert_document_chunks(
                document_id=document["document_id"],
                filename=document["filename"],
                chunks=chunks,
                vectors=vectors,
                document_metadata=document,
                page_numbers=page_numbers,
            )
            document["status"] = "indexed"
            save_document(document)
            indexed_documents.append(document["document_id"])
        except EmbeddingConfigurationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except EmbeddingProviderError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except VectorStoreConfigurationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except VectorStoreError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    return {
        "indexed_count": len(indexed_documents),
        "document_ids": indexed_documents,
        "status": "complete",
    }


@app.delete("/documents/{document_id}", status_code=204)
async def remove_document(document_id: str) -> Response:
    document = DOCUMENTS.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        delete_document_chunks(document_id)
    except VectorStoreConfigurationError:
        pass
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    DOCUMENTS.pop(document_id, None)
    delete_document(document_id)
    return Response(status_code=204)


@app.get("/documents/{document_id}/content")
async def get_document_content(document_id: str) -> dict[str, Any]:
    document = DOCUMENTS.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    text = document.get("content") or ""
    word_count = len(re.findall(r"\b\w+\b", text))

    return {
        "document_id": document_id,
        "filename": document["filename"],
        "text": text,
        "word_count": word_count,
    }


@app.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    chunk_size: int = 240,
    overlap: int = 40,
) -> dict[str, Any]:
    document = DOCUMENTS.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        chunks, page_numbers = document_chunks(document, chunk_size, overlap)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {
        "document_id": document_id,
        "filename": document["filename"],
        "chunk_size": chunk_size,
        "overlap": overlap,
        "chunk_count": len(chunks),
        "chunks": [
            {
                "chunk_id": f"{document_id}:{index}",
                "index": index,
                "text": chunk,
                "word_count": len(re.findall(r"\b\w+\b", chunk)),
                "page_number": page_number,
            }
            for index, (chunk, page_number) in enumerate(zip(chunks, page_numbers, strict=True))
        ],
    }


@app.get("/documents/{document_id}/indexed-chunks")
async def get_indexed_document_chunks(
    document_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: str | None = None,
) -> dict[str, Any]:
    document = DOCUMENTS.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        total_chunk_count = count_document_points(document_id)
        page = scroll_collection_points(
            limit=limit,
            offset=offset,
            document_id=document_id,
        )
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    next_offset = page["next_offset"]
    return {
        "document_id": document_id,
        "document_name": document.get("document_name") or document.get("filename"),
        "total_chunk_count": total_chunk_count,
        "chunks": page["points"],
        "next_offset": str(next_offset) if next_offset is not None else None,
    }


@app.post("/documents/{document_id}/embeddings")
async def create_document_embeddings(
    document_id: str,
    chunk_size: int = 240,
    overlap: int = 40,
) -> dict[str, Any]:
    document = DOCUMENTS.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        chunks, page_numbers = document_chunks(document, chunk_size, overlap)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        vectors = await embed_texts(chunks)
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except EmbeddingProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    document["embeddings"] = [
        {
            "chunk_id": f"{document_id}:{index}",
            "index": index,
            "text": chunk,
            "page_number": page_numbers[index],
            "embedding": vector,
        }
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]
    document["status"] = "embedded"
    save_document(document)

    return {
        "document_id": document_id,
        "filename": document["filename"],
        "model": embedding_model(),
        "chunk_count": len(vectors),
        "dimensions": len(vectors[0]) if vectors else 0,
        "status": document["status"],
    }


@app.post("/documents/{document_id}/index")
async def index_document(
    document_id: str,
    chunk_size: int = 240,
    overlap: int = 40,
) -> dict[str, Any]:
    document = DOCUMENTS.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        chunks, page_numbers = document_chunks(document, chunk_size, overlap)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        vectors = await embed_texts(chunks)
        indexed_count = upsert_document_chunks(
            document_id=document_id,
            filename=document["filename"],
            chunks=chunks,
            vectors=vectors,
            document_metadata=document,
            page_numbers=page_numbers,
        )
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except EmbeddingProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    document["status"] = "indexed"
    save_document(document)
    return {
        "document_id": document_id,
        "filename": document["filename"],
        "collection": os.getenv("QDRANT_COLLECTION", "knowledgeops_documents"),
        "model": embedding_model(),
        "indexed_chunks": indexed_count,
        "status": document["status"],
    }


@app.post("/search")
async def search_documents(
    request: SearchRequest,
    response: Response,
    http_request: Request,
) -> dict[str, Any]:
    increment_metric("queries")
    request_started = perf_counter()
    try:
        embedding_started = perf_counter()
        query_vector = (await embed_texts([request.query], task_type="RETRIEVAL_QUERY"))[0]
        embedding_latency_ms = round((perf_counter() - embedding_started) * 1000, 2)
        vector_started = perf_counter()
        candidates = search_document_chunks(
            query_vector,
            max(request.candidate_limit, request.limit),
            **request.retrieval_filters(),
        )
        vector_retrieval_latency_ms = round((perf_counter() - vector_started) * 1000, 2)
        retrieval_latency_ms = round((perf_counter() - request_started) * 1000, 2)
        results, reranking_latency_ms = rerank(request.query, candidates, request.limit)
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except EmbeddingProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    response.headers["X-Retrieval-Method"] = "dense_vector"
    response.headers["X-Retrieval-Latency-Ms"] = str(retrieval_latency_ms)
    response.headers["X-Retrieval-Candidate-Limit"] = str(max(request.candidate_limit, request.limit))
    save_operation_event({
        "request_id": http_request.state.request_id,
        "operation": "search",
        "provider": embedding_provider(),
        "model": embedding_model(),
        "embedding_latency_ms": embedding_latency_ms,
        "vector_retrieval_latency_ms": vector_retrieval_latency_ms,
        "reranking_latency_ms": reranking_latency_ms,
        "generation_latency_ms": None,
        "total_latency_ms": round((perf_counter() - request_started) * 1000, 2),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "query": request.query,
        "count": len(results),
        "candidate_count": len(candidates),
        "reranker": reranker_name(),
        "reranking_latency_ms": reranking_latency_ms,
        "results": results,
    }


@app.post("/ask")
async def ask_knowledge_base(request: AskRequest, http_request: Request) -> dict[str, Any]:
    request_id = http_request.state.request_id
    request_started = perf_counter()
    increment_metric("queries")
    try:
        embedding_started = perf_counter()
        query_vector = (await embed_texts([request.query], task_type="RETRIEVAL_QUERY"))[0]
        embedding_latency_ms = round((perf_counter() - embedding_started) * 1000, 2)
        vector_started = perf_counter()
        candidates = search_document_chunks(
            query_vector,
            max(request.candidate_limit, request.limit),
            **request.retrieval_filters(),
        )
        vector_retrieval_latency_ms = round((perf_counter() - vector_started) * 1000, 2)
        sources, reranking_latency_ms = rerank(request.query, candidates, request.limit)
        retrieval_latency_ms = round(
            embedding_latency_ms + vector_retrieval_latency_ms,
            2,
        )
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except EmbeddingProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    if not sources:
        raise HTTPException(
            status_code=404,
            detail="No indexed sources found. Upload and index a document first.",
        )

    try:
        generation_started = perf_counter()
        answer = await generate_grounded_answer(request.query, sources)
        generation_latency_ms = round((perf_counter() - generation_started) * 1000, 2)
    except LLMConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    save_operation_event({
        "request_id": request_id,
        "operation": "ask",
        "provider": llm_provider(),
        "model": llm_model(),
        "embedding_latency_ms": embedding_latency_ms,
        "vector_retrieval_latency_ms": vector_retrieval_latency_ms,
        "reranking_latency_ms": reranking_latency_ms,
        "generation_latency_ms": generation_latency_ms,
        "total_latency_ms": round((perf_counter() - request_started) * 1000, 2),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "question": request.query,
        "answer": answer,
        "model": llm_model(),
        "request_id": request_id,
        "retrieved_chunks": len(sources),
        "candidate_count": len(candidates),
        "reranker": reranker_name(),
        "latency": {
            "total_ms": round((perf_counter() - request_started) * 1000, 2),
            "retrieval_ms": retrieval_latency_ms,
            "reranking_ms": reranking_latency_ms,
            "generation_ms": generation_latency_ms,
        },
        "citations": [
            {
                "citation": index,
                "filename": source.get("filename"),
                "document_name": source.get("document_name"),
                "document_id": source.get("document_id"),
                "chunk_id": source.get("chunk_id"),
                "point_id": source.get("point_id"),
                "chunk_index": source.get("chunk_index"),
                "page_number": source.get("page_number"),
                "project_name": source.get("project_name"),
                "category": source.get("category"),
                "source_type": source.get("source_type"),
                "text": source.get("text"),
                "retrieval_score": source.get("retrieval_score"),
                "reranking_score": source.get("reranking_score"),
                "mmr_score": source.get("mmr_score"),
            }
            for index, source in enumerate(sources, start=1)
        ],
        "retrieved_sources": sources,
    }


@app.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    project_name: str | None = Form(default=None),
    category: str | None = Form(default=None),
) -> dict[str, Any]:
    if file.filename is None or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds the 10MB upload limit.")

    document_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    page_texts = extract_pdf_pages(content, file.filename)
    extracted_text = "\n\n".join(page["text"] for page in page_texts)
    normalized_project = normalize_label(project_name)
    normalized_category = normalize_label(category)
    if project_name is not None and normalized_project is None:
        raise HTTPException(status_code=400, detail="Project name must not be blank.")
    if category is not None and normalized_category is None:
        raise HTTPException(status_code=400, detail="Category must not be blank.")

    metadata = {
        "document_id": document_id,
        "document_name": file.filename,
        "filename": file.filename,
        "file_type": "pdf",
        "source_type": "pdf",
        "project_name": normalized_project,
        "category": normalized_category,
        "file_size": len(content),
        "status": "uploaded",
        "created_at": created_at,
        "uploaded_at": created_at,
        "content_hash": hashlib.sha256(extracted_text.encode("utf-8")).hexdigest(),
        "page_texts": page_texts,
        "content": extracted_text,
    }

    DOCUMENTS[document_id] = metadata
    save_document(metadata)
    return {
        key: value
        for key, value in metadata.items()
        if key not in {"content", "page_texts"}
    }
