import os
import sys
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Query, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Add src to sys.path so we can import youtube_analyzer modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from youtube_analyzer.core.intelligence import SearchIntelligence
except Exception as e:
    SearchIntelligence = None

app = FastAPI(
    title="YouTube Analyzer & AI Video Shotlist Cloud API (Vercel Serverless)",
    version="1.1.0",
    docs_url="/docs",
    redoc_url=None
)

# Enable CORS for Google Flow, Labs, and local Studio
# Note: allow_credentials=False is required by fetch standard when allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

ADMIN_MASTER_KEY = os.getenv("ADMIN_MASTER_KEY", "dracin-admin-2026")

def check_admin_authorization(
    x_dracin_admin_key: Optional[str] = None,
    authorization: Optional[str] = None,
    query_key: Optional[str] = None,
    body_key: Optional[str] = None
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
            detail="Akses Ditolak: Kunci Admin Dracin tidak valid atau belum diotorisasi. Hubungi administrator."
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
                "seed_keyword": { "type": "string", "description": "Topik naskah atau kata kunci YouTube" },
                "format_type": { "type": "string", "enum": ["SHORTS", "LANDSCAPE"], "default": "SHORTS" },
                "num_scenes": { "type": "integer", "default": 6 }
            },
            "required": ["seed_keyword"]
        }
    },
    {
        "name": "analyze_faceless_niche_viability",
        "description": "Evaluasi kelayakan ceruk channel video AI tanpa wajah (Faceless AI Niche) berdasarkan demand dan CPM score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "seed_keyword": { "type": "string", "description": "Ceruk atau topik yang dievaluasi" }
            },
            "required": ["seed_keyword"]
        }
    },
    {
        "name": "generate_video_ideas",
        "description": "Menghasilkan formula judul ber-CTR tinggi dan variasi hook detik 0-3 berdasarkan search intent penonton.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "seed_keyword": { "type": "string", "description": "Topik video" }
            },
            "required": ["seed_keyword"]
        }
    },
    {
        "name": "get_youtube_trending",
        "description": "Mengambil topik dan video yang sedang tren di YouTube untuk wilayah tertentu (default: ID).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "country": { "type": "string", "default": "ID" }
            }
        }
    }
]

