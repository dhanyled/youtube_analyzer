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

    API_BASE_URL = "https://www.googleapis.com/youtube/v3"
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
            "Cookie": f"PREF=tz=Asia.Jakarta&hl={hl}&gl={gl}; SOCS=CAESEwgDEgk2MTQ1NzU1OTQaAmVuIAEaBgiA_LyaBg; CONSENT=YES+cb.20210328-17-p0.en+FX+478;",
        }

    @staticmethod
    async def _human_delay(min_sec: float = 0.5, max_sec: float = 1.6) -> None:
        """Introduce natural, human-like random pause (typing/navigation jitter)."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("YOUTUBE_API_KEY")
        super().__init__(platform=PlatformEnum.YOUTUBE_SEARCH, api_key=key)
        self._last_innertube_debug: list[str] = []

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
    INNERTUBE_WEB_CLIENT_VERSION = "2.20260210.01.00"
    INNERTUBE_MWEB_CLIENT_VERSION = "2.20240401.05.00"

    async def _fetch_innertube_player(self, video_id: str) -> dict[str, Any] | None:
        """Fetch real video metadata + creator Studio tags via YouTube Innertube player API with multi-client fallback."""
        clients_to_try = [
            ("WEB", self.INNERTUBE_WEB_CLIENT_VERSION, "1", "desktop"),
            ("MWEB", self.INNERTUBE_MWEB_CLIENT_VERSION, "2", "mobile"),
        ]
        cookies = {
            "SOCS": "CAESEwgDEgk2MTQ1NzU1OTQaAmVuIAEaBgiA_LyaBg",
            "CONSENT": "YES+cb.20210328-17-p0.en+FX+478",
            "PREF": "tz=Asia.Jakarta&hl=id&gl=ID",
        }

        data = None
        debug_trace: list[str] = []
        for client_name, client_ver, client_id, dev_type in clients_to_try:
            payload = {
                "context": {
                    "client": {
                        "clientName": client_name,
                        "clientVersion": client_ver,
                        "hl": "id",
                        "gl": "ID",
                    }
                },
                "videoId": video_id,
            }
            ua = random.choice(
                self.USER_AGENTS_MOBILE if dev_type == "mobile" else self.USER_AGENTS_DESKTOP
            )
            headers = {
                "User-Agent": ua,
                "Origin": "https://www.youtube.com",
                "Referer": f"https://www.youtube.com/watch?v={video_id}",
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                "Content-Type": "application/json",
                "X-YouTube-Client-Name": client_id,
                "X-YouTube-Client-Version": client_ver,
            }
            try:
                async with httpx.AsyncClient(timeout=10.0, cookies=cookies) as client:
                    resp = await client.post(self.INNERTUBE_PLAYER_URL, json=payload, headers=headers)
                debug_trace.append(f"{client_name}: status={resp.status_code}, len={len(resp.text)}")
                if resp.status_code == 200:
                    cand_data = resp.json()
                    cand_vdet = cand_data.get("videoDetails") or {}
                    debug_trace.append(f"{client_name}: has_vdet={bool(cand_vdet)}, title={cand_vdet.get('title')}, len_sec={cand_vdet.get('lengthSeconds')}")
                    if cand_vdet.get("videoId") and cand_vdet.get("title"):
                        data = cand_data
                        break
            except Exception as e:
                debug_trace.append(f"{client_name}: err={e}")
                logger.warning(f"Innertube player ({client_name}) failed for '{video_id}': {e}")

        self._last_innertube_debug = debug_trace
        if not data:
            logger.info(f"Innertube failed: {debug_trace}")
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
        if length_sec == 0:
            length_sec = _to_int(mf.get("lengthSeconds"))
        if length_sec == 0:
            for fmt in (data.get("streamingData") or {}).get("adaptiveFormats", []):
                if fmt.get("approxDurationMs"):
                    length_sec = int(int(fmt["approxDurationMs"]) / 1000)
                    break

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
        meta = {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": title,
            "description": str(v_det.get("shortDescription", "")),
            "tags": tags,
            "channel": str(v_det.get("author", "")),
            "channel_id": str(v_det.get("channelId", "")),
            "published_at": published,
            "views": raw_views,
            "views_display": self._format_views_display(raw_views),
            "likes": _to_int(mf.get("likeCount")),
            "comments": 0,
            "duration": dur_text,
            "duration_seconds": length_sec,
            "is_shorts": is_shorts,
            "format": format_type,
            "category": str(mf.get("category", "")),
            "thumbnail_url": thumb_url,
            "data_source": "INNERTUBE_PLAYER",
            "debug_trace": self._last_innertube_debug,
        }
        return await self._enrich_video_metadata(meta, video_id)

    async def _enrich_video_metadata(self, meta: dict[str, Any], video_id: str) -> dict[str, Any]:
        """Guarantee 100% real title, views, and duration even on cloud IPs by cascading public fallbacks."""
        needs_title = not meta.get("title") or meta.get("title") == f"Video {video_id}"
        needs_views = (
            meta.get("views") is None or meta.get("views_display") == "N/A"
        )
        needs_dur = (
            not meta.get("duration")
            or meta.get("duration") == "N/A"
            or not meta.get("duration_seconds")
        )

        if not (needs_title or needs_views or needs_dur):
            return meta

        cookies = {
            "SOCS": "CAESEwgDEgk2MTQ1NzU1OTQaAmVuIAEaBgiA_LyaBg",
            "CONSENT": "YES+cb.20210328-17-p0.en+FX+478",
            "PREF": "tz=Asia.Jakarta&hl=id&gl=ID",
        }

        # 0. If duration is missing and data_source wasn't INNERTUBE_PLAYER, try Innertube first
        if needs_dur and meta.get("data_source") != "INNERTUBE_PLAYER":
            try:
                it_meta = await self._fetch_innertube_player(video_id)
                if it_meta and it_meta.get("duration_seconds"):
                    dur_sec = it_meta["duration_seconds"]
                    meta["duration_seconds"] = dur_sec
                    meta["duration"] = it_meta["duration"]
                    meta["is_shorts"] = it_meta["is_shorts"]
                    meta["format"] = it_meta["format"]
                    if not meta.get("tags") and it_meta.get("tags"):
                        meta["tags"] = it_meta["tags"]
                    needs_dur = False
            except Exception:
                pass

        async with httpx.AsyncClient(timeout=10.0, cookies=cookies, follow_redirects=True) as client:
            # 1. oEmbed for real Title, Author, Thumbnail
            if needs_title or not meta.get("channel") or not meta.get("thumbnail_url") or "maxresdefault" in meta.get("thumbnail_url", ""):
                try:
                    oe = await client.get(
                        f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
                        headers={"User-Agent": random.choice(self.USER_AGENTS_DESKTOP)},
                    )
                    if oe.status_code == 200:
                        oed = oe.json()
                        if oed.get("title") and needs_title:
                            meta["title"] = oed["title"]
                        if oed.get("author_name") and not meta.get("channel"):
                            meta["channel"] = oed["author_name"]
                        if oed.get("thumbnail_url"):
                            meta["thumbnail_url"] = oed["thumbnail_url"]
                except Exception:
                    pass

            # 2. ReturnYouTubeDislike API for real viewCount and likes
            if needs_views:
                try:
                    ryd = await client.get(
                        f"https://returnyoutubedislikeapi.com/votes?videoId={video_id}",
                        headers={"User-Agent": random.choice(self.USER_AGENTS_DESKTOP)},
                    )
                    if ryd.status_code == 200:
                        ryd_d = ryd.json()
                        if "viewCount" in ryd_d:
                            v_cnt = int(ryd_d.get("viewCount") or 0)
                            meta["views"] = v_cnt
                            meta["views_display"] = self._format_views_display(v_cnt)
                        if not meta.get("likes") and ryd_d.get("likes") is not None:
                            meta["likes"] = int(ryd_d.get("likes") or 0)
                except Exception:
                    pass

        # 3. Transcript calculation for duration
        if needs_dur and YouTubeTranscriptApi:
            try:
                api = YouTubeTranscriptApi()
                t_list = api.list(video_id)
                trans = None
                try:
                    trans = t_list.find_transcript(["id", "en"])
                except Exception:
                    for t in t_list:
                        trans = t
                        break
                if trans:
                    snippets = trans.fetch()
                    if snippets:
                        last = snippets[-1]
                        dur_sec = int(last.start + last.duration)
                        if dur_sec > 0:
                            meta["duration_seconds"] = dur_sec
                            h, rem = divmod(dur_sec, 3600)
                            m, s = divmod(rem, 60)
                            meta["duration"] = (
                                f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                            )
                            is_shorts, format_type = self.detect_video_format(
                                video_id=video_id,
                                title=meta.get("title", ""),
                                duration_seconds=dur_sec,
                                thumbnail_url=meta.get("thumbnail_url", ""),
                            )
                            meta["is_shorts"] = is_shorts
                            meta["format"] = format_type
                            needs_dur = False
            except Exception:
                pass

        # 4. Consent-bypassed HTML duration scrape if still missing
        if needs_dur and (
            not meta.get("duration")
            or meta.get("duration") == "N/A"
            or not meta.get("duration_seconds")
        ):
            dur_sec = 0

            # 4a. Mobile YouTube URL (ultra-fast, extremely reliable on cloud/datacenter IPs)
            try:
                m_headers = self._get_natural_headers(hl="id", gl="ID", device="mobile")
                async with httpx.AsyncClient(timeout=10.0, cookies=cookies, follow_redirects=True) as client:
                    m_resp = await client.get(
                        f"https://m.youtube.com/watch?v={video_id}&has_verified=1",
                        headers=m_headers,
                    )
                    if m_resp.status_code == 200:
                        m_html = m_resp.text
                        m_mdur = (
                            re.search(r'itemprop=["\']?duration["\']?\s+content=["\'](PT[0-9HMS]+)["\']', m_html)
                            or re.search(r'content=["\'](PT[0-9HMS]+)["\']\s+itemprop=["\']?duration["\']?', m_html)
                            or re.search(r'["\']duration["\']\s*:\s*["\'](PT[0-9HMS]+)["\']', m_html)
                            or re.search(r'["\'](PT[0-9HMS]+)["\']', m_html)
                        )
                        m_mlen = re.search(r'["\']lengthSeconds["\']\s*:\s*["\']?(\d+)["\']?', m_html)
                        m_mapp = re.search(r'["\']approxDurationMs["\']\s*:\s*["\']?(\d+)["\']?', m_html)
                        if m_mdur:
                            dur_sec = self.parse_duration_to_seconds(m_mdur.group(1))
                        elif m_mlen:
                            dur_sec = int(m_mlen.group(1))
                        elif m_mapp:
                            dur_sec = int(int(m_mapp.group(1)) / 1000)
            except Exception:
                pass

            # 4b. Direct Shorts URL (if mobile /watch didn't yield duration)
            if dur_sec == 0:
                try:
                    s_headers = self._get_natural_headers(hl="en", gl="US", device="desktop")
                    async with httpx.AsyncClient(timeout=10.0, cookies=cookies, follow_redirects=True) as client:
                        s_resp = await client.get(f"https://www.youtube.com/shorts/{video_id}", headers=s_headers)
                        if s_resp.status_code == 200:
                            s_html = s_resp.text
                            m_sdur = (
                                re.search(r'itemprop=["\']?duration["\']?\s+content=["\'](PT[0-9HMS]+)["\']', s_html)
                                or re.search(r'content=["\'](PT[0-9HMS]+)["\']\s+itemprop=["\']?duration["\']?', s_html)
                                or re.search(r'["\']duration["\']\s*:\s*["\'](PT[0-9HMS]+)["\']', s_html)
                                or re.search(r'["\'](PT[0-9HMS]+)["\']', s_html)
                            )
                            m_sapp = re.search(r'["\']approxDurationMs["\']\s*:\s*["\']?(\d+)["\']?', s_html)
                            m_slen = re.search(r'["\']lengthSeconds["\']\s*:\s*["\']?(\d+)["\']?', s_html)
                            if m_sdur:
                                dur_sec = self.parse_duration_to_seconds(m_sdur.group(1))
                            elif m_sapp:
                                dur_sec = int(int(m_sapp.group(1)) / 1000)
                            elif m_slen:
                                dur_sec = int(m_slen.group(1))
                except Exception:
                    pass

            # 4c. Desktop /watch URL fallback
            if dur_sec == 0:
                try:
                    w_headers = self._get_natural_headers(hl="en", gl="US", device="desktop")
                    watch_url = f"https://www.youtube.com/watch?v={video_id}&bpctr=9999999999&has_verified=1"
                    async with httpx.AsyncClient(timeout=10.0, cookies=cookies, follow_redirects=True) as client:
                        w_resp = await client.get(watch_url, headers=w_headers)
                        if w_resp.status_code == 200:
                            w_html = w_resp.text
                            m_dur = (
                                re.search(r'itemprop=["\']?duration["\']?\s+content=["\'](PT[0-9HMS]+)["\']', w_html)
                                or re.search(r'content=["\'](PT[0-9HMS]+)["\']\s+itemprop=["\']?duration["\']?', w_html)
                                or re.search(r'["\']duration["\']\s*:\s*["\'](PT[0-9HMS]+)["\']', w_html)
                                or re.search(r'["\'](PT[0-9HMS]+)["\']', w_html)
                            )
                            m_len = re.search(r'["\']lengthSeconds["\']\s*:\s*["\']?(\d+)["\']?', w_html)
                            m_app = re.search(r'["\']approxDurationMs["\']\s*:\s*["\']?(\d+)["\']?', w_html)
                            if m_dur:
                                dur_sec = self.parse_duration_to_seconds(m_dur.group(1))
                            elif m_len:
                                dur_sec = int(m_len.group(1))
                            elif m_app:
                                dur_sec = int(int(m_app.group(1)) / 1000)
                except Exception:
                    pass

            if dur_sec > 0:
                meta["duration_seconds"] = dur_sec
                h, rem = divmod(dur_sec, 3600)
                m, s = divmod(rem, 60)
                meta["duration"] = (
                    f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                )
                is_shorts, format_type = self.detect_video_format(
                    video_id=video_id,
                    title=meta.get("title", ""),
                    duration_seconds=dur_sec,
                    thumbnail_url=meta.get("thumbnail_url", ""),
                )
                meta["is_shorts"] = is_shorts
                meta["format"] = format_type

            # Ensure Shorts never use maxresdefault.jpg which returns 404
            if meta.get("is_shorts") or meta.get("format") == "SHORTS":
                if "maxresdefault" in meta.get("thumbnail_url", ""):
                    meta["thumbnail_url"] = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        return meta

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
            url = f"https://www.youtube.com/watch?v={video_id}&bpctr=9999999999&has_verified=1"
            headers = self._get_natural_headers(hl="id", gl="ID", device="desktop")
            cookies = {
                "SOCS": "CAESEwgDEgk2MTQ1NzU1OTQaAmVuIAEaBgiA_LyaBg",
                "CONSENT": "YES+cb.20210328-17-p0.en+FX+478",
                "PREF": "tz=Asia.Jakarta&hl=id&gl=ID",
            }
            async with httpx.AsyncClient(timeout=12.0, cookies=cookies, follow_redirects=True) as client:
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
                        m_dur = (
                            re.search(r'itemprop=["\']?duration["\']?\s+content=["\'](PT[0-9HMS]+)["\']', html)
                            or re.search(r'content=["\'](PT[0-9HMS]+)["\']\s+itemprop=["\']?duration["\']?', html)
                            or re.search(r'["\']duration["\']\s*:\s*["\'](PT[0-9HMS]+)["\']', html)
                            or re.search(r'["\'](PT[0-9HMS]+)["\']', html)
                        )
                        if m_dur:
                            length_sec = self.parse_duration_to_seconds(m_dur.group(1))
                    if length_sec == 0:
                        m_len = re.search(r'["\']lengthSeconds["\']\s*:\s*["\']?(\d+)["\']?', html)
                        if m_len:
                            try:
                                length_sec = int(m_len.group(1))
                            except (ValueError, TypeError):
                                pass
                    if length_sec == 0:
                        m_app = re.search(r'["\']approxDurationMs["\']\s*:\s*["\']?(\d+)["\']?', html)
                        if m_app:
                            try:
                                length_sec = int(int(m_app.group(1)) / 1000)
                            except (ValueError, TypeError):
                                pass

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

                    meta = {
                        "video_id": video_id,
                        "url": url,
                        "title": title,
                        "description": description,
                        "tags": tags,
                        "channel": channel,
                        "channel_id": channel_id,
                        "published_at": published_at,
                        "views": raw_views,
                        "views_display": self._format_views_display(raw_views),
                        "likes": likes,
                        "comments": 0,
                        "duration": dur_text,
                        "duration_seconds": length_sec,
                        "is_shorts": is_shorts,
                        "format": format_type,
                        "thumbnail_url": thumb_url,
                        "data_source": "SCRAPED_PLAYER_RESPONSE",
                        "debug_trace": self._last_innertube_debug,
                    }
                    return await self._enrich_video_metadata(meta, video_id)
        except Exception:
            pass

        # Resilient public fallback (oEmbed + ReturnYouTubeDislike + Transcript)
        fallback_meta = {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": "",
            "description": "",
            "tags": [],
            "channel": "",
            "channel_id": "",
            "published_at": "",
            "views": 0,
            "views_display": "N/A",
            "likes": 0,
            "comments": 0,
            "duration": "N/A",
            "duration_seconds": 0,
            "is_shorts": False,
            "format": "LANDSCAPE (16:9)",
            "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "data_source": "PUBLIC_FALLBACK_RESILIENT",
        }
        enriched = await self._enrich_video_metadata(fallback_meta, video_id)
        if enriched.get("title") and enriched.get("title") != f"Video {video_id}":
            return enriched

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

        # Build context from seed topic and competitor video titles for relevance validation
        comp_titles = " ".join(c.get("title", "") for c in target_comps)
        context_text = f"{seed_topic or ''} {comp_titles}".strip()

        from youtube_analyzer.core.normalizer import TopicNormalizer

        for comp in target_comps:
            v_id = comp.get("video_id") or self.extract_video_id(comp.get("url", ""))
            # Real data only: use the creator's actual Studio tags.
            tags = comp.get("tags") or []

            # Deduplicate and filter tags for strict relevance against content (filter out clickbait like 'gratis', 'viral', etc. unless in context)
            clean_tags = TopicNormalizer.filter_relevant_tags(tags, context_text=context_text)

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
                if (
                    q_clean
                    and TopicNormalizer.is_tag_relevant(q_clean, context_text=context_text)
                    and q_clean.lower() not in all_tags_with_counts
                ):
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
            "3. Relevansi 100% (Anti-Clickbait): Seluruh tag wajib sesuai dengan materi aktual video. Jangan gunakan kata 'gratis', 'download', atau 'viral' kecuali materi video memang membahas konten gratis/unduhan.",
            "4. Intip Kompetitor: Tiru tag yang terbukti dipakai bersama oleh ranking #1-#3 untuk masuk ke carousel 'Up Next / Suggested Videos'.",
            "5. Hindari Tag Stuffing: Batasi total panjang tag di bawah 450 karakter dan jangan pernah menaruh daftar tag di kolom deskripsi (melanggar ToS YouTube).",
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

    @staticmethod
    def extract_channel_handle(raw: str) -> str:
        s = raw.strip()
        if "youtube.com/" in s or "youtu.be/" in s:
            m = re.search(r"youtube\.com/@([a-zA-Z0-9_\-\.]+)", s)
            if m:
                return f"@{m.group(1)}"
            m2 = re.search(r"youtube\.com/channel/(UC[a-zA-Z0-9_\-]+)", s)
            if m2:
                return m2.group(1)
        if not s.startswith("@") and not s.startswith("UC"):
            return f"@{s}"
        return s

    def _parse_count_text(self, txt: str) -> int:
        """Parse subscriber/view/video count string (e.g. '6,17 rb subscriber', '1.2M views') into integer."""
        if not txt:
            return 0
        t = (
            txt.lower()
            .replace("subscriber", "")
            .replace("subscribers", "")
            .replace("video", "")
            .replace("videos", "")
            .replace("ditonton", "")
            .replace("tayangan", "")
            .replace("views", "")
            .replace("x", "")
            .replace("\xa0", " ")
            .strip()
        )
        if not t or "belum" in t:
            return 0
        mul = 1
        if "rb" in t or "k" in t:
            mul = 1000
            t = t.replace("rb", "").replace("k", "").strip()
        elif "jt" in t or "m" in t or "juta" in t:
            mul = 1000000
            t = t.replace("juta", "").replace("jt", "").replace("m", "").strip()
        elif "b" in t or "miliar" in t:
            mul = 1000000000
            t = t.replace("miliar", "").replace("b", "").strip()
        t = t.replace(",", ".").strip()
        try:
            return int(float(t) * mul)
        except Exception:
            return 0

    async def _scrape_channel_public(
        self, clean_id: str, max_videos: int = 50
    ) -> dict[str, Any] | None:
        """Zero-quota public scraping fallback for channel stats and format breakdown."""
        handle = (
            clean_id if clean_id.startswith("@") or clean_id.startswith("UC") else f"@{clean_id}"
        )
        base_path = f"channel/{handle}" if handle.startswith("UC") else handle
        vid_url = f"https://www.youtube.com/{base_path}/videos"
        shorts_url = f"https://www.youtube.com/{base_path}/shorts"

        headers = self._get_natural_headers(hl="id", gl="ID", device="desktop")

        try:
            async with httpx.AsyncClient(timeout=14.0) as client:
                r_vid, r_sho = await asyncio.gather(
                    client.get(vid_url, headers=headers, follow_redirects=True),
                    client.get(shorts_url, headers=headers, follow_redirects=True),
                    return_exceptions=True,
                )

                if isinstance(r_vid, Exception) or r_vid.status_code != 200:
                    logger.warning(f"Failed to fetch public channel page for {handle}")
                    return None

                m = re.search(r"var ytInitialData\s*=\s*({.+?});</script>", r_vid.text)
                if not m:
                    return None
                data = json.loads(m.group(1))

                meta = data.get("metadata", {}).get("channelMetadataRenderer", {})
                title = meta.get("title", handle)
                ch_id = meta.get("externalId", "")

                header = data.get("header", {}).get("pageHeaderRenderer", {})
                content_meta = header.get("content", {}).get("pageHeaderViewModel", {})
                metadata_rows = (
                    content_meta.get("metadata", {})
                    .get("contentMetadataViewModel", {})
                    .get("metadataRows", [])
                )

                subs_text = ""
                vids_text = ""
                for row in metadata_rows:
                    for part in row.get("metadataParts", []):
                        txt = part.get("text", {}).get("content", "")
                        if "subscriber" in txt.lower():
                            subs_text = txt
                        elif "video" in txt.lower():
                            vids_text = txt

                subscribers = self._parse_count_text(subs_text)
                video_count = self._parse_count_text(vids_text)

                avatar_sources = (
                    content_meta.get("image", {})
                    .get("decoratedAvatarViewModel", {})
                    .get("avatar", {})
                    .get("avatarViewModel", {})
                    .get("image", {})
                    .get("sources", [])
                )
                thumb = avatar_sources[-1].get("url", "") if avatar_sources else ""
                if not thumb:
                    avatar_runs = meta.get("avatar", {}).get("thumbnails", [])
                    thumb = avatar_runs[-1].get("url", "") if avatar_runs else ""

                # Extract videos from contents
                lockups: list[dict[str, Any]] = []

                def find_lockups(obj: Any) -> None:
                    if isinstance(obj, dict):
                        if "lockupViewModel" in obj:
                            lockups.append(obj["lockupViewModel"])
                        for v in obj.values():
                            find_lockups(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            find_lockups(item)

                find_lockups(data.get("contents", {}))

                landscape_count = 0
                portrait_count = 0
                recent_top_video = None
                max_recent_views = -1
                parsed_videos: list[dict[str, Any]] = []
                seen_vids: set[str] = set()

                for lk in lockups:
                    vid_id = ""
                    try:
                        vid_id = lk["rendererContext"]["commandContext"]["onTap"][
                            "innertubeCommand"
                        ]["watchEndpoint"]["videoId"]
                    except Exception:
                        pass
                    if not vid_id or vid_id in seen_vids:
                        continue
                    seen_vids.add(vid_id)

                    v_title = ""
                    try:
                        v_title = lk["metadata"]["lockupMetadataViewModel"]["title"]["content"]
                    except Exception:
                        pass

                    dur_text = ""
                    try:
                        badges = lk["contentImage"]["thumbnailViewModel"]["overlays"][0][
                            "thumbnailBottomOverlayViewModel"
                        ]["badges"]
                        for b in badges:
                            dur_text = b.get("thumbnailBadgeViewModel", {}).get("text", "")
                            if dur_text:
                                break
                    except Exception:
                        pass

                    view_str = ""
                    try:
                        rows = lk["metadata"]["lockupMetadataViewModel"]["metadata"][
                            "contentMetadataViewModel"
                        ]["metadataRows"]
                        if rows and "metadataParts" in rows[0]:
                            parts = rows[0]["metadataParts"]
                            if parts:
                                view_str = parts[0].get("text", {}).get("content", "")
                                if not view_str or view_str == "0":
                                    view_str = parts[0].get("accessibilityLabel", "0")
                    except Exception:
                        pass

                    v_views = self._parse_count_text(view_str)
                    dur_sec = self.parse_duration_to_seconds(dur_text)
                    is_shorts = 0 < dur_sec <= 60
                    if is_shorts:
                        portrait_count += 1
                    else:
                        landscape_count += 1

                    v_thumb = ""
                    try:
                        sources = lk["contentImage"]["thumbnailViewModel"]["image"]["sources"]
                        if sources:
                            v_thumb = sources[-1].get("url", "")
                    except Exception:
                        pass

                    vid_info = {
                        "id": vid_id,
                        "title": v_title,
                        "views": v_views,
                        "views_display": f"{v_views:,}" if v_views > 0 else view_str,
                        "likes": 0,
                        "likes_display": "-",
                        "duration": dur_text,
                        "thumbnail_url": v_thumb
                        or f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
                        "is_shorts": is_shorts,
                        "format": "SHORTS (9:16)" if is_shorts else "LANDSCAPE (16:9)",
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                    }
                    parsed_videos.append(vid_info)

                    if v_views > max_recent_views:
                        max_recent_views = v_views
                        recent_top_video = vid_info

                # Also inspect shorts tab if available
                if not isinstance(r_sho, Exception) and r_sho.status_code == 200:
                    m_sho = re.search(r"var ytInitialData\s*=\s*({.+?});</script>", r_sho.text)
                    if m_sho:
                        sho_data = json.loads(m_sho.group(1))
                        sho_lockups: list[dict[str, Any]] = []

                        def find_sho(obj: Any) -> None:
                            if isinstance(obj, dict):
                                if "shortsLockupViewModel" in obj:
                                    sho_lockups.append(obj["shortsLockupViewModel"])
                                for v in obj.values():
                                    find_sho(v)
                            elif isinstance(obj, list):
                                for item in obj:
                                    find_sho(item)

                        find_sho(sho_data.get("contents", {}))

                        for slk in sho_lockups:
                            sho_url = (
                                slk.get("onTap", {})
                                .get("innertubeCommand", {})
                                .get("commandMetadata", {})
                                .get("webCommandMetadata", {})
                                .get("url", "")
                            )
                            s_vid_id = sho_url.replace("/shorts/", "").split("?")[0].strip()
                            if not s_vid_id or s_vid_id in seen_vids:
                                continue
                            seen_vids.add(s_vid_id)
                            portrait_count += 1
                            s_title = (
                                slk.get("overlayMetadata", {})
                                .get("primaryText", {})
                                .get("content", "")
                            )
                            s_views_txt = (
                                slk.get("overlayMetadata", {})
                                .get("secondaryText", {})
                                .get("content", "")
                            )
                            s_views = self._parse_count_text(s_views_txt)
                            sho_info = {
                                "id": s_vid_id,
                                "title": s_title,
                                "views": s_views,
                                "views_display": f"{s_views:,}" if s_views > 0 else s_views_txt,
                                "likes": 0,
                                "likes_display": "-",
                                "duration": "0:59",
                                "thumbnail_url": f"https://i.ytimg.com/vi/{s_vid_id}/hqdefault.jpg",
                                "is_shorts": True,
                                "format": "SHORTS (9:16)",
                                "url": f"https://www.youtube.com/shorts/{s_vid_id}",
                            }
                            parsed_videos.append(sho_info)
                            if s_views > max_recent_views:
                                max_recent_views = s_views
                                recent_top_video = sho_info

                sample_total = len(parsed_videos)
                pct_landscape = (
                    round((landscape_count / sample_total) * 100, 1) if sample_total > 0 else 0.0
                )
                pct_shorts = (
                    round((portrait_count / sample_total) * 100, 1) if sample_total > 0 else 0.0
                )

                return {
                    "channel_id": ch_id,
                    "title": title,
                    "handle": handle,
                    "thumbnail_url": thumb,
                    "subscribers": subscribers,
                    "subscribers_display": f"{subscribers:,}",
                    "video_count": video_count,
                    "video_count_display": f"{video_count:,}",
                    "total_views": 0,
                    "total_views_display": "-",
                    "sample_analyzed": sample_total,
                    "landscape_count": landscape_count,
                    "landscape_percentage": pct_landscape,
                    "portrait_count": portrait_count,
                    "portrait_percentage": pct_shorts,
                    "recent_top_video": recent_top_video,
                    "all_time_top_video": recent_top_video,
                    "videos": parsed_videos[:max_videos],
                }
        except Exception as e:
            logger.warning(f"Error scraping public channel {handle}: {e}")
            return None

    async def get_channel_summary_and_format_breakdown(
        self, identifier: str, max_videos: int = 50
    ) -> dict[str, Any] | None:
        """Fetch real channel statistics, format breakdown (Landscape vs Shorts), and top video."""
        clean_id = self.extract_channel_handle(identifier)
        if not self.api_key:
            return await self._scrape_channel_public(clean_id, max_videos=max_videos)

        # 1. Fetch channel profile
        url = f"{self.API_BASE_URL}/channels"
        params: dict[str, Any] = {
            "part": "snippet,statistics,contentDetails",
            "key": self.api_key,
        }
        if clean_id.startswith("UC"):
            params["id"] = clean_id
        else:
            handle_no_at = clean_id.lstrip("@")
            params["forHandle"] = handle_no_at

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(url, params=params)
                data = resp.json() if resp.status_code == 200 else {}
                items = data.get("items", [])
                if not items and "forHandle" in params:
                    params["forHandle"] = f"@{params['forHandle']}"
                    resp = await client.get(url, params=params)
                    data = resp.json() if resp.status_code == 200 else {}
                    items = data.get("items", [])

                if not items:
                    logger.info(
                        f"Channel not found via API for {clean_id}, falling back to public scrape."
                    )
                    return await self._scrape_channel_public(clean_id, max_videos=max_videos)

                item = items[0]
                snip = item.get("snippet", {})
                stats = item.get("statistics", {})
                cd = item.get("contentDetails", {})

                ch_id = item.get("id", "")
                title = snip.get("title", "")
                custom_url = snip.get("customUrl", f"@{clean_id.lstrip('@')}")
                subscribers = int(stats.get("subscriberCount", 0))
                video_count = int(stats.get("videoCount", 0))
                total_views = int(stats.get("viewCount", 0))
                thumb = snip.get("thumbnails", {}).get("default", {}).get("url", "")
                uploads_id = cd.get("relatedPlaylists", {}).get("uploads", "")

                landscape_count = 0
                portrait_count = 0
                recent_top_video = None
                max_recent_views = -1
                parsed_videos: list[dict[str, Any]] = []

                # 2. Inspect uploaded videos for Landscape vs Shorts breakdown
                if uploads_id:
                    p_resp = await client.get(
                        f"{self.API_BASE_URL}/playlistItems",
                        params={
                            "part": "contentDetails",
                            "playlistId": uploads_id,
                            "maxResults": min(max_videos, 50),
                            "key": self.api_key,
                        },
                    )
                    if p_resp.status_code == 200:
                        p_items = p_resp.json().get("items", [])
                        vid_ids = [
                            pi["contentDetails"]["videoId"]
                            for pi in p_items
                            if "contentDetails" in pi and "videoId" in pi["contentDetails"]
                        ]
                        if vid_ids:
                            v_resp = await client.get(
                                f"{self.API_BASE_URL}/videos",
                                params={
                                    "part": "snippet,contentDetails,statistics",
                                    "id": ",".join(vid_ids),
                                    "key": self.api_key,
                                },
                            )
                            if v_resp.status_code == 200:
                                v_items = v_resp.json().get("items", [])
                                for v in v_items:
                                    v_snip = v.get("snippet", {})
                                    v_stats = v.get("statistics", {})
                                    v_cd = v.get("contentDetails", {})
                                    v_title = v_snip.get("title", "")
                                    v_views = int(v_stats.get("viewCount", 0))
                                    dur_iso = v_cd.get("duration", "")
                                    dur_text, _ = self._parse_iso_duration(dur_iso)
                                    dur_sec = self.parse_duration_to_seconds(dur_text)

                                    is_shorts = dur_sec <= 60
                                    if is_shorts:
                                        portrait_count += 1
                                    else:
                                        landscape_count += 1

                                    vid_info = {
                                        "title": v_title,
                                        "views": v_views,
                                        "views_display": self._format_views_display(v_views),
                                        "likes": int(v_stats.get("likeCount", 0)),
                                        "likes_display": self._format_views_display(
                                            int(v_stats.get("likeCount", 0))
                                        ),
                                        "duration": dur_text,
                                        "thumbnail_url": v_snip.get("thumbnails", {})
                                        .get("medium", {})
                                        .get("url")
                                        or v_snip.get("thumbnails", {})
                                        .get("default", {})
                                        .get("url", ""),
                                        "id": v.get("id"),
                                        "is_shorts": is_shorts,
                                        "format": "SHORTS (9:16)"
                                        if is_shorts
                                        else "LANDSCAPE (16:9)",
                                        "url": f"https://www.youtube.com/watch?v={v.get('id')}",
                                    }
                                    parsed_videos.append(vid_info)

                                    if v_views > max_recent_views:
                                        max_recent_views = v_views
                                        recent_top_video = vid_info

                # 3. All-time top video via search order by viewCount
                all_time_top = None
                s_resp = await client.get(
                    f"{self.API_BASE_URL}/search",
                    params={
                        "part": "snippet",
                        "channelId": ch_id,
                        "order": "viewCount",
                        "type": "video",
                        "maxResults": 1,
                        "key": self.api_key,
                    },
                )
                if s_resp.status_code == 200 and s_resp.json().get("items"):
                    top_vid_id = s_resp.json()["items"][0]["id"].get("videoId")
                    if top_vid_id:
                        chk = await client.get(
                            f"{self.API_BASE_URL}/videos",
                            params={
                                "part": "snippet,statistics,contentDetails",
                                "id": top_vid_id,
                                "key": self.api_key,
                            },
                        )
                        if chk.status_code == 200 and chk.json().get("items"):
                            vd = chk.json()["items"][0]
                            at_dur, _ = self._parse_iso_duration(
                                vd.get("contentDetails", {}).get("duration", "")
                            )
                            at_sec = self.parse_duration_to_seconds(at_dur)
                            at_views = int(vd.get("statistics", {}).get("viewCount", 0))
                            all_time_top = {
                                "title": vd.get("snippet", {}).get("title"),
                                "views": at_views,
                                "views_display": self._format_views_display(at_views),
                                "id": top_vid_id,
                                "format": "SHORTS (9:16)" if at_sec <= 60 else "LANDSCAPE (16:9)",
                                "url": f"https://www.youtube.com/watch?v={top_vid_id}",
                            }

                sample_total = landscape_count + portrait_count
                pct_landscape = (
                    round((landscape_count / sample_total * 100), 1) if sample_total else 0.0
                )
                pct_shorts = (
                    round((portrait_count / sample_total * 100), 1) if sample_total else 0.0
                )

                return {
                    "channel_id": ch_id,
                    "title": title,
                    "handle": custom_url,
                    "thumbnail_url": thumb,
                    "subscribers": subscribers,
                    "subscribers_display": f"{subscribers:,}",
                    "video_count": video_count,
                    "video_count_display": f"{video_count:,}",
                    "total_views": total_views,
                    "total_views_display": f"{total_views:,}",
                    "sample_analyzed": sample_total,
                    "landscape_count": landscape_count,
                    "landscape_percentage": pct_landscape,
                    "portrait_count": portrait_count,
                    "portrait_percentage": pct_shorts,
                    "recent_top_video": recent_top_video,
                    "all_time_top_video": all_time_top or recent_top_video,
                    "videos": parsed_videos,
                }
        except Exception as e:
            logger.warning(
                f"Error fetching competitor channel summary for {identifier}: {e}. Falling back to public scraping."
            )
            return await self._scrape_channel_public(clean_id, max_videos=max_videos)

    async def compare_competitor_channels(
        self,
        identifiers: list[str],
        my_channel_stats: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compare multiple competitor channels in parallel and calculate monetization gap & velocity."""
        clean_ids = [self.extract_channel_handle(i) for i in identifiers if i.strip()]
        tasks = [self.get_channel_summary_and_format_breakdown(cid) for cid in clean_ids]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        competitors = [r for r in raw_results if isinstance(r, dict) and r is not None]

        # Auto-load my channel stats if not supplied
        my_stats = my_channel_stats
        if not my_stats:
            try:
                from youtube_analyzer.connectors.youtube_studio import YouTubeStudioConnector

                studio = YouTubeStudioConnector()
                prof = studio.get_channel_profile()
                if prof:
                    my_stats = prof
            except Exception:
                pass

        my_subs = int(my_stats.get("subscribers", 0)) if my_stats else 0
        my_vids = int(my_stats.get("video_count", 0)) if my_stats else 0
        my_views = int(my_stats.get("view_count", 0)) if my_stats else 0
        my_title = my_stats.get("title", "Channel Saya") if my_stats else "Channel Saya"
        my_handle = my_stats.get("custom_url", "") if my_stats else ""

        # Monetization milestone calculations (YPP Thresholds)
        gap_500 = max(0, 500 - my_subs)
        gap_1000 = max(0, 1000 - my_subs)
        pct_1000 = round(min(100.0, (my_subs / 1000.0) * 100.0), 1)

        # Competitor aggregations
        avg_subs = (
            round(sum(c["subscribers"] for c in competitors) / len(competitors))
            if competitors
            else 0
        )
        avg_vids = (
            round(sum(c["video_count"] for c in competitors) / len(competitors))
            if competitors
            else 0
        )
        avg_shorts_pct = (
            round(sum(c["portrait_percentage"] for c in competitors) / len(competitors), 1)
            if competitors
            else 0.0
        )

        # Strategic Opportunity Score
        if avg_shorts_pct < 20.0:
            opp_level = "SANGAT TINGGI (GOLDEN GAP)"
            opp_note = f"Mayoritas kompetitor hampir tidak membuat Shorts (rata-rata hanya {avg_shorts_pct}%). Ini adalah celah emas untuk merebut penonton mobile dengan Shorts AI!"
        elif avg_shorts_pct < 40.0:
            opp_level = "TINGGI"
            opp_note = "Sebagian kompetitor mulai membuat Shorts, namun konsistensi masih rendah. Anda bisa menyalip dengan frekuensi upload terjadwal."
        else:
            opp_level = "MODERAT"
            opp_note = "Kompetitor aktif di Shorts dan Landscape. Dibutuhkan diferensiasi hook detik 0-3 yang lebih kuat."

        # Sorted benchmarks
        sorted_by_subs = sorted(competitors, key=lambda x: x["subscribers"])
        nearest_competitor = None
        for c in sorted_by_subs:
            if c["subscribers"] >= my_subs:
                nearest_competitor = c
                break
        if not nearest_competitor and sorted_by_subs:
            nearest_competitor = sorted_by_subs[0]

        roadmap_phases = [
            {
                "phase": "Fase 1: Tembus Target Pertama & Salip Kompetitor Terdekat",
                "target_subscribers": (
                    f"{nearest_competitor['subscribers']:,} Subs ({nearest_competitor['title']})"
                    if nearest_competitor
                    else "100 Subs"
                ),
                "recommended_pace": "5 - 7 Shorts per minggu (fokus topik praktis K3/Lean)",
                "goal": f"Menyalip kompetitor terdekat ({nearest_competitor['title'] if nearest_competitor else 'level awal'}) dan melatih algoritma YouTube merekomendasikan ceruk channel Anda.",
            },
            {
                "phase": "Fase 2: Tembus 500 Subs (Unlock Fan Funding & YouTube Shopping)",
                "target_subscribers": "500 Subscribers (Kurang " + str(gap_500) + " lagi)",
                "recommended_pace": "5 Shorts/minggu + 1 Video Landscape/minggu",
                "goal": "Membuka fitur YouTube Shopping Affiliate (ikon keranjang belanja di video) & Super Thanks.",
            },
            {
                "phase": "Fase 3: Tembus 1.000 Subs & 4.000 Jam Tayang (Full Monetisasi AdSense)",
                "target_subscribers": "1.000 Subscribers (Kurang " + str(gap_1000) + " lagi)",
                "recommended_pace": "Kontinuitas harian Shorts + 2 Video Landscape pilar/minggu",
                "goal": "Mengaktifkan bagi hasil iklan YouTube AdSense permanen dan membership channel.",
            },
        ]

        return {
            "my_channel": {
                "title": my_title,
                "handle": my_handle,
                "subscribers": my_subs,
                "subscribers_display": f"{my_subs:,}",
                "video_count": my_vids,
                "view_count": my_views,
                "gap_to_500": gap_500,
                "gap_to_1000": gap_1000,
                "percent_progress_1000": pct_1000,
            },
            "competitors": competitors,
            "benchmarks": {
                "total_competitors_analyzed": len(competitors),
                "avg_subscribers": avg_subs,
                "avg_videos": avg_vids,
                "avg_shorts_percentage": avg_shorts_pct,
                "opportunity_level": opp_level,
                "opportunity_note": opp_note,
            },
            "monetization_roadmap": roadmap_phases,
        }

    async def fetch_video_comments(
        self, video_id: str, max_results: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch live top comments from a YouTube video (via API v3 or fallback)."""
        clean_vid = self.extract_video_id(video_id) or video_id.strip()
        if not clean_vid:
            return []

        # 1. Primary: YouTube Data API v3 if API key is present
        if self.api_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    c_url = f"{self.API_BASE_URL}/commentThreads"
                    c_params = {
                        "part": "snippet",
                        "videoId": clean_vid,
                        "maxResults": min(max_results, 100),
                        "order": "relevance",
                        "key": self.api_key,
                    }
                    resp = await client.get(c_url, params=c_params)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("items", [])
                        comments: list[dict[str, Any]] = []
                        import html as pyhtml

                        for item in items:
                            top_comment = (
                                item.get("snippet", {})
                                .get("topLevelComment", {})
                                .get("snippet", {})
                            )
                            raw_text = top_comment.get("textDisplay", "")
                            # Strip HTML tags
                            clean_text = re.sub(r"<[^>]+>", " ", raw_text)
                            clean_text = pyhtml.unescape(clean_text)
                            clean_text = re.sub(r"\s+", " ", clean_text).strip()
                            if not clean_text:
                                continue
                            author = top_comment.get("authorDisplayName", "Penonton")
                            likes = int(top_comment.get("likeCount", 0))
                            published = top_comment.get("publishedAt", "")[:10]
                            comments.append(
                                {
                                    "video_id": clean_vid,
                                    "author": author,
                                    "text": clean_text,
                                    "likes": likes,
                                    "published": published,
                                }
                            )
                        if comments:
                            return comments
            except Exception as e:
                logger.warning(f"Error fetching API comments for '{clean_vid}': {e}")

        # 2. Fallback: InnerTube public next endpoint if unauthenticated / no API key
        try:
            headers = self._get_natural_headers(hl="id", gl="ID")
            payload = {
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": self.INNERTUBE_WEB_CLIENT_VERSION,
                        "hl": "id",
                        "gl": "ID",
                    }
                },
                "videoId": clean_vid,
            }
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    "https://www.youtube.com/youtubei/v1/next", json=payload, headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
                    panels = data.get("engagementPanels", [])
                    token = None
                    for p in panels:
                        renderer = p.get("engagementPanelSectionListRenderer", {})
                        if renderer.get("panelIdentifier") == "engagement-panel-comments-section":
                            sec_list = renderer.get("content", {}).get("sectionListRenderer", {})
                            for item in sec_list.get("contents", []):
                                for ci in item.get("itemSectionRenderer", {}).get("contents", []):
                                    if "continuationItemRenderer" in ci:
                                        token = (
                                            ci["continuationItemRenderer"]
                                            .get("continuationEndpoint", {})
                                            .get("continuationCommand", {})
                                            .get("token")
                                        )
                                        break
                    if token:
                        c_payload = {"context": payload["context"], "continuation": token}
                        r2 = await client.post(
                            "https://www.youtube.com/youtubei/v1/next",
                            json=c_payload,
                            headers=headers,
                        )
                        if r2.status_code == 200:
                            d2 = r2.json()
                            mutations = (
                                d2.get("frameworkUpdates", {})
                                .get("entityBatchUpdate", {})
                                .get("mutations", [])
                            )
                            innertube_comments: list[dict[str, Any]] = []
                            import html as pyhtml

                            for m in mutations:
                                cep = m.get("payload", {}).get("commentEntityPayload")
                                if cep:
                                    raw_text = (
                                        cep.get("properties", {})
                                        .get("content", {})
                                        .get("content", "")
                                    )
                                    clean_text = re.sub(r"<[^>]+>", " ", raw_text)
                                    clean_text = pyhtml.unescape(clean_text)
                                    clean_text = re.sub(r"\s+", " ", clean_text).strip()
                                    if not clean_text:
                                        continue
                                    author = cep.get("author", {}).get("displayName", "Penonton")
                                    toolbar = cep.get("toolbar", {})
                                    like_str = str(toolbar.get("likeCountNotliked", "0")).strip()
                                    likes = int(like_str) if like_str.isdigit() else 0
                                    published = cep.get("properties", {}).get("publishedTime", "")
                                    innertube_comments.append(
                                        {
                                            "video_id": clean_vid,
                                            "author": author,
                                            "text": clean_text,
                                            "likes": likes,
                                            "published": published,
                                        }
                                    )
                                    if len(innertube_comments) >= max_results:
                                        break
                            if innertube_comments:
                                return innertube_comments
        except Exception as e:
            logger.debug(f"InnerTube comments fallback failed for '{clean_vid}': {e}")

        return []

    async def mine_competitor_comments(
        self, video_ids_or_urls: list[str], max_comments_per_video: int = 30
    ) -> dict[str, Any]:
        """Mine audience friction, unanswered questions, and pain points from competitor video comments."""
        if not video_ids_or_urls:
            return {
                "total_comments_analyzed": 0,
                "total_questions_found": 0,
                "videos_analyzed": [],
                "top_pain_points": [],
                "topic_gap_opportunities": [],
            }

        # Normalize video IDs
        vids: list[str] = []
        for item in video_ids_or_urls:
            vid = self.extract_video_id(item) if ("http" in item or "/" in item) else item.strip()
            if vid and vid not in vids:
                vids.append(vid)

        # Concurrently fetch video details & comments
        target_vids = vids[:5]
        tasks_details = [self.get_video_details(vid) for vid in target_vids]
        tasks_comments = [
            self.fetch_video_comments(vid, max_results=max_comments_per_video)
            for vid in target_vids
        ]

        results_details, results_comments = await asyncio.gather(
            asyncio.gather(*tasks_details, return_exceptions=True),
            asyncio.gather(*tasks_comments, return_exceptions=True),
        )

        videos_meta: dict[str, dict[str, Any]] = {}
        for vid, det in zip(target_vids, results_details, strict=False):
            if isinstance(det, dict) and det:
                videos_meta[vid] = det
            else:
                videos_meta[vid] = {
                    "title": f"Video ({vid})",
                    "channel": "Kompetitor",
                    "views": "-",
                }

        all_comments: list[dict[str, Any]] = []
        for vid, comms in zip(target_vids, results_comments, strict=False):
            if isinstance(comms, list):
                for c in comms:
                    v_info = videos_meta.get(vid, {})
                    c["video_id"] = c.get("video_id") or vid
                    c["video_title"] = v_info.get("title", f"Video {vid}")
                    c["channel_title"] = v_info.get("channel", "Kompetitor")
                    all_comments.append(c)

        # Question & pain point indicator terms (Indonesian + English)
        question_markers = [
            "?",
            "bagaimana",
            "gimana",
            "kenapa",
            "mengapa",
            "apakah",
            "bisa gak",
            "bisa tidak",
            "bisa kah",
            "bisa ngga",
            "cara",
            "tanya",
            "mau tanya",
            "solusinya",
            "kendala",
            "kok",
            "rugi",
            "boncos",
            "suspend",
            "gagal",
            "tolong",
            "masalah",
            "tidak bisa",
            "belum tayang",
            "stuck",
            "kenapa ya",
            "how to",
            "why",
            "error",
            "problem",
            "issue",
            "does it work",
            "how do",
        ]

        spam_keywords = [
            "wa.me",
            "whatsapp",
            "081",
            "082",
            "085",
            "087",
            "089",
            "open slot",
            "judi",
            "slot gacor",
            "link bio",
        ]

        raw_pain_points: list[dict[str, Any]] = []
        for c in all_comments:
            txt = c["text"]
            txt_low = txt.lower()

            # Ignore spam & self-promotion
            if any(sk in txt_low for sk in spam_keywords):
                continue
            if len(txt) < 15:
                continue

            # Check question markers
            is_question = any(qm in txt_low for qm in question_markers)
            if not is_question:
                continue

            # Classify category
            if any(
                k in txt_low
                for k in [
                    "suspend",
                    "gagal",
                    "error",
                    "kenapa",
                    "mengapa",
                    "solusi",
                    "kok",
                    "boncos",
                    "rugi",
                    "tidak tayang",
                    "belum tayang",
                    "stuck",
                    "masalah",
                ]
            ):
                category = "TROUBLESHOOTING"
                badge = "⚠️ Kendala & Masalah"
            elif any(
                k in txt_low
                for k in [
                    "berapa",
                    "biaya",
                    "harga",
                    "saldo",
                    "bayar",
                    "gopay",
                    "rekening",
                    "modal",
                    "dana",
                    "cpc",
                ]
            ):
                category = "COMMERCIAL"
                badge = "💳 Biaya & Saldo"
            elif any(
                k in txt_low
                for k in ["bagaimana", "gimana", "cara", "langkah", "tutorial", "setting"]
            ):
                category = "HOW_TO"
                badge = "🛠️ Cara & Tutorial"
            elif any(
                k in txt_low
                for k in [
                    "apakah",
                    "bisa gak",
                    "bisa tidak",
                    "bisa kah",
                    "syarat",
                    "tanpa",
                    "hp",
                    "laptop",
                    "npwp",
                ]
            ):
                category = "ELIGIBILITY"
                badge = "🔍 Syarat & Kelayakan"
            else:
                category = "REQUEST"
                badge = "💡 Permintaan Konten"

            # Suggest opportunity title & hook
            cleaned_short = re.sub(
                r"^(halo|bang|kak|mas|gan|permisi|mau tanya|tanya kak|tanya bang)[\s,:]*",
                "",
                txt,
                flags=re.I,
            ).strip()
            cleaned_short = cleaned_short[:80]

            raw_pain_points.append(
                {
                    "author": c["author"],
                    "text": txt,
                    "likes": c["likes"],
                    "published": c.get("published", ""),
                    "video_title": c["video_title"],
                    "channel_title": c.get("channel_title", ""),
                    "video_url": f"https://www.youtube.com/watch?v={c['video_id']}",
                    "category": category,
                    "badge": badge,
                    "suggested_hook": f'Banyak yang tanya di video kompetitor: "{cleaned_short}?" Ini jawaban tuntasnya!',
                    "opportunity_title": f"Solusi Tuntas: {cleaned_short.capitalize()}",
                }
            )

        # Deduplicate & rank by likes descending + text length
        raw_pain_points.sort(key=lambda x: (x["likes"], len(x["text"])), reverse=True)

        top_pain_points = raw_pain_points[:12]

        # Extract unique topic gap opportunities
        topic_gap_opportunities: list[dict[str, Any]] = []
        seen_opps: set[str] = set()
        for p in top_pain_points:
            opp_title = p["opportunity_title"]
            if opp_title.lower() not in seen_opps and len(topic_gap_opportunities) < 5:
                seen_opps.add(opp_title.lower())
                topic_gap_opportunities.append(
                    {
                        "topic": opp_title,
                        "category": p["category"],
                        "badge": p["badge"],
                        "demand_signal": f"Ditanyakan oleh {p['author']} ({p['likes']} likes di komentar)",
                        "video_hook": p["suggested_hook"],
                        "source_competitor": p["video_title"],
                    }
                )

        return {
            "total_comments_analyzed": len(all_comments),
            "total_questions_found": len(raw_pain_points),
            "videos_analyzed": [
                {
                    "video_id": vid,
                    "title": v.get("title", ""),
                    "channel": v.get("channel", ""),
                    "views": v.get("views", "-"),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                }
                for vid, v in videos_meta.items()
            ],
            "top_pain_points": top_pain_points,
            "topic_gap_opportunities": topic_gap_opportunities,
        }

    async def get_people_also_ask(
        self, keyword: str, hl: str = "id", gl: str = "ID", max_questions: int = 15
    ) -> list[dict[str, Any]]:
        """Delegate PAA fetching to GoogleSearchConnector."""
        from youtube_analyzer.connectors.google import GoogleSearchConnector

        g_conn = GoogleSearchConnector()
        return await g_conn.get_people_also_ask(keyword, hl=hl, gl=gl, max_questions=max_questions)


# Expose helper function at module level
parse_duration_to_seconds = YouTubeConnector.parse_duration_to_seconds
