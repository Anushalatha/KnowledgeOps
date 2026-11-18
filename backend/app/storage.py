from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def database_path() -> Path | None:
    configured_path = os.getenv("DATABASE_PATH")
    return Path(configured_path) if configured_path else None


def database_status() -> str:
    path = database_path()
    if path is None:
        return "memory-only"
    try:
        with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=1) as connection:
            connection.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
    except sqlite3.Error:
        return "unavailable"
    return "operational"


def initialize_storage() -> None:
    path = database_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                metadata TEXT NOT NULL,
                content TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS request_events (
                request_id TEXT PRIMARY KEY,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_events (
                request_id TEXT PRIMARY KEY,
                operation TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                embedding_latency_ms REAL,
                vector_retrieval_latency_ms REAL,
                reranking_latency_ms REAL,
                generation_latency_ms REAL,
                total_latency_ms REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluation_datasets (
                dataset_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                cases TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluation_runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                result TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                metric_name TEXT PRIMARY KEY,
                metric_value INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.commit()


def load_documents() -> list[dict[str, Any]]:
    path = database_path()
    if path is None:
        return []
    initialize_storage()
    with sqlite3.connect(path) as connection:
        rows = connection.execute("SELECT metadata, content FROM documents").fetchall()
    return [{**json.loads(metadata), "content": content} for metadata, content in rows]


def save_document(document: dict[str, Any]) -> None:
    path = database_path()
    if path is None:
        return
    initialize_storage()
    metadata = {key: value for key, value in document.items() if key not in {"content", "embeddings"}}
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO documents (document_id, metadata, content)
            VALUES (?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET metadata = excluded.metadata, content = excluded.content
            """,
            (document["document_id"], json.dumps(metadata), document.get("content") or ""),
        )
        connection.commit()


def delete_document(document_id: str) -> None:
    path = database_path()
    if path is None:
        return
    initialize_storage()
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
        connection.commit()


def increment_metric(metric_name: str) -> int:
    path = database_path()
    if path is None:
        return 0
    initialize_storage()
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO metrics (metric_name, metric_value) VALUES (?, 1)
            ON CONFLICT(metric_name) DO UPDATE SET metric_value = metric_value + 1
            """,
            (metric_name,),
        )
        value = connection.execute(
            "SELECT metric_value FROM metrics WHERE metric_name = ?", (metric_name,)
        ).fetchone()[0]
        connection.commit()
    return value


def get_metric(metric_name: str) -> int:
    path = database_path()
    if path is None:
        return 0
    initialize_storage()
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT metric_value FROM metrics WHERE metric_name = ?", (metric_name,)
        ).fetchone()
    return int(row[0]) if row else 0


def save_evaluation_run(result: dict[str, Any]) -> None:
    path = database_path()
    if path is None:
        return
    initialize_storage()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO evaluation_runs (run_id, created_at, result) VALUES (?, ?, ?)",
            (result["run_id"], result["created_at"], json.dumps(result)),
        )
        connection.commit()


def load_evaluation_runs(limit: int = 20) -> list[dict[str, Any]]:
    path = database_path()
    if path is None:
        return []
    initialize_storage()
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            "SELECT result FROM evaluation_runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def save_evaluation_dataset(dataset: dict[str, Any]) -> None:
    path = database_path()
    if path is None:
        return
    initialize_storage()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO evaluation_datasets (dataset_id, name, created_at, cases) VALUES (?, ?, ?, ?)",
            (dataset["dataset_id"], dataset["name"], dataset["created_at"], json.dumps(dataset["cases"])),
        )
        connection.commit()


def load_evaluation_datasets() -> list[dict[str, Any]]:
    path = database_path()
    if path is None:
        return []
    initialize_storage()
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            "SELECT dataset_id, name, created_at, cases FROM evaluation_datasets ORDER BY created_at DESC"
        ).fetchall()
    return [{"dataset_id": row[0], "name": row[1], "created_at": row[2], "cases": json.loads(row[3])} for row in rows]


def save_request_event(event: dict[str, Any]) -> None:
    path = database_path()
    if path is None:
        return
    initialize_storage()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO request_events (request_id, method, path, status_code, latency_ms, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (event["request_id"], event["method"], event["path"], event["status_code"], event["latency_ms"], event["created_at"]),
        )
        connection.commit()


