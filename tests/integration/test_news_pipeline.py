import httpx
import pytest

BASE = "http://localhost:8080"


@pytest.mark.integration
async def test_news_latest_returns_real_data():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/api/news/latest?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert data["metadata"]["is_mock"] is False
    assert len(data["articles"]) > 0
    assert any("http" in a["url"] for a in data["articles"])


@pytest.mark.integration
async def test_news_has_sentiment_fields():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/api/news/latest?limit=20")
    assert r.status_code == 200
    data = r.json()
    assert len(data["articles"]) > 0
    first = data["articles"][0]
    assert "sentiment_score" in first
    assert "sentiment_label" in first


@pytest.mark.integration
async def test_news_filter_by_symbol():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/api/news/latest?symbol=XRPUSDT&limit=10")
    assert r.status_code == 200
    data = r.json()
    for article in data["articles"]:
        assert "XRP" in (article.get("symbolsMentioned") or article.get("symbols") or [])
