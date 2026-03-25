# FinTel — Multi-Agent Financial Intelligence Platform

**An LLM-orchestrated, multi-agent system for institutional-grade financial research and ESG risk assessment.**

Built as a modular platform with two production verticals:
- **Research Module** — Macro, sector, credit, and portfolio analysis with two-tier intent routing
- **ESG Module** — Regulatory-aligned ESG benchmarking for European banks (CSRD/SFDR/EU Taxonomy)

> Developed during consulting engagements at Accenture (ESG vertical) and an independent fintech project (Research vertical). Unified into a single platform architecture.

---

## Architecture

```
User Query
    │
    ├─── NLU / Intent Router ───────────────────────────┐
    │       ├── Tier-1: macro │ sector │ credit │       │
    │       │         portfolio │ esg │ general         │
    │       └── Tier-2: macro_rates │ sector_banking │  │
    │                  credit_bank │ portfolio_rates ... │
    │                                                    │
    ├─── Data Ingestion Layer ──────────────────────────┐│
    │       ├── Finnhub API (quotes, financials, news)  ││
    │       ├── Tavily (web search)                     ││
    │       ├── Yahoo Finance (company snapshots)       ││
    │       ├── Google News RSS (ESG signals)           ││
    │       └── PDF Pipeline (fetch → extract → chunk   ││
    │                          → summarize)             ││
    │                                                   ││
    ├─── Specialized Agent Pool ────────────────────────┘│
    │       ├── Macro Strategist Agent                   │
    │       ├── Sector/Industry Analyst Agent            │
    │       ├── Credit & Risk Analyst Agent              │
    │       ├── Portfolio Strategist Agent                │
    │       ├── ESG Supervisory Agent                    │
    │       └── News Summarizer Agent                    │
    │                                                    │
    ├─── Deterministic Scoring Engine ──────────────────┘
    │       └── 25+ sub-indicators, weighted E/S/G pillars
    │           (rule-based, auditable, LLM-independent)
    │
    ├─── Synthesis Layer
    │       ├── Cross-agent report synthesizer
    │       ├── Executive summary generator
    │       └── Risk disclaimer generator
    │
    └─── Streamlit Frontend
            ├── Single-entity deep analysis
            ├── Multi-entity comparative benchmarking
            ├── Radar charts, sub-score tables, source attribution
            └── PDF upload + interactive Q&A
```

---

## Key Design Decisions

### Two-Tier Intent Routing
Queries are classified twice. Tier-1 determines *which agents* to activate (macro, sector, credit, portfolio, ESG). Tier-2 determines *specialization focus* within each domain (e.g., `macro` → `macro_rates` vs `macro_inflation`). This prevents generic responses and forces domain-specific depth.

### Hybrid Scoring: LLM + Deterministic Engine
The ESG module does **not** rely solely on LLM output for scores. A rule-based `ScoreEngine` maps categorical assessments (e.g., `climate_plan: "science_based"`) to integer scores via weighted sub-indicator rubrics. This ensures reproducibility, auditability, and stability — critical for regulatory contexts.

### Graceful Degradation
Every external dependency has a fallback path. If the LLM is unavailable, deterministic category generation kicks in. If PDF fetching fails, analysis continues with news + market data only. If Finnhub/Tavily keys are missing, the system operates on free data sources (Yahoo Finance + Google News RSS).

### Global Hallucination Guard
All LLM calls are wrapped with a system-level guardrail that prohibits fabrication of specific numerical values (prices, ratios, yields). Agents use qualitative/directional language unless concrete data is present in context.

---

## Modules

### Research Module (`/research`)

Multi-agent financial research pipeline for institutional-style analysis.

| Component | File | Role |
|-----------|------|------|
| Tier-1 Router | `router.py` | Classifies queries into macro/sector/credit/portfolio/stock |
| Tier-2 Router | `router_tier2.py` | Sub-classifies within each domain (20 subtypes) |
| Agent Pool | `agents.py` | 5 specialized agents + synthesis agent |
| Data Providers | `data_providers.py` | Finnhub + Tavily integration |
| Answer Builder | `answer_builder.py` | Executive summary + risk disclaimer wrapper |
| LLM Client | `llm.py` | OpenAI-compatible client with global guardrail |
| Frontend | `app.py` | Streamlit UI with debug/agent breakdown view |

**Pipeline flow:**
```
Query → Tier-1 route → Tier-2 sub-route → fetch context
→ run N specialized agents in parallel → synthesis agent
→ executive summary + risk warning → source attribution
```

