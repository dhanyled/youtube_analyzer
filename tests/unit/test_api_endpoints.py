import os
import sys

import pytest
from httpx import ASGITransport, AsyncClient

# Add api directory to sys.path
api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "api"))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from index import app  # noqa: E402


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.3.0"
        assert data["webmcp_tools_count"] >= 8


@pytest.mark.asyncio
async def test_webmcp_tools_catalog():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/webmcp/tools")
        assert resp.status_code == 200
        data = resp.json()
        tool_names = [t["name"] for t in data["tools"]]
        assert "get_people_also_ask" in tool_names
        assert "mine_competitor_comments" in tool_names
        assert "audit_tag_relevance" in tool_names
        assert "audit_content_blindspots" in tool_names


@pytest.mark.asyncio
async def test_dashboard_audit_tags_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/dashboard/audit-tags",
            json={
                "tags": "Google Ads, Kupon Gratis, fyp",
                "context_text": "Membahas Google Ads berbayar untuk UMKM",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tags_analyzed"] == 3
        assert data["has_blindspot"] is True
        statuses = {b["tag"]: b["status"] for b in data["audit_breakdown"]}
        assert statuses["Google Ads"] == "PASS"
        assert statuses["Kupon Gratis"] == "FAIL"
        assert statuses["fyp"] == "FAIL"


@pytest.mark.asyncio
async def test_dashboard_audit_blindspots_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/dashboard/audit-blindspots",
            json={
                "title": "Judul Uji Coba Panjang Ideal untuk Optimasi YouTube",
                "description": "00:00 Pengantar\n02:00 Pembahasan\n05:00 Kesimpulan\n\nDeskripsi lengkap video.",
                "tags": "Google Ads, Tutorial",
                "context_notes": "Panduan Google Ads",
                "target_format": "LANDSCAPE (16:9)",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_score" in data
        assert data["overall_score"] >= 70


@pytest.mark.asyncio
async def test_mine_comments_endpoint_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Should return 400 when neither video_urls nor keyword provided
        resp = await client.post(
            "/api/dashboard/mine-comments", json={"video_urls": [], "keyword": ""}
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_my_channel_endpoint_switch():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/dashboard/my-channel")
        assert resp.status_code == 200
        data = resp.json()
        assert "profile" in data
        assert "videos" in data
