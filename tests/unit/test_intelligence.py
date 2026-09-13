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