**Example output structure:**
1. Executive Summary (3-5 bullets)
2. Macro Framework and Rate Regime
3. Banking / Sector Structure and Profitability
4. Credit and Balance Sheet Risk
5. Portfolio and Risk-Management Implications
6. Scenario Analysis (Base / Upside / Downside)
7. Key Risks, Monitoring, and Open Questions

### ESG Module (`/esg`)

Regulatory-aligned ESG benchmarking system for European banks.

| Component | File | Role |
|-----------|------|------|
| NLU Agent | `nlu_agent.py` | Intent extraction (bank, year, focus area) |
| ESG Agent | `esg_agent.py` | LLM-based ESG analysis + JSON category extraction |
| Score Engine | `score_engine.py` | Deterministic weighted scoring (25+ sub-indicators) |
| News Agent | `news_agent.py` | ESG news signal extraction via Google News RSS |
| PDF Pipeline | `pdf_fetcher.py`, `pdf_summarizer.py` | Official report ingestion (7 years × 3 banks) |
| Final Writer | `final_writer.py` | Audit-grade ESG intelligence report generation |
| Yahoo Client | `yahoo_client.py` | Company profile enrichment |
| Bank Registry | `dutch_banks.py` | Metadata, aliases, ticker mapping for 5 Dutch banks |
| Radar Chart | `radar_chart.py` | E/S/G visualization |
| Server | `server.py` | Central orchestrator + fallback logic |
| Frontend | `app_v2.py` | Single analysis + multi-bank comparison UI |

**Scoring rubric coverage:**

| Pillar | Sub-indicators | Examples |
|--------|---------------|----------|
| **Environmental** | 8 | Climate transition plan, financed emissions, EU Taxonomy alignment, fossil fuel policy |
| **Social** | 8 | AML/KYC maturity, customer protection, diversity & inclusion, data privacy |
| **Governance** | 9 | Board independence, ESG oversight, CSRD transparency, cyber governance |

**Regulatory frameworks referenced:** CSRD, SFDR, EU Taxonomy, EBA/ECB supervisory expectations, PCAF, SBTi

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM Backend | LLaMA 3 (local via Ollama) / OpenAI-compatible API |
| Web Framework | Streamlit |
| Market Data | Finnhub API, Yahoo Finance (`yfinance`) |
| Web Search | Tavily API, Google News RSS |
| PDF Processing | PyPDF2, custom chunking + LLM summarization |
| Visualization | Matplotlib (radar), Altair (grouped bars), Plotly |
| Language | Python 3.10+ |

---

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/fintel.git
cd fintel

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys (all optional — system degrades gracefully)

# Start local LLM (if using Ollama)
ollama pull llama3
ollama serve

# Run Research module
streamlit run research/app.py

# Run ESG module
streamlit run esg/app_v2.py
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FINNHUB_API_KEY` | Optional | Finnhub market data (free tier available) |
| `TAVILY_API_KEY` | Optional | Web search enrichment |
| `LLM_API_BASE` | Optional | LLM endpoint (default: `http://localhost:11434/v1`) |
| `LLM_MODEL_NAME` | Optional | Model name (default: `llama3`) |

---

## Project Evolution

This platform went through three major iterations:

**v1 — Keyword counter (broken)**
Initial ESG scoring used regex-based keyword frequency. A math bug (`min(freq * 500, 1.0)`) caused all scores to saturate at 1.0 regardless of input quality. No actual LLM was invoked despite env vars being loaded.

**v2 — Single-agent LLM**
Rewrote scoring to actually call Ollama. Fixed PDF parser compatibility (`PyPDF2` → `pypdf`). Added proper JSON schema enforcement for LLM output. Single-agent architecture — one LLM call per analysis.

**v3 — Multi-agent platform**
Introduced specialized agent pool with two-tier routing. Added deterministic `ScoreEngine` as LLM-independent scoring layer. Built graceful degradation for all external dependencies. Unified Research and ESG verticals into shared architecture. Added multi-entity comparison, source attribution, and Monte Carlo confidence bands.

---

## Limitations & Future Work

- **LLM dependency for qualitative analysis**: Scoring engine is deterministic, but narrative generation still requires a capable LLM. Small local models (7B) produce weaker analysis than cloud models.
- **Static PDF library**: ESG module currently has pre-mapped PDF URLs for 3 Dutch banks (2018-2024). Expanding to other banks/regions requires adding URLs or enabling Playwright-based scraping.
- **No real-time streaming**: Agents run sequentially. Parallel execution would reduce latency for multi-agent queries.
- **Single-user**: No authentication, rate limiting, or multi-tenant support.

---

## License

MIT
