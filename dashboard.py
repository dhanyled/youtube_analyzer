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
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Ensure src/ is in sys.path for Streamlit Cloud and remote deployment
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlmodel import Session, select

from youtube_analyzer.connectors.hasdata_trends import HasDataTrendsConnector
from youtube_analyzer.connectors.youtube import YouTubeConnector
from youtube_analyzer.connectors.youtube_studio import YouTubeStudioConnector
from youtube_analyzer.core.ai_generator import AITitleGenerator
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
_badge_hide_script = """
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
"""
if hasattr(st, "html"):
    st.html(_badge_hide_script)
else:
    components.html(_badge_hide_script, height=0, width=0)

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


class InMemQuery:
    def __init__(self, query_text: str, platform: Any):
        self.query_text = query_text
        self.platform = platform


class InMemTopic:
    def __init__(self, canonical_id: str, name: str, seed_keyword: str):
        self.id = 1
        self.canonical_id = canonical_id
        self.name = name
        self.seed_keyword = seed_keyword
        self.description = f"Riset topik '{seed_keyword}'"


class InMemCluster:
    def __init__(
        self,
        cluster_name: str,
        intent_type: Any,
        google_term_sample: str | None = None,
        youtube_term_sample: str | None = None,
        aeo_query_sample: str | None = None,
    ):
        self.cluster_name = cluster_name
        self.intent_type = intent_type
        self.google_term_sample = google_term_sample
        self.youtube_term_sample = youtube_term_sample
        self.aeo_query_sample = aeo_query_sample


def create_in_memory_clusters(surfaces: dict[Any, list[str]]) -> list[InMemCluster]:
    clusters_map: dict[IntentEnum, dict[str, Any]] = {
        IntentEnum.TUTORIAL: {
            "name": "Tutorial & Panduan Praktis",
            "google": None,
            "youtube": None,
            "aeo": None,
        },
        IntentEnum.COMMERCIAL: {
            "name": "Komersial & Jasa Bisnis",
            "google": None,
            "youtube": None,
            "aeo": None,
        },
        IntentEnum.INFORMATIONAL: {
            "name": "Informasional & Edukasi",
            "google": None,
            "youtube": None,
            "aeo": None,
        },
        IntentEnum.COMPARISON: {
            "name": "Komparasi & Alternatif",
            "google": None,
            "youtube": None,
            "aeo": None,
        },
    }

    for term in surfaces.get(PlatformEnum.GOOGLE_SEARCH, []):
        intent = TopicNormalizer.classify_intent(term)
        if intent in clusters_map and clusters_map[intent]["google"] is None:
            clusters_map[intent]["google"] = term

    for term in surfaces.get(PlatformEnum.YOUTUBE_SEARCH, []):
        intent = TopicNormalizer.classify_intent(term)
        if intent in clusters_map and clusters_map[intent]["youtube"] is None:
            clusters_map[intent]["youtube"] = term

    for term in surfaces.get(PlatformEnum.AI_SEARCH, []):
        intent = TopicNormalizer.classify_intent(term)
        if intent in clusters_map and clusters_map[intent]["aeo"] is None:
            clusters_map[intent]["aeo"] = term

    clusters: list[InMemCluster] = []
    for intent, data in clusters_map.items():
        if any([data["google"], data["youtube"], data["aeo"]]):
            clusters.append(
                InMemCluster(
                    cluster_name=data["name"],
                    intent_type=intent,
                    google_term_sample=data["google"],
                    youtube_term_sample=data["youtube"],
                    aeo_query_sample=data["aeo"],
                )
            )
    return clusters


def save_or_get_topic(seed_keyword: str):
    canonical_id = TopicNormalizer.generate_canonical_id(seed_keyword)
    surfaces = TopicNormalizer.expand_seed_surfaces(seed_keyword)
    in_mem_queries = [InMemQuery(q, p) for p, qs in surfaces.items() for q in qs]
    in_mem_clusters = create_in_memory_clusters(surfaces)
    in_mem_topic = InMemTopic(
        canonical_id=canonical_id,
        name=seed_keyword.strip().title(),
        seed_keyword=seed_keyword.strip(),
    )

    try:
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
                    google_terms=surfaces.get(PlatformEnum.GOOGLE_SEARCH, []),
                    youtube_terms=surfaces.get(PlatformEnum.YOUTUBE_SEARCH, []),
                    aeo_queries=surfaces.get(PlatformEnum.AI_SEARCH, []),
                )
                for c in clusters:
                    session.add(c)
                session.commit()

            queries = session.exec(select(Query).where(Query.topic_id == topic.id)).all()
            clusters = session.exec(
                select(IntentCluster).where(IntentCluster.topic_id == topic.id)
            ).all()

            return topic, surfaces, clusters, queries
    except Exception as e:
        print(f"Notice: Database session notice (fallback to in-memory): {e}")
        return in_mem_topic, surfaces, in_mem_clusters, in_mem_queries


@st.cache_data(ttl="1h", show_spinner=False)
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
    # Strict real data policy: never return synthetic or dummy fallback
    return []


