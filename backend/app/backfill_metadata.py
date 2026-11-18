from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.metadata import UNKNOWN_VALUE, normalize_label
from app.storage import load_documents
from app.vector_store import (
    VectorStoreError,
    collection_name,
    get_client,
)


METADATA_FIELDS = (
    "project_name",
    "category",
    "source_type",
    "document_id",
    "document_name",
    "chunk_id",
    "page_number",
    "content_hash",
    "uploaded_at",
)


def _document_value(
    payload: dict[str, Any],
    document: dict[str, Any],
    key: str,
) -> Any:
    current_value = payload.get(key)
    if current_value is not None:
        if key in {"project_name", "category", "source_type"}:
            return normalize_label(str(current_value))
        return current_value

    if key == "document_name":
        return document.get("document_name") or payload.get("filename") or document.get("filename")
    if key == "uploaded_at":
        return document.get("uploaded_at") or document.get("created_at")
    if key == "source_type":
        value = document.get("source_type") or document.get("file_type")
        if value:
            return normalize_label(str(value))
        filename = payload.get("filename") or document.get("filename")
        return Path(filename).suffix.lstrip(".").casefold() if filename else None
    if key in {"project_name", "category"}:
        return normalize_label(document.get(key))
    if key == "document_id":
        return document.get("document_id")
    if key == "chunk_id":
        return payload.get("chunk_id")
    if key == "page_number":
        text = payload.get("text")
        pages = document.get("page_texts")
        if not isinstance(text, str) or not isinstance(pages, list):
            return None
        chunk_words = " ".join(text.split()).casefold().split()
        if not chunk_words:
            return None
        matching_pages = []
        for page in pages:
            if not isinstance(page, dict) or not isinstance(page.get("page_number"), int):
                continue
            page_text = page.get("text")
            if not isinstance(page_text, str):
                continue
            page_words = " ".join(page_text.split()).casefold().split()
            if any(
                page_words[index : index + len(chunk_words)] == chunk_words
                for index in range(len(page_words) - len(chunk_words) + 1)
            ):
                matching_pages.append(page["page_number"])
        if len(matching_pages) == 1:
            return matching_pages[0]
        return None
    if key == "content_hash":
        text = payload.get("text")
        return hashlib.sha256(text.encode("utf-8")).hexdigest() if isinstance(text, str) else None
    return None


def backfill_collection_metadata(
    documents: list[dict[str, Any]] | None = None,
    batch_size: int = 128,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero.")

    client = get_client()
    collection = collection_name()
    try:
        if collection != "knowledgeops_documents":
            raise VectorStoreError(
                "Refusing metadata backfill: expected the existing "
                "'knowledgeops_documents' collection."
            )
        if not client.collection_exists(collection):
            raise VectorStoreError(
                f"Refusing metadata backfill: collection {collection!r} does not exist."
            )

        document_by_id = {
            str(document["document_id"]): document
            for document in (documents if documents is not None else load_documents())
            if document.get("document_id")
        }
        counts = Counter()
        unavailable = Counter()
        offset = None

        while True:
            points, offset = client.scroll(
                collection_name=collection,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            point_updates: list[tuple[Any, dict[str, Any]]] = []
            for point in points:
                payload = dict(point.payload or {})
                document_id = payload.get("document_id")
                document = document_by_id.get(str(document_id), {})
                metadata = {
                    field: _document_value(payload, document, field) or UNKNOWN_VALUE
                    for field in METADATA_FIELDS
                }
                if document_id and str(document_id) not in document_by_id:
                    counts["points_missing_document_record"] += 1
                point_has_unavailable_values = False
                for field, value in metadata.items():
                    if value == UNKNOWN_VALUE:
                        unavailable[field] += 1
                        point_has_unavailable_values = True
                if point_has_unavailable_values:
                    counts["points_with_unavailable_metadata"] += 1
                if any(payload.get(key) != value or key not in payload for key, value in metadata.items()):
                    point_updates.append((point.id, metadata))

            for point_id, metadata in point_updates:
                client.set_payload(
                    collection_name=collection,
                    payload=metadata,
                    points=[point_id],
                    wait=True,
                )
                counts["updated_points"] += 1
            counts["scanned_points"] += len(points)
            if offset is None:
                break

        summary = {
            "collection": collection,
            "scanned_points": counts["scanned_points"],
            "updated_points": counts["updated_points"],
            "points_missing_document_record": counts["points_missing_document_record"],
            "points_with_unavailable_metadata": counts["points_with_unavailable_metadata"],
            "unavailable_values": {
                field: unavailable[field]
                for field in METADATA_FIELDS
                if unavailable[field]
            },
        }
        return summary
    except VectorStoreError:
        raise
    except Exception as error:
        raise VectorStoreError("Qdrant metadata backfill failed.") from error


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    result = backfill_collection_metadata()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
