from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid5

from app.metadata import UNKNOWN_VALUE, normalize_label

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
    *,
    document_metadata: dict[str, Any] | None = None,
    page_numbers: list[int | None] | None = None,
) -> int:
    if not vectors:
        return 0
    if len(chunks) != len(vectors):
        raise VectorStoreError("Chunk and vector counts do not match.")
    if page_numbers is not None and len(chunks) != len(page_numbers):
        raise VectorStoreError("Chunk and page-number counts do not match.")

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

        metadata = document_metadata or {}
        source_type = metadata.get("source_type") or metadata.get("file_type")
        if not source_type:
            source_type = os.path.splitext(filename)[1].lstrip(".") or None
        uploaded_at = metadata.get("uploaded_at") or metadata.get("created_at")
        points = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            payload = {
                "document_id": document_id,
                "document_name": metadata.get("document_name") or filename,
                "filename": filename,
                "chunk_id": f"{document_id}:{index}",
                "chunk_index": index,
                "text": chunk,
                "project_name": normalize_label(metadata.get("project_name")) or UNKNOWN_VALUE,
                "category": normalize_label(metadata.get("category")) or UNKNOWN_VALUE,
                "source_type": normalize_label(source_type) or UNKNOWN_VALUE,
                "page_number": (
                    page_numbers[index]
                    if page_numbers is not None and page_numbers[index] is not None
                    else UNKNOWN_VALUE
                ),
                "content_hash": hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
                "uploaded_at": uploaded_at or UNKNOWN_VALUE,
            }
            points.append(
                models.PointStruct(
                    id=str(uuid5(UUID(document_id), str(index))),
                    vector=vector,
                    payload=payload,
                )
            )
        client.upsert(collection_name=name, points=points, wait=True)
        return len(points)
    except Exception as error:
        raise VectorStoreError("Qdrant could not store the document vectors.") from error


def build_metadata_filter(
    *,
    project_name: str | None = None,
    project_names: Sequence[str] | None = None,
    document_id: str | None = None,
    document_name: str | None = None,
    category: str | None = None,
    source_type: str | None = None,
):
    if models is None:
        raise VectorStoreConfigurationError(
            "Qdrant support is not installed. Install the backend requirements."
        )

    projects: list[str] = []
    for value in [project_name, *(project_names or [])]:
        normalized = normalize_label(value)
        if value is not None and normalized is None:
            raise VectorStoreError("Project filters must not be blank.")
        if normalized and normalized not in projects:
            projects.append(normalized)

    must = []
    if projects:
        must.append(
            models.FieldCondition(
                key="project_name",
                match=models.MatchAny(any=projects),
            )
        )

    normalized_labels: dict[str, str | None] = {}
    for key, value in (("category", category), ("source_type", source_type)):
        normalized = normalize_label(value)
        if value is not None and normalized is None:
            raise VectorStoreError(f"{key} filters must not be blank.")
        normalized_labels[key] = normalized

    for key, value in (
        ("document_id", document_id),
        ("document_name", document_name),
        ("category", normalized_labels["category"]),
        ("source_type", normalized_labels["source_type"]),
    ):
        if value is not None:
            normalized_value = value.strip() if key in {"document_id", "document_name"} else value
            if not normalized_value:
                raise VectorStoreError(f"{key} filters must not be blank.")
            must.append(
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=normalized_value),
                )
            )

    return models.Filter(must=must) if must else None


def search_document_chunks(
    vector: list[float],
    limit: int = 5,
    *,
    project_name: str | None = None,
    project_names: Sequence[str] | None = None,
    document_id: str | None = None,
    document_name: str | None = None,
    category: str | None = None,
    source_type: str | None = None,
) -> list[dict]:
    if limit <= 0 or limit > 50:
        raise VectorStoreError("Search limit must be between 1 and 50.")

    client = get_client()
    try:
        if not client.collection_exists(collection_name()):
            return []

        query_filter = build_metadata_filter(
            project_name=project_name,
            project_names=project_names,
            document_id=document_id,
            document_name=document_name,
            category=category,
            source_type=source_type,
        )
        response = client.query_points(
            collection_name=collection_name(),
            query=vector,
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
        )
        results = []
        for point in response.points:
            payload = dict(point.payload or {})
            for key in ("project_name", "category", "page_number", "uploaded_at"):
                if payload.get(key) == UNKNOWN_VALUE:
                    payload[key] = None
            results.append({**payload, "point_id": str(point.id), "score": point.score})
        return results
    except Exception as error:
        raise VectorStoreError("Qdrant could not search the document vectors.") from error


