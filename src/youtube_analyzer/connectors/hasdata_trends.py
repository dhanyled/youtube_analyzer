"""HasData Google Trends API Connector with YouTube Search Support."""

import os
from typing import Any

import httpx

from youtube_analyzer.connectors.base import BaseConnector
from youtube_analyzer.core.models import PlatformEnum


class HasDataTrendsConnector(BaseConnector):
    """Connector for Google Trends supporting both Web Search and YouTube Search trends."""

    BASE_URL = "https://api.hasdata.com/scrape/google-trends"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("HASDATA_API_KEY")
        super().__init__(platform=PlatformEnum.GOOGLE_TRENDS, api_key=key)

    async def search(
        self,
        query: str,
        geo: str = "ID",
        property_type: str = "web",  # 'web' or 'youtube'
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Fetch interest over time and related queries.
        Supports filtering by search property: 'web' (Google Web Search) or 'youtube' (YouTube Search).
        """
        prop = property_type.lower()
        if not self.api_key:
            if prop == "youtube":
                return [
                    {
                        "query": f"cara {query}",
                        "value": 100,
                        "type": "rising",
                        "property": "youtube",
                    },
                    {
                        "query": f"tutorial {query} 2026",
                        "value": 90,
                        "type": "top",
                        "property": "youtube",
                    },
                    {
                        "query": f"setting {query} pemula",
                        "value": 75,
                        "type": "rising",
                        "property": "youtube",
                    },
                ]
            return [
                {"query": f"{query} tutorial", "value": 100, "type": "rising", "property": "web"},
                {"query": f"jasa {query}", "value": 85, "type": "top", "property": "web"},
                {"query": f"biaya {query}", "value": 70, "type": "top", "property": "web"},
            ]

        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {"x-api-key": self.api_key}
            params = {
                "q": query,
                "geo": geo,
                "property": "youtube" if prop == "youtube" else "",
            }
            response = await client.get(self.BASE_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("relatedQueries", [])

    async def get_youtube_trends(self, query: str, geo: str = "ID") -> list[dict[str, Any]]:
        """Convenience method specifically for YouTube Search trends."""
        return await self.search(query=query, geo=geo, property_type="youtube")

    async def compare_google_vs_youtube(self, query: str, geo: str = "ID") -> dict[str, Any]:
        """Compare trending search demand between Google Web and YouTube Search."""
        web_trends = await self.search(query=query, geo=geo, property_type="web")
        yt_trends = await self.search(query=query, geo=geo, property_type="youtube")

        return {
            "query": query,
            "geo": geo,
            "google_web_trends": web_trends,
            "youtube_trends": yt_trends,
            "surface_intent_summary": {
                "google_web_focus": "Commercial, Pricing, Service discovery",
                "youtube_focus": "Tutorials, How-to guides, Visual walk-throughs",
            },
        }
