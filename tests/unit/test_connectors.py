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
    assert "youtube_interest_over_time" in comparison
    assert len(comparison["youtube_interest_over_time"]) == 52
    assert "google_interest_over_time" in comparison
    assert len(comparison["google_interest_over_time"]) == 52
    assert "interest_by_region" in comparison
    assert len(comparison["interest_by_region"]) > 0
    assert "youtube_top_queries" in comparison
    assert len(comparison["youtube_top_queries"]) == 50
    assert "youtube_rising_queries" in comparison
    assert len(comparison["youtube_rising_queries"]) == 50
    assert "google_top_queries" in comparison
    assert len(comparison["google_top_queries"]) == 50
    assert "google_rising_queries" in comparison
    assert len(comparison["google_rising_queries"]) == 50


def test_hasdata_interest_over_time():
    connector = HasDataTrendsConnector(api_key=None)
    ot = connector.get_interest_over_time("Google Ads UMKM", geo="ID", property_type="youtube")
    assert len(ot) == 52
    assert all("Tanggal" in item and "Minat Penelusuran" in item for item in ot)
    assert all(0 <= item["Minat Penelusuran"] <= 100 for item in ot)


def test_hasdata_interest_by_region():
    connector = HasDataTrendsConnector(api_key=None)
    reg_id = connector.get_interest_by_region("Google Ads UMKM", geo="ID")
    assert len(reg_id) > 0
    assert reg_id[0]["Wilayah"] == "DKI Jakarta"
    assert all("Indeks Minat" in item for item in reg_id)

    reg_ww = connector.get_interest_by_region("Google Ads UMKM", geo="")
    assert len(reg_ww) > 0
    assert any(item["Wilayah"] == "Indonesia" for item in reg_ww)


def test_hasdata_top_and_rising_queries_50():
    connector = HasDataTrendsConnector(api_key=None)
    queries = connector.get_top_and_rising_queries(
        "Google Ads UMKM", geo="ID", property_type="youtube"
    )
    assert len(queries["top"]) == 50
    assert len(queries["rising"]) == 50
    assert queries["top"][0]["Rank"] == 1
    assert queries["top"][49]["Rank"] == 50
    assert "Breakout" in queries["rising"][0]["Lonjakan Minat"]


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


@pytest.mark.asyncio
async def test_youtube_top_competitors_10():
    connector = YouTubeConnector(api_key=None)
    competitors = await connector.get_top_competitors("Google Ads UMKM", limit=10)
    assert len(competitors) == 10
    assert competitors[0]["rank"] == 1
    assert competitors[9]["rank"] == 10
    assert all(c["format"] in ["LANDSCAPE", "SHORTS"] for c in competitors)
    assert all("title" in c and "views" in c for c in competitors)


@pytest.mark.asyncio
async def test_youtube_trending_feed_10():
    connector = YouTubeConnector(api_key=None)
    trending = await connector.get_trending_feed(limit=10)
    assert len(trending) == 10
    assert trending[0]["rank"] == 1
    assert trending[9]["rank"] == 10
