"""Domain models for Search Intelligence & Topic Orchestration.

Following the core blueprint:
Topic -> Keyword -> Query -> Intent -> Platform -> Competitor -> Citation -> ContentOpportunity
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, Relationship, SQLModel


class PlatformEnum(StrEnum):
    GOOGLE_SEARCH = "google_search"
    GOOGLE_GKP = "google_gkp"
    GOOGLE_TRENDS = "google_trends"
    YOUTUBE_SEARCH = "youtube_search"
    YOUTUBE_TRENDS = "youtube_trends"
    AI_SEARCH = "ai_search"  # AEO/GEO engine


class IntentEnum(StrEnum):
    INFORMATIONAL = "informational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"
    TUTORIAL = "tutorial"
    COMPARISON = "comparison"
    NAVIGATIONAL = "navigational"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Topic(SQLModel, table=True):
    __tablename__ = "topics"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    canonical_id: str = Field(index=True, unique=True, description="Human-readable ID, e.g. GA-001")
    name: str = Field(index=True, description="Canonical topic name, e.g. 'Google Ads untuk UMKM'")
    seed_keyword: str = Field(description="Initial seed query")
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    keywords: list["Keyword"] = Relationship(back_populates="topic", cascade_delete=True)
    queries: list["Query"] = Relationship(back_populates="topic", cascade_delete=True)
    intents: list["IntentCluster"] = Relationship(back_populates="topic", cascade_delete=True)
    competitors: list["Competitor"] = Relationship(back_populates="topic", cascade_delete=True)
    citations: list["Citation"] = Relationship(back_populates="topic", cascade_delete=True)
    opportunities: list["ContentOpportunity"] = Relationship(
        back_populates="topic", cascade_delete=True
    )


class Keyword(SQLModel, table=True):
    __tablename__ = "keywords"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topics.id", index=True)
    term: str = Field(index=True)
    platform: PlatformEnum = Field(index=True)
    search_volume: int | None = Field(default=None)
    cpc: float | None = Field(default=None)
    competition_level: str | None = Field(default=None)
    opportunity_score: float | None = Field(
        default=None, description="Algorithmic opportunity score (0-100)"
    )
    estimated_rpm: float | None = Field(
        default=None, description="Estimated AdSense RPM in USD"
    )
    created_at: datetime = Field(default_factory=utc_now)

    topic: Topic | None = Relationship(back_populates="keywords")


class Query(SQLModel, table=True):
    __tablename__ = "queries"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topics.id", index=True)
    keyword_id: int | None = Field(default=None, foreign_key="keywords.id")
    query_text: str = Field(index=True)
    platform: PlatformEnum = Field(index=True)
    query_type: str = Field(description="e.g. autocomplete, paa, related_search, aeo_prompt")
    rank_position: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)

    topic: Topic | None = Relationship(back_populates="queries")


class IntentCluster(SQLModel, table=True):
    __tablename__ = "intent_clusters"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topics.id", index=True)
    cluster_name: str = Field(index=True, description="e.g. Google Ads Pemula, Biaya, Tutorial")
    intent_type: IntentEnum = Field(default=IntentEnum.INFORMATIONAL)
    google_term_sample: str | None = Field(default=None)
    youtube_term_sample: str | None = Field(default=None)
    aeo_query_sample: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)

    topic: Topic | None = Relationship(back_populates="intents")


class Competitor(SQLModel, table=True):
    __tablename__ = "competitors"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topics.id", index=True)
    platform: PlatformEnum = Field(index=True)
    channel_or_domain: str = Field(index=True)
    content_title: str
    content_url: str
    content_type: str = Field(description="e.g. video_tutorial, commercial_landing, blog_post")
    views: int | None = Field(default=None)
    channel_median_views: int | None = Field(default=None)
    outlier_score: float | None = Field(
        default=None, description="Viral outlier multiplier (views / median)"
    )
    vph: float | None = Field(default=None, description="Views Per Hour velocity")
    created_at: datetime = Field(default_factory=utc_now)

    topic: Topic | None = Relationship(back_populates="competitors")


class Citation(SQLModel, table=True):
    __tablename__ = "citations"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topics.id", index=True)
    ai_engine: str = Field(description="e.g. Perplexity, Gemini, ChatGPT")
    prompt: str
    source_url: str
    cited_domain: str = Field(index=True)
    is_own_brand: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)

    topic: Topic | None = Relationship(back_populates="citations")


class ContentOpportunity(SQLModel, table=True):
    __tablename__ = "content_opportunities"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topics.id", index=True)
    title: str
    target_platform: PlatformEnum
    gap_reason: str = Field(
        description="e.g. Competitor has tutorial video on YouTube, but we have none"
    )
    recommended_action: str
    priority_score: float = Field(default=1.0)
    created_at: datetime = Field(default_factory=utc_now)

    topic: Topic | None = Relationship(back_populates="opportunities")
