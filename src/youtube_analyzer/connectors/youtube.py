"""YouTube SERP & Autocomplete Connector."""

import os
from typing import Any

import httpx

from youtube_analyzer.connectors.base import BaseConnector
from youtube_analyzer.core.models import PlatformEnum


class YouTubeConnector(BaseConnector):
    """Connector for YouTube Search & Autocomplete queries."""

    SUGGEST_URL = "https://suggestqueries.google.com/complete/search"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("YOUTUBE_API_KEY")
        super().__init__(platform=PlatformEnum.YOUTUBE_SEARCH, api_key=key)

    async def get_autocomplete(
        self, query: str, client_type: str = "youtube", hl: str = "id"
    ) -> list[str]:
        """Fetch YouTube autocomplete suggestions (public endpoint)."""
        params = {
            "client": client_type,
            "ds": "yt",
            "q": query,
            "hl": hl,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.SUGGEST_URL, params=params)
                if resp.status_code == 200:
                    # Returns JSONP or JSON format: window.google.ac.h(["query",[["sug1",0,[...]],...]])
                    text = resp.text
                    start = text.find("(")
                    end = text.rfind(")")
                    if start != -1 and end != -1:
                        import json

                        parsed = json.loads(text[start + 1 : end])
                        if len(parsed) > 1 and isinstance(parsed[1], list):
                            items = [
                                item[0] for item in parsed[1] if isinstance(item, list) and item
                            ]
                            if items:
                                return items
        except Exception:
            pass

        # Fallback offline suggestions
        return [
            f"{query} tutorial",
            f"{query} pemula",
            f"cara {query}",
            f"{query} 2026",
        ]

    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch search queries / video results."""
        suggestions = await self.get_autocomplete(query)
        return [{"query": s, "platform": PlatformEnum.YOUTUBE_SEARCH} for s in suggestions]
