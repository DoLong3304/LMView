import asyncio

import httpx
import pytest

BASE = "http://localhost:8080"


@pytest.mark.integration
async def test_market_overview_has_metadata_shape():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/api/market/overview")
    assert r.status_code == 200
    data = r.json()
    assert "metadata" in data
    assert "data_sources" in data["metadata"]
    assert "gold_tables_healthy" in data["metadata"]
    assert "computed_at" in data["metadata"]


@pytest.mark.integration
async def test_market_overview_response_time():
    loop = asyncio.get_running_loop()
    start = loop.time()
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/api/market/overview")
    elapsed = loop.time() - start
    assert r.status_code == 200
    assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"


@pytest.mark.integration
async def test_market_overview_fallback_still_operates():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/api/market/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["metadata"]["data_sources"]
    assert "market_summary" in data
