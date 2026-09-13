"""Interactive Browser Dashboard for YouTube Analyzer & Search Intelligence Platform.

Run locally:
    uv run streamlit run dashboard.py
"""

import asyncio

import pandas as pd
import streamlit as st
from sqlmodel import Session, select

from youtube_analyzer.connectors.hasdata_trends import HasDataTrendsConnector
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

# -------------------------------------------------------------
# Streamlit Page Configuration
# -------------------------------------------------------------
st.set_page_config(
    page_title="YouTube Search Intelligence",
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

            # Simpan queries
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

            # Simpan Intent Clusters
            clusters = TopicNormalizer.create_intent_clusters(
                topic_id=topic.id,
                google_terms=surfaces[PlatformEnum.GOOGLE_SEARCH],
                youtube_terms=surfaces[PlatformEnum.YOUTUBE_SEARCH],
                aeo_queries=surfaces[PlatformEnum.AI_SEARCH],
            )
            for c in clusters:
                session.add(c)
            session.commit()

        # Load fresh queries & clusters
        queries = session.exec(select(Query).where(Query.topic_id == topic.id)).all()
        clusters = session.exec(
            select(IntentCluster).where(IntentCluster.topic_id == topic.id)
        ).all()

    return topic, surfaces, clusters, queries


# -------------------------------------------------------------
# Sidebar: Riwayat Topik
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
    **Status Koneksi:**
    - 🟢 Database: `SQLite (youtube_analyzer.db)`
    - 🟢 MCP Server: Terhubung ke Antigravity
    - ⚡ Engine: Python 3.12 + SQLModel
    """
)


# -------------------------------------------------------------
# Main Header & Search Form
# -------------------------------------------------------------
st.title("🚀 YouTube & Search Intelligence Dashboard")
st.caption("Pusat riset kata kunci, analisis video viral outlier, dan proyeksi monetisasi YouTube.")

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
    run_analysis = st.button("🔥 Riset Topik", use_container_width=True, type="primary")

if keyword_input:
    topic, surfaces, clusters, queries = save_or_get_topic(keyword_input)

    # -------------------------------------------------------------
    # Baris Metrik Skor (VidIQ & NexLev Style)
    # -------------------------------------------------------------
    st.markdown("### 📊 Ringkasan Peluang & Monetisasi")

    col_vol, col_comp = st.columns(2)
    with col_vol:
        est_volume = st.slider("Estimasi Volume Pencarian Bulanan:", 100, 100000, 5000, step=500)
    with col_comp:
        est_comp = st.slider("Tingkat Persaingan Kompetitor (0=Rendah, 100=Saturasi):", 0, 100, 35)

    opp_score = SearchIntelligence.calculate_opportunity_score(est_volume, est_comp)
    rpm_data = SearchIntelligence.estimate_rpm(keyword_input)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        label="Opportunity Score (VidIQ / TubeBuddy)",
        value=f"{opp_score} / 100",
        delta="Sangat Potensial 🔥"
        if opp_score >= 65
        else ("Moderat" if opp_score >= 45 else "Sulit/Jenuh"),
    )
    m2.metric(
        label="Kategori Niche Terdeteksi",
        value=rpm_data["detected_niche"].upper(),
        delta="Audience Tertarget",
    )
    m3.metric(
        label="Estimasi RPM AdSense (NexLev)",
        value=f"${rpm_data['avg_rpm_usd']:.2f}",
        delta=f"Range: {rpm_data['rpm_range_usd']}",
    )
    m4.metric(
        label="Potensi Cuan / 100k Views",
        value=rpm_data["potential_earnings_per_100k_views"],
        delta="Est. AdSense",
    )

    st.markdown("---")

    # -------------------------------------------------------------
    # Tab Navigasi Fitur
    # -------------------------------------------------------------
    tab_surface, tab_cluster, tab_trends, tab_outlier, tab_titles = st.tabs(
        [
            "🌐 Cross-Surface Keywords",
            "🎯 Intent Clusters (Blueprint)",
            "📈 Google vs YouTube Trends",
            "🔥 Outlier Detector (NexLev)",
            "💡 Ide Judul Viral (VidIQ AI)",
        ]
    )

    # ------------------ TAB 1: Cross-Surface Keywords ------------------
    with tab_surface:
        st.subheader("Pemisahan Kata Kunci Berdasarkan Search Behavior Platform")
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("#### 🔵 Google Search (GKP/SERP)")
            st.caption("Fokus komersial, harga, jasa, kebutuhan bisnis")
            g_terms = surfaces.get(PlatformEnum.GOOGLE_SEARCH, [])
            g_data = [
                {"Keyword": t, "Intent": TopicNormalizer.classify_intent(t).value.upper()}
                for t in g_terms
            ]
            st.dataframe(pd.DataFrame(g_data), use_container_width=True)

        with c2:
            st.markdown("#### 🔴 YouTube Search (Autocomplete)")
            st.caption("Fokus visual, panduan praktis, tutorial, cara pasang")
            yt_terms = surfaces.get(PlatformEnum.YOUTUBE_SEARCH, [])
            yt_data = [
                {"Keyword": t, "Intent": TopicNormalizer.classify_intent(t).value.upper()}
                for t in yt_terms
            ]
            st.dataframe(pd.DataFrame(yt_data), use_container_width=True)

        with c3:
            st.markdown("#### 🟣 AI & AEO Queries (ChatGPT/Perplexity)")
            st.caption("Fokus pertanyaan konversasional, pengambilan keputusan")
            ai_terms = surfaces.get(PlatformEnum.AI_SEARCH, [])
            ai_data = [
                {"Query": t, "Intent": TopicNormalizer.classify_intent(t).value.upper()}
                for t in ai_terms
            ]
            st.dataframe(pd.DataFrame(ai_data), use_container_width=True)

    # ------------------ TAB 2: Intent Clusters ------------------
    with tab_cluster:
        st.subheader("Matriks Klaster Intent Tersinkronisasi")
        st.write(
            "Setiap intent dikaitkan ke satu Canonical Topic yang sama, menghubungkan apa yang dicari di Google, YouTube, dan AI."
        )

        cluster_rows = []
        for c in clusters:
            cluster_rows.append(
                {
                    "Cluster Name": c.cluster_name,
                    "Intent Type": c.intent_type.value.upper(),
                    "Google Term": c.google_term_sample or "-",
                    "YouTube Term": c.youtube_term_sample or "-",
                    "AI/AEO Query": c.aeo_query_sample or "-",
                }
            )
        st.table(pd.DataFrame(cluster_rows))

    # ------------------ TAB 3: Google vs YouTube Trends ------------------
    with tab_trends:
        st.subheader("Perbandingan Minat Pencarian: Google Web vs YouTube")
        connector = HasDataTrendsConnector()
        with st.spinner("Mengambil perbandingan tren..."):
            trends_comp = asyncio.run(connector.compare_google_vs_youtube(keyword_input))

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("##### 🌐 Google Web Trends")
            st.dataframe(pd.DataFrame(trends_comp["google_web_trends"]), use_container_width=True)

        with col_t2:
            st.markdown("##### 📺 YouTube Search Trends (`gprop=youtube`)")
            st.dataframe(pd.DataFrame(trends_comp["youtube_trends"]), use_container_width=True)

        st.info(
            f"💡 **Ringkasan:** Di Google pengguna condong mencari: *{trends_comp['surface_intent_summary']['google_web_focus']}*, sedangkan di YouTube lebih mencari: *{trends_comp['surface_intent_summary']['youtube_focus']}*."
        )

    # ------------------ TAB 4: Outlier Detector ------------------
    with tab_outlier:
        st.subheader("Kalkulator Outlier Video Kompetitor (Ala NexLev & VidIQ)")
        st.write(
            "Cek apakah video kompetitor meledak melebihi standar channelnya (*Viral Breakout*)."
        )

        co1, co2, co3 = st.columns(3)
        with co1:
            v_title = st.text_input("Judul Video Kompetitor:", "Cara Pasang Google Ads dari Nol")
        with co2:
            v_views = st.number_input(
                "Jumlah Views Video Tersebut:", min_value=100, value=75000, step=1000
            )
        with co3:
            v_median = st.number_input(
                "Median Views Rata-rata Channelnya:", min_value=100, value=8000, step=500
            )

        outlier_res = SearchIntelligence.calculate_outlier_score(int(v_views), int(v_median))

        st.markdown(f"#### Hasil Analisis: **{outlier_res['classification']}**")
        st.metric(
            label="Outlier Multiplier",
            value=f"{outlier_res['outlier_multiplier']}x",
            delta="Viral Breakout! Wajib dibuat!" if outlier_res["is_outlier"] else "Normal",
        )
        if outlier_res["is_outlier"]:
            st.success(
                "🔥 **Rekomendasi Aksi:** Topik dan format video ini terbukti sangat disukai audiens! Buat video dengan topik serupa dengan sudut pandang unik Anda."
            )
        else:
            st.warning("⚖️ Video ini memiliki performa wajar/standar untuk channel tersebut.")

    # ------------------ TAB 5: Ide Judul Viral ------------------
    with tab_titles:
        st.subheader("Formula Judul Ber-CTR Tinggi (Ala VidIQ AI)")
        selected_intent = st.selectbox(
            "Pilih Gaya Intent Judul:",
            [
                IntentEnum.TUTORIAL.value,
                IntentEnum.COMMERCIAL.value,
                IntentEnum.COMPARISON.value,
                IntentEnum.INFORMATIONAL.value,
            ],
            format_func=lambda x: x.upper(),
        )

        titles = SearchIntelligence.generate_high_ctr_titles(
            keyword_input, IntentEnum(selected_intent)
        )
        st.markdown("##### Salin Judul Pilihan Anda:")
        for _idx, t in enumerate(titles, 1):
            st.code(t, language="text")