def get_request_metrics() -> dict[str, Any]:
    path = database_path()
    if path is None:
        return {
            "requests": 0,
            "errors": 0,
            "successes": 0,
            "success_rate": None,
            "average_latency_ms": None,
            "status_distribution": {},
            "requests_last_hour": 0,
            "request_rate_per_minute_last_hour": None,
            "by_endpoint": [],
            "recent_failures": [],
        }
    initialize_storage()
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT COUNT(*), SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END), AVG(latency_ms) FROM request_events"
        ).fetchone()
        statuses = connection.execute(
            "SELECT status_code, COUNT(*) FROM request_events GROUP BY status_code ORDER BY status_code"
        ).fetchall()
        hourly_count = connection.execute(
            "SELECT COUNT(*) FROM request_events WHERE julianday('now') - julianday(created_at) <= 1.0 / 24"
        ).fetchone()[0]
        endpoints = connection.execute(
            """
            SELECT method, path, COUNT(*),
                SUM(CASE WHEN status_code < 400 THEN 1 ELSE 0 END),
                SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END),
                AVG(latency_ms)
            FROM request_events
            GROUP BY method, path
            ORDER BY COUNT(*) DESC, path
            """
        ).fetchall()
        failures = connection.execute(
            """
            SELECT request_id, method, path, status_code, latency_ms, created_at
            FROM request_events
            WHERE status_code >= 400
            ORDER BY created_at DESC
            LIMIT 10
            """
        ).fetchall()
    requests, errors, average_latency = int(row[0]), int(row[1] or 0), row[2]
    return {
        "requests": requests,
        "errors": errors,
        "successes": requests - errors,
        "success_rate": round((requests - errors) / requests, 3) if requests else None,
        "average_latency_ms": round(float(average_latency), 2) if average_latency is not None else None,
        "status_distribution": {str(status): count for status, count in statuses},
        "requests_last_hour": int(hourly_count),
        "request_rate_per_minute_last_hour": round(int(hourly_count) / 60, 3) if hourly_count else 0.0,
        "by_endpoint": [
            {
                "method": method,
                "path": endpoint,
                "requests": count,
                "successes": int(successes or 0),
                "errors": int(failures_count or 0),
                "average_latency_ms": round(float(latency), 2) if latency is not None else None,
            }
            for method, endpoint, count, successes, failures_count, latency in endpoints
        ],
        "recent_failures": [
            {
                "request_id": request_id,
                "method": method,
                "path": endpoint,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "created_at": created_at,
            }
            for request_id, method, endpoint, status_code, latency_ms, created_at in failures
        ],
    }


def save_operation_event(event: dict[str, Any]) -> None:
    path = database_path()
    if path is None:
        return
    initialize_storage()
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO operation_events (
                request_id, operation, provider, model, embedding_latency_ms,
                vector_retrieval_latency_ms, reranking_latency_ms,
                generation_latency_ms, total_latency_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["request_id"],
                event["operation"],
                event["provider"],
                event["model"],
                event.get("embedding_latency_ms"),
                event.get("vector_retrieval_latency_ms"),
                event.get("reranking_latency_ms"),
                event.get("generation_latency_ms"),
                event["total_latency_ms"],
                event["created_at"],
            ),
        )
        connection.commit()


def get_operation_metrics() -> dict[str, Any]:
    path = database_path()
    if path is None:
        return {"operations": 0, "by_operation": []}
    initialize_storage()
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT operation, COUNT(*), AVG(embedding_latency_ms),
                AVG(vector_retrieval_latency_ms), AVG(reranking_latency_ms),
                AVG(generation_latency_ms), AVG(total_latency_ms)
            FROM operation_events
            GROUP BY operation
            ORDER BY operation
            """
        ).fetchall()
    return {
        "operations": sum(row[1] for row in rows),
        "by_operation": [
            {
                "operation": row[0],
                "count": row[1],
                "average_embedding_latency_ms": round(row[2], 2) if row[2] is not None else None,
                "average_vector_retrieval_latency_ms": round(row[3], 2) if row[3] is not None else None,
                "average_reranking_latency_ms": round(row[4], 2) if row[4] is not None else None,
                "average_generation_latency_ms": round(row[5], 2) if row[5] is not None else None,
                "average_total_latency_ms": round(row[6], 2) if row[6] is not None else None,
            }
            for row in rows
        ],
    }


def get_recent_request_events(limit: int = 20) -> list[dict[str, Any]]:
    if limit < 1 or limit > 100:
        raise ValueError("Request history limit must be between 1 and 100.")
    path = database_path()
    if path is None:
        return []
    initialize_storage()
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT request_id, method, path, status_code, latency_ms, created_at
            FROM request_events
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "request_id": row[0],
            "method": row[1],
            "path": row[2],
            "status_code": row[3],
            "latency_ms": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]
