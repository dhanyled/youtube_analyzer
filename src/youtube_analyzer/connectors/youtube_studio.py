"""YouTube Studio & Channel Analytics Connector (OAuth 2.0).

Enables deep integration with creator channel inventory, analytics,
CTR inspection, and automated batch audit.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Scopes needed for channel inventory, analytics, and automated video upload
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
]

TOKEN_FILE = os.path.abspath(".youtube_token.json")
CLIENT_SECRET_FILE = os.path.abspath("client_secret.json")


class YouTubeStudioConnector:
    """Manages YouTube Studio OAuth authentication, channel inventory, and analytics."""

    def __init__(self, token_path: str = TOKEN_FILE):
        self.token_path = token_path
        self.credentials = None
        self.youtube_service = None
        self.analytics_service = None
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load and refresh credentials from token file if present."""
        if not os.path.exists(self.token_path):
            return

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(self.token_path, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                except Exception as ref_err:
                    logger.warning(f"Could not refresh YouTube Studio token: {ref_err}")
            if creds and creds.valid:
                self.credentials = creds
                self._init_services()
        except Exception as e:
            logger.warning(f"Failed loading stored YouTube Studio credentials: {e}")

    def _init_services(self) -> None:
        """Initialize Google API clients for YouTube Data v3 and YouTube Analytics."""
        if not self.credentials:
            return
        try:
            from googleapiclient.discovery import build

            self.youtube_service = build("youtube", "v3", credentials=self.credentials)
            try:
                self.analytics_service = build(
                    "youtubeAnalytics", "v2", credentials=self.credentials
                )
            except Exception as an_err:
                logger.warning(f"Analytics service init note: {an_err}")
        except Exception as e:
            logger.error(f"Failed to build YouTube API clients: {e}")

    def is_authenticated(self) -> bool:
        """Return True if active valid credentials are ready."""
        return bool(self.credentials and self.credentials.valid and self.youtube_service)

    def logout(self) -> None:
        """Clear local credentials and token file."""
        self.credentials = None
        self.youtube_service = None
        self.analytics_service = None
        if os.path.exists(self.token_path):
            try:
                os.remove(self.token_path)
            except Exception as e:
                logger.warning(f"Could not remove token file: {e}")

    def authenticate_interactive(self, client_secrets_file: str | None = None) -> tuple[bool, str]:
        """Run interactive local server OAuth flow (opens browser to authenticate)."""
        secrets_file = client_secrets_file or CLIENT_SECRET_FILE
        if not os.path.exists(secrets_file):
            json_dir = os.path.abspath("json")
            if os.path.exists(json_dir):
                for fname in os.listdir(json_dir):
                    if fname.startswith("client_secret") and fname.endswith(".json"):
                        secrets_file = os.path.join(json_dir, fname)
                        break

        if not os.path.exists(secrets_file):
            # Check if environment variables can supply credentials
            client_id = os.getenv("YOUTUBE_CLIENT_ID")
            client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
            if client_id and client_secret:
                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                }
                with open(CLIENT_SECRET_FILE, "w", encoding="utf-8") as f:
                    json.dump(client_config, f, indent=2)
                secrets_file = CLIENT_SECRET_FILE
            else:
                return (
                    False,
                    f"File '{os.path.basename(secrets_file)}' tidak ditemukan. "
                    "Silakan unduh OAuth Client ID JSON dari Google Cloud Console.",
                )

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
            prompt_msg = (
                "\n============================================================\n"
                "SILAKAN KLIK ATAU SALIN LINK BERIKUT KE BROWSER UNTUK LOGIN:\n"
                "{url}\n"
                "============================================================\n"
            )
            # Run local server flow on an available port
            creds = flow.run_local_server(
                port=0,
                prompt="consent",
                authorization_prompt_message=prompt_msg,
                success_message="Otorisasi Berhasil! Token YouTube Studio telah tersimpan. Anda boleh menutup tab ini.",
                open_browser=True,
            )
            if creds:
                self.credentials = creds
                with open(self.token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
                self._init_services()
                return True, "Berhasil menghubungkan channel YouTube Studio!"
            return False, "Otorisasi dibatalkan."
        except Exception as e:
            return False, f"Gagal proses otorisasi: {e}"

    def get_channel_profile(self) -> dict[str, Any] | None:
        """Fetch authenticated channel details (title, subscribers, views, video count)."""
        if not self.is_authenticated():
            return None

        try:
            resp = (
                self.youtube_service.channels()
                .list(part="snippet,statistics,contentDetails", mine=True)
                .execute()
            )
            items = resp.get("items", [])
            if not items:
                return None
            item = items[0]
            snip = item.get("snippet", {})
            stats = item.get("statistics", {})
            cd = item.get("contentDetails", {})
            uploads_list_id = cd.get("relatedPlaylists", {}).get("uploads", "")

            subs = int(stats.get("subscriberCount", 0))
            v_count = int(stats.get("videoCount", 0))
            v_views = int(stats.get("viewCount", 0))

            thumbnails = snip.get("thumbnails", {})
            thumb = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url", "")
            )

            return {
                "channel_id": item.get("id", ""),
                "title": snip.get("title", ""),
                "custom_url": snip.get("customUrl", ""),
                "description": snip.get("description", ""),
                "thumbnail_url": thumb,
                "subscribers": subs,
                "subscribers_display": f"{subs:,}",
                "video_count": v_count,
                "view_count": v_views,
                "view_count_display": f"{v_views:,}",
                "uploads_playlist_id": uploads_list_id,
            }
        except Exception as e:
            logger.error(f"Error fetching channel profile: {e}")
            return None

    def get_channel_videos(self, limit: int = 30) -> list[dict[str, Any]]:
        """Fetch the latest uploaded videos from the creator's channel."""
        if not self.is_authenticated():
            return []

        profile = self.get_channel_profile()
        if not profile or not profile.get("uploads_playlist_id"):
            return []

        uploads_id = profile["uploads_playlist_id"]
        try:
            # 1. Fetch playlist items
            p_resp = (
                self.youtube_service.playlistItems()
                .list(
                    part="snippet,contentDetails",
                    playlistId=uploads_id,
                    maxResults=min(limit, 50),
                )
                .execute()
            )
            p_items = p_resp.get("items", [])
            vid_ids = [
                it["contentDetails"]["videoId"]
                for it in p_items
                if "contentDetails" in it and "videoId" in it["contentDetails"]
            ]
            if not vid_ids:
                return []

            # 2. Fetch full video statistics and content details
            v_resp = (
                self.youtube_service.videos()
                .list(
                    part="snippet,contentDetails,statistics",
                    id=",".join(vid_ids),
                )
                .execute()
            )
            v_items = v_resp.get("items", [])
            v_map = {v["id"]: v for v in v_items}

            from youtube_analyzer.connectors.youtube import YouTubeConnector

            yt_conn = YouTubeConnector()

            videos = []
            for vid_id in vid_ids:
                v_data = v_map.get(vid_id)
                if not v_data:
                    continue
                snip = v_data.get("snippet", {})
                stats = v_data.get("statistics", {})
                cd = v_data.get("contentDetails", {})

                raw_views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                comments = int(stats.get("commentCount", 0))

                dur_iso = cd.get("duration", "")
                dur_text, _ = yt_conn._parse_iso_duration(dur_iso)
                dur_sec = yt_conn.parse_duration_to_seconds(dur_text)

                thumbnails = snip.get("thumbnails", {})
                thumb_url = (
                    thumbnails.get("maxres", {}).get("url")
                    or thumbnails.get("standard", {}).get("url")
                    or thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url", "")
                )

                v_title = snip.get("title", "")
                v_desc = snip.get("description", "")

                # Authoritative format detection: does not falsely classify short landscape videos as Shorts
                is_shorts, format_type = yt_conn.detect_video_format(
                    video_id=vid_id,
                    title=v_title,
                    duration_seconds=dur_sec,
                    thumbnail_url=thumb_url,
                )

                studio_tags = [t.strip() for t in snip.get("tags", []) if t and t.strip()]
                desc_hashtags = [
                    f"#{w}" for w in re.findall(r"#([a-zA-Z0-9_\u00c0-\u00ff]+)", v_desc) if w
                ]
                unified_tags = (
                    studio_tags if studio_tags else [h.lstrip("#") for h in desc_hashtags]
                )

                pub_at = snip.get("publishedAt", "")

                videos.append(
                    {
                        "video_id": vid_id,
                        "title": v_title,
                        "description": v_desc,
                        "tags": unified_tags,
                        "studio_tags": studio_tags,
                        "desc_hashtags": desc_hashtags,
                        "has_studio_tags": len(studio_tags) > 0,
                        "channel": snip.get("channelTitle", ""),
                        "published_at": pub_at[:10] if pub_at else "",
                        "views": raw_views,
                        "views_display": yt_conn._format_views_display(raw_views),
                        "likes": likes,
                        "comments": comments,
                        "duration": dur_text,
                        "duration_seconds": dur_sec,
                        "is_shorts": is_shorts,
                        "format": format_type,
                        "thumbnail_url": thumb_url,
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                    }
                )
            return videos
        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")
            return []

    def get_channel_analytics_summary(self) -> dict[str, Any]:
        """Fetch last 28 days channel analytics summary (views, watch time, estimated CTR)."""
        if not self.is_authenticated() or not self.analytics_service:
            return {"available": False, "reason": "Layanan analitik belum diinisialisasi."}

        profile = self.get_channel_profile()
        if not profile:
            return {"available": False, "reason": "Profil channel tidak ditemukan."}

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")

        try:
            res = (
                self.analytics_service.reports()
                .query(
                    ids=f"channel=={profile['channel_id']}",
                    startDate=start_date,
                    endDate=end_date,
                    metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained",
                )
                .execute()
            )
            rows = res.get("rows", [])
            if rows and len(rows[0]) >= 4:
                row = rows[0]
                views_28d = int(row[0])
                mins_28d = int(row[1])
                avg_dur_sec = int(row[2])
                subs_gained = int(row[3])
                hours_28d = round(mins_28d / 60, 1)

                return {
                    "available": True,
                    "views_28d": views_28d,
                    "views_28d_display": f"{views_28d:,}",
                    "watch_hours_28d": hours_28d,
                    "watch_hours_display": f"{hours_28d:,.1f} jam",
                    "avg_view_duration_sec": avg_dur_sec,
                    "avg_view_duration_display": f"{avg_dur_sec // 60}:{avg_dur_sec % 60:02d}",
                    "subs_gained": subs_gained,
                }
            return {
                "available": False,
                "reason": "Belum ada cukup data analitik pada 28 hari terakhir.",
            }
        except Exception as e:
            logger.warning(f"Analytics report query note: {e}")
            return {"available": False, "reason": str(e)}

    @staticmethod
    def diagnose_channel_videos(videos: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze video catalog to identify underperforming gems and top performers."""
        if not videos:
            return {
                "total_videos": 0,
                "underperforming_gems": [],
                "top_performers": [],
                "avg_views": 0,
            }

        total = len(videos)
        views_list = [v["views"] for v in videos]
        avg_views = sum(views_list) / max(total, 1)

        # Sort by views descending
        sorted_by_views = sorted(videos, key=lambda x: x["views"], reverse=True)
        top_performers = sorted_by_views[: min(3, total)]

        # Underperforming gems: videos with views significantly below average,
        # or videos with low tags / weak titles that are prime candidates for revamp
        underperforming = []
        for v in sorted_by_views:
            title = v.get("title", "")
            studio_tags = v.get("studio_tags", [])
            desc_hashtags = v.get("desc_hashtags", [])
            studio_tags_count = len(studio_tags)
            desc_hash_count = len(desc_hashtags)
            v_views = v.get("views", 0)

            # Flag if views < 70% of average or Studio tags are scarce (< 5)
            is_underperforming = (v_views < avg_views * 0.7) or (studio_tags_count < 5)
            if is_underperforming and len(underperforming) < 5:
                weakness_reason = []
                if studio_tags_count == 0 and desc_hash_count > 0:
                    weakness_reason.append(
                        f"Kolom Tags YouTube Studio masih kosong (0 tags), baru ada {desc_hash_count} hashtag di deskripsi"
                    )
                elif studio_tags_count == 0 and desc_hash_count == 0:
                    weakness_reason.append(
                        "Belum ada tags di Studio maupun hashtag di deskripsi (minim SEO)"
                    )
                elif studio_tags_count < 5:
                    weakness_reason.append(
                        f"Hanya ada {studio_tags_count} tags di Studio (disarankan 15-20 kata kunci)"
                    )

                if v_views < avg_views * 0.5:
                    weakness_reason.append("Views jauh di bawah rata-rata channel")
                if len(title.split()) < 5:
                    weakness_reason.append("Judul terlalu singkat / kurang hook NLP")

                underperforming.append(
                    {
                        **v,
                        "weakness_reason": (
                            ", ".join(weakness_reason)
                            if weakness_reason
                            else "Potensi views belum maksimal"
                        ),
                    }
                )

        return {
            "total_videos": total,
            "avg_views": int(avg_views),
            "avg_views_display": f"{int(avg_views):,}",
            "top_performers": top_performers,
            "underperforming_gems": underperforming,
        }
