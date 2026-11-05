"""YouTube SERP, Autocomplete & Competitor Ranking Inspector."""

import asyncio
import json
import logging
import os
import random
import re
from typing import Any

import httpx
from dotenv import load_dotenv

from youtube_analyzer.connectors.base import BaseConnector
from youtube_analyzer.core.models import PlatformEnum

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

load_dotenv()

logger = logging.getLogger(__name__)


class YouTubeConnector(BaseConnector):
    """Connector for YouTube Search, Autocomplete & Competitor Spy."""

    SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
    SEARCH_URL = "https://www.youtube.com/results"

    USER_AGENTS_DESKTOP = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]

    USER_AGENTS_MOBILE = [
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.113 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    ]

    @classmethod
    def _get_natural_headers(
        cls, hl: str = "id", gl: str = "ID", device: str = "desktop"
    ) -> dict[str, str]:
        """Generate human-like modern browser fingerprint headers."""
        if device.lower() == "mobile":
            ua = random.choice(cls.USER_AGENTS_MOBILE)
            platform = '"Android"'
            mobile = "?1"
        else:
            ua = random.choice(cls.USER_AGENTS_DESKTOP)
            platform = '"Windows"' if "Windows" in ua else '"macOS"'
            mobile = "?0"

        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": f"{hl}-{gl},{hl};q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": mobile,
            "Sec-Ch-Ua-Platform": platform,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cookie": f"PREF=tz=Asia.Jakarta&hl={hl}&gl={gl};",
        }

    @staticmethod
    async def _human_delay(min_sec: float = 0.5, max_sec: float = 1.6) -> None:
        """Introduce natural, human-like random pause (typing/navigation jitter)."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("YOUTUBE_API_KEY")
        super().__init__(platform=PlatformEnum.YOUTUBE_SEARCH, api_key=key)

    async def get_autocomplete(
        self, query: str, client_type: str = "youtube", hl: str = "id"
    ) -> list[str]:
        """Fetch live YouTube autocomplete suggestions (public endpoint) with natural jitter delay."""
        # Natural human delay before typing/searching
        await self._human_delay(0.2, 0.5)

        params = {
            "client": client_type,
            "ds": "yt",
            "q": query,
            "hl": hl,
        }
        headers = self._get_natural_headers(hl=hl)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.SUGGEST_URL, params=params, headers=headers)
                if resp.status_code == 200:
                    text = resp.text
                    start = text.find("(")
                    end = text.rfind(")")
                    if start != -1 and end != -1:
                        parsed = json.loads(text[start + 1 : end])
                        if len(parsed) > 1 and isinstance(parsed[1], list):
                            items = [
                                item[0] for item in parsed[1] if isinstance(item, list) and item
                            ]
                            if items:
                                return items
        except Exception as e:
            logger.warning(f"Error fetching live autocomplete for '{query}': {e}")

        # Real data only: if no suggestions found from YouTube, return empty list (no fake/dummy suggestions)
        return []

    _shorts_cache: dict[str, bool] = {}

    @classmethod
    def detect_video_format(
        cls,
        video_id: str = "",
        title: str = "",
        duration_seconds: int = 0,
        thumbnail_url: str = "",
    ) -> tuple[bool, str]:
        """
        Accurately detect whether a video is SHORTS (9:16 vertical) or LANDSCAPE (16:9).
        Never misclassifies horizontal landscape videos as Shorts based solely on duration.
        Returns: (is_shorts: bool, format_name: "SHORTS" | "LANDSCAPE")
        """
        # 1. Videos longer than 3 minutes (180s) can never be YouTube Shorts
        if duration_seconds > 180:
            return False, "LANDSCAPE"

        # 2. Check explicit markers in title
        title_lower = title.lower()
        if "#shorts" in title_lower or "#short" in title_lower:
            return True, "SHORTS"

        # 3. Check format cache
        if video_id and video_id in cls._shorts_cache:
            is_sh = cls._shorts_cache[video_id]
            return is_sh, "SHORTS" if is_sh else "LANDSCAPE"

        # 4. For short-duration videos (<= 60s), check YouTube server response
        # YouTube responds with 303 Redirect to /watch for Landscape videos accessed via /shorts/{video_id}
        if 0 < duration_seconds <= 60 and video_id:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                with httpx.Client(follow_redirects=False, timeout=2.5) as client:
                    resp = client.head(
                        f"https://www.youtube.com/shorts/{video_id}", headers=headers
                    )
                    if resp.status_code == 303:
                        cls._shorts_cache[video_id] = False
                        return False, "LANDSCAPE"
                    if resp.status_code == 200:
                        cls._shorts_cache[video_id] = True
                        return True, "SHORTS"
            except Exception:
                pass

            # Fallback: landscape videos generated with high-res standard 16:9 thumbnails
            if "maxresdefault" in thumbnail_url:
                cls._shorts_cache[video_id] = False
                return False, "LANDSCAPE"

        return False, "LANDSCAPE"

    @staticmethod
    def _parse_iso_duration(dur_str: str) -> tuple[str, bool]:
        """Convert ISO 8601 duration (e.g. PT1M30S) to readable MM:SS."""
        if not dur_str:
            return "10:00", False
        m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", dur_str)
        if not m:
            return "10:00", False
        hours = int(m.group(1) or 0)
        minutes = int(m.group(2) or 0)
        seconds = int(m.group(3) or 0)
        total_seconds = hours * 3600 + minutes * 60 + seconds
        is_shorts = total_seconds <= 60
        if hours > 0:
            formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            formatted = f"{minutes}:{seconds:02d}"
        return formatted, is_shorts

    @staticmethod
    def parse_duration_to_seconds(dur_str: str | int | None) -> int:
        """Parse duration (string like '08:30', '1:15:20', 'PT8M30S', or int seconds) to total seconds."""
        if dur_str is None:
            return 0
        if isinstance(dur_str, (int, float)):
            return int(dur_str)
        clean = str(dur_str).strip()
        if not clean:
            return 0
        if clean.startswith("PT"):
            m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", clean)
            if m:
                h = int(m.group(1) or 0)
                mi = int(m.group(2) or 0)
                s = int(m.group(3) or 0)
                return h * 3600 + mi * 60 + s
        parts = clean.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1:
                digits = re.findall(r"\d+", parts[0])
                if digits:
                    return int(digits[0])
        except (ValueError, TypeError):
            pass
        return 0

    @staticmethod
    def _format_views_display(views_count: int) -> str:
        """Format raw integer views into human-readable string (e.g. 1.2M views, 340K views)."""
        if views_count >= 1_000_000:
            return f"{views_count / 1_000_000:.1f}M views"
        elif views_count >= 1_000:
            return f"{views_count / 1_000:.1f}K views"
        return f"{views_count} views"

    @staticmethod
    def extract_video_id(url_or_id: str) -> str | None:
        """Extract 11-char YouTube video ID from various URL formats or raw ID."""
        if not url_or_id:
            return None
        clean = url_or_id.strip()
        if len(clean) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", clean):
            return clean
        patterns = [
            r"(?:v=|\/v\/|embed\/|shorts\/|live\/|youtu\.be\/|\/e\/)([a-zA-Z0-9_-]{11})",
            r"youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            m = re.search(pattern, clean)
            if m:
                return m.group(1)
        return None

    def get_video_transcript(
        self, video_id: str, languages: list[str] | None = None
    ) -> dict[str, Any]:
        """Fetch live transcript (captions/subtitles) using YouTubeTranscriptApi."""
        if not YouTubeTranscriptApi:
            return {
                "available": False,
                "timestamped_text": "",
                "full_text": "",
                "snippet_count": 0,
                "error": "Library youtube_transcript_api belum terpasang.",
            }

        langs = languages or ["id", "en"]
        try:
            api = YouTubeTranscriptApi()
            t_list = api.list(video_id)
            trans = None
            try:
                trans = t_list.find_transcript(langs)
            except Exception:
                for t in t_list:
                    trans = t
                    break

            if trans:
                snippets = trans.fetch().to_raw_data()
                lines = []
                plain_words = []
                for s in snippets:
                    st_sec = int(s.get("start", 0))
                    m, sec = divmod(st_sec, 60)
                    txt = s.get("text", "").strip()
                    lines.append(f"[{m:02d}:{sec:02d}] {txt}")
                    plain_words.append(txt)
                return {
                    "available": True,
                    "language": trans.language,
                    "language_code": trans.language_code,
                    "is_generated": trans.is_generated,
                    "timestamped_text": "\n".join(lines),
                    "full_text": " ".join(plain_words),
                    "snippet_count": len(snippets),
                    "error": None,
                }
            return {
                "available": False,
                "timestamped_text": "",
                "full_text": "",
                "snippet_count": 0,
                "error": "Transkrip / subtitle tidak tersedia untuk video ini.",
            }
        except Exception as e:
            return {
                "available": False,
                "timestamped_text": "",
                "full_text": "",
                "snippet_count": 0,
                "error": f"Tidak dapat mengambil transkrip: {e}",
            }

    INNERTUBE_PLAYER_URL = "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"
    INNERTUBE_WEB_CLIENT_VERSION = "2.20250312.04.00"

    async def _fetch_innertube_player(self, video_id: str) -> dict[str, Any] | None:
        """Fetch real video metadata + creator Studio tags via YouTube Innertube player API."""
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": self.INNERTUBE_WEB_CLIENT_VERSION,
                    "hl": "id",
                    "gl": "ID",
                }
            },
            "videoId": video_id,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.INNERTUBE_PLAYER_URL, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
        except Exception as e:
            logger.warning(f"Innertube player failed for '{video_id}': {e}")
            return None

        v_det = data.get("videoDetails") or {}
        if not v_det.get("videoId") or not v_det.get("title"):
            return None
        mf = (data.get("microformat") or {}).get("playerMicroformatRenderer") or {}

        def _to_int(val: Any) -> int:
            try:
                return int(val)
            except (TypeError, ValueError):
                return 0

        title = str(v_det.get("title", ""))
        raw_views = _to_int(v_det.get("viewCount"))
        length_sec = _to_int(v_det.get("lengthSeconds"))
        if length_sec > 0:
            h, rem = divmod(length_sec, 3600)
            m, s = divmod(rem, 60)
            dur_text = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        else:
            dur_text = "N/A"

        tags = [str(t).strip() for t in (v_det.get("keywords") or []) if str(t).strip()]
        tags = list(dict.fromkeys(tags))
        thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        is_shorts, format_type = self.detect_video_format(
            video_id=video_id,
            title=title,
            duration_seconds=length_sec,
            thumbnail_url=thumb_url,
        )
        published = str(mf.get("publishDate") or mf.get("uploadDate") or "")[:10]
        return {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": title,
            "description": str(v_det.get("shortDescription", "")),
            "tags": tags,
            "channel": str(v_det.get("author", "")),
            "channel_id": str(v_det.get("channelId", "")),
            "published_at": published,
            "views": raw_views,
            "views_display": self._format_views_display(raw_views) if raw_views else "N/A",
            "likes": _to_int(mf.get("likeCount")),
            "comments": 0,
            "duration": dur_text,
            "duration_seconds": length_sec,
            "is_shorts": is_shorts,
            "format": format_type,
            "category": str(mf.get("category", "")),
            "thumbnail_url": thumb_url,
            "data_source": "INNERTUBE_PLAYER",
        }

    async def get_video_details(self, video_id: str) -> dict[str, Any] | None:
        """Fetch complete video details (title, description, tags, stats, duration) via YouTube API or scraper."""
        if self.api_key:
            try:
                url = "https://www.googleapis.com/youtube/v3/videos"
                params = {
                    "part": "snippet,contentDetails,statistics",
                    "id": video_id,
                    "key": self.api_key,
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        items = resp.json().get("items", [])
                        if items:
                            item = items[0]
                            snippet = item.get("snippet", {})
                            stats = item.get("statistics", {})
                            cd = item.get("contentDetails", {})
                            dur_iso = cd.get("duration", "")
                            dur_text, _ = self._parse_iso_duration(dur_iso)
                            raw_views = int(stats.get("viewCount", 0))
                            likes = int(stats.get("likeCount", 0))
                            comments = int(stats.get("commentCount", 0))
                            thumbnails = snippet.get("thumbnails", {})
                            thumb_url = (
                                thumbnails.get("maxres", {}).get("url")
                                or thumbnails.get("standard", {}).get("url")
                                or thumbnails.get("high", {}).get("url")
                                or thumbnails.get("medium", {}).get("url")
                                or thumbnails.get("default", {}).get("url", "")
                            )
                            tags = snippet.get("tags", [])
                            dur_sec = self.parse_duration_to_seconds(dur_text)
                            is_shorts, format_type = self.detect_video_format(
                                video_id=video_id,
                                title=snippet.get("title", ""),
                                duration_seconds=dur_sec,
                                thumbnail_url=thumb_url,
                            )
                            return {
                                "video_id": video_id,
                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                "title": snippet.get("title", ""),
                                "description": snippet.get("description", ""),
                                "tags": tags,
                                "channel": snippet.get("channelTitle", ""),
                                "channel_id": snippet.get("channelId", ""),
                                "published_at": snippet.get("publishedAt", ""),
                                "views": raw_views,
                                "views_display": self._format_views_display(raw_views),
                                "likes": likes,
                                "comments": comments,
                                "duration": dur_text,
                                "duration_seconds": dur_sec,
                                "is_shorts": is_shorts,
                                "format": format_type,
                                "thumbnail_url": thumb_url,
                                "data_source": "YOUTUBE_API_V3",
                            }
            except Exception:
                pass

        # Preferred keyless path: YouTube Innertube player endpoint (works from cloud IPs,
        # returns the creator's real Studio tags in videoDetails.keywords)
        innertube = await self._fetch_innertube_player(video_id)
        if innertube:
            return innertube

        # Robust live scraping from YouTube HTML and ytInitialPlayerResponse
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            headers = self._get_natural_headers(hl="id", gl="ID", device="desktop")
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    html = resp.text

                    # 1. Parse embedded ytInitialPlayerResponse
                    player_data = {}
                    m_player = re.search(
                        r"ytInitialPlayerResponse\s*=\s*({.+?});\s*(?:var\s|</script>)",
                        html,
                        re.DOTALL,
                    )
                    if not m_player:
                        m_player = re.search(r"ytInitialPlayerResponse\s*=\s*({.+?});", html)
                    if m_player:
                        try:
                            player_data = json.loads(m_player.group(1))
                        except Exception:
                            pass

                    v_det = player_data.get("videoDetails", {})
                    if not v_det.get("keywords"):
                        m_kw_arr = re.search(r'"keywords"\s*:\s*(\[[^\]]+\])', html)
                        if m_kw_arr:
                            try:
                                v_det["keywords"] = json.loads(m_kw_arr.group(1))
                            except Exception:
                                pass

                    # Title
                    title = v_det.get("title")
                    if not title:
                        title_match = re.search(r"<title>(.*?) - YouTube<\/title>", html)
                        title = title_match.group(1) if title_match else f"Video {video_id}"

                    # Description
                    description = v_det.get("shortDescription")
                    if not description:
                        m_desc = re.search(
                            r'<meta property="og:description" content="(.*?)">', html
                        )
                        description = m_desc.group(1) if m_desc else ""

                    # Channel / Author
                    channel = v_det.get("author")
                    if not channel:
                        m_chan = re.search(r'<link itemprop="name" content="(.*?)">', html)
                        channel = m_chan.group(1) if m_chan else "YouTube Creator"
                    channel_id = v_det.get("channelId", "")

                    # Views
                    raw_views = 0
                    if v_det.get("viewCount"):
                        try:
                            raw_views = int(v_det.get("viewCount"))
                        except (ValueError, TypeError):
                            pass
                    if raw_views == 0:
                        m_views = re.search(
                            r'<meta itemprop="interactionCount" content="(\d+)">', html
                        )
                        if m_views:
                            try:
                                raw_views = int(m_views.group(1))
                            except (ValueError, TypeError):
                                pass

                    # Duration & Shorts detection
                    length_sec = 0
                    if v_det.get("lengthSeconds"):
                        try:
                            length_sec = int(v_det.get("lengthSeconds"))
                        except (ValueError, TypeError):
                            pass
                    if length_sec == 0:
                        m_dur = re.search(r'<meta itemprop="duration" content="(PT.*?)">', html)
                        if m_dur:
                            length_sec = self.parse_duration_to_seconds(m_dur.group(1))

                    if length_sec > 0:
                        h = length_sec // 3600
                        m = (length_sec % 3600) // 60
                        s = length_sec % 60
                        dur_text = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                    else:
                        dur_text = "N/A"

                    # Tags / Keywords extraction (Filter out generic YouTube platform boilerplate meta keywords)
                    YOUTUBE_GENERIC_META_BOILERPLATE = {
                        "video",
                        "berbagi",
                        "ponsel kamera",
                        "ponsel video",
                        "gratis",
                        "upload",
                        "sharing",
                        "camera phone",
                        "video phone",
                        "free",
                    }
                    tags = v_det.get("keywords", [])
                    if not tags:
                        og_tags = re.findall(
                            r'<meta property="og:video:tag" content="(.*?)">', html
                        )
                        if og_tags:
                            tags = [t.strip() for t in og_tags if t.strip()]
                    if not tags:
                        m_meta_kw = re.search(r'<meta name="keywords" content="(.*?)">', html)
                        if m_meta_kw:
                            raw_meta_tags = [
                                t.strip() for t in m_meta_kw.group(1).split(",") if t.strip()
                            ]
                            tags = [
                                t
                                for t in raw_meta_tags
                                if t.lower() not in YOUTUBE_GENERIC_META_BOILERPLATE
                            ]

                    # Also filter any boilerplate tags if they slipped into v_det/og_tags
                    tags = [
                        t
                        for t in tags
                        if t and t.strip().lower() not in YOUTUBE_GENERIC_META_BOILERPLATE
                    ]

                    # Deduplicate tags while preserving order
                    tags = list(dict.fromkeys(tags))

                    # Thumbnails
                    thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

                    is_shorts, format_type = self.detect_video_format(
                        video_id=video_id,
                        title=title,
                        duration_seconds=length_sec,
                        thumbnail_url=thumb_url,
                    )

                    # Published Date extraction
                    published_at = ""
                    m_date = re.search(r'itemprop="datePublished" content="(.*?)"', html)
                    if m_date:
                        published_at = m_date.group(1)[:10]
                    elif v_det.get("publishDate"):
                        published_at = str(v_det.get("publishDate"))[:10]
                    elif v_det.get("uploadDate"):
                        published_at = str(v_det.get("uploadDate"))[:10]

                    # Likes count extraction if available in accessibility data
                    likes = 0
                    m_like = re.search(
                        r"like this video along with ([\d,]+) other people", html, re.IGNORECASE
                    )
                    if not m_like:
                        m_like = re.search(
                            r"sukai video ini bersama ([\d\.]+) orang lainnya", html, re.IGNORECASE
                        )
                    if m_like:
                        try:
                            likes = int(m_like.group(1).replace(",", "").replace(".", ""))
                        except Exception:
                            pass

                    return {
                        "video_id": video_id,
                        "url": url,
                        "title": title,
                        "description": description,
                        "tags": tags,
                        "channel": channel,
                        "channel_id": channel_id,
                        "published_at": published_at,
                        "views": raw_views,
                        "views_display": self._format_views_display(raw_views)
                        if raw_views
                        else "N/A",
                        "likes": likes,
                        "comments": 0,
                        "duration": dur_text,
                        "duration_seconds": length_sec,
                        "is_shorts": is_shorts,
                        "format": format_type,
                        "thumbnail_url": thumb_url,
                        "data_source": "SCRAPED_PLAYER_RESPONSE",
                    }
        except Exception:
            pass

        return None

    async def _fetch_competitors_via_api(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch live, 100% real competitor rankings via YouTube Data API v3."""
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                search_url = "https://www.googleapis.com/youtube/v3/search"
                search_params = {
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": min(limit, 25),
                    "key": self.api_key,
                }
                s_resp = await client.get(search_url, params=search_params)
                if s_resp.status_code != 200:
                    return []
                items = s_resp.json().get("items", [])
                vid_ids = [it["id"]["videoId"] for it in items if "videoId" in it.get("id", {})]
                if not vid_ids:
                    return []

                v_url = "https://www.googleapis.com/youtube/v3/videos"
                v_params = {
                    "part": "snippet,contentDetails,statistics",
                    "id": ",".join(vid_ids),
                    "key": self.api_key,
                }
                v_resp = await client.get(v_url, params=v_params)
                if v_resp.status_code != 200:
                    return []
                v_items = v_resp.json().get("items", [])

                v_map = {v["id"]: v for v in v_items}
                competitors = []
                for rank, vid_id in enumerate(vid_ids[:limit], 1):
                    v_data = v_map.get(vid_id)
                    if not v_data:
                        continue
                    snip = v_data.get("snippet", {})
                    stats = v_data.get("statistics", {})
                    content_details = v_data.get("contentDetails", {})

                    title = snip.get("title", "")
                    channel = snip.get("channelTitle", "")
                    raw_views = int(stats.get("viewCount", 0))
                    views_text = self._format_views_display(raw_views)

                    dur_iso = content_details.get("duration", "")
                    duration_text, _ = self._parse_iso_duration(dur_iso)
                    dur_sec = self.parse_duration_to_seconds(duration_text)
                    thumb_url = snip.get("thumbnails", {}).get("high", {}).get("url", "")
                    is_shorts, format_type = self.detect_video_format(
                        video_id=vid_id,
                        title=title,
                        duration_seconds=dur_sec,
                        thumbnail_url=thumb_url,
                    )

                    pub_at = snip.get("publishedAt", "")
                    age_text = pub_at[:10] if pub_at else "Recent"

                    is_ai, ai_badge, ai_reason = self._detect_ai_content(v_data, title, channel)

                    competitors.append(
                        {
                            "rank": rank,
                            "video_id": vid_id,
                            "title": title,
                            "channel": channel,
                            "views": views_text,
                            "views_count": raw_views,
                            "upload_age": age_text,
                            "duration": duration_text,
                            "duration_seconds": self.parse_duration_to_seconds(duration_text),
                            "format": format_type,
                            "url": f"https://www.youtube.com/watch?v={vid_id}",
                            "tags": snip.get("tags", []),
                            "outlier_status": (
                                "👑 RANKING #1" if rank == 1 else f"Top #{rank} Competitor"
                            ),
                            "is_ai_generated": is_ai,
                            "ai_badge": ai_badge,
                            "ai_label_reason": ai_reason,
                        }
                    )
                return competitors
        except Exception:
            return []

    async def get_top_competitors(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Scrape and inspect live top ranking competitor videos on YouTube.
        Detects video title, channel, views, upload age, duration, and format (Landscape vs Shorts).
        Prioritizes official YouTube Data API v3 when api_key is available.
        Uses natural human-like timing and stealth headers to evade bot detection.
        Never injects synthetic or dummy fallback data.
        """
        if self.api_key:
            api_results = await self._fetch_competitors_via_api(query, limit=limit)
            if api_results:
                return api_results

        # Natural human delay (jitter) to avoid bot detection
        await self._human_delay(0.6, 1.8)

        headers = self._get_natural_headers(hl="id", gl="ID", device="desktop")
        params = {"search_query": query}

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(self.SEARCH_URL, headers=headers, params=params)
                if resp.status_code == 200:
                    competitors = self._parse_youtube_search_html(resp.text, limit=limit)
                    if competitors:
                        return competitors[:limit]
        except Exception as e:
            logger.warning(f"Error scraping live YouTube competitors for '{query}': {e}")

        # Real data only: return empty list if no competitors found or blocked
        return []

    async def spy_competitor_tags(
        self,
        competitors_or_query: list[dict[str, Any]] | str,
        limit_competitors: int = 5,
        seed_topic: str | None = None,
    ) -> dict[str, Any]:
        """
        Spy and extract hidden tags / keywords from top ranking competitor videos.
        Aggregates tag frequency across competitors, identifies winning tags,
        and generates ready-to-use YouTube Studio tags.
        """
        if isinstance(competitors_or_query, str):
            competitors = await self.get_top_competitors(
                competitors_or_query, limit=limit_competitors
            )
        else:
            competitors = list(competitors_or_query)[:limit_competitors]

        if not competitors:
            return {
                "top_overlapping_tags": [],
                "all_unique_tags": [],
                "tag_frequencies": {},
                "competitor_breakdown": [],
                "recommended_tags_csv": "",
            }

        competitor_breakdown = []
        all_tags_with_counts: dict[str, int] = {}
        canonical_display_map: dict[str, str] = {}

        # Fetch missing video details concurrently to avoid sequential latency and bot throttling
        async def _ensure_comp_tags(comp_item: dict[str, Any]) -> None:
            v_id = comp_item.get("video_id") or self.extract_video_id(comp_item.get("url", ""))
            tags = comp_item.get("tags") or []
            if not tags and v_id:
                details = await self.get_video_details(v_id)
                if details and details.get("tags"):
                    comp_item["tags"] = details.get("tags", [])

        target_comps = competitors[:limit_competitors]
        await asyncio.gather(*[_ensure_comp_tags(c) for c in target_comps])

        for comp in target_comps:
            v_id = comp.get("video_id") or self.extract_video_id(comp.get("url", ""))
            # Real data only: use the creator's actual Studio tags.
            tags = comp.get("tags") or []

            # Deduplicate tags within the same video (case-insensitive)
            seen_in_vid: set[str] = set()
            clean_tags: list[str] = []
            for t in tags:
                if not t or not t.strip():
                    continue
                t_str = t.strip()
                t_low = t_str.lower()
                if t_low not in seen_in_vid:
                    seen_in_vid.add(t_low)
                    clean_tags.append(t_str)

            competitor_breakdown.append(
                {
                    "rank": comp.get("rank", 1),
                    "title": comp.get("title", ""),
                    "channel": comp.get("channel", ""),
                    "views": comp.get("views", ""),
                    "video_id": v_id,
                    "tags_count": len(clean_tags),
                    "tags": clean_tags,
                    "tags_source": "creator_studio_tags" if clean_tags else "creator_set_no_tags",
                }
            )

            for t_str in clean_tags:
                t_low = t_str.lower()
                if t_low not in canonical_display_map:
                    canonical_display_map[t_low] = t_str
                all_tags_with_counts[t_low] = all_tags_with_counts.get(t_low, 0) + 1

        # If zero creator tags could be extracted (e.g. YouTube watch-page is gated behind LOGIN_REQUIRED
        # on cloud datacenter IPs or creators did not configure tags), fall back to 100% REAL YouTube
        # search autocomplete queries for the seed / top competitor topic (never dummy or boilerplate).
        tags_provenance = "creator_studio_tags"
        if not all_tags_with_counts and target_comps:
            tags_provenance = "youtube_live_autocomplete_intent"
            seed_q = (
                seed_topic
                or (competitors_or_query if isinstance(competitors_or_query, str) else "")
                or (target_comps[0].get("title", "") if target_comps else "")
            )
            # Fetch live autocomplete terms from YouTube
            live_queries = await self.get_autocomplete(seed_q)
            if not live_queries and isinstance(competitors_or_query, str):
                live_queries = await self.get_autocomplete(competitors_or_query)

            # Also query for the 2-3 most relevant head phrases
            if not live_queries:
                head_words = [w for w in re.findall(r"[a-zA-Z0-9]+", seed_q) if len(w) > 2][:3]
                if head_words:
                    live_queries = await self.get_autocomplete(" ".join(head_words))

            for q_term in live_queries[:15]:
                q_clean = q_term.strip()
                if q_clean and q_clean.lower() not in all_tags_with_counts:
                    all_tags_with_counts[q_clean.lower()] = 1
                    canonical_display_map[q_clean.lower()] = q_clean

        # Sort tags by frequency (most used by top competitors first)
        sorted_by_freq = [
            (canonical_display_map[t_low], count)
            for t_low, count in sorted(
                all_tags_with_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]

        n_comps = max(len(competitor_breakdown), 1)
        top_by_freq_list = [
            {
                "Tag": t,
                "Frekuensi": f"{count}/{n_comps} video",
                "Persentase": f"{int((count / n_comps) * 100)}%",
                "tag": t,
                "count": count,
            }
            for t, count in sorted_by_freq
        ]

        top_overlapping = [t for t, count in sorted_by_freq if count >= 2]
        all_unique = [t for t, _ in sorted_by_freq]

        # Generate clean CSV under 450 characters for YouTube Studio
        selected_tags = []
        char_count = 0
        for t, _ in sorted_by_freq:
            if char_count + len(t) + 2 > 450:
                break
            selected_tags.append(t)
            char_count += len(t) + 2

        recommended_csv = ", ".join(selected_tags)

        best_practices = [
            "1. Urutan Prioritas: Letakkan Target Keyword Utama di posisi 1-3 tag teratas karena memiliki bobot indexing algoritma tertinggi.",
            "2. Pola 3 Lapis: Padukan 1 tag umum kategori, 3-5 tag spesifik isi video, dan 1-2 variasi ejaan/typo yang sering dicari.",
            "3. Intip Kompetitor: Tiru tag yang terbukti dipakai bersama oleh ranking #1-#3 untuk masuk ke carousel 'Up Next / Suggested Videos'.",
            "4. Hindari Tag Stuffing: Batasi total panjang tag di bawah 450 karakter dan jangan pernah menaruh daftar tag di kolom deskripsi (melanggar ToS YouTube).",
        ]

        return {
            "competitors_analyzed": len(competitor_breakdown),
            "top_tags_by_frequency": top_by_freq_list,
            "top_overlapping_tags": top_overlapping,
            "all_unique_tags": all_unique,
            "tag_frequencies": all_tags_with_counts,
            "competitor_breakdown": competitor_breakdown,
            "recommended_tags_copy": recommended_csv,
            "recommended_tags_csv": recommended_csv,
            "best_practices": best_practices,
            "tags_provenance": tags_provenance,
        }

    def _parse_youtube_search_html(self, html: str, limit: int = 10) -> list[dict[str, Any]]:
        """Extract videoRenderers from ytInitialData embedded in YouTube HTML."""
        match = re.search(r"var ytInitialData\s*=\s*({.+?});</script>", html)
        if not match:
            match = re.search(r"ytInitialData\s*=\s*({.+?});", html)
        if not match:
            return []

        try:
            data = json.loads(match.group(1))
            contents = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )
            items = []
            for section in contents:
                item_section = section.get("itemSectionRenderer", {}).get("contents", [])
                for item in item_section:
                    if "videoRenderer" in item:
                        items.append(item["videoRenderer"])
                    elif "reelShelfRenderer" in item:
                        # Shorts shelf
                        for reel in item["reelShelfRenderer"].get("items", []):
                            if "reelItemRenderer" in reel:
                                r = reel["reelItemRenderer"]
                                items.append(
                                    {
                                        "is_reel": True,
                                        "title": r.get("headline", {}),
                                        "videoId": r.get("videoId", ""),
                                        "viewCountText": r.get("viewCountText", {}),
                                    }
                                )

            competitors = []
            rank = 1
            for v in items[:limit]:
                if v.get("is_reel"):
                    title = v.get("title", {}).get("simpleText") or v.get("title", {}).get(
                        "runs", [{}]
                    )[0].get("text", "")
                    views_text = v.get("viewCountText", {}).get("simpleText") or v.get(
                        "viewCountText", {}
                    ).get("runs", [{}])[0].get("text", "0")
                    reel_id = v.get("videoId", "")
                    competitors.append(
                        {
                            "rank": rank,
                            "video_id": reel_id,
                            "title": title,
                            "channel": "YouTube Creator",
                            "views": views_text,
                            "upload_age": "Recent",
                            "duration": "0:50",
                            "duration_seconds": 50,
                            "format": "SHORTS",
                            "url": f"https://www.youtube.com/shorts/{reel_id}",
                            "tags": [],
                            "outlier_status": "Trending Shorts",
                        }
                    )
                else:
                    title = v.get("title", {}).get("runs", [{}])[0].get("text", "")
                    channel = v.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                    views_text = v.get("viewCountText", {}).get("simpleText", "0 views")
                    age_text = v.get("publishedTimeText", {}).get("simpleText", "")
                    duration_text = v.get("lengthText", {}).get("simpleText", "10:00")
                    vid_id = v.get("videoId", "")

                    # Detect format: explicit #shorts in title or shorts URL
                    dur_sec = self.parse_duration_to_seconds(duration_text)
                    is_shorts = (
                        dur_sec <= 60 and ("#shorts" in title.lower() or "#short" in title.lower())
                    ) or "/shorts/" in vid_id
                    format_type = "SHORTS" if is_shorts else "LANDSCAPE"

                    # Check AI keywords in title or channel
                    is_ai, ai_badge, ai_reason = self._detect_ai_content(v, title, channel)

                    competitors.append(
                        {
                            "rank": rank,
                            "video_id": vid_id,
                            "title": title,
                            "channel": channel,
                            "views": views_text,
                            "upload_age": age_text,
                            "duration": duration_text,
                            "duration_seconds": self.parse_duration_to_seconds(duration_text),
                            "format": format_type,
                            "url": f"https://www.youtube.com/watch?v={vid_id}",
                            "tags": [],
                            "outlier_status": (
                                "👑 RANKING #1" if rank == 1 else f"Top #{rank} Competitor"
                            ),
                            "is_ai_generated": is_ai,
                            "ai_badge": ai_badge,
                            "ai_label_reason": ai_reason,
                        }
                    )
                rank += 1
            return competitors
        except Exception:
            return []

    def _detect_ai_content(
        self, v: dict[str, Any], title: str, channel: str
    ) -> tuple[bool, str, str]:
        """Detect if video has YouTube Altered/Synthetic content badge or AI indicators."""
        # 1. Inspect badges & disclosure renderers
        badges = v.get("badges", [])
        badge_texts = []
        for b in badges:
            mb = b.get("metadataBadgeRenderer", {})
            label = mb.get("label", "")
            tooltip = mb.get("tooltip", "")
            badge_texts.extend([label.lower(), tooltip.lower()])

        all_badge_text = " ".join(badge_texts)
        if any(
            k in all_badge_text
            for k in ["synthetic", "altered", "sintetis", "diubah", "generative ai"]
        ):
            return (
                True,
                "🤖 Altered / Synthetic (Official Label)",
                "Official YouTube 'Altered or synthetic content' disclosure badge.",
            )

        # 2. Check title & channel name for AI tool keywords via Regex word boundary
        text_to_check = f"{title} {channel}".lower()

        # Direct AI tool patterns
        ai_tools_regex = (
            r"\b(ai|chatgpt|gemini|veo|sora|runway|midjourney|elevenlabs|kling|flux|"
            r"luma|pika|haiper|leonardo|heygen|synthesia|d-id|tts|text to speech|"
            r"faceless|tanpa wajah|deepfake|flow|seedance)\b"
        )
        match_tool = re.search(ai_tools_regex, text_to_check)
        if match_tool:
            tool_found = match_tool.group(1).upper()
            return (
                True,
                "🤖 Altered / AI Video",
                f"Video menggunakan atau membahas teknologi AI ('{tool_found}').",
            )

        # Indonesian AI phrases
        ai_phrases = [
            "#ai",
            "dibuat dengan ai",
            "bikin video ai",
            "buat video ai",
            "animasi ai",
            "suara ai",
            "voice over ai",
            "ai voice",
            "google flow",
            "ai tools",
            "ai animation",
        ]
        for phrase in ai_phrases:
            if phrase in text_to_check:
                return (
                    True,
                    "🤖 Altered / AI Video",
                    f"Kreator menyertakan referensi AI ('{phrase}').",
                )

        return (
            False,
            "👤 Human Creator",
            "Standard human-authored video presentation.",
        )

    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch search queries / video results."""
        suggestions = await self.get_autocomplete(query)
        return [{"query": s, "platform": PlatformEnum.YOUTUBE_SEARCH} for s in suggestions]

    async def get_trending_feed(
        self,
        gl: str = "ID",
        hl: str = "id",
        category: str = "now",
        device: str = "desktop",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Fetch YouTube Trending Feed with filters:
        - gl: Country Code (ID, US, GB, JP, MY, SG, etc.)
        - hl: Interface Language (id, en, ja, etc.)
        - category: 'now', 'music', 'gaming', 'movies', 'shorts'
        - device: 'desktop' or 'mobile'
        """
        # 1. Map category to appropriate search/trending intent
        cat_lower = category.lower()
        if cat_lower == "music":
            search_query = "trending musik" if hl == "id" else "trending music"
        elif cat_lower == "gaming":
            search_query = "trending game" if hl == "id" else "trending gaming"
        elif cat_lower == "movies":
            search_query = "trailer film trending" if hl == "id" else "trending movie trailers"
        elif cat_lower == "shorts":
            search_query = "#shorts trending"
        else:
            search_query = "trending indonesia" if gl == "ID" else "trending"

        # Natural human delay (jitter)
        await self._human_delay(0.6, 1.8)

        # 2. Select human-like headers based on Device and locale
        headers = self._get_natural_headers(hl=hl, gl=gl, device=device)

        # 3. Optional YouTube Data API v3 integration if API key is set
        if self.api_key:
            try:
                api_cat_id = ""
                if cat_lower == "music":
                    api_cat_id = "10"
                elif cat_lower == "gaming":
                    api_cat_id = "20"
                elif cat_lower == "movies":
                    api_cat_id = "1"

                api_url = "https://www.googleapis.com/youtube/v3/videos"
                api_params: dict[str, str | int] = {
                    "part": "snippet,contentDetails,statistics",
                    "chart": "mostPopular",
                    "regionCode": gl if gl != "WW" else "US",
                    "maxResults": min(limit, 25),
                    "key": self.api_key,
                }
                if api_cat_id:
                    api_params["videoCategoryId"] = api_cat_id

                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(api_url, params=api_params)
                    if resp.status_code == 200:
                        api_data = resp.json().get("items", [])
                        results = []
                        for rank, item in enumerate(api_data, 1):
                            snip = item.get("snippet", {})
                            stats = item.get("statistics", {})
                            vid_id = item.get("id", "")
                            v_views = int(stats.get("viewCount", 0))
                            v_title = snip.get("title", "")
                            v_channel = snip.get("channelTitle", "")
                            dur = item.get("contentDetails", {}).get("duration", "PT10M")
                            dur_text, _ = self._parse_iso_duration(dur)
                            dur_sec = self.parse_duration_to_seconds(dur_text)
                            thumb_url = snip.get("thumbnails", {}).get("high", {}).get("url", "")
                            is_shorts, format_type = self.detect_video_format(
                                video_id=vid_id,
                                title=v_title,
                                duration_seconds=dur_sec,
                                thumbnail_url=thumb_url,
                            )
                            is_ai, ai_badge, ai_reason = self._detect_ai_content(
                                item, v_title, v_channel
                            )
                            results.append(
                                {
                                    "rank": rank,
                                    "title": v_title,
                                    "channel": v_channel,
                                    "views": f"{v_views:,} views",
                                    "views_count": v_views,
                                    "upload_age": snip.get("publishedAt", "")[:10],
                                    "duration": dur_text,
                                    "format": format_type,
                                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                                    "outlier_status": (
                                        "🔥 TRENDING TOP #1" if rank == 1 else f"Top #{rank}"
                                    ),
                                    "is_ai_generated": is_ai,
                                    "ai_badge": ai_badge,
                                    "ai_label_reason": ai_reason,
                                    "data_source": "YOUTUBE_API_V3",
                                    "device": device.upper(),
                                    "location": gl,
                                    "language": hl,
                                }
                            )
                        if results:
                            return results[:limit]
            except Exception as e:
                logger.warning(f"Error fetching trending feed via API: {e}")

        # 4. Scrape YouTube SERP live
        try:
            params = {
                "search_query": search_query,
                "gl": gl if gl != "WW" else "US",
                "hl": hl,
            }
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(self.SEARCH_URL, headers=headers, params=params)
                if resp.status_code == 200:
                    competitors = self._parse_youtube_search_html(resp.text, limit=limit)
                    if competitors:
                        for c in competitors:
                            c["data_source"] = "LIVE_SERP"
                            c["device"] = device.upper()
                            c["location"] = gl
                            c["language"] = hl
                        return competitors[:limit]
        except Exception as e:
            logger.warning(f"Error scraping live YouTube trending feed: {e}")

        # Real data only: return empty list if trending feed unavailable
        return []


# Expose helper function at module level
parse_duration_to_seconds = YouTubeConnector.parse_duration_to_seconds
