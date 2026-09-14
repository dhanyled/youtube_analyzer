"""Comprehensive Verification Suite: DB, Brand Scrub, Live Connectors, and Data Integrity."""

import asyncio
import os
import sys
import xml.etree.ElementTree as ET

import httpx
from sqlmodel import Session, select

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

from youtube_analyzer.connectors.youtube import YouTubeConnector
from youtube_analyzer.core.intelligence import SearchIntelligence
from youtube_analyzer.core.models import Topic
from youtube_analyzer.db.database import engine, init_db


def test_database():
    print("[1/5] Testing Database Initialization & SQLModel CRUD...")
    init_db()
    with Session(engine) as session:
        existing = session.exec(
            select(Topic).where(Topic.canonical_id == "TEST-VERIFY-001")
        ).first()
        if existing:
            session.delete(existing)
            session.commit()

        test_topic = Topic(
            canonical_id="TEST-VERIFY-001",
            name="Verification Topic",
            seed_keyword="verifikasi integrasi",
        )
        session.add(test_topic)
        session.commit()
        session.refresh(test_topic)

        # Query
        record = session.exec(select(Topic).where(Topic.canonical_id == "TEST-VERIFY-001")).first()
        assert record is not None
        assert record.name == "Verification Topic"

        # Cleanup
        session.delete(record)
        session.commit()
    print("   -> OK: Database tables created, written, queried, and cleaned successfully.")


def test_brand_scrub():
    print("[2/5] Scanning entire repository for prohibited brand names...")
    forbidden = ["vid" + "iq", "tube" + "buddy", "nex" + "lev"]
    matches = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [
            d
            for d in dirs
            if d not in {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
        ]
        for f in files:
            if f == "verify_suite.py":
                continue
            if f.endswith((".py", ".md", ".toml", ".txt", ".json", ".bat")):
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, encoding="utf-8") as fh:
                        for line_no, line in enumerate(fh, 1):
                            lower = line.lower()
                            for b in forbidden:
                                if b in lower:
                                    matches.append((file_path, line_no, b, line.strip()))
                except Exception:
                    pass

    if matches:
        for m in matches:
            print(f"   -> FAIL: Found '{m[2]}' in {m[0]}:{m[1]}")
        sys.exit(1)
    print("   -> OK: ZERO occurrences of 'vidiq', 'tubebuddy', or 'nexlev' across all files.")


async def test_live_youtube():
    print("[3/5] Testing Live YouTube Trending & Competitor Connectors...")
    conn = YouTubeConnector()
    trending = await conn.get_trending_feed(
        gl="ID", hl="id", category="now", device="desktop", limit=3
    )
    assert len(trending) > 0
    sample = trending[0]
    print(
        f"   -> OK: Trending fetched {len(trending)} items. Sample: '{sample['title'][:35]}...' ({sample['views']})"
    )

    competitors = await conn.get_top_competitors("google ads pemula", limit=3)
    assert len(competitors) > 0
    print(
        f"   -> OK: Competitor spy fetched {len(competitors)} videos. Top rank: '{competitors[0]['title'][:35]}...'"
    )


def test_google_trends_rss():
    print("[4/5] Testing Live Google Daily Trends RSS...")
    url = "https://trends.google.co.id/trending/rss?geo=ID"
    with httpx.Client(timeout=8.0) as client:
        resp = client.get(url)
        assert resp.status_code == 200
        root = ET.fromstring(resp.text)
        items = root.findall(".//item")
        assert len(items) > 0
        top_trend = items[0].find("title").text if items[0].find("title") is not None else "Unknown"
        print(
            f"   -> OK: Google Trends RSS live fetched {len(items)} items. Top trend: '{top_trend}'"
        )


def test_dynamic_metrics():
    print("[5/5] Testing Dynamic Metric Differencing (Anti-Static Guardrail)...")
    kw_tech = SearchIntelligence.estimate_keyword_metrics(
        "python programming", [{"views": "500K views"}]
    )
    kw_cooking = SearchIntelligence.estimate_keyword_metrics(
        "resep tahu tempe murah", [{"views": "5K views"}]
    )
    assert kw_tech["search_volume"] != kw_cooking["search_volume"]
    assert kw_tech["opportunity_score"] != kw_cooking["opportunity_score"]
    print(
        f"   -> OK: High view keyword: vol={kw_tech['search_volume']}, score={kw_tech['opportunity_score']}"
    )
    print(
        f"   -> OK: Niche keyword: vol={kw_cooking['search_volume']}, score={kw_cooking['opportunity_score']}"
    )


async def main():
    test_database()
    test_brand_scrub()
    await test_live_youtube()
    test_google_trends_rss()
    test_dynamic_metrics()
    print("\n==================================================")
    print(" ALL 5 EXTRA VALIDATION CHECKS PASSED PERFECTLY! ")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
