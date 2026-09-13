"""Unit tests for search connectors (HasData & YouTube)."""

import pytest

from youtube_analyzer.connectors.hasdata_trends import HasDataTrendsConnector
from youtube_analyzer.connectors.youtube import YouTubeConnector
from youtube_analyzer.core.models import PlatformEnum


@pytest.mark.asyncio
async def test_hasdata_trends_offline_mock():
    connector = HasDataTrendsConnector(api_key=None)
    web_results = await connector.search(query="Google Ads UMKM", property_type="web")
    assert len(web_results) > 0
    assert any("jasa" in r["query"] or "biaya" in r["query"] for r in web_results)

    yt_results = await connector.get_youtube_trends(query="Google Ads UMKM")
    assert len(yt_results) > 0
    assert any("cara" in r["query"] or "tutorial" in r["query"] for r in yt_results)


@pytest.mark.asyncio
async def test_compare_google_vs_youtube():
    connector = HasDataTrendsConnector(api_key=None)
    comparison = await connector.compare_google_vs_youtube(query="Google Ads UMKM")
    assert "google_web_trends" in comparison
    assert "youtube_trends" in comparison
    assert len(comparison["youtube_trends"]) > 0


@pytest.mark.asyncio
async def test_youtube_connector_search():
    connector = YouTubeConnector(api_key=None)
    results = await connector.search(query="Google Ads UMKM")
    assert len(results) > 0
    assert results[0]["platform"] == PlatformEnum.YOUTUBE_SEARCH


@pytest.mark.asyncio
async def test_youtube_trending_feed():
    connector = YouTubeConnector(api_key=None)
    # Test desktop trending
    desktop_trending = await connector.get_trending_feed(
        gl="ID", hl="id", category="now", device="desktop", limit=5
    )
    assert len(desktop_trending) > 0
    assert "title" in desktop_trending[0]
    assert "views" in desktop_trending[0]
    assert "format" in desktop_trending[0]
    assert desktop_trending[0]["device"] == "DESKTOP"

    # Test mobile trending
    mobile_trending = await connector.get_trending_feed(
        gl="US", hl="en", category="gaming", device="mobile", limit=5
    )
    assert len(mobile_trending) > 0
    assert mobile_trending[0]["device"] == "MOBILE"
    assert mobile_trending[0]["location"] == "US"

