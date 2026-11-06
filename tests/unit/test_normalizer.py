"""Unit tests for TopicNormalizer."""

import pytest

from youtube_analyzer.core.models import IntentEnum, PlatformEnum
from youtube_analyzer.core.normalizer import TopicNormalizer


def test_generate_canonical_id():
    cid1 = TopicNormalizer.generate_canonical_id("Google Ads untuk UMKM")
    cid2 = TopicNormalizer.generate_canonical_id("Google Ads untuk UMKM")
    assert cid1 == cid2
    assert cid1.startswith("TOPIC-")
    assert "GOO" in cid1


@pytest.mark.parametrize(
    "query, expected_intent",
    [
        ("tutorial google ads pemula", IntentEnum.TUTORIAL),
        ("cara pasang google ads", IntentEnum.TUTORIAL),
        ("jasa google ads murah", IntentEnum.COMMERCIAL),
        ("biaya iklan google", IntentEnum.COMMERCIAL),
        ("apakah google ads efektif untuk bisnis", IntentEnum.INFORMATIONAL),
        ("google ads vs tiktok ads", IntentEnum.COMPARISON),
    ],
)
def test_classify_intent(query: str, expected_intent: IntentEnum):
    intent = TopicNormalizer.classify_intent(query)
    assert intent == expected_intent


def test_expand_seed_surfaces():
    seed = "Google Ads UMKM"
    surfaces = TopicNormalizer.expand_seed_surfaces(seed)

    assert PlatformEnum.GOOGLE_SEARCH in surfaces
    assert PlatformEnum.YOUTUBE_SEARCH in surfaces
    assert PlatformEnum.AI_SEARCH in surfaces

    google_terms = surfaces[PlatformEnum.GOOGLE_SEARCH]
    youtube_terms = surfaces[PlatformEnum.YOUTUBE_SEARCH]
    ai_queries = surfaces[PlatformEnum.AI_SEARCH]

    # Verify Google has commercial variants
    assert any("jasa" in t or "biaya" in t for t in google_terms)

    # Verify YouTube has tutorial / cara variants
    assert any("tutorial" in t or "cara" in t for t in youtube_terms)

    # Verify AI has conversational question variants
    assert any("apakah" in q or "bagaimana" in q or "?" in q for q in ai_queries)


def test_create_intent_clusters():
    google_terms = ["google ads pemula", "biaya google ads", "cara google ads"]
    youtube_terms = ["tutorial google ads", "cara pasang google ads", "biaya iklan google"]
    aeo_queries = ["apakah google ads efektif?", "berapa biaya google ads?"]

    clusters = TopicNormalizer.create_intent_clusters(
        topic_id=1,
        google_terms=google_terms,
        youtube_terms=youtube_terms,
        aeo_queries=aeo_queries,
    )

    cluster_names = [c.cluster_name for c in clusters]
    assert "Tutorial" in cluster_names
    assert "Biaya & Jasa" in cluster_names

    tutorial_cluster = next(c for c in clusters if c.cluster_name == "Tutorial")
    assert tutorial_cluster.intent_type == IntentEnum.TUTORIAL


def test_create_intent_clusters_all_intents():
    google_terms = ["google ads vs facebook ads", "beli voucher google ads"]
    youtube_terms = ["review google ads vs tiktok ads", "order jasa google ads"]
    aeo_queries = ["perbandingan google ads dan fb ads", "diskon promo google ads"]

    clusters = TopicNormalizer.create_intent_clusters(
        topic_id=1,
        google_terms=google_terms,
        youtube_terms=youtube_terms,
        aeo_queries=aeo_queries,
    )

    cluster_names = [c.cluster_name for c in clusters]
    assert "Evaluasi & Review" in cluster_names
    assert "Transaksi & Pembelian" in cluster_names

    comp_cluster = next(c for c in clusters if c.cluster_name == "Evaluasi & Review")
    assert comp_cluster.intent_type == IntentEnum.COMPARISON
    assert comp_cluster.google_term_sample is not None

    tx_cluster = next(c for c in clusters if c.cluster_name == "Transaksi & Pembelian")
    assert tx_cluster.intent_type == IntentEnum.TRANSACTIONAL
    assert tx_cluster.google_term_sample is not None


