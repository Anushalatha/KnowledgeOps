from __future__ import annotations

import asyncio
from typing import Any

import httpx

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


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
            await asyncio.sleep(0.5 * (2**attempt))
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as error:
            last_error = error
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(0.5 * (2**attempt))
    raise last_error or RuntimeError("Retry attempts exhausted.")
