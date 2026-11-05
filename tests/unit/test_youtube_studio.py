from youtube_analyzer.connectors.youtube_studio import YouTubeStudioConnector


def test_youtube_studio_connector_init():
    conn = YouTubeStudioConnector(token_path=".non_existent_token.json")
    assert not conn.is_authenticated()


def test_diagnose_channel_videos():
    sample_videos = [
        {
            "video_id": "v1",
            "title": "Video Terpopuler di Channel Ini",
            "views": 20000,
            "views_display": "20.0K views",
            "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"],
            "url": "https://www.youtube.com/watch?v=v1",
        },
        {
            "video_id": "v2",
            "title": "Video Menengah Rata-Rata",
            "views": 10000,
            "views_display": "10.0K views",
            "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
            "url": "https://www.youtube.com/watch?v=v2",
        },
        {
            "video_id": "v3",
            "title": "Video Pendek",
            "views": 1500,
            "views_display": "1.5K views",
            "tags": ["tag1"],
            "url": "https://www.youtube.com/watch?v=v3",
        },
    ]

    diag = YouTubeStudioConnector.diagnose_channel_videos(sample_videos)

    assert diag["total_videos"] == 3
    assert diag["avg_views"] > 0
    assert len(diag["top_performers"]) > 0
    assert diag["top_performers"][0]["video_id"] == "v1"

    # v3 should be flagged as underperforming gem due to low tags and views < 70% of average
    assert len(diag["underperforming_gems"]) >= 1
    assert any(g["video_id"] == "v3" for g in diag["underperforming_gems"])
    v3_gem = next(g for g in diag["underperforming_gems"] if g["video_id"] == "v3")
    assert "tags" in v3_gem["weakness_reason"].lower() or "views" in v3_gem["weakness_reason"].lower()
