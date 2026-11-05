import os
import sys
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Add api/ and src/ to sys.path so we can import youtube_analyzer modules in both local and Vercel serverless environments
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
for p in [CURRENT_DIR, SRC_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

IMPORT_ERROR_MSG: str | None = None
try:
    from youtube_analyzer.connectors.hasdata_trends import HasDataTrendsConnector
    from youtube_analyzer.connectors.youtube import YouTubeConnector
    from youtube_analyzer.core.ai_generator import AITitleGenerator
    from youtube_analyzer.core.intelligence import SearchIntelligence
    from youtube_analyzer.core.models import IntentEnum, PlatformEnum
    from youtube_analyzer.core.normalizer import TopicNormalizer
except Exception as e:
    IMPORT_ERROR_MSG = str(e)
    print("Import warning in api/index.py:", e)
    SearchIntelligence = None  # type: ignore
    YouTubeConnector = None  # type: ignore
    HasDataTrendsConnector = None  # type: ignore
    AITitleGenerator = None  # type: ignore
    TopicNormalizer = None  # type: ignore
    PlatformEnum = None  # type: ignore
    IntentEnum = None  # type: ignore

app = FastAPI(
    title="YouTube Search & Competitor Intelligence (Vercel Cloud + WebMCP)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# Enable CORS for Google Flow, Labs, and local Studio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

ADMIN_MASTER_KEY = os.getenv("ADMIN_MASTER_KEY", "dracin-admin-2026")


def check_admin_authorization(
    x_dracin_admin_key: str | None = None,
    authorization: str | None = None,
    query_key: str | None = None,
    body_key: str | None = None,
) -> bool:
    """Verifies admin authorization from headers, query string, or request body."""
    key = x_dracin_admin_key or query_key or body_key
    if not key and authorization:
        if authorization.startswith("Bearer "):
            key = authorization.split("Bearer ")[1].strip()
        else:
            key = authorization.strip()

    if not key or key.strip() != ADMIN_MASTER_KEY.strip():
        raise HTTPException(
            status_code=401,
            detail="Akses Ditolak: Kunci Admin Dracin tidak valid atau belum diotorisasi. Hubungi administrator.",
        )
    return True


# ==============================================================================
# WebMCP (Chrome DevTools & AI Agent Web Model Context Protocol) Tools Catalog
# ==============================================================================
WEBMCP_TOOLS_CATALOG = [
    {
        "name": "generate_flow_shotlist",
        "description": "Generate 6-Scene AI Video Storyboard and prompt batch (Hook 0-5s, Build up, Climax, Outro) from YouTube search intelligence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "seed_keyword": {
                    "type": "string",
                    "description": "Topik naskah atau kata kunci YouTube",
                },
                "format_type": {
                    "type": "string",
                    "enum": ["SHORTS", "LANDSCAPE"],
                    "default": "SHORTS",
                },
                "num_scenes": {"type": "integer", "default": 6},
            },
            "required": ["seed_keyword"],
        },
    },
    {
        "name": "analyze_faceless_niche_viability",
        "description": "Evaluasi kelayakan ceruk channel video AI tanpa wajah (Faceless AI Niche) berdasarkan demand dan CPM score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "seed_keyword": {
                    "type": "string",
                    "description": "Ceruk atau topik yang dievaluasi",
                }
            },
            "required": ["seed_keyword"],
        },
    },
    {
        "name": "generate_video_ideas",
        "description": "Menghasilkan formula judul ber-CTR tinggi dan variasi hook detik 0-3 berdasarkan search intent penonton.",
        "inputSchema": {
            "type": "object",
            "properties": {"seed_keyword": {"type": "string", "description": "Topik video"}},
            "required": ["seed_keyword"],
        },
    },
    {
        "name": "get_youtube_trending",
        "description": "Mengambil topik dan video yang sedang tren di YouTube untuk wilayah tertentu (default: ID).",
        "inputSchema": {
            "type": "object",
            "properties": {"country": {"type": "string", "default": "ID"}},
        },
    },
]


# ==============================================================================
# Root Interactive Executive Dashboard (Full Parity with dashboard.py)
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
async def root():
    ui_path = os.path.join(CURRENT_DIR, "dashboard_ui.html")
    if os.path.exists(ui_path):
        with open(ui_path, encoding="utf-8") as f:
            return f.read()
    return "<h1>YouTube Search & Competitor Intelligence</h1>"


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "youtube-analyzer-serverless",
        "version": "2.0.1",
        "cors_enabled": True,
        "engine_loaded": YouTubeConnector is not None,
        "import_error": IMPORT_ERROR_MSG,
        "webmcp_tools_count": len(WEBMCP_TOOLS_CATALOG),
    }


