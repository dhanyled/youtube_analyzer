import pytest

from youtube_analyzer.connectors.youtube import YouTubeConnector
from youtube_analyzer.core.ai_generator import AITitleGenerator


def test_extract_video_id():
    yt = YouTubeConnector()
    assert yt.extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yt.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yt.extract_video_id("https://youtu.be/dQw4w9WgXcQ?si=123") == "dQw4w9WgXcQ"
    assert yt.extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yt.extract_video_id("https://example.com/random-page") is None
    assert yt.extract_video_id("") is None


def test_audit_and_revamp_fallback():
    vid_details = {
        "title": "Cara Membuat Rendang Sapi",
        "description": "Resep rendang enak.",
        "tags": ["rendang", "kuliner"],
        "views_display": "100K views",
        "duration": "15:00",
        "channel": "Dapur Nusantara",
    }
    transcript_data = {
        "timestamped_text": "[00:00] Siapkan daging sapi.\n[05:00] Masukkan santan kental.",
        "full_text": "Siapkan daging sapi. Masukkan santan kental.",
    }
    competitors = [
        {
            "title": "Resep Rendang Padang Asli Minang Warisan Nenek",
            "views": "2M views",
            "channel": "Koki Padang",
        }
    ]
    res = AITitleGenerator.audit_and_revamp(
        video_details=vid_details,
        transcript_data=transcript_data,
        competitors=competitors,
    )
    assert "audit" in res
    assert "outranking_title" in res
    assert "psychological_angles" in res
    assert "video_tags" in res
    assert "full_description" in res


def test_plan_pre_upload_fallback():
    res = AITitleGenerator.plan_pre_upload(
        topic="Tips Menabung 10 Juta Pertama",
        content_notes="Gunakan metode amplop 50/30/20, kurangi nongkrong di cafe mahal, catat pengeluaran di aplikasi.",
        target_format="LANDSCAPE (16:9)",
        duration="10:00",
        competitors=[],
    )
    assert "outranking_title" in res
    assert "detected_content_summary" in res
    assert "psychological_angles" in res
    assert "video_tags" in res
    assert "launch_checklist" in res
    assert len(res["launch_checklist"]) > 0


def test_generate_video_schema_jsonld():
    schema_str = AITitleGenerator.generate_video_schema_jsonld(
        title="Rahasia Belajar Koding Pemula",
        description="Deskripsi koding pemula.",
        video_id="dQw4w9WgXcQ",
        duration="12:30",
        timestamps_text="00:00 - Intro\n02:15 - Tips 1\n05:40 - Tips 2",
    )
    import json

    parsed = json.loads(schema_str)
    assert parsed["@type"] == "VideoObject"
    assert parsed["name"] == "Rahasia Belajar Koding Pemula"
    assert parsed["duration"] == "PT12M30S"
    assert "hasPart" in parsed
    assert len(parsed["hasPart"]) == 3
    assert parsed["hasPart"][1]["name"] == "Tips 1"
    assert parsed["hasPart"][1]["startOffset"] == 135


def test_synchronized_timestamps():
    from youtube_analyzer.connectors.youtube import parse_duration_to_seconds

    # 1. Shorts (<= 60s) must have empty chapters
    assert AITitleGenerator.generate_synchronized_timestamps("Shorts Trik", "0:45") == []
    assert AITitleGenerator.generate_synchronized_timestamps("Shorts Trik", 59) == []

    # 2. Short video (02:30 = 150s) must never exceed duration
    ts_short = AITitleGenerator.generate_synchronized_timestamps("Short Video", "02:30")
    assert len(ts_short) >= 3
    assert ts_short[0].startswith("00:00")
    max_sec = parse_duration_to_seconds("02:30")
    for ts in ts_short:
        parts = ts.split("-")[0].strip().split(":")
        sec = int(parts[0]) * 60 + int(parts[1])
        assert sec <= max_sec

    # 3. Long video (45:00 = 2700s) must stay within duration
    ts_long = AITitleGenerator.generate_synchronized_timestamps("Long Video", "45:00")
    assert ts_long[0].startswith("00:00")
    max_long = parse_duration_to_seconds("45:00")
    for ts in ts_long:
        parts = ts.split("-")[0].strip().split(":")
        sec = int(parts[0]) * 60 + int(parts[1])
        assert sec <= max_long


def test_audit_tags_and_no_generic_hashtags():
    vid_with_tags = {
        "title": "Tutorial Belajar Kopi Manual Brew",
        "description": "Video tentang kopi.",
        "tags": ["kopi", "manual brew", "v60", "kopi indonesia"],
        "views_display": "50K views",
        "duration": "10:00",
        "channel": "Kopi Mania",
    }
    res = AITitleGenerator.audit_and_revamp(vid_with_tags)
    # Tags exist -> score must be >= 6
    assert res["audit"]["tags_score"] >= 6
    assert "tidak memiliki tags" not in res["audit"]["tags_flaws"].lower()
    # No generic #YouTubeSEO
    assert "#youtubeseo" not in res["full_description"].lower()
    assert "#videomarketing" not in res["full_description"].lower()


