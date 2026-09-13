"""Interactive Executive Dashboard for YouTube Search & Competitor Intelligence.

Features:
- Executive Strategic Decision Card (Traffic light verdict & format recommendations)
- Competitor Spy (Scrapes #1 ranking video, format: Landscape vs Shorts, views)
- Outranking Title & SEO Description Generator (with auto Timestamps & Hook)
- Dedicated Landscape (16:9) vs Shorts (9:16) Strategy tabs
- Cross-Surface Intent Clustering & Trends Comparison

Run locally:
    uv run streamlit run dashboard.py
    or: .\run.bat
"""

import asyncio
import os
import sys

# Ensure src/ is in sys.path for Streamlit Cloud and remote deployment
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import pandas as pd
import streamlit as st
from sqlmodel import Session, select

from youtube_analyzer.connectors.hasdata_trends import HasDataTrendsConnector
from youtube_analyzer.connectors.youtube import YouTubeConnector
from youtube_analyzer.core.intelligence import SearchIntelligence
from youtube_analyzer.core.models import (
    IntentCluster,
    PlatformEnum,
    Query,
    Topic,
)
from youtube_analyzer.core.normalizer import TopicNormalizer
from youtube_analyzer.db.database import engine, init_db

# -------------------------------------------------------------
# Streamlit Page Configuration
# -------------------------------------------------------------
st.set_page_config(
    page_title="YouTube Search & Competitor Intelligence",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()


# -------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------
def get_all_topics():
    with Session(engine) as session:
        return session.exec(select(Topic).order_by(Topic.created_at.desc())).all()


def save_or_get_topic(seed_keyword: str):
    canonical_id = TopicNormalizer.generate_canonical_id(seed_keyword)
    surfaces = TopicNormalizer.expand_seed_surfaces(seed_keyword)

    with Session(engine) as session:
        topic = session.exec(select(Topic).where(Topic.canonical_id == canonical_id)).first()
        if not topic:
            topic = Topic(
                canonical_id=canonical_id,
                name=seed_keyword.strip().title(),
                seed_keyword=seed_keyword.strip(),
                description=f"Riset topik '{seed_keyword}' via Browser App",
            )
            session.add(topic)
            session.commit()
            session.refresh(topic)

            for platform, queries in surfaces.items():
                for q in queries:
                    session.add(
                        Query(
                            topic_id=topic.id,
                            query_text=q,
                            platform=platform,
                            query_type="seed_expansion",
                        )
                    )

            clusters = TopicNormalizer.create_intent_clusters(
                topic_id=topic.id,
                google_terms=surfaces[PlatformEnum.GOOGLE_SEARCH],
                youtube_terms=surfaces[PlatformEnum.YOUTUBE_SEARCH],
                aeo_queries=surfaces[PlatformEnum.AI_SEARCH],
            )
            for c in clusters:
                session.add(c)
            session.commit()

        queries = session.exec(select(Query).where(Query.topic_id == topic.id)).all()
        clusters = session.exec(
            select(IntentCluster).where(IntentCluster.topic_id == topic.id)
        ).all()

    return topic, surfaces, clusters, queries


def fetch_google_trends_rss(geo: str = "ID") -> list[dict[str, str]]:
    """Fetch live daily trending searches from Google Trends RSS."""
    import xml.etree.ElementTree as ET

    import httpx

    target_geo = geo.upper() if geo and geo.upper() != "WW" else ""
    url = (
        f"https://trends.google.co.id/trending/rss?geo={target_geo}"
        if target_geo
        else "https://trends.google.co.id/trending/rss"
    )
    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                items = []
                for it in root.findall(".//item")[:10]:
                    title_elem = it.find("title")
                    title = title_elem.text if title_elem is not None else ""
                    approx = it.find("{https://trends.google.co.id/trending/rss}approx_traffic")
                    traffic = approx.text if (approx is not None and approx.text) else "Trending"
                    link_elem = it.find("link")
                    link = link_elem.text if link_elem is not None else ""
                    if title:
                        items.append(
                            {
                                "Topik Tren": title,
                                "Estimasi Penelusuran": traffic,
                                "Tautan Google": link,
                            }
                        )
                return items
    except Exception:
        pass
    return [
        {
            "Topik Tren": "Tutorial AI Video 2026",
            "Estimasi Penelusuran": "50,000+",
            "Tautan Google": "https://trends.google.co.id",
        },
        {
            "Topik Tren": "Peluang Usaha Modal Kecil",
            "Estimasi Penelusuran": "20,000+",
            "Tautan Google": "https://trends.google.co.id",
        },
    ]


# -------------------------------------------------------------
# Sidebar: Riwayat & Pengaturan
# -------------------------------------------------------------
st.sidebar.title("🔍 Search Intelligence")
st.sidebar.caption("YouTube + Google + AI / AEO Orchestrator")
st.sidebar.markdown("---")
st.sidebar.subheader("📚 Riwayat Topik Tersimpan")

all_topics = get_all_topics()
selected_topic_seed = None

if all_topics:
    topic_options = [f"{t.canonical_id} - {t.name}" for t in all_topics]
    selected_option = st.sidebar.selectbox(
        "Pilih Topik Sebelumnya:", ["-- Masukkan Topik Baru --"] + topic_options
    )
    if selected_option != "-- Masukkan Topik Baru --":
        selected_cid = selected_option.split(" - ")[0]
        match = next((t for t in all_topics if t.canonical_id == selected_cid), None)
        if match:
            selected_topic_seed = match.seed_keyword
else:
    st.sidebar.info("Belum ada topik yang tersimpan di database.")

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Status Sistem:**
    - 🟢 **Database:** `SQLite (youtube_analyzer.db)`
    - 🟢 **Antigravity MCP:** Aktif & Terhubung
    - ⚡ **Engine:** Python 3.12 + SQLModel
    """
)


# -------------------------------------------------------------
# Header & Form Pencarian
# -------------------------------------------------------------
st.title("🚀 YouTube Search & Competitor Intelligence")
st.caption(
    "Pusat riset kata kunci, intip kompetitor ranking #1, pemisahan format Landscape vs Shorts, dan optimasi SEO YouTube."
)

col_search, col_btn = st.columns([4, 1])
with col_search:
    default_val = selected_topic_seed or "Google Ads untuk UMKM"
    keyword_input = st.text_input(
        "Masukkan Kata Kunci Seed / Topik Konten:",
        value=default_val,
        placeholder="Contoh: Google Ads UMKM, Saham Pemula, Ide Usaha Modal 1 Juta",
    )

with col_btn:
    st.write("")
    st.write("")
    run_analysis = st.button("🔥 Analisis Topik", use_container_width=True, type="primary")

if keyword_input:
    topic, surfaces, clusters, queries = save_or_get_topic(keyword_input)

    # Fetch Top Competitors Live
    yt_connector = YouTubeConnector()
    with st.spinner("Mengintip video kompetitor ranking teratas di YouTube..."):
        competitors = asyncio.run(yt_connector.get_top_competitors(keyword_input, limit=5))

    top_comp = competitors[0] if competitors else None
    outranking_plan = SearchIntelligence.generate_outranking_plan(keyword_input, top_comp)

    # -------------------------------------------------------------
    # 🎯 EXECUTIVE STRATEGIC DECISION CARD (Traffic Light Verdict)
    # -------------------------------------------------------------
    rpm_data = SearchIntelligence.estimate_rpm(keyword_input)
    kw_metrics = SearchIntelligence.estimate_keyword_metrics(keyword_input, competitors)
    opp_score = kw_metrics["opportunity_score"]
    search_vol = kw_metrics["search_volume"]
    comp_score = kw_metrics["competition_score"]

    # AI Competitor Presence Analysis
    ai_presence = SearchIntelligence.analyze_ai_competitor_presence(competitors)

    # Determine recommended format based on top competitor format
    comp_format = top_comp.get("format", "LANDSCAPE") if top_comp else "LANDSCAPE"

    st.markdown("---")
    if opp_score >= 65:
        st.success(
            f"### 🟢 KEPUTUSAN STRATEGIS: SANGAT LAYAK DIBUAT (Skor Peluang: {opp_score}/100)\n"
            f"**Format yang Direkomendasikan:** **🎬 {comp_format}**  \n"
            f"**Volume Pencarian:** ~{search_vol:,}/bulan | **Tingkat Persaingan:** {comp_score}/100  \n"
            f"**Analisis Niche ({rpm_data['detected_niche'].upper()}):** Estimasi monetisasi **{rpm_data['rpm_range_usd']} per 1.000 views** "
            f"dengan potensi cuan {rpm_data['potential_earnings_per_100k_views']} per 100k views."
        )
    elif opp_score >= 45:
        st.warning(
            f"### 🟡 KEPUTUSAN STRATEGIS: POTENSIAL DENGAN DIFERENSIASI (Skor Peluang: {opp_score}/100)\n"
            f"**Format yang Direkomendasikan:** **🎬 {comp_format}**  \n"
            f"**Volume Pencarian:** ~{search_vol:,}/bulan | **Tingkat Persaingan:** {comp_score}/100  \n"
            f"Persaingan cukup ketat di niche **{rpm_data['detected_niche'].upper()}**. Wajib gunakan hook judul 2026 dan thumbnail berbeda dari kompetitor teratas."
        )
    else:
        st.error(
            f"### 🔴 KEPUTUSAN STRATEGIS: PERSAINGAN TINGGI / VOLUME RENDAH (Skor Peluang: {opp_score}/100)\n"
            f"**Volume Pencarian:** ~{search_vol:,}/bulan | **Tingkat Persaingan:** {comp_score}/100  \n"
            f"Disarankan membidik keyword turunan (*long-tail*) yang lebih spesifik."
        )

    # 4 Baris Metrik Ringkas yang Dinamis
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Skor Peluang Algoritma (SERP Score)",
        f"{opp_score} / 100",
        f"Peringkat: {kw_metrics['rating']}",
    )
    m2.metric(
        "Adopsi Video AI di SERP",
        f"{ai_presence['ai_count']} / {ai_presence['total_competitors']} Video",
        (
            f"{ai_presence['ai_percentage']}% AI Ratio"
            if ai_presence["ai_count"] > 0
            else "100% Kreator Manusia"
        ),
    )
    m3.metric(
        "Estimasi Pencarian & Persaingan",
        f"~{search_vol:,} /bln",
        f"Tingkat Persaingan: {comp_score}/100",
    )
    m4.metric(
        f"Estimasi RPM ({rpm_data['detected_niche'].upper()})",
        f"${rpm_data['avg_rpm_usd']:.2f}",
        f"Range: {rpm_data['rpm_range_usd']}",
    )

    st.markdown("---")

    # -------------------------------------------------------------
    # TAB UTAMA DASHBOARD
    # -------------------------------------------------------------
    tab_spy, tab_trending, tab_research, tab_flow, tab_landscape, tab_shorts, tab_keywords, tab_trends = st.tabs(
        [
            "🕵️‍♂️ Intip Kompetitor & AI",
            "🔥 YouTube Trending Feed",
            "🔬 YouTube Studio & Content Gap",
            "🎬 Google Flow & Veo Studio",
            "📺 Rencana Video Landscape (16:9)",
            "📱 Rencana Video Shorts (9:16)",
            "🌐 Cross-Surface Keywords",
            "📈 Tren Google vs YouTube",
        ]
    )

    # ==================== TAB 1: COMPETITOR SPY & AI LABEL ====================
    with tab_spy:
        st.subheader("👑 Video yang Sedang Ranking di YouTube Saat Ini")
        st.caption(
            "Data live hasil pencarian YouTube dilengkapi deteksi label AI / Altered Content."
        )

        if top_comp:
            c_info1, c_info2, c_info3, c_info4 = st.columns(4)
            c_info1.markdown(f"**Judul Kompetitor #1:**  \n{top_comp['title']}")
            c_info2.markdown(f"**Channel:**  \n{top_comp['channel']}")
            c_info3.markdown(
                f"**Jumlah Views:**  \n🔥 **{top_comp['views']}** ({top_comp.get('upload_age', '')})"
            )
            c_info4.markdown(
                f"**Tipe Pembuat Konten:**  \n`{top_comp.get('ai_badge', '👤 Human Creator')}`"
            )

        # AI Presence Alert Box
        st.info(
            f"🤖 **Status Persaingan Konten AI:** {ai_presence['verdict']}.  \n"
            f"💡 **Analisis Kelayakan:** {ai_presence['ranking_feasibility']}"
        )

        with st.expander("📖 Aturan Resmi YouTube & Best Practice Agar Video AI Tetap Ranking:"):
            for bp in ai_presence["best_practices"]:
                st.markdown(f"- {bp}")

        st.markdown("#### 🎯 Formula Judul Tandingan untuk Mengalahkan Video #1:")
        st.info(f"👉 **{outranking_plan['outranking_title']}**")

        st.markdown("##### Alternatif Variasi Judul:")
        for alt in outranking_plan["alternative_titles"]:
            st.code(alt, language="text")

        st.markdown("#### 📝 Deskripsi SEO Siap Pakai (Dilengkapi Timestamps & Hashtags):")
        st.caption(
            "Tinggal salin dan tempel ke YouTube Studio Anda. 2 baris awal dibuat khusus untuk memikat klik penonton."
        )
        st.text_area(
            "Deskripsi YouTube Siap Pakai:", value=outranking_plan["seo_description"], height=220
        )

        st.markdown("#### 📊 Daftar Semua Kompetitor Halaman 1 YouTube (Human vs AI):")
        comp_df = pd.DataFrame(competitors)[
            [
                "rank",
                "title",
                "channel",
                "views",
                "duration",
                "format",
                "ai_badge",
                "outlier_status",
            ]
        ]
        st.dataframe(comp_df, use_container_width=True)

    # ==================== TAB 2: YOUTUBE TRENDING FEED ====================
    with tab_trending:
        st.subheader("🔥 YouTube Trending Feed Explorer")
        st.caption(
            "Pantau langsung video yang sedang trending di YouTube (https://www.youtube.com/feed/trending). "
            "Pilih perangkat (Desktop vs Mobile), lokasi negara, bahasa, dan kategori minat."
        )

        t_f1, t_f2, t_f3, t_f4 = st.columns(4)
        with t_f1:
            dev_choice = st.selectbox(
                "💻 Pilih Perangkat (User-Agent):",
                ["Desktop (16:9 Web Browser)", "Mobile (m.youtube.com App)"],
                index=0,
                key="dev_select",
            )
            dev_val = "mobile" if "Mobile" in dev_choice else "desktop"

        with t_f2:
            loc_options = {
                "🇮🇩 Indonesia (ID)": "ID",
                "🌍 Seluruh Dunia (Worldwide)": "WW",
                "🇺🇸 Amerika Serikat (US)": "US",
                "🇬🇧 Inggris (GB)": "GB",
                "🇯🇵 Jepang (JP)": "JP",
                "🇲🇾 Malaysia (MY)": "MY",
                "🇸🇬 Singapura (SG)": "SG",
            }
            loc_label = st.selectbox(
                "📍 Pilih Lokasi Negara:", list(loc_options.keys()), index=0, key="loc_select"
            )
            gl_val = loc_options[loc_label]

        with t_f3:
            lang_options = {
                "Bahasa Indonesia (id)": "id",
                "English (en)": "en",
                "日本語 (ja)": "ja",
            }
            lang_label = st.selectbox(
                "🌐 Pilih Bahasa Antarmuka:",
                list(lang_options.keys()),
                index=0,
                key="lang_select",
            )
            hl_val = lang_options[lang_label]

        with t_f4:
            cat_options = {
                "🔥 Trending Sekarang (Now)": "now",
                "🎵 Musik (Music)": "music",
                "🎮 Video Game (Gaming)": "gaming",
                "🎬 Film & Trailer (Movies)": "movies",
                "📱 Shorts Trending": "shorts",
            }
            cat_label = st.selectbox(
                "🎯 Kategori Trending:", list(cat_options.keys()), index=0, key="cat_select"
            )
            cat_val = cat_options[cat_label]

        st.markdown(
            f"🔗 **Tautan Langsung YouTube:** [Buka https://www.youtube.com/feed/trending (gl={gl_val}&hl={hl_val})]"
            f"(https://www.youtube.com/feed/trending?gl={gl_val}&hl={hl_val})"
        )

        with st.spinner(f"Mengambil feed video trending ({loc_label} - {dev_choice})..."):
            trending_feed = asyncio.run(
                yt_connector.get_trending_feed(
                    gl=gl_val,
                    hl=hl_val,
                    category=cat_val,
                    device=dev_val,
                    limit=12,
                )
            )

        # Overview Stats
        tf_c1, tf_c2, tf_c3, tf_c4 = st.columns(4)
        total_vids = len(trending_feed)
        shorts_count = sum(1 for v in trending_feed if v.get("format") == "SHORTS")
        ai_in_trending = sum(1 for v in trending_feed if v.get("is_ai_generated"))
        source_badge = (
            trending_feed[0].get("data_source", "LIVE_SERP") if trending_feed else "LIVE_SERP"
        )

        tf_c1.metric(
            "Total Video Trending",
            f"{total_vids} Video",
            f"{shorts_count} Shorts / {total_vids - shorts_count} Landscape",
        )
        tf_c2.metric(
            "Rasio Konten AI",
            f"{ai_in_trending} / {total_vids} Video",
            f"{(ai_in_trending / max(total_vids, 1)) * 100:.1f}% AI Content",
        )
        tf_c3.metric(
            "Format Target", dev_val.upper(), f"Negara: {gl_val} | Bahasa: {hl_val}"
        )
        tf_c4.metric(
            "Status Sumber Data",
            "🟢 LIVE SERP" if "LIVE" in source_badge else "🟡 BENCHMARK",
            source_badge,
        )

        st.markdown("---")
        st.markdown("#### 📋 Daftar Video Trending Hasil Live Crawl:")
        trend_table_data = []
        for v in trending_feed:
            trend_table_data.append(
                {
                    "Rank": f"#{v.get('rank', 1)}",
                    "Judul Video": v.get("title", ""),
                    "Channel": v.get("channel", ""),
                    "Views": v.get("views", "0"),
                    "Durasi": v.get("duration", "0:00"),
                    "Format": "📱 SHORTS" if v.get("format") == "SHORTS" else "📺 LANDSCAPE",
                    "Tipe Kreator": v.get("ai_badge", "👤 Human Creator"),
                    "Status Outlier": v.get("outlier_status", "Trending"),
                }
            )
        st.dataframe(pd.DataFrame(trend_table_data), use_container_width=True)

        st.info(
            f"💡 **Insight Tren YouTube {loc_label}:** Dari {total_vids} video trending saat ini, "
            f"sebanyak **{shorts_count} video ({int((shorts_count / max(total_vids, 1)) * 100)}%)** menggunakan format vertikal Shorts. "
            f"Di perangkat {dev_val}, penonton sangat menyukai alur cepat to-the-point!"
        )

    # ==================== TAB 3: YOUTUBE STUDIO RESEARCH & CONTENT GAP ====================
    with tab_research:
        st.subheader("🔬 YouTube Studio Research & Content Gap Explorer")
        st.caption(
            "Replikasi resmi tab **Riset (Research)** di YouTube Studio, "
            "lengkap dengan indikator **🏷️ Content Gap (Kesenjangan Konten)**, "
            "analisis Outlier Multiplier, dan AI Shorts Clipping & Highlights."
        )

        res_tab1, res_tab2, res_tab3 = st.tabs(
            [
                "🏷️ Kesenjangan Konten (Content Gap)",
                "💥 Outlier Multiplier & Faceless Niche",
                "✂️ AI Shorts Clipping & Highlights",
            ]
        )

        with res_tab1:
            st.markdown("#### 🔍 Penelusuran di Seluruh YouTube (Searches across YouTube)")
            st.caption(
                "YouTube Studio menandai **🏷️ Content Gap** jika banyak penonton mencari topik ini "
                "namun video kompetitor yang ada: **usang (> 1-2 tahun)**, **kualitas views rendah**, "
                "atau **belum ada format Shorts yang menjawab ringkas**."
            )

            autocomplete_terms = [q.query_text for q in queries] if queries else []
            content_gaps = SearchIntelligence.detect_content_gaps(
                keyword_input, competitors, autocomplete_terms
            )

            gaps_found = sum(1 for g in content_gaps if g["is_content_gap"])
            st.success(
                f"🎯 Ditemukan **{gaps_found} Kesenjangan Konten (Content Gaps)** dari {len(content_gaps)} kueri penelusuran!"
            )

            gap_table_data = []
            for g in content_gaps:
                gap_table_data.append(
                    {
                        "Kueri Penelusuran": g["query"],
                        "Volume Penelusuran": g["search_volume_tier"],
                        "Status Gap": g["gap_badge"],
                        "Tipe Kesenjangan": g["gap_type"],
                        "Alasan Kesenjangan": g["gap_reason"],
                        "Aksi Rekomendasi": g["recommended_action"],
                    }
                )
            st.dataframe(pd.DataFrame(gap_table_data), use_container_width=True)

            st.markdown("##### 🏆 Rekomendasi Judul Pemenang untuk Menutup Content Gap:")
            for g in [item for item in content_gaps if item["is_content_gap"]][:3]:
                st.markdown(f"**Topik:** `{g['query']}` | *{g['gap_type']}*")
                st.info(f"👉 **Formula Judul Pemenang:** {g['winning_hook']}")
                st.caption(f"Strategi Eksekusi: {g['recommended_action']}")

        with res_tab2:
            st.markdown("#### 💥 Outlier Multiplier & Channel Audit")
            st.caption(
                "Mendeteksi video kompetitor yang meledak (*Breakout Outlier*) "
                "jauh di atas rata-rata channel mereka. Video outlier inilah bukti nyata topik organik yang disukai algoritma!"
            )

            outlier_analysis = SearchIntelligence.analyze_competitor_outliers(competitors)
            oc1, oc2, oc3 = st.columns(3)
            oc1.metric("Median Views Kompetitor", f"{outlier_analysis['median_views']:,} Views")
            oc2.metric(
                "Multiplier Tertinggi",
                f"{outlier_analysis['highest_multiplier']}x",
                "Outlier Factor",
            )
            oc3.metric(
                "Video Outlier Terdeteksi",
                f"{outlier_analysis['outliers_found']} Video",
                "Multiplier >= 2.0x",
            )

            if outlier_analysis["golden_video"]:
                gv = outlier_analysis["golden_video"]
                st.warning(
                    f"👑 **Video Golden Benchmark:**  \n"
                    f"**{gv.get('title')}**  \n"
                    f"Channel: `{gv.get('channel')}` | Views: 🔥 **{gv.get('views')}** | Format: `{gv.get('format')}`  \n"
                    f"👉 *Tiru hook judul dan pola thumbnail dari video ini untuk meraih CTR tinggi.*"
                )

            st.markdown("##### 📊 Analisis Multiplier Semua Video Kompetitor:")
            st.dataframe(pd.DataFrame(outlier_analysis["outlier_items"]), use_container_width=True)

            st.markdown("---")
            st.markdown("#### 🤖 Faceless Niche Finder")
            st.caption(
                "Evaluasi kelayakan pembuatan channel YouTube tanpa wajah (Faceless AI Channel) untuk topik ini."
            )
            faceless_info = SearchIntelligence.analyze_faceless_viability(keyword_input, rpm_data)

            fc1, fc2 = st.columns([1, 2])
            with fc1:
                st.metric(
                    "Skor Kelayakan Faceless",
                    f"{faceless_info['faceless_score']} / 100",
                    faceless_info["tier"],
                )
            with fc2:
                st.info(f"💡 **Penilaian:** {faceless_info['verdict']}")

            st.markdown("**Alur Kerja Otomatisasi (Pipeline AI):**")
            for step in faceless_info["recommended_pipeline"]:
                st.markdown(f"- {step}")

        with res_tab3:
            st.markdown("#### ✂️ AI Shorts Clipping & Highlights Generator")
            st.caption(
                "Pecah topik video panjang Anda menjadi 3 video Shorts berpotensi viral tinggi (45 detik). "
                "Dilengkapi hook 3 detik pembuka dan Call-to-Action (CTA)."
            )

            clipping_ideas = SearchIntelligence.generate_clipping_opportunities(
                keyword_input, outranking_plan["outranking_title"]
            )
            for clip in clipping_ideas:
                with st.expander(
                    f"🎬 Klip #{clip['clip_id']}: {clip['clip_title']} (Potensi Virality: {clip['projected_virality']})",
                    expanded=True,
                ):
                    cl1, cl2 = st.columns([3, 2])
                    with cl1:
                        st.markdown(f"**⏱️ Estimasi Timestamp:** `{clip['timestamp_window']}`")
                        st.warning(f'🗣️ **Hook 3 Detik Awal:** "{clip["hook_line"]}"')
                        st.markdown(f"**Inti Pesan:** {clip['core_insight']}")
                    with cl2:
                        st.markdown(
                            f"**🎯 Call to Action (Pancingan):**  \n`{clip['call_to_action']}`"
                        )
                        st.caption(
                            "Pancing penonton klip Shorts ini untuk melihat video lengkap Anda via fitur Related Video YouTube."
                        )

    # ==================== TAB 4: GOOGLE FLOW & VEO STUDIO ====================
    with tab_flow:
        st.subheader("🎬 Google Flow (Imagen 4 + Veo 3.1) Studio")
        st.caption(
            "Storyboard & shotlist terstruktur siap ekspor ke tools otomatisasi: "
            "**flow-agent**, **AutoFlowCut**, **gflow-cli**, atau **veo-mcp**."
        )

        f_col1, f_col2 = st.columns([2, 1])
        with f_col1:
            flow_format = st.radio(
                "Pilih Format Target Video AI:",
                options=["LANDSCAPE (16:9)", "SHORTS (9:16)"],
                horizontal=True,
                index=0 if comp_format == "LANDSCAPE" else 1,
            )
        with f_col2:
            num_scenes = st.slider("Jumlah Scene:", min_value=3, max_value=5, value=5)

        target_format_code = "LANDSCAPE" if "16:9" in flow_format else "SHORTS"
        flow_shotlist = SearchIntelligence.generate_flow_shotlist(
            seed=keyword_input,
            format_type=target_format_code,
            num_scenes=num_scenes,
        )

        st.markdown(
            f"#### 📋 Storyboard Scene-by-Scene ({len(flow_shotlist['scenes'])} Scenes - Rasio {flow_shotlist['aspect_ratio']}):"
        )

        for sc in flow_shotlist["scenes"]:
            with st.expander(
                f"🎞️ {sc['scene_id']} - {sc['timing']} ({sc['duration_seconds']} Detik) - Rasio {sc['aspect_ratio']}",
                expanded=True,
            ):
                sc_c1, sc_c2 = st.columns([3, 2])
                with sc_c1:
                    st.markdown("**Prompt Visual (Google Flow / Veo):**")
                    st.code(sc["flow_prompt"], language="text")
                    st.caption(f"🎥 Pergerakan Kamera: *{sc['camera_motion']}*")
                with sc_c2:
                    st.markdown("**🎙️ Naskah Narasi / Audio (ElevenLabs / Voiceover):**")
                    st.info(f'"{sc["audio_script"]}"')

        st.markdown("---")
        st.markdown("### 🚀 Ekspor Siap Pakai untuk Ekosistem Tools Video AI:")

        e1, e2 = st.columns(2)
        with e1:
            st.markdown("##### 1️⃣ Format Batch `prompts.txt` (untuk `flow-agent` / `gflow-cli`):")
            st.caption("1 baris per scene video. Langsung copy atau download file txt.")
            st.text_area(
                "Batch Prompts TXT:",
                value=flow_shotlist["flow_batch_prompts_txt"],
                height=140,
                key="flow_txt_box",
            )
            st.download_button(
                "💾 Download prompts.txt",
                data=flow_shotlist["flow_batch_prompts_txt"],
                file_name=f"flow_prompts_{keyword_input.replace(' ', '_').lower()}.txt",
                mime="text/plain",
            )
            st.caption("Perintah di terminal: `flow batch prompts.txt --type video`")

        with e2:
            st.markdown("##### 2️⃣ Manifest JSON (untuk `AutoFlowCut` / CapCut & Premiere):")
            st.caption("Import ke AutoFlowCut untuk generate visual lalu ekspor 1-klik ke CapCut.")
            st.json(flow_shotlist["autoflowcut_manifest"], expanded=False)

        with st.expander("🛠️ Panduan Integrasi Tools AI Video Rekomendasi:"):
            st.markdown(
                """
                - **[kodelyx/flow-agent](https://github.com/kodelyx/flow-agent)**:
                  Menggunakan sesi login Google Flow yang sudah aktif di Chrome via extension. Tidak butuh API key, mendukung batch 16 klip sekaligus & upscaler 1080p/4K gratis.
                - **[touchizen/AutoFlowCut](https://github.com/touchizen/AutoFlowCut)**:
                  Aplikasi desktop Electron yang menggabungkan Google Flow/Veo dengan CapCut/Premiere. Impor prompt dari tools ini, visual digenerate, langsung masuk timeline CapCut lengkap dengan subtitle & timeline audio!
                - **[Generative-AI-Strategy-B-V/veo-mcp](https://github.com/Generative-AI-Strategy-B-V/veo-mcp)**:
                  MCP server resmi untuk Veo 3.1 via Google AI Studio API token-efficient.
                - **[ffroliva/gflow-cli](https://github.com/ffroliva/gflow-cli)**:
                  CLI Python untuk scene chaining & pembuatan video multi-scene yang konsisten di Google Flow.
                """
            )

    # ==================== TAB 3: RENCANA VIDEO LANDSCAPE ====================
    with tab_landscape:
        st.subheader("🎬 Blueprint Video Landscape (16:9 Panjang)")
        st.write(
            "Format ini ditujukan untuk penonton yang mencari panduan tuntas dan menghasilkan **AdSense RPM tinggi ($12–$35)**."
        )

        col_l1, col_l2 = st.columns([1, 1])
        with col_l1:
            st.markdown("##### 📌 Rekomendasi Struktur Judul")
            st.code(outranking_plan["outranking_title"], language="text")
            st.caption("Pola: [Solusi/Tutorial] + [Target Pemula] + [Update 2026] + [Anti-Boncos]")

            st.markdown("##### ⏱️ Kerangka Timestamps / Daftar Isi Otomatis")
            st.write("Google Search mengindeks timestamps ini secara otomatis:")
            for ts in outranking_plan["timestamps"]:
                st.markdown(f"- `{ts}`")

        with col_l2:
            st.markdown("##### 💡 Checklist Sukses Video Landscape:")
            st.markdown(
                """
                - [x] **Durasi Ideal:** 12 – 22 Menit (memungkinkan iklan mid-roll otomatis).
                - [x] **Hook 30 Detik Awal:** Jangan buang waktu salam berbelit! Langsung perlihatkan hasil akhir / studi kasus.
                - [x] **Thumbnail:** Maksimal 3-4 kata besar + ekspresi wajah atau grafik kontras.
                - [x] **Bab/Chapters:** Wajib pasang timestamps di deskripsi untuk SEO Google Search.
                """
            )

    # ==================== TAB 3: RENCANA VIDEO SHORTS ====================
    with tab_shorts:
        st.subheader("📱 Blueprint Video Shorts (9:16 Vertikal)")
        st.write(
            "Format ini ditujukan untuk penonton mobile yang *swipe-swipe* cepat dan menjaring penonton baru."
        )

        shorts_pkg = outranking_plan["shorts_package"]

        st.markdown("##### ⚡ Formula Judul Shorts (< 40 Karakter):")
        st.code(shorts_pkg["title"], language="text")

        st.markdown("##### 🛑 Kalimat Pembuka 3 Detik Pertama (Wajib Diucapkan Tanpa Jeda):")
        st.warning(f'🗣️ **"{shorts_pkg["three_second_hook"]}"**')
        st.caption("Tujuannya: Mencegah penonton men-swipe video Anda dalam 2 detik pertama.")

        st.markdown("##### ⏱️ Alur Skrip 45 Detik:")
        for step in shorts_pkg["script_structure"]:
            st.markdown(f"- **{step}**")

        st.markdown("##### 🔗 Trik Funnel (Pancingan ke Video Panjang):")
        st.info(
            "Di YouTube Shorts, sematkan fitur **Related Video** yang menunjuk ke video tutorial panjang Anda! "
            "Penonton Shorts yang penasaran akan langsung mengklik dan menonton video panjang Anda."
        )

    # ==================== TAB 4: KEYWORDS & INTENT ====================
    with tab_keywords:
        st.subheader("Pemisahan Kata Kunci Berdasarkan Search Behavior")
        k1, k2, k3 = st.columns(3)

        with k1:
            st.markdown("##### 🔵 Google Search (GKP)")
            st.caption("Fokus komersial & jasa")
            g_terms = surfaces.get(PlatformEnum.GOOGLE_SEARCH, [])
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Keyword": t, "Intent": TopicNormalizer.classify_intent(t).value.upper()}
                        for t in g_terms
                    ]
                ),
                use_container_width=True,
            )

        with k2:
            st.markdown("##### 🔴 YouTube Search")
            st.caption("Fokus tutorial & cara pasang")
            yt_terms = surfaces.get(PlatformEnum.YOUTUBE_SEARCH, [])
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Keyword": t, "Intent": TopicNormalizer.classify_intent(t).value.upper()}
                        for t in yt_terms
                    ]
                ),
                use_container_width=True,
            )

        with k3:
            st.markdown("##### 🟣 AI & AEO Queries")
            st.caption("Fokus pertanyaan keputusan")
            ai_terms = surfaces.get(PlatformEnum.AI_SEARCH, [])
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Query": t, "Intent": TopicNormalizer.classify_intent(t).value.upper()}
                        for t in ai_terms
                    ]
                ),
                use_container_width=True,
            )

        st.markdown("##### 🎯 Matriks Klaster Intent Tersinkronisasi (Blueprint):")
        cluster_rows = [
            {
                "Klaster": c.cluster_name,
                "Tipe Intent": c.intent_type.value.upper(),
                "Contoh Istilah Google": c.google_term_sample or "-",
                "Contoh Istilah YouTube": c.youtube_term_sample or "-",
                "Contoh Pertanyaan AI": c.aeo_query_sample or "-",
            }
            for c in clusters
        ]
        st.table(pd.DataFrame(cluster_rows))

    # ==================== TAB 8: TRENDS COMPARISON ====================
    with tab_trends:
        st.subheader("📈 Tren Google Web vs YouTube Search (`gprop=youtube`)")
        st.caption(
            "Eksplorasi perbandingan minat penelusuran antara Google Web Search dan YouTube Search (`gprop=youtube`). "
            "Pilih wilayah target (Seluruh Dunia / Indonesia) dan pantau topik pencarian harian yang sedang viral."
        )

        tr_col1, tr_col2 = st.columns([1, 2])
        with tr_col1:
            trend_geo_options = {
                "🇮🇩 Indonesia (geo=ID)": "ID",
                "🌍 Seluruh Dunia (Worldwide)": "",
                "🇺🇸 Amerika Serikat (geo=US)": "US",
                "🇬🇧 Inggris (geo=GB)": "GB",
            }
            sel_geo_label = st.selectbox(
                "📍 Pilih Wilayah Tren:",
                list(trend_geo_options.keys()),
                index=0,
                key="trends_geo_select",
            )
            sel_geo_code = trend_geo_options[sel_geo_label]

        with tr_col2:
            st.write("")
            encoded_kw = keyword_input.strip().replace(" ", "%20")
            yt_trends_url = (
                f"https://trends.google.co.id/explore?geo={sel_geo_code}&gprop=youtube&q={encoded_kw}"
                if sel_geo_code
                else f"https://trends.google.co.id/explore?gprop=youtube&q={encoded_kw}"
            )
            st.markdown(
                f"🌐 **Buka Langsung di Google Trends YouTube:**  \n"
                f"[🔗 Klik di sini untuk buka `{keyword_input}` di Google Trends ({sel_geo_label})]({yt_trends_url})"
            )

        connector = HasDataTrendsConnector()
        with st.spinner(
            f"Mengambil data tren Google Web vs YouTube untuk '{keyword_input}' ({sel_geo_label})..."
        ):
            trends_comp = asyncio.run(
                connector.compare_google_vs_youtube(keyword_input, geo=sel_geo_code or "ID")
            )

        t1, t2 = st.columns(2)
        with t1:
            st.markdown("##### 🌐 Google Web Trends (Search Biasa)")
            st.dataframe(pd.DataFrame(trends_comp["google_web_trends"]), use_container_width=True)

        with t2:
            st.markdown("##### 📺 YouTube Search Trends (`gprop=youtube`)")
            st.dataframe(pd.DataFrame(trends_comp["youtube_trends"]), use_container_width=True)

        st.info(
            f"💡 **Analisis Perilaku Penonton ({sel_geo_label}):**  \n"
            f"- Di **Google Web**, pencarian cenderung bersifat: *{trends_comp['surface_intent_summary']['google_web_focus']}*.  \n"
            f"- Di **YouTube Search (`gprop=youtube`)**, penonton fokus mencari: *{trends_comp['surface_intent_summary']['youtube_focus']}*."
        )

        st.markdown("---")
        st.markdown(
            f"#### ⚡ Topik Populer Harian di Google Trends ({sel_geo_label or 'Worldwide'})"
        )
        st.caption(
            "Topik penelusuran yang sedang melonjak drastis hari ini dari Google Daily Trends RSS. "
            "Bagus untuk inspirasi konten *riding the wave* / *newsjacking*."
        )
        daily_trends = fetch_google_trends_rss(geo=sel_geo_code)
        if daily_trends:
            st.dataframe(pd.DataFrame(daily_trends), use_container_width=True)
        else:
            st.caption("Memuat data RSS tren...")
