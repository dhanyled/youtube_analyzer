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

from youtube_analyzer.connectors.hasdata_trends import HasDataTrendsConnector
from youtube_analyzer.connectors.youtube import YouTubeConnector
from youtube_analyzer.core.intelligence import SearchIntelligence
from youtube_analyzer.core.models import (
    IntentCluster,
    IntentEnum,
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

        if topic.id is None:
            raise ValueError("Topic ID cannot be None")

        topic_id: int = topic.id

        # Save queries
        for platform, query_list in surfaces.items():
            for q_text in query_list:
                existing = session.exec(
                    select(Query).where(
                        Query.topic_id == topic_id,
                        Query.query_text == q_text,
                        Query.platform == platform,
                    )
                ).first()
                if not existing:
                    session.add(
                        Query(
                            topic_id=topic_id,
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
            topic_id=topic_id,
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


@mcp.tool()
async def analyze_keyword_opportunity(
    keyword: str,
    search_volume: int | None = None,
    competition_score: float | None = None,
) -> str:
    """
    Analyze keyword search demand vs competition score (0-100).
    If volume/competition are omitted, dynamically estimates them from live YouTube competitor metrics.
    Includes RPM monetization estimate across 12 distinct niches.
    """
    if search_volume is None or competition_score is None:
        connector = YouTubeConnector()
        competitors = await connector.get_top_competitors(keyword, limit=5)
        kw_metrics = SearchIntelligence.estimate_keyword_metrics(keyword, competitors)
        final_vol = kw_metrics["search_volume"] if search_volume is None else search_volume
        final_comp = (
            kw_metrics["competition_score"] if competition_score is None else competition_score
        )
        opp_score = SearchIntelligence.calculate_opportunity_score(final_vol, final_comp)
        rating = kw_metrics["rating"]
    else:
        final_vol = search_volume
        final_comp = competition_score
        opp_score = SearchIntelligence.calculate_opportunity_score(final_vol, final_comp)
        rating = (
            "HIGH_POTENTIAL"
            if opp_score >= 68.0
            else ("MODERATE" if opp_score >= 48.0 else "COMPETITIVE")
        )

    rpm_data = SearchIntelligence.estimate_rpm(keyword)

    return json.dumps(
        {
            "keyword": keyword,
            "opportunity_score": opp_score,
            "rating": rating,
            "search_volume": final_vol,
            "competition_score": final_comp,
            "monetization": rpm_data,
        },
        indent=2,
    )


@mcp.tool()
def detect_outlier_opportunity(
    video_title: str,
    views: int,
    channel_median_views: int,
) -> str:
    """
    Detect viral outlier videos and breakout topics.
    Checks if a video outperforms the creator's channel median views.
    """
    outlier = SearchIntelligence.calculate_outlier_score(views, channel_median_views)
    return json.dumps(
        {
            "video_title": video_title,
            **outlier,
            "recommendation": (
                "High-priority topic to replicate/model! High viral breakout indicator."
                if outlier["is_outlier"]
                else "Baseline performance. Topic has normal audience reach."
            ),
        },
        indent=2,
    )


@mcp.tool()
def generate_video_ideas(
    seed_keyword: str,
    intent_type: str = "tutorial",
) -> str:
    """
    Generate high-CTR title formulas and hooks based on search intent.
    """
    try:
        intent = IntentEnum(intent_type.lower())
    except ValueError:
        intent = IntentEnum.TUTORIAL

    titles = SearchIntelligence.generate_high_ctr_titles(seed_keyword, intent)
    return json.dumps(
        {
            "seed_keyword": seed_keyword,
            "intent": intent.value,
            "recommended_high_ctr_titles": titles,
        },
        indent=2,
    )


@mcp.tool()
async def compare_google_vs_youtube_trends(
    keyword: str,
    geo: str = "ID",
) -> str:
    """
    Compare Google Web Search Trends vs YouTube Search Trends for a keyword.
    Identifies whether search interest is predominantly on YouTube (Tutorial/How-to)
    or Google Web (Commercial/Service).
    """
    connector = HasDataTrendsConnector()
    comparison = await connector.compare_google_vs_youtube(keyword, geo)
    return json.dumps(comparison, indent=2)


@mcp.tool()
async def inspect_top_competitors(
    query: str,
    limit: int = 5,
) -> str:
    """
    Spy on live top ranking competitor videos on YouTube.
    Detects video title, channel, views, upload age, duration, and format (Landscape vs Shorts).
    """
    connector = YouTubeConnector()
    competitors = await connector.get_top_competitors(query, limit=limit)
    return json.dumps(
        {
            "query": query,
            "total_competitors": len(competitors),
            "top_competitors": competitors,
        },
        indent=2,
    )


@mcp.tool()
async def generate_outranking_plan(
    seed_keyword: str,
) -> str:
    """
    Generate an actionable blueprint to outrank the #1 competitor on YouTube:
    - Outranking Title Formula
    - Full SEO Description with Timestamps & Hashtags
    - YouTube Shorts 3-Second Hook Package
    - Landscape (16:9) vs Shorts (9:16) format recommendation
    """
    connector = YouTubeConnector()
    competitors = await connector.get_top_competitors(seed_keyword, limit=1)
    top_comp = competitors[0] if competitors else None

    plan = SearchIntelligence.generate_outranking_plan(seed_keyword, top_comp)
    return json.dumps(plan, indent=2)


@mcp.tool()
async def generate_flow_shotlist(
    seed_keyword: str,
    format_type: str = "LANDSCAPE",
    num_scenes: int = 5,
) -> str:
    """
    Generate Google Flow (Imagen 4 + Veo 3.1) Storyboard & Shotlist.
    Exports prompt batch format for flow-agent / gflow-cli, AutoFlowCut manifest, and veo-mcp payload.
    - format_type: 'LANDSCAPE' (16:9) or 'SHORTS' (9:16)
    - num_scenes: Number of scenes (default 5)
    """
    shotlist = SearchIntelligence.generate_flow_shotlist(
        seed=seed_keyword,
        format_type=format_type,
        num_scenes=num_scenes,
    )
    return json.dumps(shotlist, indent=2)


@mcp.tool()
async def get_youtube_trending(
    gl: str = "ID",
    hl: str = "id",
    category: str = "now",
    device: str = "desktop",
    limit: int = 10,
) -> str:
    """
    Fetch live YouTube Trending Feed (https://www.youtube.com/feed/trending).
    - gl: Country code ('ID', 'US', 'GB', 'JP', 'MY', 'SG', 'WW')
    - hl: Interface language ('id', 'en', 'ja')
    - category: 'now' (General), 'music', 'gaming', 'movies', 'shorts'
    - device: 'desktop' or 'mobile'
    """
    connector = YouTubeConnector()
    items = await connector.get_trending_feed(
        gl=gl, hl=hl, category=category, device=device, limit=limit
    )
    return json.dumps(
        {
            "gl": gl,
            "hl": hl,
            "category": category,
            "device": device,
            "total_items": len(items),
            "trending_videos": items,
        },
        indent=2,
    )


@mcp.tool()
async def detect_youtube_studio_content_gaps(seed_keyword: str) -> str:
    """
    Replicates YouTube Studio 'Research' -> 'Content Gaps' feature.
    Finds search queries with high viewer demand but weak, outdated (> 1-2 years old),
    or missing Shorts format from competitors.
    """
    connector = YouTubeConnector()
    competitors = await connector.get_top_competitors(seed_keyword, limit=5)
    autocomplete = await connector.get_autocomplete(seed_keyword)
    gaps = SearchIntelligence.detect_content_gaps(seed_keyword, competitors, autocomplete)
    return json.dumps(
        {
            "seed_keyword": seed_keyword,
            "total_queries_analyzed": len(gaps),
            "content_gaps": gaps,
        },
        indent=2,
    )


@mcp.tool()
async def analyze_competitor_outliers(seed_keyword: str) -> str:
    """
    Viral Outlier Multiplier Inspector.
    Calculates median views across top ranking videos and finds viral breakout videos (2.5x - 50x median).
    """
    connector = YouTubeConnector()
    competitors = await connector.get_top_competitors(seed_keyword, limit=5)
    outliers = SearchIntelligence.analyze_competitor_outliers(competitors)
    return json.dumps(outliers, indent=2)


@mcp.tool()
async def analyze_faceless_niche_viability(seed_keyword: str) -> str:
    """
    Faceless Niche Opportunity Finder.
    Evaluates suitability for AI Faceless channel creation (Google Flow, Veo 3.1, ElevenLabs).
    """
    rpm_info = SearchIntelligence.estimate_rpm(seed_keyword)
    viability = SearchIntelligence.analyze_faceless_viability(seed_keyword, rpm_info)
    return json.dumps(
        {
            "seed_keyword": seed_keyword,
            "rpm_info": rpm_info,
            "faceless_viability": viability,
        },
        indent=2,
    )


@mcp.tool()
async def generate_shorts_clipping_ideas(topic: str, title: str = "") -> str:
    """
    AI Shorts Clipping & Viral Highlights Finder.
    Deconstructs a long-form video topic into 3-4 viral Short clips with hooks and timestamps.
    """
    clips = SearchIntelligence.generate_clipping_opportunities(topic, title or topic)
    return json.dumps(
        {
            "topic": topic,
            "suggested_clips": clips,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()

