from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_DELAY_SECONDS = 10.0


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            delay = max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                delay = 0.5 * (2**attempt)
        return min(delay, MAX_RETRY_DELAY_SECONDS)
    return min(0.5 * (2**attempt), MAX_RETRY_DELAY_SECONDS)


async def post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    attempts: int = 3,
    **kwargs: Any,
) -> httpx.Response:
    """Retry only transient HTTP/network failures with bounded exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = await client.post(url, **kwargs)
            if response.status_code not in TRANSIENT_STATUS_CODES or attempt == attempts - 1:
                return response
            await asyncio.sleep(_retry_delay(response, attempt))
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as error:
            last_error = error
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(0.5 * (2**attempt))
    raise last_error or RuntimeError("Retry attempts exhausted.")
