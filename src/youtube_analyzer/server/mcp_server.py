"""Search Intelligence & YouTube Analyzer MCP Server.

Provides tools for AI assistants to research canonical topics, expand cross-surface queries,
and analyze competitor content gaps.
"""

import json

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP  # type: ignore

from sqlmodel import Session, select

from youtube_analyzer.core.models import (
    IntentCluster,
    PlatformEnum,
    Query,
    Topic,
)
from youtube_analyzer.core.normalizer import TopicNormalizer
from youtube_analyzer.db.database import engine, init_db

# Initialize MCP Server
mcp = FastMCP("youtube-analyzer")


@mcp.tool()
def research_topic(seed_keyword: str) -> str:
    """
    Research a seed topic across Google, YouTube, and AI/AEO surfaces.
    Generates a Canonical Topic ID and intent clusters.
    """
    init_db()
    canonical_id = TopicNormalizer.generate_canonical_id(seed_keyword)
    surfaces = TopicNormalizer.expand_seed_surfaces(seed_keyword)

    with Session(engine) as session:
        # Check if topic already exists
        statement = select(Topic).where(Topic.canonical_id == canonical_id)
        topic = session.exec(statement).first()

        if not topic:
            topic = Topic(
                canonical_id=canonical_id,
                name=seed_keyword.strip().title(),
                seed_keyword=seed_keyword.strip(),
                description=f"Cross-surface intelligence topic for '{seed_keyword}'",
            )
            session.add(topic)
            session.commit()
            session.refresh(topic)

        # Save queries
        for platform, query_list in surfaces.items():
            for q_text in query_list:
                existing = session.exec(
                    select(Query).where(
                        Query.topic_id == topic.id,
                        Query.query_text == q_text,
                        Query.platform == platform,
                    )
                ).first()
                if not existing:
                    session.add(
                        Query(
                            topic_id=topic.id,
                            query_text=q_text,
                            platform=platform,
                            query_type="seed_expansion",
                        )
                    )

        # Create intent clusters
        google_terms = surfaces[PlatformEnum.GOOGLE_SEARCH]
        youtube_terms = surfaces[PlatformEnum.YOUTUBE_SEARCH]
        aeo_queries = surfaces[PlatformEnum.AI_SEARCH]

        clusters = TopicNormalizer.create_intent_clusters(
            topic_id=topic.id,
            google_terms=google_terms,
            youtube_terms=youtube_terms,
            aeo_queries=aeo_queries,
        )

        for cluster in clusters:
            existing_cluster = session.exec(
                select(IntentCluster).where(
                    IntentCluster.topic_id == topic.id,
                    IntentCluster.cluster_name == cluster.cluster_name,
                )
            ).first()
            if not existing_cluster:
                session.add(cluster)

        session.commit()

    return json.dumps(
        {
            "status": "success",
            "canonical_id": canonical_id,
            "topic": seed_keyword,
            "surfaces": {
                "google_search": surfaces[PlatformEnum.GOOGLE_SEARCH],
                "youtube_search": surfaces[PlatformEnum.YOUTUBE_SEARCH],
                "ai_search": surfaces[PlatformEnum.AI_SEARCH],
            },
        },
        indent=2,
    )


@mcp.tool()
def get_topic_summary(canonical_id: str) -> str:
    """Retrieve full canonical topic details, queries, and intent clusters."""
    init_db()
    with Session(engine) as session:
        topic = session.exec(select(Topic).where(Topic.canonical_id == canonical_id)).first()
        if not topic:
            return json.dumps({"error": f"Topic '{canonical_id}' not found."}, indent=2)

        queries = session.exec(select(Query).where(Query.topic_id == topic.id)).all()
        clusters = session.exec(
            select(IntentCluster).where(IntentCluster.topic_id == topic.id)
        ).all()

        return json.dumps(
            {
                "canonical_id": topic.canonical_id,
                "name": topic.name,
                "seed_keyword": topic.seed_keyword,
                "total_queries": len(queries),
                "intent_clusters": [
                    {
                        "cluster_name": c.cluster_name,
                        "intent_type": c.intent_type.value,
                        "google_term": c.google_term_sample,
                        "youtube_term": c.youtube_term_sample,
                        "aeo_query": c.aeo_query_sample,
                    }
                    for c in clusters
                ],
            },
            indent=2,
        )


if __name__ == "__main__":
    mcp.run()