@pytest.mark.asyncio
async def test_spy_competitor_tags_unit():
    yt = YouTubeConnector()
    sample_comps = [
        {"title": "Video 1", "tags": ["resep kopi", "manual brew", "barista"]},
        {"title": "Video 2", "tags": ["resep kopi", "v60", "manual brew"]},
        {"title": "Video 3", "tags": ["resep kopi", "tips kopi"]},
    ]
    spy_res = await yt.spy_competitor_tags(sample_comps)
    assert spy_res["competitors_analyzed"] == 3
    assert len(spy_res["top_tags_by_frequency"]) > 0
    # "resep kopi" appears in all 3 -> 100%
    top_tag = spy_res["top_tags_by_frequency"][0]
    assert top_tag["tag"] == "resep kopi"
    assert top_tag["count"] == 3
    assert "100%" in top_tag["Persentase"]
    assert len(spy_res["best_practices"]) >= 3
    assert "resep kopi" in spy_res["recommended_tags_copy"]


def test_outranking_plan_dynamic_timestamps():
    from youtube_analyzer.connectors.youtube import parse_duration_to_seconds
    from youtube_analyzer.core.intelligence import SearchIntelligence

    # Test with short duration competitor (04:15 = 255 seconds)
    competitor = {
        "title": "Panduan Umroh Lengkap 2026",
        "duration": "04:15",
        "views": "150K views",
        "channel": "Travel Channel",
        "format": "LANDSCAPE",
    }
    plan = SearchIntelligence.generate_outranking_plan(
        seed="biro umroh berizin resmi",
        competitor=competitor,
    )
    max_sec = parse_duration_to_seconds("04:15")
    assert plan["timestamps"], "Timestamps should be generated for landscape video"
    for ts in plan["timestamps"]:
        parts = ts.split("-")[0].strip().split(":")
        sec = int(parts[0]) * 60 + int(parts[1])
        assert sec <= max_sec, f"Timestamp {ts} exceeds max_sec {max_sec}"
    assert plan["timestamps"][0].startswith("00:00")


def test_outranking_plan_shorts_empty_timestamps():
    from youtube_analyzer.core.intelligence import SearchIntelligence

    competitor = {
        "title": "Trik Kilat Belajar Koding #shorts",
        "duration": "00:45",
        "views": "500K views",
        "channel": "Koding Shorts",
        "format": "SHORTS",
    }
    plan = SearchIntelligence.generate_outranking_plan(
        seed="trik kilat koding",
        competitor=competitor,
    )
    assert plan["timestamps"] == [], "Shorts format should have empty timestamps"


def test_schema_upload_date_dynamic():
    import json
    from datetime import datetime

    schema_str = AITitleGenerator.generate_video_schema_jsonld(
        title="Test Schema Dynamic Date",
        description="Testing upload date.",
        video_id="xyz123",
        duration="08:00",
    )
    parsed = json.loads(schema_str)
    assert "uploadDate" in parsed
    # Should be valid ISO format with current year
    upload_dt = datetime.fromisoformat(parsed["uploadDate"])
    assert upload_dt.year == datetime.now().year


def test_gemini_default_model_and_fallbacks():
    from youtube_analyzer.core.ai_generator import DEFAULT_MODELS

    assert DEFAULT_MODELS["gemini"] == "gemini-flash-lite-latest"


def test_detect_video_format_landscape_vs_shorts():
    yt = YouTubeConnector()
    # Explicit #shorts in title -> SHORTS
    is_sh, fmt = yt.detect_video_format(
        video_id="vid1", title="Trik Koding Cepat #shorts", duration_seconds=45
    )
    assert is_sh is True
    assert fmt == "SHORTS"

    # Longer than 180s -> always LANDSCAPE
    is_sh, fmt = yt.detect_video_format(
        video_id="vid2", title="Tutorial Panjang", duration_seconds=600
    )
    assert is_sh is False
    assert fmt == "LANDSCAPE"

    # 16:9 thumbnail fallback -> LANDSCAPE even if <= 60s
    is_sh, fmt = yt.detect_video_format(
        video_id="vid3",
        title="Selamat Tahun Baru Imlek 2022",
        duration_seconds=31,
        thumbnail_url="https://i.ytimg.com/vi/vid3/maxresdefault.jpg",
    )
    assert is_sh is False
    assert fmt == "LANDSCAPE"
