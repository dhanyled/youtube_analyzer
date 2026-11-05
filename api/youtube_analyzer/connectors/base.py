"""Abstract Base Connector for Search Surfaces."""

from abc import ABC, abstractmethod
from typing import Any

from youtube_analyzer.core.models import PlatformEnum


class BaseConnector(ABC):
    """Base interface for all search surface connectors (HasData, YouTube, GKP, SERP)."""

    def __init__(self, platform: PlatformEnum, api_key: str | None = None):
        self.platform = platform
        self.api_key = api_key

    @abstractmethod
    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch search results, autocomplete suggestions, or metrics for a given query."""
        pass
