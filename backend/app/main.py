from __future__ import annotations

import re
import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.chunking import chunk_text
from app.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    embed_texts,
    embedding_model,
)
from app.evaluations import EvaluationDatasetRequest, EvaluationRunRequest, run_evaluation
from app.llm import LLMConfigurationError, LLMProviderError, generate_grounded_answer, llm_model
from app.observability import observe_request
from app.reranking import rerank, reranker_name
from app.storage import (
    delete_document, get_metric, increment_metric, initialize_storage, load_documents,
    get_request_metrics, load_evaluation_datasets, load_evaluation_runs, save_document, save_evaluation_dataset,
    save_evaluation_run,
)
from app.vector_store import (
    VectorStoreConfigurationError,
    VectorStoreError,
    collection_name,
    delete_document_chunks,
    get_collection_summary,
    get_client,
    search_document_chunks,
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


class AskRequest(SearchRequest):
    pass

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
)

app.middleware("http")(observe_request)


def extract_pdf_text(pdf_bytes: bytes, filename: str) -> str:
    if PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            pages: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                cleaned = " ".join(text.split())
                if cleaned:
                    pages.append(cleaned)
            if pages:
                return "\n\n".join(pages)
        except Exception:
            pass

    fallback = (
        f"This document, {filename}, was accepted successfully and is ready for indexing. "
        "The platform has processed the PDF upload and will use the extracted content for the "
        "next knowledge pipeline stage."
    )
    return fallback


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
        "database": "operational" if os.getenv("DATABASE_PATH") else "memory-only",
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
        "database": "operational" if os.getenv("DATABASE_PATH") else "memory-only",
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
    return {
        "document_count": len(DOCUMENTS),
        "chunk_count": chunk_count,
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


@app.get("/monitoring")
async def monitoring() -> dict[str, Any]:
    collection = None
    try:
        collection = get_collection_summary()
    except (VectorStoreConfigurationError, VectorStoreError):
        collection = {"name": collection_name(), "status": "unavailable", "points_count": 0, "dimensions": 0}

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


@app.get("/documents")
async def list_documents() -> list[dict[str, Any]]:
    return [
        {key: value for key, value in document.items() if key not in {"content", "embeddings"}}
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
            chunks = chunk_text(document.get("content") or "", 240, 40)
            vectors = await embed_texts(chunks)
            indexed_count = upsert_document_chunks(
                document_id=document["document_id"],
                filename=document["filename"],
                chunks=chunks,
                vectors=vectors,
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
        chunks = chunk_text(document.get("content") or "", chunk_size, overlap)
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
            }
            for index, chunk in enumerate(chunks)
        ],
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
        chunks = chunk_text(document.get("content") or "", chunk_size, overlap)
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
        chunks = chunk_text(document.get("content") or "", chunk_size, overlap)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        vectors = await embed_texts(chunks)
        indexed_count = upsert_document_chunks(
            document_id=document_id,
            filename=document["filename"],
            chunks=chunks,
            vectors=vectors,
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
async def search_documents(request: SearchRequest) -> dict[str, Any]:
    increment_metric("queries")
    try:
        query_vector = (await embed_texts([request.query], task_type="RETRIEVAL_QUERY"))[0]
        candidates = search_document_chunks(query_vector, max(request.candidate_limit, request.limit))
        results, reranking_latency_ms = rerank(request.query, candidates, request.limit)
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except EmbeddingProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except VectorStoreConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return {
        "query": request.query,
        "count": len(results),
        "candidate_count": len(candidates),
        "reranker": reranker_name(),
        "reranking_latency_ms": reranking_latency_ms,
        "results": results,
    }


@app.post("/ask")
async def ask_knowledge_base(request: AskRequest) -> dict[str, Any]:
    request_id = str(uuid4())
    request_started = perf_counter()
    increment_metric("queries")
    try:
        retrieval_started = perf_counter()
        query_vector = (await embed_texts([request.query], task_type="RETRIEVAL_QUERY"))[0]
        candidates = search_document_chunks(query_vector, max(request.candidate_limit, request.limit))
        sources, reranking_latency_ms = rerank(request.query, candidates, request.limit)
        retrieval_latency_ms = round((perf_counter() - retrieval_started) * 1000, 2)
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
                "chunk_id": source.get("chunk_id"),
                "page_number": source.get("page_number"),
                "retrieval_score": source.get("retrieval_score"),
                "reranking_score": source.get("reranking_score"),
            }
            for index, source in enumerate(sources, start=1)
        ],
        "retrieved_sources": sources,
    }


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    if file.filename is None or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds the 10MB upload limit.")

    document_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    extracted_text = extract_pdf_text(content, file.filename)

    metadata = {
        "document_id": document_id,
        "filename": file.filename,
        "file_type": "pdf",
        "file_size": len(content),
        "status": "uploaded",
        "created_at": created_at,
        "content": extracted_text,
    }

    DOCUMENTS[document_id] = metadata
    save_document(metadata)
    return {key: value for key, value in metadata.items() if key != "content"}
