import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

# Add api directory to sys.path
api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "api"))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from index import app

@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["webmcp_tools_count"] >= 6

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

@pytest.mark.asyncio
async def test_mine_comments_endpoint_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Should return 400 when neither video_urls nor keyword provided
        resp = await client.post("/api/dashboard/mine-comments", json={"video_urls": [], "keyword": ""})
        assert resp.status_code == 400
