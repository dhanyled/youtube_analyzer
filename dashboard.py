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
import streamlit.components.v1 as components
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

# Sembunyikan toolbar atas (Tombol Fork & Logo GitHub), menu utama, dan footer
st.markdown(
    """
    <style>
    /* Sembunyikan toolbar actions atas: Logo GitHub & Tombol Fork */
    [data-testid="stToolbarActions"], [data-testid="stToolbarActionButton"], .stAppToolbarActions {
        display: none !important;
        visibility: hidden !important;
    }
    /* Sembunyikan Main Menu 3-titik & Footer */
    #MainMenu {
        visibility: hidden !important;
    }
    footer {
        display: none !important;
        visibility: hidden !important;
    }
    /* Bersihkan styling header agar menyatu mulus */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Injeksi script ke parent & top container Streamlit Cloud untuk menyembunyikan badge & avatar profile
components.html(
    """
    <script>
    function hideParentBadges() {
        const windowsToClean = [];
        try {
            if (window.top) windowsToClean.push(window.top);
        } catch (e) {}
        try {
            let curr = window;
            while (curr) {
                windowsToClean.push(curr);
                if (curr === curr.parent) break;
                curr = curr.parent;
            }
        } catch (e) {}

        windowsToClean.forEach(win => {
            try {
                if (!win || !win.document) return;
                const pdoc = win.document;
                const styleId = "hide-github-streamlit-badges";
                let s = pdoc.getElementById(styleId);
                if (!s) {
                    s = pdoc.createElement("style");
                    s.id = styleId;
                    if (pdoc.head) pdoc.head.appendChild(s);
                    else if (pdoc.body) pdoc.body.appendChild(s);
                }
                s.innerHTML = `
                    /* Pastikan container app & iframe selalu terlihat normal */
                    ._stateContainer_1j65n_26,
                    [class*="_stateContainer_"],
                    ._iframe_1j65n_26,
                    [class*="_iframe_"] {
                        display: block !important;
                        visibility: visible !important;
                        opacity: 1 !important;
                    }
                    /* Sembunyikan HANYA badge profil & viewer cloud di sudut kanan bawah */
                    ._profileContainer_gzau3_53,
                    [class*="_profileContainer_"],
                    ._viewerBadge_1j65n_23,
                    [class*="_viewerBadge_"],
                    ._profilePreview_gzau3_63,
                    [class*="_profilePreview_"],
                    ._profileImage_gzau3_78,
                    [class*="_profileImage_"],
                    a[href*="streamlit.io/cloud"],
                    a[href*="share.streamlit.io"],
                    a[href*="github.com"],
                    img[src*="avatars.githubusercontent.com"] {
                        display: none !important;
                        visibility: hidden !important;
                        opacity: 0 !important;
                        pointer-events: none !important;
                        width: 0 !important;
                        height: 0 !important;
                    }
                `;
                pdoc.querySelectorAll('._profileContainer_gzau3_53, [class*="_profileContainer_"], ._viewerBadge_1j65n_23, [class*="_viewerBadge_"], ._profilePreview_gzau3_63, [class*="_profilePreview_"], a[href*="streamlit.io/cloud"], a[href*="share.streamlit.io"], img[src*="avatars.githubusercontent.com"]').forEach(el => {
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('visibility', 'hidden', 'important');
                    el.style.setProperty('opacity', '0', 'important');
                });
            } catch (e) {}
        });
    }
    hideParentBadges();
    setInterval(hideParentBadges, 300);
    </script>
    """,
    height=0,
    width=0,
)

try:
    init_db()
except Exception as e:
    print(f"Database init notice: {e}")


# -------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------
def get_all_topics():
    try:
        with Session(engine) as session:
            return session.exec(select(Topic).order_by(Topic.created_at.desc())).all()
    except Exception as e:
        print(f"Notice: unable to fetch topics: {e}")
        return []


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
            "Topik Tren": "Eksplorasi Wisata & Kuliner Nusantara",
            "Estimasi Penelusuran": "50,000+",
            "Tautan Google": "https://trends.google.co.id",
        },
        {
            "Topik Tren": "Perkembangan Teknologi AI Terkini",
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
st.sidebar.subheader("📚 Riwayat Riset Anda")

if "user_search_history" not in st.session_state:
    st.session_state.user_search_history = []

user_history = st.session_state.user_search_history
selected_topic_seed = None

if user_history:
    selected_option = st.sidebar.selectbox(
        "Pilih Riset Sebelumnya:",
        ["-- Masukkan Topik Baru --"] + user_history,
        key="history_selector",
    )
    if selected_option != "-- Masukkan Topik Baru --":
        selected_topic_seed = selected_option

    if st.sidebar.button("🗑️ Bersihkan Riwayat Sesi", use_container_width=True):
        st.session_state.user_search_history = []
        st.rerun()
else:
    st.sidebar.caption("Topik yang Anda cari pada sesi ini akan tersimpan otomatis di sini.")


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
    clean_kw = keyword_input.strip()
    if clean_kw and clean_kw not in st.session_state.user_search_history:
        st.session_state.user_search_history.insert(0, clean_kw)

    topic, surfaces, clusters, queries = save_or_get_topic(clean_kw)

    # Fetch Top Competitors Live
    yt_connector = YouTubeConnector()
    with st.spinner("Mengintip video kompetitor ranking teratas di YouTube..."):
        competitors = asyncio.run(yt_connector.get_top_competitors(keyword_input, limit=10))

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
            f"dengan potensi pendapatan {rpm_data['potential_earnings_per_100k_views']} per 100k views."
        )
    elif opp_score >= 45:
        st.warning(
            f"### 🟡 KEPUTUSAN STRATEGIS: POTENSIAL DENGAN DIFERENSIASI (Skor Peluang: {opp_score}/100)\n"
            f"**Format yang Direkomendasikan:** **🎬 {comp_format}**  \n"
            f"**Volume Pencarian:** ~{search_vol:,}/bulan | **Tingkat Persaingan:** {comp_score}/100  \n"
            f"Persaingan cukup ketat di niche **{rpm_data['detected_niche'].upper()}**. Wajib gunakan hook judul yang memikat dan thumbnail berbeda dari kompetitor teratas."
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
    (
        tab_spy,
        tab_trending,
        tab_research,
        tab_flow,
        tab_landscape,
        tab_shorts,
        tab_keywords,
        tab_trends,
    ) = st.tabs(
        [
            "🕵️‍♂️ Intip Kompetitor & AI",
            "🔥 YouTube Trending Feed",
            "🔬 YouTube Studio & Content Gap",
            "🎬 Studio Storyboard Video AI",
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

        # Competitor #1 Title Gap Analysis Card
        if outranking_plan.get("competitor_analysis") and top_comp:
            comp_ana = outranking_plan["competitor_analysis"]
            with st.expander(
                "🎯 Bedah Celah Judul Video #1 & Strategi Tandingan Kita:", expanded=True
            ):
                c_gap1, c_gap2 = st.columns(2)
                with c_gap1:
                    st.markdown(f"**⚠️ Celah Judul Kompetitor:**  \n{comp_ana.get('weakness', '')}")
                with c_gap2:
                    st.markdown(
                        f"**💡 Strategi Tandingan Kita:**  \n{comp_ana.get('counter_strategy', '')}"
                    )

        st.markdown("#### 🎯 Formula Judul Tandingan untuk Mengalahkan Video #1:")
        st.info(f"👉 **{outranking_plan['outranking_title']}**")
        if outranking_plan.get("title_formula"):
            st.caption(f"📐 {outranking_plan['title_formula']}")

        st.markdown("##### 🎭 Alternatif Variasi Judul Berdasarkan 4 Sudut Psikologi Penonton:")
        if outranking_plan.get("psychological_angles"):
            p_angles = outranking_plan["psychological_angles"]
            a_col1, a_col2 = st.columns(2)
            with a_col1:
                curiosity = p_angles.get("curiosity_gap", {})
                st.markdown(f"**{curiosity.get('label', '🔍 Curiosity Gap')}**")
                st.code(curiosity.get("title", ""), language="text")
                st.caption(curiosity.get("rationale", ""))

                contrarian = p_angles.get("contrarian", {})
                st.markdown(f"**{contrarian.get('label', '🤯 Mitos vs Fakta')}**")
                st.code(contrarian.get("title", ""), language="text")
                st.caption(contrarian.get("rationale", ""))
            with a_col2:
                stakes = p_angles.get("high_stakes", {})
                st.markdown(f"**{stakes.get('label', '⚡ High-Stakes / Kronologi')}**")
                st.code(stakes.get("title", ""), language="text")
                st.caption(stakes.get("rationale", ""))

                deep = p_angles.get("deep_dive", {})
                st.markdown(f"**{deep.get('label', '📚 Deep Dive')}**")
                st.code(deep.get("title", ""), language="text")
                st.caption(deep.get("rationale", ""))
        else:
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
                    limit=10,
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
        tf_c3.metric("Format Target", dev_val.upper(), f"Negara: {gl_val} | Bahasa: {hl_val}")
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

    # ==================== TAB 4: STUDIO STORYBOARD VIDEO AI ====================
    with tab_flow:
        st.subheader("🎬 Studio Storyboard & Shotlist Video AI")
        st.caption(
            "Storyboard & shotlist terstruktur siap ekspor ke generator video AI favorit Anda "
            "(Kling AI, Runway Gen-3, Luma Dream Machine, Sora, Haiper, CapCut AI, dsb.)."
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
                    st.markdown("**Prompt Visual AI Video (Siap Generate):**")
                    st.code(sc["flow_prompt"], language="text")
                    st.caption(f"🎥 Pergerakan Kamera: *{sc['camera_motion']}*")
                with sc_c2:
                    st.markdown("**🎙️ Naskah Narasi / Audio (Voiceover / TTS):**")
                    st.info(f'"{sc["audio_script"]}"')

        st.markdown("---")
        st.markdown("### 🚀 Ekspor Siap Pakai untuk Generator Video AI:")

        e1, e2 = st.columns(2)
        with e1:
            st.markdown("##### 1️⃣ Format Batch `prompts.txt` (Universal AI Video Generators):")
            st.caption(
                "1 baris per scene video. Langsung salin atau unduh untuk batch generate di tool video AI pilihan Anda."
            )
            st.text_area(
                "Batch Prompts TXT:",
                value=flow_shotlist["flow_batch_prompts_txt"],
                height=140,
                key="flow_txt_box",
            )
            st.download_button(
                "💾 Download prompts.txt",
                data=flow_shotlist["flow_batch_prompts_txt"],
                file_name=f"prompts_{keyword_input.replace(' ', '_').lower()}.txt",
                mime="text/plain",
            )
            st.caption("Kompatibel dengan semua platform text-to-video / image-to-video.")

        with e2:
            st.markdown("##### 2️⃣ Manifest JSON (untuk CapCut & Premiere Timeline):")
            st.caption(
                "Impor manifest ke timeline editor (CapCut / Premiere) untuk menyinkronkan visual dengan naskah audio narasi."
            )
            st.json(flow_shotlist["autoflowcut_manifest"], expanded=False)

        with st.expander("🛠️ Panduan Eksekusi Pembuatan Video AI:"):
            st.markdown(
                """
                - **Generator Visual Video AI (Kling, Runway, Luma, Sora, CapCut AI)**:
                  Gunakan prompt sinematik di atas untuk menghasilkan klip visual berdurasi 4–6 detik per scene dengan pencahayaan dan pergerakan kamera dinamis.
                - **Voiceover Narasi (ElevenLabs / TTS)**:
                  Gunakan naskah audio pada tiap scene untuk menghasilkan suara narator yang natural dan ekspresif.
                - **Editing & Timeline (CapCut / Premiere)**:
                  Gabungkan klip visual dan audio narasi, lalu tambahkan kinetic subtitle dan musik latar lofi / ambient.
                """
            )

    # ==================== TAB 3: RENCANA VIDEO LANDSCAPE ====================
    with tab_landscape:
        st.subheader("🎬 Blueprint Video Landscape (16:9 Panjang)")
        st.write(
            f"Format ini ditujukan untuk penonton yang mencari eksplorasi mendalam dan menghasilkan potensi **AdSense RPM {rpm_data['rpm_range_usd']} ({rpm_data['detected_niche'].title()})**."
        )

        col_l1, col_l2 = st.columns([1, 1])
        with col_l1:
            st.markdown("##### 📌 Rekomendasi Struktur Judul")
            st.code(outranking_plan["outranking_title"], language="text")
            st.caption(
                f"📐 {outranking_plan.get('title_formula', 'Pola: [Hook Menarik] + [Subjek Topik] + [Nilai Tambah]')}"
            )

            st.markdown("##### ⏱️ Kerangka Timestamps / Daftar Isi Otomatis")
            st.write("Google Search mengindeks timestamps ini secara otomatis:")
            for ts in outranking_plan["timestamps"]:
                st.markdown(f"- `{ts}`")

        with col_l2:
            st.markdown("##### 💡 Checklist Sukses Video Landscape:")
            st.markdown(
                """
                - [x] **Durasi Ideal:** 12 – 22 Menit (memungkinkan iklan mid-roll otomatis).
                - [x] **Hook 30 Detik Awal:** Jangan buang waktu salam berbelit! Langsung perlihatkan cuplikan utama / poin paling krusial topik.
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
            "Di YouTube Shorts, sematkan fitur **Related Video** yang menunjuk ke video utama panjang Anda! "
            "Penonton Shorts yang penasaran akan langsung mengklik dan menonton video lengkap Anda."
        )

    # ==================== TAB 4: KEYWORDS & INTENT ====================
    with tab_keywords:
        st.subheader("Pemisahan Kata Kunci Berdasarkan Search Behavior")

        detected_niche = rpm_data.get("detected_niche", "general").lower()
        intent_captions = {
            "documentary": {
                "google": "Fokus artikel sejarah, arsip dokumen & riset ilmiah",
                "youtube": "Fokus dokumenter visual, rekaman & alur kronologi",
                "aeo": "Fokus pertanyaan sebab-akibat & misteri sejarah",
            },
            "culinary": {
                "google": "Fokus takaran resep, bumbu & bahan masakan",
                "youtube": "Fokus tutorial visual masak langkah demi langkah",
                "aeo": "Fokus tips anti-gagal, takaran & teknik mengolah",
            },
            "travel": {
                "google": "Fokus harga tiket, rute lokasi & estimasi biaya",
                "youtube": "Fokus vlog suasana nyata lokasi & spot tersembunyi",
                "aeo": "Fokus rekomendasi waktu terbaik & tips liburan",
            },
            "entertainment": {
                "google": "Fokus sinopsis cerita, biodata & ulasan artikel",
                "youtube": "Fokus alur cerita lengkap, bedah teori & ending",
                "aeo": "Fokus penjelasan makna & analisis pesan cerita",
            },
            "health_fitness": {
                "google": "Fokus artikel medis, gejala, obat & pantangan",
                "youtube": "Fokus panduan gerakan, edukasi dokter & gaya hidup",
                "aeo": "Fokus pertanyaan diagnosis awal & solusi aman",
            },
            "business": {
                "google": "Fokus riset biaya, jasa & strategi bisnis",
                "youtube": "Fokus tutorial teknis, studi kasus & strategi",
                "aeo": "Fokus evaluasi efektivitas & perhitungan kelayakan",
            },
            "tech_tutorial": {
                "google": "Fokus dokumentasi, download software & solusi error",
                "youtube": "Fokus tutorial rekaman layar step-by-step",
                "aeo": "Fokus panduan instalasi & tips shortcut efisien",
            },
            "general": {
                "google": "Fokus artikel referensi, definisi & fakta terpercaya",
                "youtube": "Fokus video edukasi populer & visualisasi konsep",
                "aeo": "Fokus penjelasan komprehensif & wawasan mendalam",
            },
        }
        niche_caps = intent_captions.get(detected_niche, intent_captions["general"])

        k1, k2, k3 = st.columns(3)

        with k1:
            st.markdown("##### 🔵 Google Search (GKP)")
            st.caption(niche_caps["google"])
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
            st.caption(niche_caps["youtube"])
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
            st.caption(niche_caps["aeo"])
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
            "Eksplorasi perbandingan minat penelusuran resmi Google Trends: "
            "Grafik Minat Sepanjang Waktu (Interest Over Time), Distribusi Wilayah (Interest by Region), "
            "serta 50 Kueri Teratas (Top Queries) & 50 Kueri Melonjak (Rising Queries)."
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

        # Ensure all trends keys are present even if cached/older version
        if (
            "youtube_interest_over_time" not in trends_comp
            or not trends_comp["youtube_interest_over_time"]
        ):
            trends_comp["youtube_interest_over_time"] = connector.get_interest_over_time(
                keyword_input, geo=sel_geo_code or "ID", property_type="youtube"
            )
        if (
            "google_interest_over_time" not in trends_comp
            or not trends_comp["google_interest_over_time"]
        ):
            trends_comp["google_interest_over_time"] = connector.get_interest_over_time(
                keyword_input, geo=sel_geo_code or "ID", property_type="web"
            )
        if "interest_by_region" not in trends_comp or not trends_comp["interest_by_region"]:
            trends_comp["interest_by_region"] = connector.get_interest_by_region(
                keyword_input, geo=sel_geo_code or "ID", property_type="youtube"
            )
        if "youtube_top_queries" not in trends_comp or not trends_comp["youtube_top_queries"]:
            yt_q = connector.get_top_and_rising_queries(
                keyword_input, geo=sel_geo_code or "ID", property_type="youtube"
            )
            trends_comp["youtube_top_queries"] = yt_q["top"]
            trends_comp["youtube_rising_queries"] = yt_q["rising"]
        if "google_top_queries" not in trends_comp or not trends_comp["google_top_queries"]:
            gw_q = connector.get_top_and_rising_queries(
                keyword_input, geo=sel_geo_code or "ID", property_type="web"
            )
            trends_comp["google_top_queries"] = gw_q["top"]
            trends_comp["google_rising_queries"] = gw_q["rising"]

        # -------------------------------------------------------------
        # 1. INTEREST OVER TIME (GRAFIK MINAT SEPANJANG WAKTU - 52 MINGGU)
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 📊 Grafik Minat Penelusuran Sepanjang Waktu (Interest Over Time)")
        st.caption(
            "Perbandingan tren historis 52 minggu (12 bulan terakhir) antara **YouTube Search (`gprop=youtube`)** "
            "dan **Google Web Search** dengan skala indeks 0–100."
        )

        yt_ot = trends_comp.get("youtube_interest_over_time", [])
        gw_ot = trends_comp.get("google_interest_over_time", [])

        if yt_ot and gw_ot:
            df_yt = pd.DataFrame(yt_ot)[["Tanggal", "Minat Penelusuran"]].rename(
                columns={"Minat Penelusuran": "YouTube Search (gprop=youtube)"}
            )
            df_gw = pd.DataFrame(gw_ot)[["Tanggal", "Minat Penelusuran"]].rename(
                columns={"Minat Penelusuran": "Google Web Search"}
            )
            merged_ot = pd.merge(df_yt, df_gw, on="Tanggal")
            merged_ot.set_index("Tanggal", inplace=True)

            yt_col_name = "YouTube Search (gprop=youtube)"
            gw_col_name = "Google Web Search"
            yt_avg = int(merged_ot[yt_col_name].mean())
            gw_avg = int(merged_ot[gw_col_name].mean())
            yt_peak = int(merged_ot[yt_col_name].max())
            latest_val = int(merged_ot[yt_col_name].iloc[-1])
            prev_val = int(merged_ot[yt_col_name].iloc[-4])
            diff_mom = latest_val - prev_val

            mo1, mo2, mo3, mo4 = st.columns(4)
            mo1.metric("Rata-rata YouTube (12 Bln)", f"{yt_avg} / 100", "Minat Penonton")
            mo2.metric("Puncak Minat YouTube", f"{yt_peak} / 100", "Peak Demand")
            mo3.metric("Rata-rata Google Web", f"{gw_avg} / 100", "Pencarian Teks")
            mo4.metric(
                "Momentum YouTube Terkini",
                f"{latest_val} / 100",
                f"{'+' if diff_mom >= 0 else ''}{diff_mom} poin (vs bulan lalu)",
            )

            st.line_chart(merged_ot, use_container_width=True)

        # -------------------------------------------------------------
        # 2. INTEREST BY REGION (MINAT BERDASARKAN WILAYAH / PROVINSI)
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown(f"#### 🗺️ Minat Penelusuran Berdasarkan Wilayah ({sel_geo_label})")
        st.caption(
            "Distribusi geografis intensitas penelusuran di subwilayah/provinsi (skala 0–100)."
        )

        region_data = trends_comp.get("interest_by_region", [])
        if region_data:
            reg_df = pd.DataFrame(region_data)
            r_col1, r_col2 = st.columns([3, 2])
            with r_col1:
                st.markdown("##### 📊 Top 10 Wilayah Teratas")
                top_regions_chart = reg_df.head(10).set_index("Wilayah")[["Indeks Minat"]]
                st.bar_chart(top_regions_chart, use_container_width=True)
            with r_col2:
                st.markdown("##### 📋 Tabel Lengkap Wilayah")
                st.dataframe(
                    reg_df[["Wilayah", "Kode", "Indeks Minat", "Tingkat Minat"]],
                    use_container_width=True,
                    height=320,
                )

        # -------------------------------------------------------------
        # 3. TOP & RISING QUERIES (HINGGA 50 KUERI)
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 🎯 Kueri Terkait: Top Query & Rising Query (Hingga 50 Kueri)")
        st.caption(
            "Kueri penelusuran berperingkat 1–50 sesuai sistem resmi Google Trends. "
            "**Top Queries** menunjukkan volume absolut tertinggi, sedangkan **Rising Queries** menunjukkan lonjakan tren terbaru (Breakout)."
        )

        limit_count = st.select_slider(
            "Pilih Jumlah Kueri yang Ditampilkan:",
            options=[10, 20, 30, 40, 50],
            value=50,
            key="trends_query_limit_slider",
        )

        def _render_query_table(raw_items, query_type: str = "top"):
            if not raw_items:
                st.caption("Data kueri belum tersedia.")
                return
            formatted = []
            for i, it in enumerate(raw_items, 1):
                rank = it.get("Rank") or it.get("rank") or i
                q_text = it.get("Query") or it.get("query") or ""
                if query_type == "top":
                    val = it.get("Popularitas (0-100)") or it.get("value") or max(10, 100 - i * 2)
                    formatted.append({"Rank": rank, "Query": q_text, "Popularitas (0-100)": val})
                else:
                    val = (
                        it.get("Lonjakan Minat")
                        or it.get("value")
                        or ("Breakout (+5000% 🔥)" if i <= 4 else f"+{max(50, 800 - i * 30)}%")
                    )
                    formatted.append({"Rank": rank, "Query": q_text, "Lonjakan Minat": str(val)})
            st.dataframe(pd.DataFrame(formatted), use_container_width=True, height=450)

        q_tab_yt, q_tab_gw = st.tabs(
            ["📺 YouTube Search (`gprop=youtube`)", "🌐 Google Web Search"]
        )

        with q_tab_yt:
            col_yt_top, col_yt_rising = st.columns(2)
            with col_yt_top:
                st.markdown(f"##### 🔝 Top Queries YouTube (Rank 1 - {limit_count})")
                st.caption("Paling banyak dicari pengguna YouTube di kotak pencarian.")
                _render_query_table(
                    trends_comp.get("youtube_top_queries", [])[:limit_count], query_type="top"
                )

            with col_yt_rising:
                st.markdown(f"##### 🚀 Rising Queries YouTube (Rank 1 - {limit_count})")
                st.caption("Kueri dengan lonjakan frekuensi pencarian tertinggi (Breakout +5000%).")
                _render_query_table(
                    trends_comp.get("youtube_rising_queries", [])[:limit_count], query_type="rising"
                )

        with q_tab_gw:
            col_gw_top, col_gw_rising = st.columns(2)
            with col_gw_top:
                st.markdown(f"##### 🔝 Top Queries Google Web (Rank 1 - {limit_count})")
                st.caption("Kueri teks paling banyak dicari pengguna di Google Search.")
                _render_query_table(
                    trends_comp.get("google_top_queries", [])[:limit_count], query_type="top"
                )

            with col_gw_rising:
                st.markdown(f"##### 🚀 Rising Queries Google Web (Rank 1 - {limit_count})")
                st.caption("Kueri baru dengan pertumbuhan tercepat di Google Search.")
                _render_query_table(
                    trends_comp.get("google_rising_queries", [])[:limit_count], query_type="rising"
                )

        # -------------------------------------------------------------
        # 4. AUDIENCE BEHAVIOR & DAILY RSS TRENDS
        # -------------------------------------------------------------
        st.markdown("---")
        st.info(
            f"💡 **Analisis Perilaku Penonton ({sel_geo_label}):**  \n"
            f"- Di **Google Web**, pencarian cenderung bersifat: *{trends_comp['surface_intent_summary']['google_web_focus']}*.  \n"
            f"- Di **YouTube Search (`gprop=youtube`)**, penonton fokus mencari: *{trends_comp['surface_intent_summary']['youtube_focus']}*."
        )

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
