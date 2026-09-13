"""Unit tests for Core Data Models and Database Schema."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from youtube_analyzer.core.models import (
    Competitor,
    ContentOpportunity,
    IntentCluster,
    IntentEnum,
    Keyword,
    PlatformEnum,
    Query,
    Topic,
)


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_topic_creation_and_relationships(session: Session):
    # 1. Create Topic
    topic = Topic(
        canonical_id="GA-001",
        name="Google Ads UMKM",
        seed_keyword="google ads umkm",
    )
    session.add(topic)
    session.commit()
    session.refresh(topic)

    assert topic.id is not None
    assert topic.canonical_id == "GA-001"

    # 2. Add Keywords
    kw1 = Keyword(
        topic_id=topic.id,
        term="jasa google ads",
        platform=PlatformEnum.GOOGLE_GKP,
        search_volume=1200,
        cpc=4500.0,
    )
    kw2 = Keyword(
        topic_id=topic.id,
        term="tutorial google ads pemula",
        platform=PlatformEnum.YOUTUBE_SEARCH,
    )
    session.add_all([kw1, kw2])
    session.commit()

    # 3. Add Queries
    q1 = Query(
        topic_id=topic.id,
        query_text="cara pasang google ads",
        platform=PlatformEnum.YOUTUBE_SEARCH,
        query_type="autocomplete",
    )
    session.add(q1)

    # 4. Add Intent Cluster
    cluster = IntentCluster(
        topic_id=topic.id,
        cluster_name="Tutorial",
        intent_type=IntentEnum.TUTORIAL,
        google_term_sample="cara google ads",
        youtube_term_sample="cara pasang google ads",
    )
    session.add(cluster)

    # 5. Add Competitor
    comp = Competitor(
        topic_id=topic.id,
        platform=PlatformEnum.YOUTUBE_SEARCH,
        channel_or_domain="PakarDigital",
        content_title="Tutorial Google Ads 2026",
        content_url="https://youtube.com/watch?v=sample",
        content_type="video_tutorial",
    )
    session.add(comp)

    # 6. Add Content Opportunity
    opp = ContentOpportunity(
        topic_id=topic.id,
        title="Buat Video Tutorial Google Ads dari Nol",
        target_platform=PlatformEnum.YOUTUBE_SEARCH,
        gap_reason="Competitor has high ranking tutorial video, our channel has none",
        recommended_action="Produce 10-minute beginner guide",
        priority_score=9.5,
    )
    session.add(opp)
    session.commit()

    # Verify query back from database
    stored_topic = session.exec(select(Topic).where(Topic.canonical_id == "GA-001")).first()
    assert stored_topic is not None
    assert len(stored_topic.keywords) == 2
    assert len(stored_topic.queries) == 1
    assert len(stored_topic.intents) == 1
    assert len(stored_topic.competitors) == 1
    assert len(stored_topic.opportunities) == 1
