from __future__ import annotations

import os
from uuid import UUID, uuid5

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:  # pragma: no cover
    QdrantClient = None
    models = None


class VectorStoreConfigurationError(Exception):
    pass


class VectorStoreError(Exception):
    pass


def collection_name() -> str:
    return os.getenv("QDRANT_COLLECTION", "knowledgeops_documents")


def get_client():
    url = os.getenv("QDRANT_URL")
    if not url:
        raise VectorStoreConfigurationError(
            "Qdrant is not configured. Set QDRANT_URL in the project .env file."
        )
    if QdrantClient is None or models is None:
        raise VectorStoreConfigurationError(
            "Qdrant support is not installed. Install the backend requirements."
        )

    try:
        return QdrantClient(url=url, api_key=os.getenv("QDRANT_API_KEY") or None)
    except Exception as error:
        raise VectorStoreError("Qdrant client could not be initialized.") from error


def upsert_document_chunks(
    document_id: str,
    filename: str,
    chunks: list[str],
    vectors: list[list[float]],
) -> int:
    if not vectors:
        return 0
    if len(chunks) != len(vectors):
        raise VectorStoreError("Chunk and vector counts do not match.")

    client = get_client()
    dimension = len(vectors[0])
    name = collection_name()

    try:
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE,
                ),
            )
        else:
            client.delete(
                collection_name=name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
                wait=True,
            )

        points = [
            models.PointStruct(
                id=str(uuid5(UUID(document_id), str(index))),
                vector=vector,
                payload={
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_id": f"{document_id}:{index}",
                    "chunk_index": index,
                    "text": chunk,
                },
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
        client.upsert(collection_name=name, points=points, wait=True)
        return len(points)
    except Exception as error:
        raise VectorStoreError("Qdrant could not store the document vectors.") from error


def search_document_chunks(vector: list[float], limit: int = 5) -> list[dict]:
    if limit <= 0 or limit > 50:
        raise VectorStoreError("Search limit must be between 1 and 50.")

    client = get_client()
    try:
        if not client.collection_exists(collection_name()):
            return []

        response = client.query_points(
            collection_name=collection_name(),
            query=vector,
            limit=limit,
            with_payload=True,
        )
        return [
            {
                "score": point.score,
                **(point.payload or {}),
            }
            for point in response.points
        ]
    except Exception as error:
        raise VectorStoreError("Qdrant could not search the document vectors.") from error


def delete_document_chunks(document_id: str) -> None:
    client = get_client()
    name = collection_name()
    try:
        if not client.collection_exists(name):
            return
        client.delete(
            collection_name=name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )
    except Exception as error:
        raise VectorStoreError("Qdrant could not delete the document vectors.") from error


def get_collection_summary() -> dict:
    client = get_client()
    name = collection_name()
    try:
        if not client.collection_exists(name):
            return {"name": name, "status": "empty", "points_count": 0, "dimensions": 0}
        info = client.get_collection(name)
        vectors_config = info.config.params.vectors
        dimensions = vectors_config.size if hasattr(vectors_config, "size") else 0
        return {
            "name": name,
            "status": "operational",
            "points_count": info.points_count or 0,
            "dimensions": dimensions,
        }
    except Exception as error:
        raise VectorStoreError("Qdrant collection metadata could not be read.") from error