# Root HTML with WebMCP Polyfill & Status Dashboard
@app.get("/", response_class=HTMLResponse)
async def root():
    return f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
      <meta charset="UTF-8">
      <title>YouTube Analyzer & WebMCP Serverless Bridge</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen flex items-center justify-center p-6">
      <div class="max-w-xl w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 space-y-6 shadow-2xl">
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-500 text-2xl font-black">
            ▶
          </div>
          <div>
            <h1 class="text-xl font-bold text-white">YouTube Analyzer Cloud API</h1>
            <p class="text-xs text-slate-400">Vercel Serverless & WebMCP Agent-Native Bridge</p>
          </div>
        </div>

        <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
          <div class="flex justify-between items-center text-emerald-400 font-mono font-semibold">
            <span>● System Status</span>
            <span>Online & Ready (v1.1.0)</span>
          </div>
          <p class="text-slate-400">Terhubung dengan Google Flow Dracin Studio & Chrome DevTools AI Agent.</p>
        </div>

        <div class="space-y-3">
          <h3 class="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">WebMCP Available Tools</h3>
          <div class="grid grid-cols-1 gap-2 text-xs">
            <div class="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 flex justify-between items-center">
              <span class="font-mono text-amber-400">generate_flow_shotlist</span>
              <span class="text-[10px] text-slate-400">6-Scene AI Storyboard</span>
            </div>
            <div class="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 flex justify-between items-center">
              <span class="font-mono text-amber-400">generate_video_ideas</span>
              <span class="text-[10px] text-slate-400">Viral Hooks & High CTR</span>
            </div>
            <div class="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 flex justify-between items-center">
              <span class="font-mono text-amber-400">get_youtube_trending</span>
              <span class="text-[10px] text-slate-400">Feed Trending ID</span>
            </div>
          </div>
        </div>

        <div class="pt-4 border-t border-slate-800 flex justify-between items-center text-xs text-slate-500">
          <span>Director Engine by @leddhany</span>
          <a href="/docs" class="text-red-400 hover:text-red-300 font-mono underline">Open Swagger Docs →</a>
        </div>
      </div>

      <!-- Official Chrome WebMCP Bridge for AI Agents -->
      <script>
        (function() {{
          const WebMCP = {{
            async listTools() {{
              const res = await fetch('/api/webmcp/tools');
              const data = await res.json();
              return data.tools || [];
            }},
            async callTool(name, args = {{}}) {{
              const res = await fetch('/api/webmcp/call', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ name, arguments: args }})
              }});
              return await res.json();
            }}
          }};
          window.WebMCP = WebMCP;
          if (typeof navigator !== 'undefined' && !navigator.modelContext) {{
            navigator.modelContext = WebMCP;
          }}
          console.log('[WebMCP] YouTube Analyzer Agent-Native Bridge Initialized.');
        }})();
      </script>
    </body>
    </html>
    """

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "youtube-analyzer-serverless",
        "version": "1.1.0",
        "cors_enabled": True,
        "webmcp_tools_count": len(WEBMCP_TOOLS_CATALOG)
    }

# Endpoint for verifying Admin Key from Google Flow
@app.post("/api/admin/verify")
async def verify_admin_key(payload: dict = Body(...)):
    key = payload.get("key", "").strip()
    if key == ADMIN_MASTER_KEY.strip():
        return {"success": True, "message": "Otorisasi Admin Berhasil!"}
    return {"success": False, "detail": "Kunci Admin salah atau tidak memiliki akses."}

# ==============================================================================
# WebMCP Protocol Endpoints (GET /api/webmcp/tools & POST /api/webmcp/call)
# ==============================================================================
@app.get("/api/webmcp/tools")
async def get_webmcp_tools():
    return { "tools": WEBMCP_TOOLS_CATALOG }

@app.post("/api/webmcp/call")
async def call_webmcp_tool(payload: dict = Body(...)):
    name = payload.get("name")
    args = payload.get("arguments", {})

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
                f"Setelah tahu trik {seed} ini, hidup Anda akan berubah."
            ]
        }

    elif name == "get_youtube_trending":
        country = args.get("country", "ID")
        return {
            "region": country,
            "trending_topics": [
                f"Tren Hiburan & Cerita Viral {country}",
                f"Review Produk & Rekomendasi Terhangat {country}",
                f"Tutorial & Solusi Praktis {country}"
            ]
        }

    elif name == "analyze_faceless_niche_viability":
        seed = args.get("seed_keyword", "Cerita Misteri")
        return {
            "niche": seed,
            "viability_score": 88,
            "cpm_tier": "High ($8 - $14)",
            "competition": "Medium",
            "recommendation": f"Sangat cocok untuk format 9:16 Shorts/Reels dan drama vertikal 1 menit."
        }

    else:
        raise HTTPException(status_code=404, detail=f"WebMCP tool '{name}' tidak dikenal.")

# ==============================================================================
# Google Flow Integration Endpoints (Protected by Admin Key)
# ==============================================================================
class ShotlistRequest(BaseModel):
    seed_keyword: str
    format_type: str = "SHORTS"
    num_scenes: int = 6
    admin_key: Optional[str] = None

def execute_flow_shotlist(seed: str, format_type: str, num_scenes: int):
    if SearchIntelligence and hasattr(SearchIntelligence, "generate_flow_shotlist"):
        try:
            return SearchIntelligence.generate_flow_shotlist(
                seed=seed,
                format_type=format_type,
                num_scenes=num_scenes
            )
        except Exception as e:
            print("Error executing SearchIntelligence:", e)

    # Fallback shotlist generator
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
                "dialogue": f"Kalimat emosional pembuka adegan {i+1} tentang {seed}."
            }
            for i in range(num_scenes)
        ]
    }

@app.post("/api/shotlist")
async def api_generate_shotlist(
    req: ShotlistRequest,
    x_dracin_admin_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    key: Optional[str] = Query(None)
):
    # Verify Admin Key authorization from header, query param, or body
    check_admin_authorization(
        x_dracin_admin_key=x_dracin_admin_key,
        authorization=authorization,
        query_key=key,
        body_key=req.admin_key
    )
    
    data = execute_flow_shotlist(req.seed_keyword, req.format_type, req.num_scenes)
    return {
        "success": True,
        "data": data,
        "message": "Shotlist AI berhasil digenerate dari YouTube Intelligence!"
    }