def test_tag_relevance_filters_irrelevant_gratis():
    """Verify that 'gratis' tags are filtered out when the video is about general/paid topics."""
    context = "Tutorial Google Ads untuk UMKM strategi budget harian campaign"
    tags = [
        "Google Ads",
        "Google Ads Gratis",
        "Setting Google Ads",
        "Download Gratis",
        "fyp",
        "viral",
    ]
    filtered = TopicNormalizer.filter_relevant_tags(tags, context_text=context)
    assert "Google Ads" in filtered
    assert "Setting Google Ads" in filtered
    assert "Google Ads Gratis" not in filtered
    assert "Download Gratis" not in filtered
    assert "fyp" not in filtered
    assert "viral" not in filtered


def test_tag_relevance_keeps_gratis_when_context_is_free():
    """Verify that 'gratis' tags ARE KEPT when the content explicitly discusses free resources/services."""
    context = "Cara mendapatkan saldo kupon Google Ads gratis tanpa biaya promo resmi"
    tags = [
        "Google Ads",
        "Google Ads Gratis",
        "Saldo Google Ads Gratis",
        "Voucher Google Ads",
        "fyp",
    ]
    filtered = TopicNormalizer.filter_relevant_tags(tags, context_text=context)
    assert "Google Ads" in filtered
    assert "Google Ads Gratis" in filtered
    assert "Saldo Google Ads Gratis" in filtered
    assert "Voucher Google Ads" in filtered
    assert "fyp" not in filtered  # unconditional spam is still removed


def test_clean_comma_tags_utility():
    """Verify clean_comma_tags formats and filters comma-separated tag string."""
    context = "Belajar Python Dasar untuk Pemula"
    raw_str = "Python, Python Pemula, Python Gratis, Belajar Python, viral, Tutorial Python"
    cleaned = TopicNormalizer.clean_comma_tags(raw_str, context_text=context)
    assert "Python" in cleaned
    assert "Python Pemula" in cleaned
    assert "Belajar Python" in cleaned
    assert "Tutorial Python" in cleaned
    assert "Python Gratis" not in cleaned
    assert "viral" not in cleaned


def test_audit_tags_detailed_diagnostics():
    """Verify audit_tags_detailed returns breakdown, statuses, and actionable recommendations."""
    context = "Strategi Beriklan Google Ads Berbayar untuk Perusahaan"
    tags = "Google Ads, Belajar Google Ads, Kupon Gratis, fyp, viral, Tag Yang Sengaja Dibuat Sangat Panjang Melebihi Batas Tiga Puluh Lima Karakter"

    audit = TopicNormalizer.audit_tags_detailed(tags, context_text=context)
    assert audit["total_tags_analyzed"] == 6
    assert audit["has_blindspot"] is True
    assert audit["rejected_count"] >= 3

    statuses = {b["tag"]: b["status"] for b in audit["audit_breakdown"]}
    assert statuses["Google Ads"] == "PASS"
    assert statuses["Belajar Google Ads"] == "PASS"
    assert statuses["Kupon Gratis"] == "FAIL"  # unsupported clickbait
    assert statuses["fyp"] == "FAIL"  # unconditional spam
    assert statuses["viral"] == "FAIL"  # unconditional spam


def test_audit_content_blindspots_scoring():
    """Verify 5-pillar blindspot audit detects missing timestamps, long title, and tag issues."""
    audit = TopicNormalizer.audit_content_blindspots(
        title="Tutorial Singkat",  # too short
        description="Deskripsi pendek tanpa babak sama sekali.",  # no timestamps
        tags="Google Ads, fyp",  # fyp is spam
        context_notes="Membahas Google Ads",
        target_format="LANDSCAPE (16:9)",
    )
    assert "overall_score" in audit
    assert audit["overall_score"] < 80
    assert any(
        b["pillar"] == "Google Key Moments (Timestamps)" and b["status"] == "FAIL"
        for b in audit["blindspots"]
    )
    assert any(
        b["pillar"] == "Relevansi Tags & Anti-Spam" and b["status"] == "FAIL"
        for b in audit["blindspots"]
    )