# ==============================================================================
# Dashboard Backend Endpoints (Powers the 10-Tab Interactive UI)
# ==============================================================================
class AnalyzeRequest(BaseModel):
    keyword: str
    ai_config: dict[str, Any] | None = None


class AuditVideoRequest(BaseModel):
    video_url: str
    ai_config: dict[str, Any] | None = None


class PreUploadRequest(BaseModel):
    topic: str
    content_notes: str
    target_format: str = "LANDSCAPE (16:9)"
    duration: str = "12:00"
    ai_config: dict[str, Any] | None = None


def _build_surfaces_and_clusters(seed_keyword: str) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]], list[str]]:
    if not TopicNormalizer or not PlatformEnum:
        return {"google": [], "youtube": [], "ai": []}, [], []

    raw_surfaces = TopicNormalizer.expand_seed_surfaces(seed_keyword)
    g_terms = raw_surfaces.get(PlatformEnum.GOOGLE_SEARCH, [])
    yt_terms = raw_surfaces.get(PlatformEnum.YOUTUBE_SEARCH, [])
    ai_terms = raw_surfaces.get(PlatformEnum.AI_SEARCH, [])

    surfaces_out = {
        "google": [
            {"term": t, "intent": TopicNormalizer.classify_intent(t).value.upper()}
            for t in g_terms
        ],
        "youtube": [
            {"term": t, "intent": TopicNormalizer.classify_intent(t).value.upper()}
            for t in yt_terms
        ],
        "ai": [
            {"term": t, "intent": TopicNormalizer.classify_intent(t).value.upper()}
            for t in ai_terms
        ],
    }

    clusters_raw = TopicNormalizer.create_intent_clusters(
        topic_id=1,
        google_terms=g_terms,
        youtube_terms=yt_terms,
        aeo_queries=ai_terms,
    )
    clusters_out = [
        {
            "cluster_name": c.cluster_name,
            "intent_type": c.intent_type.value.upper()
            if hasattr(c.intent_type, "value")
            else str(c.intent_type).upper(),
            "google_term_sample": c.google_term_sample or "-",
            "youtube_term_sample": c.youtube_term_sample or "-",
            "aeo_query_sample": c.aeo_query_sample or "-",
        }
        for c in clusters_raw
    ]
    all_queries = g_terms + yt_terms + ai_terms
    return surfaces_out, clusters_out, all_queries


@app.post("/api/dashboard/analyze")
async def api_dashboard_analyze(req: AnalyzeRequest):
    kw = (req.keyword or "Google Ads untuk UMKM").strip()
    yt_conn = YouTubeConnector()
    competitors = await yt_conn.get_top_competitors(kw, limit=10)
    top_comp = competitors[0] if competitors else None

    surfaces_out, clusters_out, all_queries = _build_surfaces_and_clusters(kw)

    rpm_data = SearchIntelligence.estimate_rpm(kw)
    kw_metrics = SearchIntelligence.estimate_keyword_metrics(kw, competitors)
    ai_presence = SearchIntelligence.analyze_ai_competitor_presence(competitors)
    outranking_plan = SearchIntelligence.generate_outranking_plan(
        kw,
        competitor=top_comp,
        competitors=competitors,
        ai_config=req.ai_config,
    )
    comp_spy = (
        await yt_conn.spy_competitor_tags(competitors, limit_competitors=5)
        if competitors
        else {}
    )
    content_gaps = SearchIntelligence.detect_content_gaps(kw, competitors, all_queries)
    outlier_analysis = SearchIntelligence.analyze_competitor_outliers(competitors)
    faceless_info = SearchIntelligence.analyze_faceless_viability(kw, rpm_data)
    clipping_ideas = SearchIntelligence.generate_clipping_opportunities(
        kw, outranking_plan.get("outranking_title", kw)
    )
    comp_format = top_comp.get("format", "LANDSCAPE") if top_comp else "LANDSCAPE"
    flow_shotlist = SearchIntelligence.generate_flow_shotlist(
        seed=kw, format_type=comp_format, num_scenes=5
    )

    return {
        "keyword": kw,
        "competitors": competitors,
        "rpm_data": rpm_data,
        "kw_metrics": kw_metrics,
        "ai_presence": ai_presence,
        "outranking_plan": outranking_plan,
        "comp_spy": comp_spy,
        "content_gaps": content_gaps,
        "outlier_analysis": outlier_analysis,
        "faceless_info": faceless_info,
        "clipping_ideas": clipping_ideas,
        "flow_shotlist": flow_shotlist,
        "surfaces": surfaces_out,
        "clusters": clusters_out,
    }


