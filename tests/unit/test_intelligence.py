"""Unit tests for VidIQ, TubeBuddy, and NexLev intelligence features."""

from youtube_analyzer.core.intelligence import SearchIntelligence
from youtube_analyzer.core.models import IntentEnum


def test_calculate_opportunity_score():
    # High volume (50k) and Low competition (20) should yield high opportunity score (> 70)
    high_opp = SearchIntelligence.calculate_opportunity_score(
        search_volume=50000, competition_score=20.0
    )
    assert high_opp >= 70.0

    # Low volume (50) and Saturated competition (90) should yield low opportunity score (< 40)
    low_opp = SearchIntelligence.calculate_opportunity_score(
        search_volume=50, competition_score=90.0
    )
    assert low_opp <= 40.0


def test_calculate_outlier_score():
    # 50,000 views on a channel with 5,000 median views is a 10x viral breakout
    outlier = SearchIntelligence.calculate_outlier_score(views=50000, channel_median_views=5000)
    assert outlier["outlier_multiplier"] == 10.0
    assert outlier["is_outlier"] is True
    assert "VIRAL_BREAKOUT" in outlier["classification"]

    # 4,500 views on a 5,000 median channel is average
    average = SearchIntelligence.calculate_outlier_score(views=4500, channel_median_views=5000)
    assert average["is_outlier"] is False


def test_estimate_rpm():
    rpm_data = SearchIntelligence.estimate_rpm("Google Ads untuk Bisnis")
    assert rpm_data["detected_niche"] == "advertising"
    assert rpm_data["avg_rpm_usd"] >= 15.0

    tech_rpm = SearchIntelligence.estimate_rpm("Python Tutorial Pemula")
    assert tech_rpm["detected_niche"] == "tech"


def test_generate_high_ctr_titles():
    titles = SearchIntelligence.generate_high_ctr_titles("Google Ads UMKM", IntentEnum.TUTORIAL)
    assert len(titles) >= 3
    assert any("Cara" in t or "Tutorial" in t for t in titles)

    commercial_titles = SearchIntelligence.generate_high_ctr_titles(
        "Google Ads UMKM", IntentEnum.COMMERCIAL
    )
    assert any("Biaya" in t or "Review" in t for t in commercial_titles)


def test_generate_outranking_plan():
    plan = SearchIntelligence.generate_outranking_plan("Google Ads UMKM")
    assert "outranking_title" in plan
    assert "seo_description" in plan
    assert "timestamps" in plan
    assert "shorts_package" in plan
    assert len(plan["timestamps"]) >= 3
    assert plan["recommended_format"] in ["LANDSCAPE", "SHORTS"]


def test_analyze_ai_competitor_presence():
    sample_competitors = [
        {"rank": 1, "is_ai_generated": False, "ai_badge": "👤 Human"},
        {"rank": 2, "is_ai_generated": True, "ai_badge": "🤖 AI"},
        {"rank": 3, "is_ai_generated": False, "ai_badge": "👤 Human"},
        {"rank": 4, "is_ai_generated": True, "ai_badge": "🤖 AI"},
        {"rank": 5, "is_ai_generated": False, "ai_badge": "👤 Human"},
    ]
    analysis = SearchIntelligence.analyze_ai_competitor_presence(sample_competitors)
    assert analysis["total_competitors"] == 5
    assert analysis["ai_count"] == 2
    assert analysis["human_count"] == 3
    assert analysis["ai_percentage"] == 40.0
    assert len(analysis["best_practices"]) >= 4


def test_generate_flow_shotlist():
    shotlist = SearchIntelligence.generate_flow_shotlist(
        seed="Google Ads Pemula",
        format_type="LANDSCAPE",
        num_scenes=4,
    )
    assert shotlist["scenes_count"] == 4
    assert shotlist["aspect_ratio"] == "16:9"
    assert "flow_batch_prompts_txt" in shotlist
    assert len(shotlist["flow_batch_prompts_txt"].split("\n")) == 4
    assert "autoflowcut_manifest" in shotlist
    assert "veo_mcp_payload" in shotlist


def test_parse_views_str():
    assert SearchIntelligence.parse_views_str("79K views") == 79000
    assert SearchIntelligence.parse_views_str("1.2M views") == 1200000
    assert SearchIntelligence.parse_views_str("500 views") == 500
    assert SearchIntelligence.parse_views_str(15000) == 15000


def test_estimate_keyword_metrics_differentiation():
    # Keyword A: High view competition
    comp_a = [
        {"views": "1.5M views", "title": "Saham Pemula 2026", "upload_age": "2 tahun lalu"},
        {"views": "800K views", "title": "Panduan Saham Lengkap", "upload_age": "1 tahun lalu"},
    ]
    metrics_a = SearchIntelligence.estimate_keyword_metrics("saham pemula", comp_a)

    # Keyword B: Niche low view competition
    comp_b = [
        {"views": "3.5K views", "title": "Beli Bibit Anggrek", "upload_age": "2 bulan lalu"},
        {
            "views": "1.2K views",
            "title": "Cara Merawat Anggrek Bulan",
            "upload_age": "3 minggu lalu",
        },
    ]
    metrics_b = SearchIntelligence.estimate_keyword_metrics("budidaya bibit anggrek hitam", comp_b)

    # Metrics MUST be dynamically differentiated, not identical!
    assert metrics_a["search_volume"] > metrics_b["search_volume"]
    assert metrics_a["competition_score"] > metrics_b["competition_score"]
    assert metrics_a["opportunity_score"] != metrics_b["opportunity_score"]