@st.cache_data(ttl="15m", show_spinner=False)
def fetch_top_competitors_cached(keyword: str, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch live competitors with 15-minute Streamlit cache to eliminate redundant scraping."""
    connector = YouTubeConnector()
    return asyncio.run(connector.get_top_competitors(keyword, limit=limit))


@st.cache_data(ttl="15m", show_spinner=False)
def fetch_trending_feed_cached(
    gl: str, hl: str, category: str, device: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Fetch live trending feed with 15-minute Streamlit cache."""
    connector = YouTubeConnector()
    return asyncio.run(
        connector.get_trending_feed(
            gl=gl,
            hl=hl,
            category=category,
            device=device,
            limit=limit,
        )
    )


@st.cache_data(ttl="1h", show_spinner=False)
def fetch_trends_comparison_cached(keyword: str, geo: str = "ID") -> dict[str, Any]:
    """Fetch Google Trends vs YouTube comparison with 1-hour Streamlit cache."""
    connector = HasDataTrendsConnector()
    res = asyncio.run(connector.compare_google_vs_youtube(keyword, geo=geo))
    # Ensure all trends keys are present
    if "youtube_interest_over_time" not in res or not res["youtube_interest_over_time"]:
        res["youtube_interest_over_time"] = connector.get_interest_over_time(
            keyword, geo=geo, property_type="youtube"
        )
    if "google_interest_over_time" not in res or not res["google_interest_over_time"]:
        res["google_interest_over_time"] = connector.get_interest_over_time(
            keyword, geo=geo, property_type="web"
        )
    if "interest_by_region" not in res or not res["interest_by_region"]:
        res["interest_by_region"] = connector.get_interest_by_region(
            keyword, geo=geo, property_type="youtube"
        )
    if "youtube_top_queries" not in res or not res["youtube_top_queries"]:
        yt_q = connector.get_top_and_rising_queries(keyword, geo=geo, property_type="youtube")
        res["youtube_top_queries"] = yt_q["top"]
        res["youtube_rising_queries"] = yt_q["rising"]
    if "google_top_queries" not in res or not res["google_top_queries"]:
        gw_q = connector.get_top_and_rising_queries(keyword, geo=geo, property_type="web")
        res["google_top_queries"] = gw_q["top"]
        res["google_rising_queries"] = gw_q["rising"]
    return res


# -------------------------------------------------------------
# Sidebar: Riwayat & Pengaturan
# -------------------------------------------------------------
st.sidebar.title("🔍 Search Intelligence")
st.sidebar.caption("YouTube + Google + AI / AEO Orchestrator")
st.sidebar.markdown("---")
st.sidebar.subheader("📚 Riwayat Riset Anda")

if "user_search_history" not in st.session_state:
    st.session_state.user_search_history = []
if "video_audit_result" not in st.session_state:
    st.session_state.video_audit_result = None
if "video_audit_details" not in st.session_state:
    st.session_state.video_audit_details = None
if "video_audit_transcript" not in st.session_state:
    st.session_state.video_audit_transcript = None
if "pre_upload_result" not in st.session_state:
    st.session_state.pre_upload_result = None

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

    if st.sidebar.button("🗑️ Bersihkan Riwayat Sesi"):
        st.session_state.user_search_history = []
        st.rerun()
else:
    st.sidebar.caption("Topik yang Anda cari pada sesi ini akan tersimpan otomatis di sini.")

# -------------------------------------------------------------
# Sidebar: Pengaturan AI Generator (Opsional)
# -------------------------------------------------------------
st.sidebar.markdown("---")
with st.sidebar.expander("🤖 Pengaturan AI Generator (Opsional)", expanded=False):
    ai_provider_label = st.selectbox(
        "Pilih Provider AI:",
        [
            "Google Gemini (Rekomendasi / Kuota Gratis)",
            "Groq (Super Cepat & Gratis)",
            "OpenAI (GPT-4o / GPT-4o-mini)",
            "OpenRouter (Multi-Model)",
            "Custom OpenAI-Compatible",
        ],
        key="sidebar_ai_provider",
    )

    provider_map = {
        "Google Gemini (Rekomendasi / Kuota Gratis)": "gemini",
        "Groq (Super Cepat & Gratis)": "groq",
        "OpenAI (GPT-4o / GPT-4o-mini)": "openai",
        "OpenRouter (Multi-Model)": "openrouter",
        "Custom OpenAI-Compatible": "custom",
    }
    sel_provider = provider_map[ai_provider_label]

    default_models = {
        "gemini": "gemini-flash-lite-latest",
        "groq": "llama-3.3-70b-versatile",
        "openai": "gpt-4o-mini",
        "openrouter": "google/gemini-2.0-flash-001",
        "custom": "",
    }

    env_api_key = (
        os.getenv("GEMINI_API_KEY", "")
        if sel_provider == "gemini"
        else (
            os.getenv("GROQ_API_KEY", "")
            if sel_provider == "groq"
            else (
                os.getenv("OPENAI_API_KEY", "")
                if sel_provider == "openai"
                else os.getenv("AI_API_KEY", "")
            )
        )
    )

    api_key_val = st.text_input(
        "API Key (Opsional):",
        type="password",
        value=st.session_state.get("custom_ai_api_key", env_api_key),
        placeholder="Tempel API Key Anda di sini...",
        help="Opsional. Jika diisi, judul tandingan & sudut psikologi di-generate langsung oleh AI. Jika kosong, sistem otomatis memakai Smart Competitor Heuristic.",
        key="input_ai_api_key",
    )
    st.session_state.custom_ai_api_key = api_key_val

    model_val = st.text_input(
        "Model Name (Opsional):",
        value=st.session_state.get("custom_ai_model", default_models.get(sel_provider, "")),
        placeholder=default_models.get(sel_provider, ""),
        key="input_ai_model",
    )
    st.session_state.custom_ai_model = model_val

    custom_url_val = ""
    if sel_provider == "custom":
        custom_url_val = st.text_input(
            "Base URL Endpoint:",
            placeholder="https://api.groq.com/openai/v1",
            key="input_ai_custom_url",
        )

    if api_key_val:
        st.success(f"🟢 **Mode: AI Enhanced ({sel_provider.upper()})**")
        st.caption("Judul diracik langsung oleh AI membaca data 5 video kompetitor.")
    else:
        st.info("🧠 **Mode: Smart Competitor Heuristic**")
        st.caption("Tanpa API Key, sistem mengekstrak entitas penting dari video riil kompetitor.")


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
    run_analysis = st.button("Analisis Topik", icon=":material/search:", type="primary")

if keyword_input:
    clean_kw = keyword_input.strip()
    if clean_kw and clean_kw not in st.session_state.user_search_history:
        st.session_state.user_search_history.insert(0, clean_kw)

    try:
        topic, surfaces, clusters, queries = save_or_get_topic(clean_kw)
    except Exception as e:
        print(f"Notice: save_or_get_topic fallback: {e}")
        surfaces = TopicNormalizer.expand_seed_surfaces(clean_kw)
        queries = [InMemQuery(q, p) for p, qs in surfaces.items() for q in qs]
        clusters = create_in_memory_clusters(surfaces)
        topic = InMemTopic(
            canonical_id=TopicNormalizer.generate_canonical_id(clean_kw),
            name=clean_kw.strip().title(),
            seed_keyword=clean_kw.strip(),
        )

    # Fetch Top Competitors Live (with 15m Cache)
    with st.spinner("Mengintip video kompetitor ranking teratas di YouTube..."):
        competitors = fetch_top_competitors_cached(clean_kw, limit=10)

    top_comp = competitors[0] if competitors else None

    # Prepare AI Config if API key provided
    ai_cfg = None
    user_key = st.session_state.get("custom_ai_api_key", "").strip()
    if user_key:
        ai_cfg = {
            "provider": sel_provider,
            "api_key": user_key,
            "model_name": st.session_state.get("custom_ai_model", "").strip() or None,
            "custom_base_url": custom_url_val.strip() if custom_url_val else None,
        }

    outranking_plan = SearchIntelligence.generate_outranking_plan(
        keyword_input,
        competitor=top_comp,
        competitors=competitors,
        ai_config=ai_cfg,
    )

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
    if not competitors or kw_metrics["rating"] == "INSUFFICIENT_DATA":
        st.warning(
            f"### ⚠️ DATA KOMPETITOR LIVE TIDAK DITEMUKAN\n"
            f'Tidak ada video yang berhasil di-scrape secara live untuk kata kunci **"{keyword_input}"** di YouTube SERP saat ini.  \n'
            f"Sistem **hanya menampilkan data riil** dan menolak menghasilkan angka perkiraan fiktif.  \n"
            f"💡 *Saran:* Pastikan koneksi internet stabil, gunakan kata kunci yang lebih umum, atau periksa langsung hasil di YouTube."
        )
    elif opp_score >= 65:
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
        border=True,
    )
    m2.metric(
        "Adopsi Video AI di SERP",
        f"{ai_presence['ai_count']} / {ai_presence['total_competitors']} Video",
        (
            f"{ai_presence['ai_percentage']}% AI Ratio"
            if ai_presence["ai_count"] > 0
            else "100% Kreator Manusia"
        ),
        border=True,
    )
    m3.metric(
        "Estimasi Pencarian & Persaingan",
        f"~{search_vol:,} /bln",
        f"Tingkat Persaingan: {comp_score}/100",
        border=True,
    )
    m4.metric(
        f"Estimasi RPM ({rpm_data['detected_niche'].upper()})",
        f"${rpm_data['avg_rpm_usd']:.2f}",
        f"Range: {rpm_data['rpm_range_usd']}",
        border=True,
    )

    st.markdown("---")

    # -------------------------------------------------------------
    # TAB UTAMA DASHBOARD
    # -------------------------------------------------------------
    (
        tab_spy,
        tab_audit,
        tab_channel,
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
            "🛠️ Studio Optimasi Video (Audit & Revamp SEO)",
            "📊 Channel YouTube Studio Saya (Koneksi & Batch Audit)",
            "🔥 YouTube Trending Feed",
            "🔬 Riset Kesenjangan Konten (Content Gap)",
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
            with st.container(border=True):
                st.markdown(
                    f"**🏆 Benchmark Video Ranking #1 ({top_comp.get('format', 'LANDSCAPE')})**"
                )
                c_info1, c_info2, c_info3, c_info4 = st.columns(4)
                c_info1.markdown(f"**Judul Video:**  \n{top_comp['title']}")
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

        mode_label = (
            f"⚡ AI Enhanced ({outranking_plan.get('ai_provider', 'AI').upper()})"
            if outranking_plan.get("generation_mode") == "ai_enhanced"
            else "🧠 Smart Competitor SERP Analysis"
        )
        st.markdown(
            f"#### 🎯 Formula Judul Tandingan untuk Mengalahkan Video #1: &nbsp; `{mode_label}`"
        )
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

        if outranking_plan.get("video_tags"):
            st.markdown("#### 🏷️ Video Tags Siap Salin (Kolom Tags YouTube Studio):")
            st.caption(
                "Daftar kata kunci dipisahkan tanda koma (di bawah batas 500 karakter). Tinggal salin dan tempel ke kolom Tags saat upload di YouTube Studio."
            )
            st.code(outranking_plan["video_tags"], language="text")

        # Competitor Tags Spy Box
        if competitors:
            yt_conn_spy = YouTubeConnector()
            comp_spy = asyncio.run(
                yt_conn_spy.spy_competitor_tags(competitors, limit_competitors=5)
            )
            if comp_spy.get("top_tags_by_frequency"):
                with st.expander(
                    "🕵️ Intip Tags Kompetitor Ranking #1-5 & Best Practice Tagging", expanded=False
                ):
                    st.markdown(
                        f"**Dianalisis secara live dari {comp_spy['competitors_analyzed']} video ranking teratas di YouTube:**"
                    )
                    c_tag_col1, c_tag_col2 = st.columns([3, 2])
                    with c_tag_col1:
                        st.markdown("##### 🏆 Tags Paling Sering Digunakan Kompetitor:")
                        comp_tag_df = pd.DataFrame(comp_spy["top_tags_by_frequency"][:15])
                        st.dataframe(comp_tag_df, width="stretch", hide_index=True)
                    with c_tag_col2:
                        st.markdown("##### 📋 Rekomendasi Tag Terkuat:")
                        st.code(comp_spy["recommended_tags_copy"], language="text")

                    st.markdown("##### 💡 Best Practice Tagging Resmi YouTube:")
                    for bp in comp_spy.get("best_practices", []):
                        st.markdown(f"- {bp}")

        st.markdown("#### 📊 Daftar Semua Kompetitor Halaman 1 YouTube (Human vs AI):")
        if competitors:
            cols = [
                "rank",
                "title",
                "channel",
                "views",
                "duration",
                "format",
                "ai_badge",
                "outlier_status",
            ]
            valid_cols = [c for c in cols if any(c in comp for comp in competitors)]
            comp_df = pd.DataFrame(competitors)[valid_cols]
            st.dataframe(comp_df, width="stretch", hide_index=True)
        else:
            st.info(
                "ℹ️ Tidak ada video kompetitor live yang ditemukan untuk kata kunci ini di YouTube SERP."
            )

    # ==================== TAB 2: VIDEO OPTIMIZATION STUDIO (AUDIT & REVAMP) ====================
    with tab_audit:
        st.subheader("🛠️ Studio Optimasi Video (Audit & Revamp SEO)")
        st.caption(
            "Tingkatkan CTR & Peringkat Video Anda: Audit video yang sudah ada di YouTube "
            "(atau upload Unlisted) untuk perbaikan menyeluruh, atau siapkan paket metadata sebelum di-upload."
        )

        opt_mode = st.radio(
            "Pilih Mode Optimasi:",
            [
                "🔗 Mode 1: Video YouTube (Sudah Upload / Unlisted)",
                "📝 Mode 2: Video Belum Upload (Draft Naskah / Poin Bahasan)",
            ],
            horizontal=True,
            key="opt_mode_selection",
        )

        st.markdown("---")

        if "Mode 1" in opt_mode:
            with st.expander(
                "💡 Mengapa Menggunakan 'Unlisted' (Bukan 'Private') untuk Video Baru?",
                expanded=False,
            ):
                st.markdown(
                    """
                    > **🌟 Pro Creator Best Practice: Rahasia Status Unlisted (Tidak Publik)**
                    >
                    > 1. **100% Aman & Tersembunyi:** Video berstatus *Unlisted* tidak akan muncul di feed subscriber, tidak ada di hasil pencarian publik, dan tidak bisa ditonton siapa pun kecuali orang yang memiliki tautan link-nya.
                    > 2. **AI Speech-to-Text YouTube Bekerja Otomatis:** Begitu video terunggah sebagai *Unlisted*, dalam 2–5 menit server YouTube secara otomatis memproses audio menjadi transkrip/subtitle kata demi kata.
                    > 3. **Kenapa BUKAN Private?** Video *Private* dikunci rapat dengan enkripsi akun Google dan menolak akses subtitle/transkrip via API tools pihak ketiga tanpa otentikasi login OAuth Google yang rumit.
                    > 4. **Alur Peluncuran Sempurna:**
                    >    - Upload video ke YouTube Studio dengan status **Unlisted** (cukup beri judul draft sederhana).
                    >    - Salin link videonya dan tempel di bawah ini -> Klik **Audit & Revamp**.
                    >    - Sistem kami langsung membaca transkrip riil video Anda kata-demi-kata, mendiagnosis kelemahan metadata lama, dan meracik paket **Judul NLP, Deskripsi SEO dengan Timestamps Akurat per babak, serta Tags**.
                    >    - Salin hasil perbaikan kembali ke YouTube Studio.
                    >    - Ubah status dari *Unlisted* menjadi **Public**! Begitu live, algoritma YouTube langsung membaca metadata terbaik sejak detik pertama launching.
                    """
                )

            # Check if user channel is authenticated for 1-click select
            studio_conn_audit = YouTubeStudioConnector()
            default_audit_url = st.session_state.get("quick_audit_url", "")
            opt_from_ch = False
            if studio_conn_audit.is_authenticated():
                ch_vids = studio_conn_audit.get_channel_videos(limit=30)
                if ch_vids:
                    opt_from_ch = st.checkbox(
                        f"📥 Pilih Cepat dari Video Channel Saya ({len(ch_vids)} video terdeteksi)",
                        value=bool(default_audit_url),
                        key="chk_use_my_ch_vids",
                    )
                    if opt_from_ch:
                        v_map = {
                            f"🎬 {v['title']} ({v['views_display']})": v["url"] for v in ch_vids
                        }
                        init_idx = 0
                        if default_audit_url:
                            for i, u in enumerate(v_map.values()):
                                if u == default_audit_url:
                                    init_idx = i
                                    break
                        sel_v_title = st.selectbox(
                            "Pilih Video dari Channel Anda:",
                            list(v_map.keys()),
                            index=init_idx,
                            key="sel_my_ch_vid_audit",
                        )
                        selected_ch_url = v_map[sel_v_title]
                        default_audit_url = selected_ch_url
                        # Auto-fill the URL input widget's session state before it renders!
                        st.session_state["input_audit_video_url"] = selected_ch_url
            elif default_audit_url and "input_audit_video_url" not in st.session_state:
                st.session_state["input_audit_video_url"] = default_audit_url

            c_inp_url, c_btn_run = st.columns([4, 1])
            with c_inp_url:
                target_url = st.text_input(
                    "Masukkan URL Video YouTube atau Video ID (Bisa Video Publik atau Unlisted):",
                    value=st.session_state.get("input_audit_video_url", default_audit_url),
                    placeholder="Contoh: https://www.youtube.com/watch?v=dQw4w9WgXcQ atau dQw4w9WgXcQ",
                    key="input_audit_video_url",
                )
            with c_btn_run:
                st.write("")
                st.write("")
                btn_do_audit = st.button("🔍 Audit & Revamp", type="primary", key="btn_do_audit")

            # Check if auto-audit was requested from the Channel tab
            if st.session_state.get("trigger_auto_audit"):
                btn_do_audit = True
                st.session_state["trigger_auto_audit"] = False

            if btn_do_audit:
                effective_url = (target_url or "").strip()
                if not effective_url and default_audit_url:
                    effective_url = default_audit_url
                extracted_id = YouTubeConnector.extract_video_id(effective_url)
                if not extracted_id:
                    st.error(
                        "❌ Format URL atau Video ID tidak valid. Mohon masukkan link YouTube yang valid."
                    )
                else:
                    with st.spinner(
                        "Mengambil metadata riil video, subtitle/transkrip, dan data kompetitor YouTube..."
                    ):
                        yt_conn = YouTubeConnector()
                        vid_meta = asyncio.run(yt_conn.get_video_details(extracted_id))
                        if not vid_meta:
                            st.error(
                                f"❌ Gagal mengambil detail video untuk ID: `{extracted_id}`. "
                                "Pastikan video tidak diset ke 'Private' (Gunakan 'Unlisted' atau 'Public')."
                            )
                        else:
                            st.session_state.video_audit_details = vid_meta
                            vid_transcript = yt_conn.get_video_transcript(extracted_id)
                            st.session_state.video_audit_transcript = vid_transcript

                            topic_query = vid_meta.get("title", keyword_input)
                            rel_competitors = asyncio.run(
                                yt_conn.get_top_competitors(topic_query, limit=5)
                            )
                            st.session_state.video_audit_competitors = rel_competitors

                            ai_prov = sel_provider
                            ai_k = user_key
                            ai_m = st.session_state.get("custom_ai_model", "").strip() or None
                            ai_b = custom_url_val.strip() if custom_url_val else None

                            audit_res = AITitleGenerator.audit_and_revamp(
                                video_details=vid_meta,
                                transcript_data=vid_transcript,
                                competitors=rel_competitors,
                                provider=ai_prov,
                                api_key=ai_k,
                                model_name=ai_m,
                                custom_base_url=ai_b,
                            )
                            st.session_state.video_audit_result = audit_res
                            st.success("✅ Audit & Revamp Video Berhasil Diselesaikan!")

            if st.session_state.get("video_audit_details") and st.session_state.get(
                "video_audit_result"
            ):
                v_det = st.session_state.video_audit_details
                v_trans = st.session_state.video_audit_transcript or {}
                a_res = st.session_state.video_audit_result
                audit_scores = a_res.get("audit", {})

                st.markdown("### 📋 Status Video Saat Ini")
                v_c1, v_c2 = st.columns([1, 2])
                with v_c1:
                    if v_det.get("thumbnail_url"):
                        st.image(
                            v_det["thumbnail_url"],
                            caption=f"Channel: {v_det.get('channel', 'N/A')}",
                        )
                    likes_val = v_det.get("likes", 0)
                    likes_display = (
                        f"{likes_val:,}" if likes_val > 0 else "Tersedia via YouTube Studio / API"
                    )
                    pub_date = v_det.get("published_at", "")[:10] or "N/A"
                    st.caption(
                        f"⏱️ **Durasi:** {v_det.get('duration', 'N/A')} ({v_det.get('format', 'LANDSCAPE')})  \n"
                        f"👁️ **Views:** {v_det.get('views_display', '0')} | 👍 **Likes:** {likes_display}  \n"
                        f"📅 **Upload:** {pub_date}"
                    )
                with v_c2:
                    st.markdown(f"**Judul Saat Ini:**  \n### {v_det.get('title', '')}")
                    cur_tags = v_det.get("tags", [])
                    if cur_tags:
                        st.markdown(
                            f"**Tags Terpasang ({len(cur_tags)}):** `"
                            + "`, `".join(cur_tags[:12])
                            + ("`..." if len(cur_tags) > 12 else "`")
                        )
                    else:
                        st.warning("⚠️ Video ini belum memiliki Tags terpasang.")

                    if v_trans.get("available"):
                        st.success(
                            f"🟢 **Transkrip Suara Terdeteksi ({v_trans.get('snippet_count', 0)} kalimat)**: "
                            f"Bahasa {v_trans.get('language', 'ID')} "
                            f"({'Otomatis' if v_trans.get('is_generated') else 'Manual'})"
                        )
                        with st.expander(
                            "Lihat Cuplikan Transkrip Kata-demi-Kata yang Diekstrak",
                            expanded=False,
                        ):
                            st.text_area(
                                "Transkrip Audio:",
                                value=v_trans.get("timestamped_text", "")[:2500],
                                height=180,
                                disabled=True,
                            )
                    else:
                        st.info(
                            "ℹ️ Subtitle/Transkrip suara belum tersedia pada video ini "
                            "(Revamp menggunakan konteks judul & deskripsi)."
                        )

                st.markdown("---")
                st.markdown("### 🔍 Hasil Diagnosis Kelemahan (Audit Score)")
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    t_sc = audit_scores.get("title_score", 5)
                    sc1.metric(
                        "Skor Judul Lama",
                        f"{t_sc}/10",
                        delta="- Perlu Perbaikan" if t_sc < 7 else "Cukup Baik",
                        border=True,
                    )
                    sc1.markdown(f"**Catatan:** {audit_scores.get('title_flaws', '-')}")
                with sc2:
                    d_sc = audit_scores.get("description_score", 4)
                    sc2.metric(
                        "Skor Deskripsi Lama",
                        f"{d_sc}/10",
                        delta="- Kurang Optimal" if d_sc < 7 else "Cukup Baik",
                        border=True,
                    )
                    sc2.markdown(f"**Catatan:** {audit_scores.get('description_flaws', '-')}")
                with sc3:
                    tg_sc = audit_scores.get("tags_score", 4)
                    sc3.metric(
                        "Skor Tags Lama",
                        f"{tg_sc}/10",
                        delta="- Perlu Diperkaya" if tg_sc < 7 else "Lengkap",
                        border=True,
                    )
                    sc3.markdown(f"**Catatan:** {audit_scores.get('tags_flaws', '-')}")

                st.markdown("---")
                st.markdown("### 🚀 Paket Revamp Judul Baru (High CTR & NLP)")

                out_title = a_res.get("outranking_title", "")
                st.success(
                    f"#### 👑 Rekomendasi Judul Utama (Outranking Title):\n"
                    f"# **{out_title}**\n\n"
                    f"💡 *Formula Psikologi:* **{a_res.get('title_formula', '-')}**"
                )
                st.code(out_title, language="text")

                angles = a_res.get("psychological_angles", {})
                if angles:
                    st.markdown("#### 🧠 4 Alternatif Sudut Pandang Psikologi Penonton:")
                    ang_c1, ang_c2 = st.columns(2)
                    idx = 0
                    for k, val in angles.items():
                        col = ang_c1 if idx % 2 == 0 else ang_c2
                        with col:
                            st.info(
                                f"**{val.get('label', k.upper())}**\n\n"
                                f"### {val.get('title', '')}\n\n"
                                f"🎯 *Alasan Psikologis:* {val.get('rationale', '')}"
                            )
                            st.code(val.get("title", ""), language="text")
                        idx += 1

                st.markdown("---")
                st.markdown("### 📝 Paket Deskripsi Video Baru (Siap Salin ke YouTube Studio)")
                hook_2line = a_res.get("two_line_hook", "")
                if hook_2line:
                    st.markdown(
                        f"**🎯 Hook 2 Baris Awal (Muncul di Hasil Pencarian YouTube & Google Sebelum '...more'):**  \n"
                        f"> *{hook_2line}*"
                    )

                full_desc = a_res.get("full_description", "")
                st.caption(
                    "Deskripsi di bawah sudah terstruktur rapi lengkap dengan Timestamps / Chapters babak pembahasan, "
                    "Call To Action, dan Hashtags:"
                )
                st.code(full_desc, language="markdown")

                st.markdown("---")
                st.markdown("### 🏷️ Paket Video Tags Baru (YouTube Studio Ready)")
                v_tags = a_res.get("video_tags", "")
                st.caption(
                    f"Salin teks di bawah ini langsung ke kolom **Tags** di YouTube Studio "
                    f"({len(v_tags)} karakter / batas aman 500 karakter):"
                )
                st.code(v_tags, language="text")

                audit_comps = st.session_state.get("video_audit_competitors", [])
                if audit_comps:
                    yt_conn_audit_spy = YouTubeConnector()
                    comp_spy_audit = asyncio.run(
                        yt_conn_audit_spy.spy_competitor_tags(audit_comps, limit_competitors=5)
                    )
                    if comp_spy_audit.get("top_tags_by_frequency"):
                        with st.expander(
                            "🕵️ Intip Tags Kompetitor Ranking #1-5 untuk Video Ini & Best Practice",
                            expanded=False,
                        ):
                            st.markdown(
                                f"**Dianalisis secara live dari {comp_spy_audit['competitors_analyzed']} video kompetitor sejenis:**"
                            )
                            c_tag_col1, c_tag_col2 = st.columns([3, 2])
                            with c_tag_col1:
                                st.markdown("##### 🏆 Tags Paling Sering Digunakan Kompetitor:")
                                comp_tag_df = pd.DataFrame(
                                    comp_spy_audit["top_tags_by_frequency"][:15]
                                )
                                st.dataframe(comp_tag_df, width="stretch", hide_index=True)
                            with c_tag_col2:
                                st.markdown("##### 📋 Rekomendasi Tag Terkuat Kompetitor:")
                                st.code(comp_spy_audit["recommended_tags_copy"], language="text")

                            st.markdown("##### 💡 Best Practice Tagging Resmi YouTube:")
                            for bp in comp_spy_audit.get("best_practices", []):
                                st.markdown(f"- {bp}")

                g_seo = a_res.get("google_seo_strategy", "")
                if g_seo:
                    st.markdown(f"#### 🌐 Strategi Tembus Google Search & Key Moments:\n💡 {g_seo}")

                st.markdown("---")
                schema_jsonld = AITitleGenerator.generate_video_schema_jsonld(
                    title=out_title or v_det.get("title", ""),
                    description=full_desc,
                    video_id=v_det.get("video_id", "VIDEO_ID"),
                    thumbnail_url=v_det.get("thumbnail_url", ""),
                    duration=v_det.get("duration", "10:00"),
                    upload_date=v_det.get("published_at", ""),
                    timestamps_text=full_desc,
                )
                with st.expander(
                    "🏷️ Schema.org VideoObject JSON-LD (Google Search Carousel & Key Moments)",
                    expanded=False,
                ):
                    st.caption(
                        "Salin kode `<script>` di bawah ini dan tempelkan ke artikel blog atau landing page website tempat video ini di-embed. "
                        "Ini memungkinkan Google Web Search menampilkan video Anda dengan thumbnail besar dan garis waktu babak (Key Moments)!"
                    )
                    st.code(
                        f'<script type="application/ld+json">\n{schema_jsonld}\n</script>',
                        language="html",
                    )

        else:
            # Mode 2: Video Belum Upload
            st.markdown("### 📝 Rancang Paket Metadata Video Sebelum Di-Upload")
            st.caption(
                "Masukkan poin-poin yang Anda bicarakan di video. AI akan membaca inti pembahasannya, "
                "mencocokkan dengan kompetitor YouTube live, lalu meracik paket judul NLP, deskripsi dengan chapters, dan tags."
            )

            p_col1, p_col2, p_col3 = st.columns([2, 1, 1])
            with p_col1:
                pre_topic = st.text_input(
                    "Topik Utama / Judul Sementara Video:",
                    value=keyword_input,
                    placeholder="Contoh: Cara Iklan Google Ads Modal 50 Ribu untuk Pemula",
                    key="pre_topic_input",
                )
            with p_col2:
                pre_format = st.selectbox(
                    "Format Video:",
                    ["LANDSCAPE (16:9)", "SHORTS (9:16)"],
                    key="pre_format_select",
                )
            with p_col3:
                pre_duration = st.text_input(
                    "Estimasi Durasi:",
                    value="12:00" if "LANDSCAPE" in pre_format else "0:50",
                    key="pre_duration_input",
                )

            pre_notes = st.text_area(
                "Poin-Poin Bahasan / Ringkasan Naskah / Garis Besar Isi Video:",
                placeholder=(
                    "Tuliskan poin-poin yang dibahas di video...\nContoh:\n"
                    "1. Masalah boncos saat pasang iklan pertama kali\n"
                    "2. Setting akun Google Ads mode Expert\n"
                    "3. Pemilihan kata kunci dengan niat beli tinggi\n"
                    "4. Menentukan budget harian Rp50.000\n"
                    "5. Hasil nyata leads yang masuk di WhatsApp"
                ),
                height=150,
                key="pre_notes_textarea",
            )

            btn_run_pre = st.button(
                "🚀 Racik Paket Peluncuran SEO", type="primary", key="btn_run_pre"
            )

            if btn_run_pre:
                if not pre_topic or not pre_notes:
                    st.warning(
                        "⚠️ Mohon isi Topik Utama dan Poin-Poin Bahasan video terlebih dahulu."
                    )
                else:
                    with st.spinner(
                        "Menganalisis naskah, memeriksa SERP kompetitor live, dan meracik paket peluncuran..."
                    ):
                        yt_conn = YouTubeConnector()
                        comp_for_draft = asyncio.run(
                            yt_conn.get_top_competitors(pre_topic, limit=5)
                        )

                        ai_prov = sel_provider
                        ai_k = user_key
                        ai_m = st.session_state.get("custom_ai_model", "").strip() or None
                        ai_b = custom_url_val.strip() if custom_url_val else None

                        pre_res = AITitleGenerator.plan_pre_upload(
                            topic=pre_topic,
                            content_notes=pre_notes,
                            target_format=pre_format,
                            duration=pre_duration,
                            competitors=comp_for_draft,
                            provider=ai_prov,
                            api_key=ai_k,
                            model_name=ai_m,
                            custom_base_url=ai_b,
                        )
                        st.session_state.pre_upload_result = pre_res
                        st.success("✅ Paket Peluncuran Berhasil Dirancang!")

            if st.session_state.get("pre_upload_result"):
                p_res = st.session_state.pre_upload_result

                st.markdown("---")
                st.markdown(
                    f"### 🎯 Nilai Jual Konten Terdeteksi:\n"
                    f"> *{p_res.get('detected_content_summary', '')}*"
                )

                st.markdown("### 👑 Rekomendasi Judul Peluncuran (High CTR):")
                p_out_title = p_res.get("outranking_title", "")
                st.success(
                    f"### **{p_out_title}**\n\n"
                    f"💡 *Formula Psikologi:* **{p_res.get('title_formula', '-')}**"
                )
                st.code(p_out_title, language="text")

                p_angles = p_res.get("psychological_angles", {})
                if p_angles:
                    st.markdown("#### 🧠 4 Variasi Sudut Pandang Psikologi Penonton:")
                    p_ang_c1, p_ang_c2 = st.columns(2)
                    p_idx = 0
                    for k, val in p_angles.items():
                        col = p_ang_c1 if p_idx % 2 == 0 else p_ang_c2
                        with col:
                            st.info(
                                f"**{val.get('label', k.upper())}**\n\n"
                                f"### {val.get('title', '')}\n\n"
                                f"🎯 *Alasan Psikologis:* {val.get('rationale', '')}"
                            )
                            st.code(val.get("title", ""), language="text")
                        p_idx += 1

                st.markdown("---")
                st.markdown("### 📝 Paket Deskripsi Draft (Siap Salin):")
                p_hook = p_res.get("two_line_hook", "")
                if p_hook:
                    st.markdown(f"**🎯 2 Baris Hook Pembuka:**  \n> *{p_hook}*")

                p_desc = p_res.get("full_description", "")
                st.code(p_desc, language="markdown")

                st.markdown("---")
                st.markdown("### 🏷️ Paket Video Tags Siap Pakai:")
                p_tags = p_res.get("video_tags", "")
                st.code(p_tags, language="text")

                checklist = p_res.get("launch_checklist", [])
                if checklist:
                    st.markdown("---")
                    st.markdown("### 📋 Checklist & Best Practice Peluncuran:")
                    for chk in checklist:
                        st.markdown(f"- ✅ **{chk}**")

                st.markdown("---")
                p_schema_jsonld = AITitleGenerator.generate_video_schema_jsonld(
                    title=p_out_title,
                    description=p_desc,
                    video_id="VIDEO_ID_ANDA",
                    duration=pre_duration,
                    timestamps_text=p_desc,
                )
                with st.expander(
                    "🏷️ Schema.org VideoObject JSON-LD (Siap Pasang di Website/Blog)", expanded=False
                ):
                    st.caption(
                        "Kode Schema resmi Google untuk dipasang di artikel web tempat video di-embed. "
                        "Ganti 'VIDEO_ID_ANDA' dengan ID video sebenarnya setelah video di-upload ke YouTube."
                    )
                    st.code(
                        f'<script type="application/ld+json">\n{p_schema_jsonld}\n</script>',
                        language="html",
                    )

    # ==================== TAB 3: CHANNEL YOUTUBE STUDIO SAYA ====================
    with tab_channel:
        st.subheader("📊 Channel YouTube Studio Saya (Koneksi & Batch Audit)")
        st.caption(
            "Integrasi langsung dengan YouTube Studio Anda melalui Google OAuth 2.0. "
            "Pantau inventaris video, temukan video dengan performa rendah yang perlu direvamp, dan audit instan tanpa copy-paste URL."
        )

        ch_studio = YouTubeStudioConnector()

        if not ch_studio.is_authenticated():
            st.info("🔒 Channel YouTube Anda belum terhubung.")

            c_auth1, c_auth2 = st.columns([3, 2])
            with c_auth1:
                st.markdown("#### 🚀 Hubungkan Channel Anda (Setup 3 Menit)")
                st.markdown(
                    "Setelah terhubung, aplikasi ini dapat memuat daftar video channel Anda secara otomatis, "
                    "menganalisis performa penayangan, dan merekomendasikan video yang mendesak untuk diperbaiki judulnya."
                )

                has_client_secret = os.path.exists("client_secret.json")
                if has_client_secret:
                    st.success(
                        "🟢 **Kredensial OAuth Ditemukan & Siap Digunakan (`client_secret.json`)!**"
                    )
                    st.caption("Project: `youtube-andonpokayokebizid` | Tipe: Desktop App")

                btn_login_google = st.button(
                    "🔗 Hubungkan Channel YouTube Saya Sekarang (Buka Login Google)",
                    type="primary",
                    key="btn_login_google",
                )
                if btn_login_google:
                    with st.spinner("Membuka browser untuk otorisasi Google..."):
                        success, msg = ch_studio.authenticate_interactive()
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

                st.write("")
                with st.expander(
                    "⚙️ Pengaturan Kredensial OAuth (Ganti File / Edit Manual)",
                    expanded=not has_client_secret,
                ):
                    auth_tab_file, auth_tab_manual = st.tabs(
                        ["📁 Unggah client_secret.json", "✏️ Input Client ID & Secret Manual"]
                    )

                    with auth_tab_file:
                        uploaded_secret = st.file_uploader(
                            "Unggah file 'client_secret.json' dari Google Cloud Console:",
                            type=["json"],
                            key="upload_client_secret_file",
                        )
                        if uploaded_secret:
                            try:
                                content = uploaded_secret.read().decode("utf-8")
                                with open("client_secret.json", "w", encoding="utf-8") as f:
                                    f.write(content)
                                st.success("✅ File 'client_secret.json' berhasil disimpan!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal menyimpan file: {e}")

                    with auth_tab_manual:
                        c_id = st.text_input(
                            "OAuth Client ID:",
                            value=os.getenv("YOUTUBE_CLIENT_ID", ""),
                            key="input_oauth_client_id",
                        )
                        c_sec = st.text_input(
                            "OAuth Client Secret:",
                            type="password",
                            value=os.getenv("YOUTUBE_CLIENT_SECRET", ""),
                            key="input_oauth_client_secret",
                        )
                        if st.button("💾 Simpan Client ID & Secret", key="btn_save_client_creds"):
                            if c_id and c_sec:
                                client_config = {
                                    "installed": {
                                        "client_id": c_id.strip(),
                                        "client_secret": c_sec.strip(),
                                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                        "token_uri": "https://oauth2.googleapis.com/token",
                                    }
                                }
                                with open("client_secret.json", "w", encoding="utf-8") as f:
                                    json.dump(client_config, f, indent=2)
                                st.success(
                                    "✅ Kredensial OAuth berhasil disimpan ke client_secret.json!"
                                )
                                st.rerun()
                            else:
                                st.warning("Mohon isi Client ID dan Client Secret.")

            with c_auth2:
                with st.expander(
                    "📖 Panduan Singkat Membuat OAuth Client ID di GCP", expanded=True
                ):
                    st.markdown(
                        """
                        **Langkah di Google Cloud Console (`youtube-andonpokayokebizid`):**
                        1. Buka [Google Cloud Console](https://console.cloud.google.com).
                        2. Pastikan project **`youtube-andonpokayokebizid`** terpilih di bagian atas.
                        3. Buka menu **APIs & Services > Library**, pastikan aktif:
                           - **YouTube Data API v3** *(sudah aktif)*
                           - **YouTube Analytics API** *(klik Enable jika belum)*
                        4. Buka menu **APIs & Services > OAuth consent screen**:
                           - Pilih User Type: **External**
                           - Masukkan App name (misal: *YouTube Analyzer*) & Email pengembang Anda.
                           - Pada langkah Scopes, tambahkan `.../auth/youtube.readonly` dan `.../auth/yt-analytics.readonly`.
                           - Pada **Test users**, tambahkan alamat email Gmail pemilik channel YouTube Anda.
                        5. Buka **APIs & Services > Credentials**:
                           - Klik **Create Credentials > OAuth client ID**.
                           - Application type: **Desktop app**.
                           - Download file JSON dan unggah di form sebelah kiri!
                        """
                    )
        else:
            profile = ch_studio.get_channel_profile()
            if not profile:
                st.error("Gagal memuat profil channel. Silakan coba login ulang.")
                if st.button("Logout"):
                    ch_studio.logout()
                    st.rerun()
            else:
                p_c1, p_c2, p_c3 = st.columns([1, 3, 1])
                with p_c1:
                    if profile.get("thumbnail_url"):
                        st.image(profile["thumbnail_url"])
                with p_c2:
                    st.markdown(f"## {profile.get('title', 'Channel YouTube')}")
                    custom_u = profile.get("custom_url", "")
                    if custom_u:
                        st.markdown(f"**`{custom_u}`**")
                    st.caption(
                        f"👥 **{profile.get('subscribers_display', '0')}** Subscribers | "
                        f"🎬 **{profile.get('video_count', 0)}** Video Terupload | "
                        f"👁️ **{profile.get('view_count_display', '0')}** Total Penayangan Channel"
                    )
                with p_c3:
                    st.write("")
                    if st.button("🚪 Putuskan Koneksi (Logout)", key="btn_logout_channel"):
                        ch_studio.logout()
                        st.rerun()

                st.markdown("---")

                analytics_summary = ch_studio.get_channel_analytics_summary()
                if analytics_summary.get("available"):
                    st.markdown("### 📈 Ringkasan Performa Channel (28 Hari Terakhir)")
                    a_m1, a_m2, a_m3, a_m4 = st.columns(4)
                    a_m1.metric(
                        "Penayangan (28 Hari)",
                        analytics_summary.get("views_28d_display", "0"),
                        border=True,
                    )
                    a_m2.metric(
                        "Waktu Tonton",
                        analytics_summary.get("watch_hours_display", "0 jam"),
                        border=True,
                    )
                    a_m3.metric(
                        "Rata-Rata Durasi Tonton",
                        analytics_summary.get("avg_view_duration_display", "0:00"),
                        border=True,
                    )
                    a_m4.metric(
                        "Pertumbuhan Subscriber",
                        f"+{analytics_summary.get('subs_gained', 0)}",
                        border=True,
                    )
                    st.markdown("---")

                with st.spinner("Memuat inventaris video channel Anda..."):
                    ch_videos = ch_studio.get_channel_videos(limit=30)
                    ch_diag = ch_studio.diagnose_channel_videos(ch_videos)

                underperforming = ch_diag.get("underperforming_gems", [])
                st.markdown(
                    "### 🚨 Deteksi Cerdas: Video yang Perlu Diperbaiki (Underperforming Gems)"
                )
                st.caption(
                    "Algoritma kami memindai video di channel Anda yang memiliki views tertinggal jauh, "
                    "minim tags, atau judul kurang hook NLP sehingga potensi impresinya terbuang sia-sia."
                )

                if underperforming:
                    for uv in underperforming[:3]:
                        u_card = st.container(border=True)
                        with u_card:
                            u_c1, u_c2, u_c3 = st.columns([1, 3, 1])
                            with u_c1:
                                if uv.get("thumbnail_url"):
                                    st.image(uv["thumbnail_url"])
                                st.caption(
                                    f"⏱️ {uv.get('duration', 'N/A')} | 👁️ {uv.get('views_display', '0')}"
                                )
                            with u_c2:
                                st.markdown(f"**{uv.get('title', '')}**")
                                st.markdown(
                                    f"⚠️ **Diagnosis Kelemahan:** *{uv.get('weakness_reason', '')}*"
                                )
                                studio_cnt = len(uv.get("studio_tags", []))
                                hash_cnt = len(uv.get("desc_hashtags", []))
                                st.caption(
                                    f"🏷️ Tags Studio: **{studio_cnt}** | 🔖 Hashtag Deskripsi: **{hash_cnt}** | 🎬 Format: **{uv.get('format', 'LANDSCAPE')}**"
                                )
                            with u_c3:
                                st.write("")
                                if st.button(
                                    "⚡ Audit & Revamp", key=f"btn_revamp_{uv['video_id']}"
                                ):
                                    st.session_state["quick_audit_url"] = uv["url"]
                                    st.session_state["trigger_auto_audit"] = True
                                    st.success(
                                        f"Video '{uv['title'][:30]}...' siap diaudit! Buka tab 'Studio Optimasi Video'."
                                    )
                else:
                    st.success("🎉 Seluruh video teratas di channel Anda memiliki performa stabil!")

                st.markdown("---")

                st.markdown(f"### 📋 Inventaris Video Channel ({len(ch_videos)} Video)")
                filter_kw = st.text_input(
                    "🔍 Cari Judul Video di Channel Anda:", key="filter_ch_videos"
                )

                filtered_vids = [
                    v for v in ch_videos if not filter_kw or filter_kw.lower() in v["title"].lower()
                ]

                if filtered_vids:
                    table_rows = []
                    for rank, v in enumerate(filtered_vids, 1):
                        table_rows.append(
                            {
                                "No": rank,
                                "Judul Video": v["title"],
                                "Views": v["views_display"],
                                "Likes": f"{v['likes']:,}",
                                "Komentar": f"{v['comments']:,}",
                                "Durasi": v["duration"],
                                "Format": v["format"],
                                "Tags Studio": len(v.get("studio_tags", [])),
                                "Hashtag Deskripsi": len(v.get("desc_hashtags", [])),
                                "Tanggal Upload": v["published_at"],
                                "Link URL": v["url"],
                            }
                        )
                    st.dataframe(pd.DataFrame(table_rows), width="stretch", hide_index=True)
                else:
                    st.info("Tidak ada video yang cocok dengan pencarian.")

                st.markdown("---")
                st.markdown("### 🌐 Inspeksi Video Schema & Web Embedding (Google Search Console)")
                st.caption(
                    "Jika Anda meng-embed video YouTube ini ke artikel blog atau landing page, "
                    "pastikan Google mengenali halaman tersebut sebagai 'Video Page' dengan Rich Results valid."
                )
                g_c1, g_c2 = st.columns([3, 1])
                with g_c1:
                    test_web_url = st.text_input(
                        "Masukkan URL Artikel / Halaman Web Tempat Video Di-Embed:",
                        placeholder="Contoh: https://domain-anda.com/panduan-lengkap atau https://domain-anda.com/video-tips",
                        key="input_web_embed_url",
                    )
                with g_c2:
                    st.write("")
                    st.write("")
                    btn_check_schema = st.button(
                        "🔍 Panduan Status Video di GSC", key="btn_check_schema_gsc"
                    )

                if btn_check_schema:
                    if test_web_url:
                        st.info(
                            f"📋 **Target URL:** `{test_web_url}`\n\n"
                            "💡 **Panduan Validasi Video Schema (Google Rich Results):**\n"
                            "1. Buka tab **🛠️ Studio Optimasi Video**, gulir ke bawah dan salin kode **Schema.org VideoObject JSON-LD**.\n"
                            "2. Tempelkan script tersebut di dalam tag `<head>` atau di editor HTML artikel web Anda.\n"
                            "3. Begitu Googlebot merayapi URL tersebut, Google Search Console akan otomatis mendeteksi tab 'Video Page' dan memunculkan garis waktu **Key Moments** di Google Search!"
                        )
                    else:
                        st.warning("Mohon masukkan URL halaman web terlebih dahulu.")

    # ==================== TAB 4: YOUTUBE TRENDING FEED ====================
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
            trending_feed = fetch_trending_feed_cached(
                gl=gl_val,
                hl=hl_val,
                category=cat_val,
                device=dev_val,
                limit=10,
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
            border=True,
        )
        tf_c2.metric(
            "Rasio Konten AI",
            f"{ai_in_trending} / {total_vids} Video",
            f"{(ai_in_trending / max(total_vids, 1)) * 100:.1f}% AI Content",
            border=True,
        )
        tf_c3.metric(
            "Format Target",
            dev_val.upper(),
            f"Negara: {gl_val} | Bahasa: {hl_val}",
            border=True,
        )
        tf_c4.metric(
            "Status Sumber Data",
            "🟢 LIVE SERP" if "LIVE" in source_badge else "🟡 BENCHMARK",
            source_badge,
            border=True,
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
        st.dataframe(pd.DataFrame(trend_table_data), width="stretch", hide_index=True)

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
            st.dataframe(pd.DataFrame(gap_table_data), width="stretch", hide_index=True)

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
            oc1.metric(
                "Median Views Kompetitor",
                f"{outlier_analysis['median_views']:,} Views",
                border=True,
            )
            oc2.metric(
                "Multiplier Tertinggi",
                f"{outlier_analysis['highest_multiplier']}x",
                "Outlier Factor",
                border=True,
            )
            oc3.metric(
                "Video Outlier Terdeteksi",
                f"{outlier_analysis['outliers_found']} Video",
                "Multiplier >= 2.0x",
                border=True,
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
            st.dataframe(
                pd.DataFrame(outlier_analysis["outlier_items"]), width="stretch", hide_index=True
            )

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
                    border=True,
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
                width="stretch",
                hide_index=True,
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
                width="stretch",
                hide_index=True,
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
                width="stretch",
                hide_index=True,
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

        with st.spinner(
            f"Mengambil data tren Google Web vs YouTube untuk '{keyword_input}' ({sel_geo_label})..."
        ):
            trends_comp = fetch_trends_comparison_cached(keyword_input, geo=sel_geo_code or "ID")

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
            mo1.metric(
                "Rata-rata YouTube (12 Bln)", f"{yt_avg} / 100", "Minat Penonton", border=True
            )
            mo2.metric("Puncak Minat YouTube", f"{yt_peak} / 100", "Peak Demand", border=True)
            mo3.metric("Rata-rata Google Web", f"{gw_avg} / 100", "Pencarian Teks", border=True)
            mo4.metric(
                "Momentum YouTube Terkini",
                f"{latest_val} / 100",
                f"{'+' if diff_mom >= 0 else ''}{diff_mom} poin (vs bulan lalu)",
                border=True,
            )

            st.line_chart(merged_ot, width="stretch")
        else:
            st.warning(
                "⚠️ **Data historis Google Trends tidak memiliki volume yang cukup untuk kata kunci ini di wilayah tersebut.**  \n"
                "Google Trends hanya mencatat kata kunci yang memenuhi ambang batas pencarian minimum. Silakan gunakan tautan Google Trends di atas untuk memeriksa grafik secara langsung."
            )

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
                st.bar_chart(top_regions_chart, width="stretch")
            with r_col2:
                st.markdown("##### 📋 Tabel Lengkap Wilayah")
                st.dataframe(
                    reg_df[["Wilayah", "Kode", "Indeks Minat", "Tingkat Minat"]],
                    width="stretch",
                    height=320,
                    hide_index=True,
                )
        else:
            st.info(
                "ℹ️ Tidak ada data sebaran minat wilayah dari Google Trends untuk kata kunci ini."
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
                st.caption("Data kueri belum tersedia dari Google Trends.")
                return
            formatted = []
            for i, it in enumerate(raw_items, 1):
                rank = it.get("Rank") or it.get("rank") or i
                q_text = it.get("Query") or it.get("query") or ""
                if query_type == "top":
                    val = it.get("Popularitas (0-100)") or it.get("value") or "-"
                    formatted.append({"Rank": rank, "Query": q_text, "Popularitas (0-100)": val})
                else:
                    val = it.get("Lonjakan Minat") or it.get("value") or "-"
                    formatted.append({"Rank": rank, "Query": q_text, "Lonjakan Minat": str(val)})
            st.dataframe(pd.DataFrame(formatted), width="stretch", height=450, hide_index=True)

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
            st.dataframe(pd.DataFrame(daily_trends), width="stretch", hide_index=True)
        else:
            st.info("ℹ️ Data RSS tren harian Google saat ini belum tersedia untuk wilayah ini.")
