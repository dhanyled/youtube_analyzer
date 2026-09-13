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