def scroll_collection_points(
    *,
    limit: int = 50,
    offset: str | int | None = None,
    chunk_id: str | None = None,
    document_id: str | None = None,
    document_name: str | None = None,
) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise VectorStoreError("Point page size must be between 1 and 100.")

    client = get_client()
    name = collection_name()
    must = []
    for key, value in (
        ("chunk_id", chunk_id),
        ("document_id", document_id),
        ("document_name", document_name),
    ):
        if value is not None:
            normalized = value.strip()
            if not normalized:
                raise VectorStoreError(f"{key} filter must not be blank.")
            must.append(
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=normalized),
                )
            )
    query_filter = models.Filter(must=must) if must else None

    try:
        if not client.collection_exists(name):
            return {"points": [], "next_offset": None}
        points, next_offset = client.scroll(
            collection_name=name,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False,
            scroll_filter=query_filter,
        )
        return {
            "points": [
                {"point_id": str(point.id), **dict(point.payload or {})}
                for point in points
            ],
            "next_offset": next_offset,
        }
    except Exception as error:
        raise VectorStoreError("Qdrant collection points could not be read.") from error


def get_point_by_chunk_id(chunk_id: str) -> dict[str, Any] | None:
    if not chunk_id.strip():
        raise VectorStoreError("Chunk ID must not be blank.")
    client = get_client()
    name = collection_name()
    try:
        if not client.collection_exists(name):
            return None
        points, _ = client.scroll(
            collection_name=name,
            limit=2,
            with_payload=True,
            with_vectors=False,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="chunk_id",
                        match=models.MatchValue(value=chunk_id),
                    )
                ]
            ),
        )
        matches = [
            {"point_id": str(point.id), **dict(point.payload or {})}
            for point in points
            if (point.payload or {}).get("chunk_id") == chunk_id
        ]
        if len(matches) > 1:
            raise VectorStoreError(f"Chunk ID {chunk_id!r} is not unique in the collection.")
        return matches[0] if matches else None
    except VectorStoreError:
        raise
    except Exception as error:
        raise VectorStoreError("Qdrant chunk could not be read.") from error


def get_point_by_id(point_id: str) -> dict[str, Any] | None:
    if not point_id.strip():
        raise VectorStoreError("Point ID must not be blank.")
    client = get_client()
    name = collection_name()
    try:
        if not client.collection_exists(name):
            return None
        points = client.retrieve(
            collection_name=name,
            ids=[point_id],
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            return None
        point = points[0]
        return {"point_id": str(point.id), **dict(point.payload or {})}
    except Exception as error:
        raise VectorStoreError("Qdrant point could not be read.") from error


def count_document_points(document_id: str) -> int:
    if not document_id.strip():
        raise VectorStoreError("Document ID must not be blank.")
    client = get_client()
    name = collection_name()
    try:
        if not client.collection_exists(name):
            return 0
        result = client.count(
            collection_name=name,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            ),
            exact=True,
        )
        return result.count
    except Exception as error:
        raise VectorStoreError("Document chunk count could not be read.") from error


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


