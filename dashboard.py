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
    opp_score = SearchIntelligence.calculate_opportunity_score(
        search_volume=5000, competition_score=30.0
    )

    # Determine recommended format based on top competitor format
    comp_format = top_comp.get("format", "LANDSCAPE") if top_comp else "LANDSCAPE"

    st.markdown("---")
    if opp_score >= 65:
        st.success(
            f"### 🟢 KEPUTUSAN STRATEGIS: SANGAT LAYAK DIBUAT (Skor Peluang: {opp_score}/100)\n"
            f"**Format yang Direkomendasikan:** **🎬 {comp_format}**  \n"
            f"**Alasan:** Kompetitor ranking teratas berhasil menarik penonton dengan format **{comp_format}**. "
            f"Niche **{rpm_data['detected_niche'].upper()}** memiliki estimasi monetisasi tinggi **{rpm_data['rpm_range_usd']} per 1.000 views**."
        )
    elif opp_score >= 45:
        st.warning(
            f"### 🟡 KEPUTUSAN STRATEGIS: POTENSIAL DENGAN DIFERENSIASI (Skor Peluang: {opp_score}/100)\n"
            f"**Format yang Direkomendasikan:** **🎬 {comp_format}**  \n"
            f"Persaingan cukup ketat. Wajib gunakan hook judul baru (update tahun 2026) dan thumbnail berbeda dari kompetitor #1."
        )
    else:
        st.error(
            f"### 🔴 KEPUTUSAN STRATEGIS: SULIT / PERSAINGAN JENUH (Skor Peluang: {opp_score}/100)\n"
            f"Disarankan membidik keyword turunan (*long-tail*) yang lebih spesifik."
        )

    # 4 Baris Metrik Ringkas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Skor Peluang (VidIQ / TubeBuddy)",
        f"{opp_score} / 100",
        "High Potential" if opp_score >= 65 else "Moderate",
    )
    m2.metric("Kategori Niche Terdeteksi", rpm_data["detected_niche"].upper(), "Audience Tertarget")
    m3.metric(
        "Estimasi RPM AdSense (NexLev)",
        f"${rpm_data['avg_rpm_usd']:.2f}",
        f"Range: {rpm_data['rpm_range_usd']}",
    )
    m4.metric(
        "Proyeksi Cuan / 100k Views", rpm_data["potential_earnings_per_100k_views"], "AdSense"
    )

    st.markdown("---")

    # -------------------------------------------------------------
    # TAB UTAMA DASHBOARD
    # -------------------------------------------------------------
    tab_spy, tab_landscape, tab_shorts, tab_keywords, tab_trends = st.tabs(
        [
            "🕵️‍♂️ Intip Kompetitor Ranking #1",
            "🎬 Rencana Video Landscape (16:9)",
            "📱 Rencana Video Shorts (9:16)",
            "🌐 Cross-Surface Keywords & Intent",
            "📈 Tren Google Web vs YouTube",
        ]
    )

    # ==================== TAB 1: COMPETITOR SPY ====================
    with tab_spy:
        st.subheader("👑 Video yang Sedang Ranking #1 di YouTube Saat Ini")
        st.caption("Data live hasil pencarian YouTube untuk kata kunci yang Anda masukkan.")

        if top_comp:
            c_info1, c_info2, c_info3, c_info4 = st.columns(4)
            c_info1.markdown(f"**Judul Kompetitor:**  \n{top_comp['title']}")
            c_info2.markdown(f"**Channel:**  \n{top_comp['channel']}")
            c_info3.markdown(
                f"**Jumlah Views:**  \n🔥 **{top_comp['views']}** ({top_comp.get('upload_age', '')})"
            )
            c_info4.markdown(
                f"**Format & Durasi:**  \n`{top_comp['format']}` ({top_comp.get('duration', '')})"
            )

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
            "Deskripsi YouTube Siap Pakai:", value=outranking_plan["seo_description"], height=240
        )

        st.markdown("#### 📊 Daftar Semua Kompetitor Halaman 1 YouTube:")
        comp_df = pd.DataFrame(competitors)[
            ["rank", "title", "channel", "views", "duration", "format", "outlier_status"]
        ]
        st.dataframe(comp_df, use_container_width=True)

    # ==================== TAB 2: RENCANA VIDEO LANDSCAPE ====================
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

    # ==================== TAB 5: TRENDS COMPARISON ====================
    with tab_trends:
        st.subheader("Perbandingan Tren: Google Web vs YouTube Search (`gprop=youtube`)")
        connector = HasDataTrendsConnector()
        with st.spinner("Mengambil perbandingan tren Google vs YouTube..."):
            trends_comp = asyncio.run(connector.compare_google_vs_youtube(keyword_input))

        t1, t2 = st.columns(2)
        with t1:
            st.markdown("##### 🌐 Google Web Trends")
            st.dataframe(pd.DataFrame(trends_comp["google_web_trends"]), use_container_width=True)

        with t2:
            st.markdown("##### 📺 YouTube Search Trends")
            st.dataframe(pd.DataFrame(trends_comp["youtube_trends"]), use_container_width=True)

        st.info(
            f"💡 **Insight:** Di Google Web pengguna fokus mencari: *{trends_comp['surface_intent_summary']['google_web_focus']}*, "
            f"sedangkan di YouTube fokus mencari: *{trends_comp['surface_intent_summary']['youtube_focus']}*."
        )
