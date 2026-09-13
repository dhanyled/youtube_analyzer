"""Unit tests for FastMCP tools in mcp_server.py."""

import json

import pytest

from youtube_analyzer.server.mcp_server import (
    analyze_keyword_opportunity,
    detect_outlier_opportunity,
    generate_video_ideas,
    get_topic_summary,
    research_topic,
)


@pytest.mark.asyncio
async def test_mcp_research_topic_and_get_summary():
    seed = "Google Ads Pemula"
    res_str = await research_topic(seed)
    res = json.loads(res_str)

    assert res["status"] == "success"
    assert "canonical_id" in res
    canonical_id = res["canonical_id"]
    assert canonical_id.startswith("TOPIC-")

    summary_str = get_topic_summary(canonical_id)
    summary = json.loads(summary_str)

    assert summary["canonical_id"] == canonical_id
    assert summary["name"] == "Google Ads Pemula"
    assert summary["total_queries"] > 0
    assert len(summary["intent_clusters"]) > 0


def test_mcp_get_topic_summary_not_found():
    summary_str = get_topic_summary("TOPIC-NONEXISTENT")
    summary = json.loads(summary_str)
    assert "error" in summary


def test_mcp_analyze_keyword_opportunity():
    res_str = analyze_keyword_opportunity("google ads", search_volume=5000, competition_score=30.0)
    res = json.loads(res_str)

    assert res["keyword"] == "google ads"
    assert res["opportunity_score"] > 0
    assert "rating" in res
    assert "monetization" in res


def test_mcp_detect_outlier_opportunity():
    res_str = detect_outlier_opportunity(
        "Viral Google Ads Guide", views=50000, channel_median_views=5000
    )
    res = json.loads(res_str)

    assert res["video_title"] == "Viral Google Ads Guide"
    assert res["outlier_multiplier"] == 10.0
    assert res["is_outlier"] is True
    assert "High-priority topic" in res["recommendation"]


def test_mcp_generate_video_ideas():
    res_str = generate_video_ideas("Google Ads UMKM", intent_type="tutorial")
    res = json.loads(res_str)

    assert res["seed_keyword"] == "Google Ads UMKM"
    assert res["intent"] == "tutorial"
    assert len(res["recommended_high_ctr_titles"]) > 0