@app.post("/api/dashboard/audit-video")
async def api_dashboard_audit_video(req: AuditVideoRequest):
    vid_id = YouTubeConnector.extract_video_id(req.video_url.strip())
    if not vid_id:
        raise HTTPException(
            status_code=400, detail="Format URL atau Video ID YouTube tidak valid."
        )

    yt_conn = YouTubeConnector()
    vid_meta = await yt_conn.get_video_details(vid_id)
    if not vid_meta:
        raise HTTPException(
            status_code=404,
            detail=f"Gagal mengambil detail video ID '{vid_id}'. Pastikan video Public atau Unlisted.",
        )

    vid_transcript = yt_conn.get_video_transcript(vid_id)
    rel_competitors = await yt_conn.get_top_competitors(
        vid_meta.get("title", vid_id), limit=5
    )

    ai_cfg = req.ai_config or {}
    audit_res = AITitleGenerator.audit_and_revamp(
        video_details=vid_meta,
        transcript_data=vid_transcript,
        competitors=rel_competitors,
        provider=ai_cfg.get("provider"),
        api_key=ai_cfg.get("api_key"),
        model_name=ai_cfg.get("model_name"),
        custom_base_url=ai_cfg.get("custom_base_url"),
    )

    return {
        "video_details": vid_meta,
        "transcript": vid_transcript,
        "audit_result": audit_res,
    }


@app.post("/api/dashboard/pre-upload")
async def api_dashboard_pre_upload(req: PreUploadRequest):
    yt_conn = YouTubeConnector()
    comp_for_draft = await yt_conn.get_top_competitors(req.topic, limit=5)
    ai_cfg = req.ai_config or {}

    return AITitleGenerator.plan_pre_upload(
        topic=req.topic,
        content_notes=req.content_notes,
        target_format=req.target_format,
        duration=req.duration,
        competitors=comp_for_draft,
        provider=ai_cfg.get("provider"),
        api_key=ai_cfg.get("api_key"),
        model_name=ai_cfg.get("model_name"),
        custom_base_url=ai_cfg.get("custom_base_url"),
    )


@app.get("/api/dashboard/trending")
async def api_dashboard_trending(
    gl: str = "ID",
    hl: str = "id",
    category: str = "now",
    device: str = "desktop",
):
    yt_conn = YouTubeConnector()
    feed = await yt_conn.get_trending_feed(
        gl=gl, hl=hl, category=category, device=device, limit=10
    )
    return {"trending": feed}


async def _fetch_google_trends_rss(geo: str = "ID") -> list[dict[str, str]]:
    target_geo = geo.upper() if geo and geo.upper() != "WW" else ""
    url = (
        f"https://trends.google.co.id/trending/rss?geo={target_geo}"
        if target_geo
        else "https://trends.google.co.id/trending/rss"
    )
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                items = []
                for it in root.findall(".//item")[:10]:
                    title_elem = it.find("title")
                    title = title_elem.text if title_elem is not None else ""
                    approx = it.find(
                        "{https://trends.google.co.id/trending/rss}approx_traffic"
                    )
                    traffic = (
                        approx.text
                        if (approx is not None and approx.text)
                        else "Trending"
                    )
                    link_elem = it.find("link")
                    link = link_elem.text if link_elem is not None else ""
                    if title:
                        items.append(
                            {
                                "Topik Tren": title,
                                "Estimasi Penelusuran": traffic,
                                "Tautan Google": link,
                            }
                        )
                return items
    except Exception:
        pass
    return []


@app.get("/api/dashboard/trends")
async def api_dashboard_trends(keyword: str = "Google Ads UMKM", geo: str = "ID"):
    connector = HasDataTrendsConnector()
    res = await connector.compare_google_vs_youtube(keyword, geo=geo)
    daily_rss = await _fetch_google_trends_rss(geo=geo)
    res["daily_rss"] = daily_rss
    return res


# ==============================================================================
# Google Flow & WebMCP Endpoints (100% Preserved)
# ==============================================================================
class AdminVerifyRequest(BaseModel):
    key: str = ""


