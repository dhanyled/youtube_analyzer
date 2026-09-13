"""HasData Google Trends API Connector."""

import os
from typing import Any

import httpx

from youtube_analyzer.connectors.base import BaseConnector
from youtube_analyzer.core.models import PlatformEnum


class HasDataTrendsConnector(BaseConnector):
    """Connector for HasData Google Trends API."""

    BASE_URL = "https://api.hasdata.com/scrape/google-trends"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("HASDATA_API_KEY")
        super().__init__(platform=PlatformEnum.GOOGLE_TRENDS, api_key=key)

    async def search(self, query: str, geo: str = "ID", **kwargs: Any) -> list[dict[str, Any]]:
        """
        Fetch interest over time and related queries.
        If no API key is set, returns structured mock data for development & CI testing.
        """
        if not self.api_key:
            return [
                {"query": f"{query} tutorial", "value": 100, "type": "rising"},
                {"query": f"{query} pemula", "value": 85, "type": "top"},
                {"query": f"biaya {query}", "value": 70, "type": "top"},
            ]

        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {"x-api-key": self.api_key}
            params = {"q": query, "geo": geo}
            response = await client.get(self.BASE_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("relatedQueries", [])