def get_collection_details() -> dict[str, Any]:
    client = get_client()
    name = collection_name()
    try:
        if not client.collection_exists(name):
            return {
                "name": name,
                "status": "empty",
                "points_count": 0,
                "dimensions": 0,
                "distance": None,
                "vectors": [],
                "payload_fields": [],
                "document_count": 0,
                "metadata_completeness": {},
                "optimizer_config": None,
                "hnsw_config": None,
            }

        info = client.get_collection(name)
        vector_config = info.config.params.vectors
        vector_items = (
            list(vector_config.items())
            if isinstance(vector_config, dict)
            else [("default", vector_config)]
        )
        vectors = [
            {
                "name": vector_name,
                "size": config.size,
                "distance": getattr(config.distance, "value", str(config.distance)),
            }
            for vector_name, config in vector_items
        ]

        payload_fields: set[str] = set()
        document_ids: set[str] = set()
        field_presence: dict[str, dict[str, Any]] = {}
        scanned_points = 0
        offset = None
        while True:
            points, offset = client.scroll(
                collection_name=name,
                limit=128,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                scanned_points += 1
                payload_fields.update(payload.keys())
                document_id = payload.get("document_id")
                if isinstance(document_id, str) and document_id:
                    document_ids.add(document_id)
                for field in payload_fields:
                    stats = field_presence.setdefault(
                        field,
                        {
                            "present_points": 0,
                            "missing_points": max(scanned_points - 1, 0),
                            "unknown_points": 0,
                            "types": set(),
                        },
                    )
                    if field not in payload:
                        stats["missing_points"] += 1
                        continue
                    stats["present_points"] += 1
                    value = payload[field]
                    if value is not None:
                        stats["types"].add(type(value).__name__)
                    if value is None or value == "":
                        stats["missing_points"] += 1
                    elif value == UNKNOWN_VALUE:
                        stats["unknown_points"] += 1
            if offset is None:
                break

        def dump_config(config: Any) -> Any:
            if config is None:
                return None
            if hasattr(config, "model_dump"):
                return config.model_dump(mode="json")
            return config

        dimensions = vectors[0]["size"] if vectors else 0
        distance = vectors[0]["distance"] if vectors else None
        return {
            "name": name,
            "status": "operational",
            "points_count": info.points_count or 0,
            "scanned_points": scanned_points,
            "dimensions": dimensions,
            "distance": distance,
            "vectors": vectors,
            "payload_fields": sorted(payload_fields),
            "document_count": len(document_ids),
            "payload_field_statistics": {
                field: {
                    "present_points": stats["present_points"],
                    "missing_points": stats["missing_points"],
                    "unknown_points": stats["unknown_points"],
                    "known_points": max(
                        scanned_points - stats["missing_points"] - stats["unknown_points"],
                        0,
                    ),
                    "completeness_percent": round(
                        max(scanned_points - stats["missing_points"] - stats["unknown_points"], 0)
                        / scanned_points * 100,
                        1,
                    ) if scanned_points else None,
                    "types": sorted(stats["types"]),
                }
                for field, stats in sorted(field_presence.items())
            },
            "metadata_completeness": {
                field: {
                    "unknown_points": field_presence.get(field, {}).get("unknown_points", 0)
                    + field_presence.get(field, {}).get("missing_points", 0),
                    "known_points": max(
                        scanned_points
                        - field_presence.get(field, {}).get("unknown_points", 0)
                        - field_presence.get(field, {}).get("missing_points", 0),
                        0,
                    ),
                }
                for field in ("project_name", "category", "page_number")
            },
            "optimizer_config": dump_config(info.config.optimizer_config),
            "hnsw_config": dump_config(info.config.hnsw_config),
            "indexed_payload_schema": sorted((info.payload_schema or {}).keys()),
        }
    except Exception as error:
        raise VectorStoreError("Qdrant collection details could not be read.") from error


def scan_collection_points(
    *,
    limit: int,
    offset: int = 0,
    query: str | None = None,
    filter_field: str | None = None,
    filter_value: str | None = None,
    payload_filters: dict[str, str] | None = None,
    unmatched_document_ids: set[str | None] | None = None,
) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise VectorStoreError("Point page size must be between 1 and 100.")
    if offset < 0:
        raise VectorStoreError("Point offset must not be negative.")
    if bool(filter_field) != bool(filter_value):
        raise VectorStoreError("Payload field and value filters must be provided together.")

    all_points: list[dict[str, Any]] = []
    cursor: str | int | None = None
    while True:
        page = scroll_collection_points(limit=100, offset=cursor)
        all_points.extend(page["points"])
        cursor = page["next_offset"]
        if cursor is None:
            break

    normalized_query = query.strip().casefold() if query else ""
    normalized_filter = filter_value.casefold() if filter_value else ""
    normalized_filters = {
        field: value.casefold()
        for field, value in (payload_filters or {}).items()
        if value.strip()
    }
    filtered_points = []
    for point in all_points:
        if unmatched_document_ids is not None and point.get("document_id") not in unmatched_document_ids:
            continue
        if normalized_query and not any(
            normalized_query in str(value).casefold()
            for value in [point.get("point_id"), *point.values()]
            if value is not None
        ):
            continue
        if filter_field and normalized_filter:
            value = point.get(filter_field)
            if value is None or normalized_filter != str(value).casefold():
                continue
        if any(
            point.get(field) is None or value != str(point[field]).casefold()
            for field, value in normalized_filters.items()
        ):
            continue
        filtered_points.append(point)

    page_points = filtered_points[offset:offset + limit]
    next_offset = offset + len(page_points) if offset + len(page_points) < len(filtered_points) else None
    return {
        "points": page_points,
        "next_offset": str(next_offset) if next_offset is not None else None,
        "total": len(filtered_points),
    }
