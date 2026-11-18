from __future__ import annotations

import asyncio

import httpx
import pytest

from app.reliability import post_with_retry


class FakeClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = iter(responses)
        self.calls = 0

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        self.calls += 1
        return next(self.responses)


@pytest.mark.parametrize(
    ("retry_after", "expected_delay"),
    [("2", 2.0), ("invalid", 0.5)],
)
def test_post_with_retry_honors_retry_after(monkeypatch, retry_after, expected_delay):
    client = FakeClient([
        httpx.Response(503, headers={"Retry-After": retry_after}),
        httpx.Response(200),
    ])
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.reliability.asyncio.sleep", record_sleep)
    response = asyncio.run(post_with_retry(client, "https://example.test", attempts=2))

    assert response.status_code == 200
    assert client.calls == 2
    assert delays == [expected_delay]


def test_post_with_retry_bounds_server_retry_after(monkeypatch):
    client = FakeClient([
        httpx.Response(503, headers={"Retry-After": "1000"}),
        httpx.Response(200),
    ])
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.reliability.asyncio.sleep", record_sleep)
    asyncio.run(post_with_retry(client, "https://example.test", attempts=2))

    assert delays == [10.0]
