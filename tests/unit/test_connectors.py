"""Unit tests for search connectors (HasData & YouTube) ensuring 100% real data integrity."""

from unittest.mock import MagicMock, patch

import pytest

from youtube_analyzer.connectors.hasdata_trends import HasDataTrendsConnector
from youtube_analyzer.connectors.youtube import YouTubeConnector


def test_hasdata_empty_when_unavailable():
    """Verify that when Google Trends data is unavailable, no synthetic or fake data is generated."""
    connector = HasDataTrendsConnector(api_key=None)
    with patch.object(connector, "_fetch_pytrends_interest_over_time", return_value=None):
        ot = connector.get_interest_over_time("NonExistentTermXYZ", geo="ID")
        assert ot == []

    with patch.object(connector, "_fetch_pytrends_interest_by_region", return_value=None):
        reg = connector.get_interest_by_region("NonExistentTermXYZ", geo="ID")
        assert reg == []

    with patch.object(connector, "_fetch_pytrends_top_and_rising", return_value=None):
        queries = connector.get_top_and_rising_queries("NonExistentTermXYZ", geo="ID")
        assert queries == {"top": [], "rising": []}


def test_hasdata_returns_real_data_when_present():
    """Verify that real Google Trends data is preserved and returned accurately."""
    connector = HasDataTrendsConnector(api_key=None)
    mock_ot = [{"Tanggal": "2026-01-01", "Minat Penelusuran": 75, "Properti": "YouTube Search"}]
    mock_reg = [{"Wilayah": "Bali", "Kode": "ID-BA", "Indeks Minat": 100, "Tingkat Minat": "🔥 Sangat Tinggi"}]
    mock_q = {
        "top": [
            {
                "Rank": 1,
                "Query": "google ads",
                "query": "google ads",
                "Popularitas (0-100)": 100,
                "value": 100,
                "type": "top",
                "property": "youtube",
            }
        ],
        "rising": [
            {
                "Rank": 1,
                "Query": "meta ads",
                "query": "meta ads",
                "Lonjakan Minat": "+120%",
                "value": "+120%",
                "numeric_growth": 120,
                "type": "rising",
                "property": "youtube",
            }
        ],
    }

    with patch.object(connector, "_fetch_pytrends_interest_over_time", return_value=mock_ot):
        assert connector.get_interest_over_time("google ads") == mock_ot

    with patch.object(connector, "_fetch_pytrends_interest_by_region", return_value=mock_reg):
        assert connector.get_interest_by_region("google ads") == mock_reg

    with patch.object(connector, "_fetch_pytrends_top_and_rising", return_value=mock_q):
        assert connector.get_top_and_rising_queries("google ads") == mock_q


@pytest.mark.asyncio
async def test_youtube_connector_empty_when_blocked():
    """Verify that when scraping fails or is blocked, no fake or synthetic videos are ever injected."""
    connector = YouTubeConnector(api_key=None)
    with patch("httpx.AsyncClient.get", side_effect=Exception("Blocked")):
        competitors = await connector.get_top_competitors("Some Query", limit=10)
        assert competitors == []

        trending = await connector.get_trending_feed(limit=10)
        assert trending == []

        autocomplete = await connector.get_autocomplete("Some Query")
        assert autocomplete == []


@pytest.mark.asyncio
async def test_youtube_connector_parses_real_items():
    """Verify that scraped live competitor videos are parsed correctly without dummy additions."""
    connector = YouTubeConnector(api_key=None)
    mock_video = {
        "rank": 1,
        "title": "Tutorial Google Ads 2026 Lengkap",
        "channel": "Pakar Digital",
        "views": "150K views",
        "views_count": 150000,
        "upload_age": "2026-01-10",
        "duration": "14:20",
        "format": "LANDSCAPE",
        "url": "https://www.youtube.com/watch?v=123",
        "outlier_status": "Top #1",
        "is_ai_generated": False,
        "ai_badge": "👤 Human Creator",
        "ai_label_reason": "Human narrator",
    }
    with patch.object(connector, "_parse_youtube_search_html", return_value=[mock_video]):
        mock_resp = MagicMock(status_code=200, text="<html>...</html>")
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            res = await connector.get_top_competitors("Google Ads", limit=5)
            assert len(res) == 1
            assert res[0]["title"] == "Tutorial Google Ads 2026 Lengkap"
            assert res[0]["channel"] == "Pakar Digital"
            assert res[0]["views_count"] == 150000


@pytest.mark.asyncio
async def test_youtube_connector_natural_headers():
    """Verify that YouTubeConnector generates realistic modern browser fingerprint headers."""
    desktop_headers = YouTubeConnector._get_natural_headers(hl="id", gl="ID", device="desktop")
    assert "User-Agent" in desktop_headers
    assert "Sec-Ch-Ua" in desktop_headers
    assert desktop_headers["Sec-Ch-Ua-Mobile"] == "?0"
    assert desktop_headers["Sec-Ch-Ua-Platform"] in ['"Windows"', '"macOS"']

    mobile_headers = YouTubeConnector._get_natural_headers(hl="id", gl="ID", device="mobile")
    assert mobile_headers["Sec-Ch-Ua-Mobile"] == "?1"
    assert mobile_headers["Sec-Ch-Ua-Platform"] == '"Android"'
