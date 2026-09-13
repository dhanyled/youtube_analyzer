"""Unit tests for search connectors (HasData & YouTube)."""

import pytest

from youtube_analyzer.connectors.hasdata_trends import HasDataTrendsConnector
from youtube_analyzer.connectors.youtube import YouTubeConnector
from youtube_analyzer.core.models import PlatformEnum


@pytest.mark.asyncio
async def test_hasdata_trends_offline_mock():
    connector = HasDataTrendsConnector(api_key=None)
    results = await connector.search(query="Google Ads UMKM")
    assert len(results) > 0
    assert any("tutorial" in r["query"] or "pemula" in r["query"] for r in results)


@pytest.mark.asyncio
async def test_youtube_connector_search():
    connector = YouTubeConnector(api_key=None)
    results = await connector.search(query="Google Ads UMKM")
    assert len(results) > 0
    assert results[0]["platform"] == PlatformEnum.YOUTUBE_SEARCH
