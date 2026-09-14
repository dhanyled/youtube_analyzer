"""Unit tests for Search Intelligence, Opportunity Score, and Outlier Engine features."""

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


def test_smart_heuristic_volcano_vs_climbing_differentiation():
    kra_plan = SearchIntelligence.generate_outranking_plan(
        "gunung krakatau",
        competitors=[
            {"title": "Anak Krakatau Kembali Mengalami Erupsi", "views": "1M"},
            {
                "title": "TRAGEDI KRAKATAU 1883: Hari Ketika Laut Berubah Menjadi Maut",
                "views": "2M",
            },
        ],
    )
    sla_plan = SearchIntelligence.generate_outranking_plan(
        "gunung selamet",
        competitors=[
            {
                "title": "KISAH MEMILUKAN 7 PENDAKI MAHASISWA YANG TERJEBAK DI GUNUNG SLAMET",
                "views": "1.5M",
            },
            {"title": "PENDAKIAN MAUT DI GUNUNG SLAMET", "views": "800K"},
        ],
    )

    # They should not be identical templates
    assert kra_plan["outranking_title"] != sla_plan["outranking_title"]
    assert "Erupsi" in kra_plan["outranking_title"] or "Bencana" in kra_plan["outranking_title"]
    assert (
        "Pendaki" in sla_plan["outranking_title"]
        or "Bertahan Hidup" in sla_plan["outranking_title"]
    )


def test_generate_outranking_plan_ai_error_graceful_fallback():
    from unittest.mock import patch

    with patch(
        "youtube_analyzer.core.ai_generator.AITitleGenerator.generate_strategy",
        side_effect=Exception("API Timeout"),
    ):
        plan = SearchIntelligence.generate_outranking_plan(
            "gunung krakatau",
            competitors=[{"title": "Erupsi Krakatau", "views": "100K"}],
            ai_config={"provider": "gemini", "api_key": "mock"},
        )
        assert "outranking_title" in plan
        assert len(plan["alternative_titles"]) == 4


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


def test_detect_content_gaps():
    sample_comps = [
        {"upload_age": "3 tahun lalu", "format": "LANDSCAPE", "views": "15K views"},
        {"upload_age": "2 tahun lalu", "format": "LANDSCAPE", "views": "8K views"},
    ]
    gaps = SearchIntelligence.detect_content_gaps("google ads pemula", sample_comps)
    assert len(gaps) > 0
    # Should identify at least one gap due to outdated competitor videos
    assert any(g["is_content_gap"] for g in gaps)
    assert any(g["search_volume_tier"] in ["High", "Medium"] for g in gaps)
    assert any("CONTENT GAP" in g["gap_badge"] for g in gaps)


def test_analyze_competitor_outliers():
    sample_comps = [
        {"rank": 1, "title": "Viral 10x Breakout", "channel": "Ch A", "views": "250K views"},
        {"rank": 2, "title": "Normal Video 1", "channel": "Ch B", "views": "20K views"},
        {"rank": 3, "title": "Normal Video 2", "channel": "Ch C", "views": "15K views"},
    ]
    analysis = SearchIntelligence.analyze_competitor_outliers(sample_comps)
    assert analysis["median_views"] > 0
    assert analysis["highest_multiplier"] > 5.0
    assert analysis["outliers_found"] >= 1
    assert analysis["golden_video"] is not None
    assert analysis["golden_video"]["title"] == "Viral 10x Breakout"


def test_analyze_faceless_viability():
    rpm_info = {"detected_niche": "advertising", "avg_rpm_usd": 20.0}
    faceless = SearchIntelligence.analyze_faceless_viability("Google Ads Tutorial", rpm_info)
    assert faceless["faceless_score"] >= 80
    assert "IDEAL" in faceless["tier"]
    assert len(faceless["recommended_pipeline"]) == 5


def test_generate_clipping_opportunities():
    clips = SearchIntelligence.generate_clipping_opportunities(
        "Google Ads UMKM", "Tutorial Google Ads 2026"
    )
    assert len(clips) == 3
    for c in clips:
        assert "clip_title" in c
        assert "timestamp_window" in c
        assert "hook_line" in c
        assert "call_to_action" in c
