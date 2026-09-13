# YouTube Analyzer & Search Intelligence Platform

An intelligent search orchestrator and MCP server that unifies **Google (GKP, SERP, Trends)**, **YouTube Search/SERP**, and **AI/AEO Prompts** into a synchronized **Canonical Topic & Intent Universe**.

---

## 🎯 Core Concept (from `blueprint.txt`)

Instead of naively copying raw keyword lists across platforms, this platform maintains **one Canonical Topic** that expands into platform-native search behaviors:

```text
                    CANONICAL TOPIC
                 ("Google Ads untuk UMKM")
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
     Google              YouTube              AI/AEO
  (GKP / SERP)       (YT Autocomplete)      (Prompts)
       │                    │                    │
  "jasa google ads"   "tutorial google ads" "apakah google ads
  "biaya google ads"  "cara pasang google"   efektif untuk umkm?"
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                    NORMALIZATION ENGINE
                            │
                            ▼
                     INTENT CLUSTERS
          (Tutorial, Biaya/Commercial, Pemula)
                            │
                            ▼
                   CONTENT OPPORTUNITIES
```

---

## 🏗️ Architecture & Database Schema

The relational schema strictly enforces the data hierarchy:
$$\text{Topic} \longrightarrow \text{Keyword} \longrightarrow \text{Query} \longrightarrow \text{Intent} \longrightarrow \text{Platform} \longrightarrow \text{Competitor} \longrightarrow \text{Citation} \longrightarrow \text{ContentOpportunity}$$

* **`Topic`**: Canonical identifier (e.g. `TOPIC-GOOADSUMK`), seed query, metadata.
* **`Keyword`**: Metrics (Search volume, CPC, competition level).
* **`Query`**: Autocomplete, PAA, related searches, and AEO prompts.
* **`IntentCluster`**: Grouping cross-surface search queries by intent (Tutorial, Commercial, Informational, Comparison).
* **`Competitor`**: Content gap tracking across YouTube and Google.
* **`Citation`**: AI Engine (Perplexity, Gemini, ChatGPT) citations and source URLs.
* **`ContentOpportunity`**: Actionable content strategy recommendations.

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

1. **Lint & Format Check**: Enforced via `ruff` (< 10 seconds).
2. **Secret & Vulnerability Scanning**:
   - `gitleaks` to prevent accidental commit of API keys (HasData, YouTube, Google Ads).
   - `pip-audit` for known CVE detection in dependencies.
3. **Automated Testing**:
   - 100% mocked offline tests to protect third-party API quotas.
   - Cross-platform verification of models and normalization logic.
