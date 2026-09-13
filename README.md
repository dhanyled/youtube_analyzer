# YouTube Analyzer & Search Intelligence Platform

An intelligent search orchestrator and MCP server that unifies **Google (GKP, SERP, Trends)**, **YouTube Search/SERP**, and **AI/AEO Prompts** into a synchronized **Canonical Topic & Intent Universe**.

Powered by algorithmic search intelligence formulas:
* **Keyword Opportunity Score Engine**: Search Volume vs. Competition Difficulty & High-CTR Title Formulas.
* **Intent Clustering & SERP Intelligence**: Search Rank Optimization across Google & YouTube surfaces.
* **Outlier Video Multiplier Engine**: Breakout Viral Topic Identification & Niche AdSense RPM Economics.

---

## 🎯 Core Features

| Feature | Engine | Description |
| :--- | :--- | :--- |
| **Cross-Surface Canonical Topics** | Blueprint Core | 1 Seed topic expands to native Google terms, YouTube tutorial queries, and AI conversational prompts. |
| **Keyword Opportunity Score (0-100)** | Opportunity Engine | Logarithmic search volume weighted against competition density (`vol * 0.55 + (100 - comp) * 0.45`). |
| **Outlier Breakout Multiplier** | Outlier Engine | Identifies 5x–10x breakout videos (`views / channel_median_views`) to spot viral topics before saturation. |
| **Niche RPM & Earnings Projections** | Monetization Engine | Benchmark AdSense RPM ranges ($15-$35 for finance/ads, $8-$18 for tech, etc.) and earnings per 100k views across 12 niches. |
| **High-CTR Psychological Titles** | Title Generator | Generates intent-specific title hooks (Step-by-Step, Curiosity Gaps, Budget Revelations, 2026 recency). |
| **Global MCP Ecosystem Integration** | MCP Orchestrator | Seamlessly bridges to global `google-ads-mcp` (`generate_keyword_ideas`) and `google-trends-mcp` for live SERP analysis. |

---

## 🏗️ Architecture & Database Schema

The relational schema strictly enforces the data hierarchy:
$$\text{Topic} \longrightarrow \text{Keyword} \longrightarrow \text{Query} \longrightarrow \text{Intent} \longrightarrow \text{Platform} \longrightarrow \text{Competitor} \longrightarrow \text{Citation} \longrightarrow \text{ContentOpportunity}$$

* **`Topic`**: Canonical identifier (e.g. `TOPIC-GOOADSUMK`), seed query, metadata.
* **`Keyword`**: Metrics (Search volume, CPC, competition level, opportunity score, estimated RPM).
* **`Query`**: Autocomplete, PAA, related searches, and AEO prompts.
* **`IntentCluster`**: Grouping cross-surface search queries by intent (Tutorial, Commercial, Informational, Comparison).
* **`Competitor`**: Content gap tracking, video views, channel median, outlier multiplier, and VPH velocity.
* **`Citation`**: AI Engine (Perplexity, Gemini, ChatGPT) citations and source URLs.
* **`ContentOpportunity`**: Actionable content strategy recommendations.

---

## 🛠️ MCP Tools Exposed

When connected to Claude, Gemini, or Antigravity via Model Context Protocol:

1. **`research_topic(seed_keyword)`**:
   Expands seed query into Google, YouTube, and AI search variants, saves to database, and creates intent clusters.
2. **`get_topic_summary(canonical_id)`**:
   Retrieves all queries, intent clusters, and competitor gaps for a topic.
3. **`analyze_keyword_opportunity(keyword, search_volume, competition_score)`**:
   Calculates 0-100 algorithmic opportunity score and estimated RPM economics across 12 distinct niches.
4. **`detect_outlier_opportunity(video_title, views, channel_median_views)`**:
   Detects if a competitor's video is a breakout outlier (5x+ multiplier) to replicate.
5. **`generate_video_ideas(seed_keyword, intent_type)`**:
   Generates high-CTR title formulas and hooks based on intent.
6. **`inspect_top_competitors(keyword)`**:
   Scrapes top YouTube ranking competitors live, extracting views, channel, duration, format (Landscape vs Shorts), and VPH velocity.
7. **`generate_outranking_plan(keyword, competitor_title, competitor_views, duration_seconds)`**:
   Produces a ready-to-use outranking package: psychological title hook, full SEO description with auto-timestamps, and dedicated Landscape vs Shorts content blueprint.
8. **`compare_google_vs_youtube_trends(keyword)`**:
   Compares relative search velocity on Google Web Search vs YouTube Search.
9. **`generate_flow_shotlist(seed_keyword, format_type, num_scenes)`**:
   Generates a scene-by-scene storyboard and prompt batch for Google Flow (Imagen 4 + Veo 3.1) with camera motions, durations, and audio scripts. Exports ready-to-run manifests for `flow-agent`, `AutoFlowCut`, and `veo-mcp`.

---

## 💻 Web Dashboard

To launch the interactive visual intelligence dashboard:
```bash
# Via Python runner
python run_dashboard.py

# Or on Windows via double click
run.bat
```
Visit `http://localhost:8501` to access:
* **Strategic Verdict Card**: Executive decision (Opportunity Score, AI Adoption Ratio in SERP, Estimated RPM, Landscape vs Shorts verdict).
* **Tab 1: 🕵️‍♂️ Intip Kompetitor & Label AI**: Live competitor spy with YouTube Altered/Synthetic content badge detection and best practice compliance rules.
* **Tab 2: 🎬 Google Flow & Veo Studio**: Scene-by-scene AI video storyboard generator, copyable `prompts.txt` batch for `flow-agent` / `gflow-cli`, and CapCut manifest for `AutoFlowCut`.
* **Tab 3: 📺 Rencana Video Landscape**: 16:9 Long-form blueprint, psychological hook formula, and chapter breakdown for maximum retention.
* **Tab 4: 📱 Rencana Video Shorts**: 9:16 vertical hook, 45-second retention script, and Related Video funnel strategy.
* **Tab 5: 🌐 Cross-Surface Intent Matrix**: Google vs YouTube vs AI query mapping.
* **Tab 6: 📈 Realtime Trends Comparison**: Google vs YouTube momentum graph.

### Prerequisites
* Python 3.12+
* [uv](https://github.com/astral-sh/uv) (ultra-fast package manager)

### Installation
```bash
# Clone the repository
git clone git@github.com:dhanyled/youtube_analyzer.git
cd youtube_analyzer

# Install dependencies
uv sync
```

### Running Tests & Quality Checks
```bash
# Run unit tests
uv run pytest

# Check formatting & linting
uv run ruff check .
uv run ruff format --check .
```

### Running the MCP Server
```bash
uv run python -m youtube_analyzer.server.mcp_server
```

---

## 🔄 CI/CD Pipeline (GitHub Actions)

The repository includes a production-ready CI pipeline (`.github/workflows/ci.yml`):

1. **Lint & Format Check**: Enforced via `ruff` (< 5 seconds).
2. **Secret & Vulnerability Scanning**:
   - `gitleaks` to prevent accidental commit of API keys (HasData, YouTube, Google Ads).
   - `pip-audit` for known CVE detection in dependencies.
3. **Automated Testing**:
   - 100% mocked offline tests to protect third-party API quotas.
   - Cross-platform verification of models, normalization logic, and intelligence scores.
