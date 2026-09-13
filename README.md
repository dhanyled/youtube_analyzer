# YouTube Analyzer & Search Intelligence Platform

An intelligent search orchestrator and MCP server that unifies **Google (GKP, SERP, Trends)**, **YouTube Search/SERP**, and **AI/AEO Prompts** into a synchronized **Canonical Topic & Intent Universe**.

Powered by algorithms and tool designs inspired by industry leaders:
* **VidIQ**: Keyword Opportunity Score (Search Volume vs. Competition) & SEO Title Formulas.
* **TubeBuddy**: Intent Clustering & Search Rank Intelligence.
* **NexLev & NexLev MCP**: Outlier Video Multipliers (Breakout Viral Topics) & Niche RPM Economics.

---

## 🎯 Core Features (VidIQ + TubeBuddy + NexLev + MCP)

| Feature | Inspired By | Description |
| :--- | :--- | :--- |
| **Cross-Surface Canonical Topics** | Blueprint Core | 1 Seed topic expands to native Google terms, YouTube tutorial queries, and AI conversational prompts. |
| **Keyword Opportunity Score (0-100)** | VidIQ / TubeBuddy | Logarithmic search volume weighted against competition density (`vol * 0.55 + (100 - comp) * 0.45`). |
| **Outlier Breakout Multiplier** | NexLev / VidIQ | Identifies 5x–10x breakout videos (`views / channel_median_views`) to spot viral topics before saturation. |
| **Niche RPM & Earnings Projections** | NexLev MCP | Benchmark AdSense RPM ranges ($15-$35 for finance/ads, $8-$18 for tech, etc.) and earnings per 100k views. |
| **High-CTR Psychological Titles** | VidIQ AI / TubeBuddy | Generates intent-specific title hooks (Step-by-Step, Curiosity Gaps, Budget Revelations, 2026 recency). |
| **Global MCP Ecosystem Integration** | Claude / Gemini MCP | Seamlessly bridges to global `google-ads-mcp` (`generate_keyword_ideas`) and `playwright-mcp` for live SERP scraping. |

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

When connected to Claude, Gemini, or Cursor via Model Context Protocol:

1. **`research_topic(seed_keyword)`**:
   Expands seed query into Google, YouTube, and AI search variants, saves to database, and creates intent clusters.
2. **`get_topic_summary(canonical_id)`**:
   Retrieves all queries, intent clusters, and competitor gaps for a topic.
3. **`analyze_keyword_opportunity(keyword, search_volume, competition_score)`**:
   Calculates 0-100 VidIQ/TubeBuddy opportunity score and NexLev estimated RPM economics.
4. **`detect_outlier_opportunity(video_title, views, channel_median_views)`**:
   Detects if a competitor's video is a breakout outlier (5x+ multiplier) to replicate.
5. **`generate_video_ideas(seed_keyword, intent_type)`**:
   Generates high-CTR title formulas and hooks based on intent.

---

## 🚀 Quick Start

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