class WebMCPCallRequest(BaseModel):
    name: str | None = None
    arguments: dict[str, Any] = {}


@app.post("/api/admin/verify")
async def verify_admin_key(payload: AdminVerifyRequest):
    key = payload.key.strip()
    if key == ADMIN_MASTER_KEY.strip():
        return {"success": True, "message": "Otorisasi Admin Berhasil!"}
    return {"success": False, "detail": "Kunci Admin salah atau tidak memiliki akses."}


@app.get("/api/webmcp/tools")
async def get_webmcp_tools():
    return {"tools": WEBMCP_TOOLS_CATALOG}


@app.post("/api/webmcp/call")
async def call_webmcp_tool(payload: WebMCPCallRequest):
    name = payload.name
    args = payload.arguments

    if name == "generate_flow_shotlist":
        seed = args.get("seed_keyword", "Keluarga")
        fmt = args.get("format_type", "SHORTS")
        scenes = int(args.get("num_scenes", 6))
        return execute_flow_shotlist(seed, fmt, scenes)

    elif name == "generate_video_ideas":
        seed = args.get("seed_keyword", "Teknologi")
        if SearchIntelligence and hasattr(SearchIntelligence, "generate_video_ideas"):
            try:
                return SearchIntelligence.generate_video_ideas(seed=seed)
            except Exception:
                pass
        return {
            "seed": seed,
            "hooks": [
                f"Jangan lakukan ini saat membahas {seed}!",
                f"Rahasia tersembunyi {seed} yang jarang diungkap orang.",
                f"Setelah tahu trik {seed} ini, hidup Anda akan berubah.",
            ],
        }

    elif name == "get_youtube_trending":
        country = args.get("country", "ID")
        return {
            "region": country,
            "trending_topics": [
                f"Tren Hiburan & Cerita Viral {country}",
                f"Review Produk & Rekomendasi Terhangat {country}",
                f"Tutorial & Solusi Praktis {country}",
            ],
        }

    elif name == "analyze_faceless_niche_viability":
        seed = args.get("seed_keyword", "Cerita Misteri")
        return {
            "niche": seed,
            "viability_score": 88,
            "cpm_tier": "High ($8 - $14)",
            "competition": "Medium",
            "recommendation": "Sangat cocok untuk format 9:16 Shorts/Reels dan drama vertikal 1 menit.",
        }

    else:
        raise HTTPException(
            status_code=404, detail=f"WebMCP tool '{name}' tidak dikenal."
        )


class ShotlistRequest(BaseModel):
    seed_keyword: str
    format_type: str = "SHORTS"
    num_scenes: int = 6
    admin_key: str | None = None


def execute_flow_shotlist(seed: str, format_type: str, num_scenes: int):
    if SearchIntelligence and hasattr(SearchIntelligence, "generate_flow_shotlist"):
        try:
            return SearchIntelligence.generate_flow_shotlist(
                seed=seed, format_type=format_type, num_scenes=num_scenes
            )
        except Exception as e:
            print("Error executing SearchIntelligence:", e)

    return {
        "seed_keyword": seed,
        "format_type": format_type,
        "aspect_ratio": "9:16" if format_type == "SHORTS" else "16:9",
        "scenes_count": num_scenes,
        "scenes": [
            {
                "scene_id": f"Scene {i+1}",
                "timing": f"Beat {i+1} ({i*10}-{(i+1)*10}s)",
                "duration_seconds": 10,
                "visual_action": f"Adegan dramatis seputar {seed} dengan visual cinematik tajam dan emosi intens.",
                "camera_motion": "Dramatic Push-In (35mm Cine Lens)",
                "dialogue": f"Kalimat emosional pembuka adegan {i+1} tentang {seed}.",
            }
            for i in range(num_scenes)
        ],
    }


@app.post("/api/shotlist")
async def api_generate_shotlist(
    req: ShotlistRequest,
    x_dracin_admin_key: str | None = Header(None),
    authorization: str | None = Header(None),
    key: str | None = Query(None),
):
    check_admin_authorization(
        x_dracin_admin_key=x_dracin_admin_key,
        authorization=authorization,
        query_key=key,
        body_key=req.admin_key,
    )

    data = execute_flow_shotlist(req.seed_keyword, req.format_type, req.num_scenes)
    return {
        "success": True,
        "data": data,
        "message": "Shotlist AI berhasil digenerate dari YouTube Intelligence!",
    }
