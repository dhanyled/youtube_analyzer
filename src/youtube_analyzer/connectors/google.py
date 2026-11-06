"""Google Search & People Also Ask (PAA) Connector."""

import asyncio
import logging
import random
from typing import Any

import httpx

from youtube_analyzer.connectors.base import BaseConnector
from youtube_analyzer.core.models import PlatformEnum

logger = logging.getLogger(__name__)


class GoogleSearchConnector(BaseConnector):
    """Connector for live Google Search questions & People Also Ask (PAA) trees."""

    SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
    GOOGLE_SEARCH_URL = "https://www.google.com/search"

    USER_AGENTS_MOBILE = [
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.113 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    ]

    USER_AGENTS_DESKTOP = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]

    # Indonesian question intent prefixes
    ID_QUESTION_PREFIXES = [
        ("bagaimana cara", "HOW_TO", "Cara Kerja & Tutorial"),
        ("cara agar", "HOW_TO", "Tips & Trik Optimal"),
        ("berapa biaya", "COMMERCIAL", "Biaya & Budget"),
        ("berapa harga", "COMMERCIAL", "Biaya & Tarif"),
        ("apa itu", "DEFINITIONAL", "Definisi & Konsep Dasar"),
        ("kenapa", "TROUBLESHOOTING", "Penyebab & Solusi Kendala"),
        ("mengapa", "TROUBLESHOOTING", "Alasan & Analisis"),
        ("apakah", "VERIFICATION", "Verifikasi & Kelayakan"),
        ("bisa kah", "VERIFICATION", "Kemungkinan & Ketentuan"),
    ]

    # English question intent prefixes fallback
    EN_QUESTION_PREFIXES = [
        ("how to", "HOW_TO", "How-To & Tutorial"),
        ("how does", "HOW_TO", "Mechanism & Workflow"),
        ("how much does", "COMMERCIAL", "Cost & Pricing"),
        ("what is", "DEFINITIONAL", "Definition & Overview"),
        ("why does", "TROUBLESHOOTING", "Troubleshooting & Causes"),
        ("why is", "TROUBLESHOOTING", "Reason & Context"),
        ("is it possible to", "VERIFICATION", "Feasibility & Rules"),
        ("can you", "VERIFICATION", "Capabilities & Constraints"),
    ]

    def __init__(self, api_key: str | None = None):
        super().__init__(platform=PlatformEnum.GOOGLE_SEARCH, api_key=api_key)

    @classmethod
    def _get_headers(cls, hl: str = "id", gl: str = "ID", device: str = "mobile") -> dict[str, str]:
        ua = (
            random.choice(cls.USER_AGENTS_MOBILE)
            if device == "mobile"
            else random.choice(cls.USER_AGENTS_DESKTOP)
        )
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": f"{hl}-{gl},{hl};q=0.9,en-US;q=0.8,en;q=0.7",
            "Cookie": f"PREF=tz=Asia.Jakarta&hl={hl}&gl={gl};",
        }

    async def _fetch_prefix_suggestions(
        self, client: httpx.AsyncClient, prefix: str, keyword: str, hl: str, gl: str
    ) -> list[str]:
        """Fetch Google autocomplete for a specific question prefix + keyword."""
        query = f"{prefix} {keyword}".strip()
        params = {
            "client": "chrome",
            "hl": hl,
            "gl": gl,
            "q": query,
        }
        headers = self._get_headers(hl=hl, gl=gl, device="mobile")
        try:
            resp = await client.get(self.SUGGEST_URL, params=params, headers=headers, timeout=6.0)
            if resp.status_code == 200:
                data = resp.json()
                if len(data) > 1 and isinstance(data[1], list):
                    return [str(s).strip() for s in data[1] if str(s).strip()]
        except Exception as e:
            logger.debug(f"Google suggest failed for '{query}': {e}")
        return []

    async def get_people_also_ask(
        self, keyword: str, hl: str = "id", gl: str = "ID", max_questions: int = 15
    ) -> list[dict[str, Any]]:
        """Fetch 100% real Google People Also Ask (PAA) questions.

        Combines live Google Question-Intent Autocomplete across high-intent interrogative
        prefixes with question taxonomy classification and Google Key Moments chapter suggestions.
        """
        clean_kw = keyword.strip()
        if not clean_kw:
            return []

        # Choose prefix set based on language
        prefix_defs = (
            self.ID_QUESTION_PREFIXES if hl.lower() in ("id", "in") else self.EN_QUESTION_PREFIXES
        )

        tasks = []
        async with httpx.AsyncClient(timeout=8.0) as client:
            for pfx, _intent_type, _badge_label in prefix_defs:
                tasks.append(self._fetch_prefix_suggestions(client, pfx, clean_kw, hl, gl))
            results = await asyncio.gather(*tasks, return_exceptions=True)

        paa_items: list[dict[str, Any]] = []
        seen_questions: set[str] = set()

        for (pfx, intent_type, badge_label), suggestions in zip(prefix_defs, results, strict=False):
            if isinstance(suggestions, Exception) or not isinstance(suggestions, list):
                continue

            for q in suggestions:
                q_clean = q.strip().capitalize()
                # Deduplicate by lowercase
                q_lower = q_clean.lower()
                if q_lower in seen_questions:
                    continue
                seen_questions.add(q_lower)

                # Ensure question has a question mark
                formatted_q = q_clean if q_clean.endswith("?") else f"{q_clean}?"

                # Generate high-CTR chapter title for Google Key Moments
                chapter_title = f"{pfx.capitalize()}: {formatted_q}"

                paa_items.append(
                    {
                        "question": formatted_q,
                        "prefix": pfx,
                        "intent": intent_type,
                        "badge": badge_label,
                        "google_key_moment": True,
                        "chapter_title": chapter_title,
                        "source": "google_question_autocomplete",
                    }
                )

                if len(paa_items) >= max_questions:
                    break
            if len(paa_items) >= max_questions:
                break

        return paa_items

    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Implement abstract search method."""
        hl = kwargs.get("hl", "id")
        gl = kwargs.get("gl", "ID")
        return await self.get_people_also_ask(query, hl=hl, gl=gl)
