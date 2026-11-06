"""Unit tests for search connectors (HasData & YouTube) ensuring 100% real data integrity."""

from unittest.mock import AsyncMock, MagicMock, patch

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
    mock_reg = [
        {
            "Wilayah": "Bali",
            "Kode": "ID-BA",
            "Indeks Minat": 100,
            "Tingkat Minat": "🔥 Sangat Tinggi",
        }
    ]
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


def test_youtube_connector_parse_count_text():
    """Verify numeric string parsing for YouTube stats."""
    connector = YouTubeConnector(api_key=None)
    assert connector._parse_count_text("14 subscriber") == 14
    assert connector._parse_count_text("6,17 rb subscriber") == 6170
    assert connector._parse_count_text("1,8 rb video") == 1800
    assert connector._parse_count_text("2,9 rb subscriber") == 2900
    assert connector._parse_count_text("1.2 jt subscriber") == 1200000
    assert connector._parse_count_text("543 x ditonton") == 543
    assert connector._parse_count_text("Belum ditonton") == 0
    assert connector._parse_count_text("") == 0
    assert connector._parse_count_text(None) == 0


@pytest.mark.asyncio
async def test_get_channel_summary_fallback_to_scrape():
    """Verify that when API key is None, channel summary automatically falls back to public scraping."""
    connector = YouTubeConnector(api_key="")
    connector.api_key = None
    mock_summary = {
        "channel_id": "UC_TEST",
        "title": "Test Channel",
        "handle": "@testchannel",
        "subscribers": 5000,
        "video_count": 50,
        "sample_analyzed": 10,
        "landscape_count": 8,
        "landscape_percentage": 80.0,
        "portrait_count": 2,
        "portrait_percentage": 20.0,
        "recent_top_video": {"title": "Top Video", "views": 1000},
        "all_time_top_video": {"title": "Top Video", "views": 1000},
        "videos": [],
    }
    with patch.object(
        connector, "_scrape_channel_public", new_callable=AsyncMock
    ) as mock_scrape:
        mock_scrape.return_value = mock_summary
        res = await connector.get_channel_summary_and_format_breakdown("@testchannel")
        assert res is not None
        assert res["title"] == "Test Channel"
        assert res["subscribers"] == 5000
        assert res["landscape_count"] == 8
        assert res["portrait_percentage"] == 20.0


@pytest.mark.asyncio
async def test_google_search_connector_paa():
    from youtube_analyzer.connectors.google import GoogleSearchConnector
    connector = GoogleSearchConnector()
    with patch.object(connector, "_fetch_prefix_suggestions", new_callable=AsyncMock) as mock_pfx:
        mock_pfx.side_effect = [
            ["bagaimana cara google ads bekerja", "bagaimana cara beriklan di google ads"],
            ["cara agar iklan google ads winning"],
            ["berapa biaya pasang google ads", "berapa biaya klik google ads"],
            ["berapa harga jasa kelola google ads"],
            ["apa itu google ads"],
            ["kenapa iklan google ads tidak tayang"],
            ["mengapa akun google ads ditangguhkan"],
            ["apakah google ads berbayar"],
            ["bisa kah pasang google ads tanpa kartu kredit"],
        ]
        paa = await connector.get_people_also_ask("google ads", hl="id", gl="ID")
        assert len(paa) > 0
        assert any("bagaimana cara" in p["question"].lower() for p in paa)
        assert any(p["intent"] == "HOW_TO" for p in paa)
        assert any(p["intent"] == "COMMERCIAL" for p in paa)
        assert all("?" in p["question"] for p in paa)
        assert all(p["google_key_moment"] is True for p in paa)


@pytest.mark.asyncio
async def test_youtube_connector_mine_competitor_comments():
    connector = YouTubeConnector(api_key="TEST_KEY")
    mock_comments = [
        {"author": "@budi", "text": "Mau tanya kak, iklan nya belum tayang ada solusinya?", "likes": 5, "published": "2026-01-01"},
        {"author": "@siti", "text": "Berapa biaya minimal untuk pasang iklan?", "likes": 12, "published": "2026-01-02"},
        {"author": "@spam", "text": "Hubungi wa 0812345678 untuk slot gacor", "likes": 0, "published": "2026-01-03"},
        {"author": "@andi", "text": "Mantap bang keren banget", "likes": 1, "published": "2026-01-04"},
        {"author": "@dian", "text": "Apakah bisa pasang iklan tanpa kartu kredit kak?", "likes": 8, "published": "2026-01-05"},
    ]
    with patch.object(connector, "fetch_video_comments", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_comments
        with patch.object(connector, "get_video_details", new_callable=AsyncMock) as mock_det:
            mock_det.return_value = {"title": "Tutorial Google Ads", "channel": "Kanal Guru", "views": "50K"}
            res = await connector.mine_competitor_comments(["vid123"])
            assert res["total_comments_analyzed"] == 5
            # Spam and generic praises should be filtered out
            assert res["total_questions_found"] == 3
            top_pp = res["top_pain_points"]
            assert len(top_pp) == 3
            # Check sorted by likes descending (12 likes first, then 8, then 5)
            assert top_pp[0]["likes"] == 12
            assert top_pp[0]["category"] == "COMMERCIAL"
            assert top_pp[1]["likes"] == 8
            assert top_pp[1]["category"] == "ELIGIBILITY"
            assert top_pp[2]["likes"] == 5
            assert top_pp[2]["category"] == "TROUBLESHOOTING"
            # Topic gap opportunities extracted
            assert len(res["topic_gap_opportunities"]) > 0


