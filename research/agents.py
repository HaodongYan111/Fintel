from typing import Dict, Any, List, Optional

from llm import call_llm
from router import route_tags          # Tier-1 router: macro / sector / credit / portfolio ...
from router_tier2 import route_tier2   # Tier-2 router: macro_rates, sector_banking, etc.
from data_providers import (
    get_company_profile,
    get_realtime_quote,
    get_recommendation_trends,
    get_latest_financials,
    get_company_news,
    search_finance_web,
)
from answer_builder import wrap_final_answer

# ============================================================
# Base role prompts (Tier-1)
# ============================================================

MACRO_BASE_PROMPT = """
You are a senior MACRO STRATEGIST in a global markets division.

Scope:
- interest rate regimes (e.g., "higher for longer")
- yield curve shape and term premium
- inflation dynamics and real vs nominal rates
- growth vs recession risk and business cycle phases
- liquidity, funding conditions, and overall financial conditions
- cross-asset macro linkages (rates, credit, FX, equities, commodities)

Constraints:
- Do NOT invent precise macro data (CPI %, GDP %, unemployment, etc.).
- Use directional / qualitative language (higher, lower, steeper, flatter, tightening, easing).
- Explicitly acknowledge uncertainty and multiple possible paths where appropriate.

Focus:
- Explain not only *what* might happen, but *through which channels* it happens.
- Think in terms of "if rates stay high, then funding costs → credit conditions → growth".
"""


SECTOR_BASE_PROMPT = """
You are a senior SECTOR / INDUSTRY ANALYST.

Scope:
- industry structure and competition
- revenue and margin drivers across the cycle
- sensitivity of the sector to macro drivers and regulation
- differences in business models within the sector (e.g., global vs regional banks)

Constraints:
- Focus on sector- and business-model-level dynamics, not individual stock calls.
- Highlight where sector averages hide dispersion across subsegments.
"""


CREDIT_BASE_PROMPT = """
You are a senior CREDIT & RISK ANALYST.

Scope:
- funding costs and credit spreads
- balance sheet structure, leverage, and capital buffers
- asset quality, non-performing loans, default risk, loss-given-default
- systemic risk channels and financial stability considerations

Constraints:
- Do NOT invent specific spread levels or capital ratios.
- Use qualitative credit language (tightening, widening, elevated risk, benign, stressed).
- Distinguish clearly between idiosyncratic vs systemic risk.

Focus:
- Think in terms of the credit cycle, refinancing walls, and where stress can propagate.
"""


PORTFOLIO_BASE_PROMPT = """
You are a PORTFOLIO STRATEGIST for institutional investors.

Scope:
- strategic vs tactical asset allocation
- duration and curve positioning
- equity and sector tilts, style factors
- credit risk budget and quality tilt
- scenario-based risk management and hedging approaches

Constraints:
- No personalized advice or product-specific recommendations.
- Focus on frameworks and trade-offs, not tickers.

Focus:
- Translate macro / sector / credit views into high-level portfolio stances
  (more/less duration, more/less credit beta, which risks to be paid vs hedged).
"""


GENERAL_AGENT_PROMPT = """
You are a FINANCE EDUCATOR with institutional-level knowledge.

Scope:
- explain core finance concepts clearly (duration, NII, funding cost, etc.)
- link concepts to how professionals use them in practice.

Output:
- clear definitions
- intuitive explanation / analogy
- professional use cases
- common pitfalls
"""

SYNTH_AGENT_PROMPT = """
You are the LEAD AUTHOR of a professional FINANCE RESEARCH NOTE
at a top-tier global bank or asset manager (e.g., Goldman Sachs, JPMorgan,
Morgan Stanley, BlackRock).

Inputs:
- The user's question,
- Tier-1 analysis tags (macro, sector, credit, portfolio, etc.),
- Tier-2 specializations (e.g., macro_rates, sector_banking, credit_bank, portfolio_rates),
- Individual agent analyses for each dimension,
- A compact data/web context.

Your job:
Synthesize everything into ONE cohesive, client-ready cross-asset note.

Tone:
- Institutional, neutral, analytical.
- No "teaching mode", no basic textbook explanations.
- Avoid repetition; each section should add NEW insight.

Hard constraints:
- NEVER invent specific numbers (rates, spreads, ratios, etc.) that are not in context.
- Prefer directional and qualitative language.
- Be explicit about uncertainty and dependency on assumptions.
- Do NOT give personalized investment advice or product recommendations.

Depth requirements (VERY IMPORTANT):
- Macro: discuss transmission channels (rates → funding costs → credit conditions),
         yield curve shape, policy path, and how "higher for longer" changes incentives.
- Sector (especially banks): discuss NIM drivers, deposit betas, funding mix,
         regulatory capital, and exposure to sensitive asset classes (e.g., CRE).
- Credit: discuss where in the credit cycle we likely are, funding stress channels,
         asset quality risks, and how losses could crystallize on bank balance sheets.
- Portfolio: discuss frameworks (duration risk, credit risk budget, sector tilts,
         hedging approaches) rather than simple "buy/sell" ideas.

Required structure (headings must appear):

1. Executive Summary
   - 3–5 concise bullet points.
   - Each bullet should combine a clear view + the main driver + key risk/uncertainty.

2. Macro Framework and Rate Regime
   - Describe the macro backdrop relevant to the question.
   - Explain the current or assumed rate regime (e.g., "higher for longer").
   - Highlight key transmission channels into banks / markets.

3. Banking / Sector Structure and Profitability
   - For banks: discuss NIM, deposit beta behavior, funding mix (retail vs wholesale),
     fee income vs spread income, and regulatory constraints.
   - Clarify which business models might be more resilient vs more vulnerable.

4. Credit and Balance Sheet Risk
   - Discuss funding cost risks, refinancing risk, asset quality (e.g., CRE, consumer),
     and potential loss channels.
   - Distinguish between idiosyncratic risk (weak banks) and systemic risk.

5. Portfolio and Risk-Management Implications
   - From an institutional investor's perspective:
     - How might they think about duration, credit exposure, and sector tilts?
     - How could they adjust risk budgets or hedging, qualitatively?
   - No specific security picks; emphasize frameworks and trade-offs.

6. Scenario Analysis (Base / Upside / Downside)
   - For each scenario:
     - Describe macro path qualitatively,
     - How banks and credit risk might evolve,
     - High-level portfolio stance (more/less duration, more/less credit risk, etc.).
   - Make scenarios internally consistent.

7. Key Risks, Monitoring, and Open Questions
   - What could invalidate the base case?
   - Which indicators or events should professionals monitor (e.g., funding spreads,
     deposit flows, policy communication, CRE stress indicators)?
   - Explicitly mention model/analysis limitations.

General style:
- Write in well-structured paragraphs with clear topic sentences.
- Avoid repeating the same sentence in multiple sections.
- Prefer "likely", "broadly", "if X then Y" language instead of overconfidence.
"""


# ============================================================
# Tier-2 subtype descriptions (will be injected into prompts)
# ============================================================

MACRO_SUBTYPE_FOCUS = {
    "macro_rates": "Focus specifically on interest rate path, yield curve dynamics, term premium, and the transmission of monetary policy into funding costs and discount rates.",
    "macro_inflation": "Focus specifically on inflation dynamics (CPI, PCE), inflation expectations, and their interaction with policy rates and real yields.",
    "macro_growth": "Focus specifically on growth vs recession risk, labor market conditions, output gaps, and business cycle implications.",
    "macro_liquidity": "Focus specifically on financial conditions, liquidity, funding environment, and how tightening or easing impacts markets and banks.",
    "macro_fx": "Focus specifically on FX dynamics, USD strength, policy divergence across central banks, and global capital flows.",
}

SECTOR_SUBTYPE_FOCUS = {
    "sector_banking": "Focus specifically on the BANKING sector: net interest income, deposit betas, funding mix, regulation (e.g., Basel), and sensitivity to macro conditions.",
    "sector_tech": "Focus specifically on the TECHNOLOGY sector: growth expectations, capex, cost of capital, and sensitivity to discount rates.",
    "sector_energy": "Focus specifically on the ENERGY sector: oil/commodity prices, capex cycle, supply/demand balance, and geopolitical risk.",
    "sector_cre": "Focus specifically on COMMERCIAL REAL ESTATE (CRE): vacancy rates, refinancing risk, property values, and bank/credit linkages.",
    "sector_consumer": "Focus specifically on CONSUMER-related sectors: consumption trends, disposable income, confidence, and credit conditions.",
}

CREDIT_SUBTYPE_FOCUS = {
    "credit_bank": "Focus specifically on BANK CREDIT RISK: funding profile, deposit stability, wholesale funding reliance, capital buffers, and asset quality (e.g., CRE, consumer loans).",
    "credit_corporate": "Focus specifically on CORPORATE CREDIT: leverage, refinancing risk, maturity walls, HY vs IG spreads, and default cycle dynamics.",
    "credit_sovereign": "Focus specifically on SOVEREIGN CREDIT: fiscal sustainability, debt dynamics, yields, and potential stress channels.",
    "credit_liquidity": "Focus specifically on LIQUIDITY & FUNDING stress: market liquidity, dealer balance sheets, margin/funding squeezes, and contagion channels.",
}

PORTFOLIO_SUBTYPE_FOCUS = {
    "portfolio_multiasset": "Focus specifically on MULTI-ASSET allocation: balance across equities, credit, rates, cash, and alternatives under the described environment.",
    "portfolio_rates": "Focus specifically on RATES / DURATION positioning within fixed income portfolios.",
    "portfolio_equity": "Focus specifically on EQUITY portfolio construction: sector tilts, style factors, and regional exposures.",
    "portfolio_credit": "Focus specifically on CREDIT portfolio construction: HY vs IG balance, quality tilt, and spread risk.",
    "portfolio_risk": "Focus specifically on RISK MANAGEMENT: volatility regime, correlation structure, drawdown risk, and stress testing.",
}


# ============================================================
# Context building
# ============================================================

def build_context(question: str, ticker: Optional[str]) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {"ticker": ticker}

    if ticker:
        ctx["profile"] = get_company_profile(ticker)
        ctx["quote"] = get_realtime_quote(ticker)
        ctx["recommendations"] = get_recommendation_trends(ticker)
        ctx["financials"] = get_latest_financials(ticker)
        ctx["news"] = get_company_news(ticker, days=10)
    else:
        ctx["profile"] = {}
        ctx["quote"] = {}
        ctx["recommendations"] = []
        ctx["financials"] = {}
        ctx["news"] = []

    # always include macro/finance web context
    ctx["web_search"] = search_finance_web(
        f"Latest finance / macro / credit information relevant to: {question}",
        max_results=5,
    )
    return ctx


def format_context_for_llm(ctx: Dict[str, Any]) -> str:
    lines: List[str] = []

    ticker = ctx.get("ticker")
    if ticker:
        lines.append(f"[Ticker]: {ticker}")

    profile = ctx.get("profile", {})
    if isinstance(profile, dict) and profile:
        lines.append("\n[Company Profile]")
        for k in ["name", "country", "exchange", "finnhubIndustry"]:
            if k in profile:
                lines.append(f"- {k}: {profile[k]}")

    quote = ctx.get("quote", {})
    if isinstance(quote, dict) and quote.get("c") is not None:
        lines.append("\n[Quote Snapshot]")
        lines.append(f"- Last price: {quote.get('c')}")
        lines.append(f"- Prev close: {quote.get('pc')}")

    fin = ctx.get("financials", {})
    metric = fin.get("metric", {}) if isinstance(fin, dict) else {}
    if metric:
        lines.append("\n[Key Financial Metrics]")
        for k in ["marketCapitalization", "peTTM", "epsTTM"]:
            if k in metric:
                lines.append(f"- {k}: {metric[k]}")

    recs = ctx.get("recommendations", [])
    if isinstance(recs, list) and recs:
        last = recs[0]
        lines.append("\n[Analyst Recommendation Snapshot]")
        for k in ["strongBuy", "buy", "hold", "sell", "strongSell"]:
            if k in last:
                lines.append(f"- {k}: {last[k]}")

    news = ctx.get("news", [])
    if isinstance(news, list) and news:
        lines.append("\n[Recent Company / Sector News (headlines)]")
        for item in news[:5]:
            title = item.get("headline") or item.get("title")
            if title:
                lines.append(f"- {title}")

    web = ctx.get("web_search", [])
    if isinstance(web, list) and web:
        lines.append("\n[Web Search Snapshot (titles)]")
        for w in web[:5]:
            title = w.get("title")
            source = w.get("source") or ""
            if title:
                lines.append(f"- {title} ({source})")

    return "\n".join(lines)


# ============================================================
# Source collection & formatting for citations
# ============================================================

def collect_sources(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect citation sources from context:
    - Tavily web_search results
    - Finnhub company_news (if ticker is provided)
    """
    sources: List[Dict[str, Any]] = []

    # From web_search (Tavily)
    web = ctx.get("web_search", [])
    if isinstance(web, list):
        for item in web:
            title = item.get("title")
            url = item.get("url")
            origin = item.get("source")
            if title:
                sources.append(
                    {
                        "title": title,
                        "url": url,
                        "source": origin or "web",
                    }
                )

    # From company_news (Finnhub)
    news = ctx.get("news", [])
    if isinstance(news, list):
        for item in news:
            title = item.get("headline") or item.get("title")
            url = item.get("url")
            origin = item.get("source") or "news"
            if title:
                sources.append(
                    {
                        "title": title,
                        "url": url,
                        "source": origin,
                    }
                )

    # Deduplicate by (title, url)
    unique: List[Dict[str, Any]] = []
    seen = set()
    for s in sources:
        key = (s.get("title"), s.get("url"))
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


def format_sources_for_report(sources: List[Dict[str, Any]]) -> str:
    """
    Turn collected sources into a markdown "## Sources" section.
    """
    if not sources:
        return ""

    lines: List[str] = []
    lines.append("\n---")
    lines.append("## Sources")

    for idx, s in enumerate(sources, 1):
        title = s.get("title") or "(untitled source)"
        url = s.get("url")
        origin = s.get("source")

        if url:
            if origin:
                lines.append(f"{idx}. {title} — {origin} — {url}")
            else:
                lines.append(f"{idx}. {title} — {url}")
        else:
            if origin:
                lines.append(f"{idx}. {title} — {origin}")
            else:
                lines.append(f"{idx}. {title}")

    return "\n".join(lines)


# ============================================================
# Agent prompt selection (Tier-1 + Tier-2)
# ============================================================

def _get_system_prompt(tier1_tag: str, tier2_subtag: str) -> str:
    """
    Combine Tier-1 base prompt + Tier-2 specialization focus.
    """
    if tier1_tag == "macro":
        base = MACRO_BASE_PROMPT
        focus = MACRO_SUBTYPE_FOCUS.get(tier2_subtag, "")
    elif tier1_tag == "sector":
        base = SECTOR_BASE_PROMPT
        focus = SECTOR_SUBTYPE_FOCUS.get(tier2_subtag, "")
    elif tier1_tag == "credit":
        base = CREDIT_BASE_PROMPT
        focus = CREDIT_SUBTYPE_FOCUS.get(tier2_subtag, "")
    elif tier1_tag == "portfolio":
        base = PORTFOLIO_BASE_PROMPT
        focus = PORTFOLIO_SUBTYPE_FOCUS.get(tier2_subtag, "")
    else:
        return GENERAL_AGENT_PROMPT

    if focus:
        return base + "\n\nTier-2 focus:\n" + focus + "\n"
    else:
        return base


def _run_single_agent(
    tier1_tag: str,
    tier2_subtag: str,
    question: str,
    ctx_text: str,
) -> str:
    """
    Run one specialized agent given Tier-1 + Tier-2 routing.
    """
    system_prompt = _get_system_prompt(tier1_tag, tier2_subtag)

    # Build user prompt
    user_prompt = f"""
User question:
{question}

Tier-1 tag: {tier1_tag}
Tier-2 specialization: {tier2_subtag or "none"}

Structured context (data & web):
{ctx_text}

Instructions:
- Focus ONLY on your specialization area.
- Avoid generic textbook definitions unless absolutely necessary.
- Provide institutional-grade analysis with clear structure and logic.
- Use qualitative terms instead of inventing numbers.
"""

    return call_llm(system_prompt, user_prompt, temperature=0.15)


# ============================================================
# Main multi-agent pipeline
# ============================================================

def run_multiagent_pipeline(question: str, ticker: Optional[str] = None) -> Dict[str, Any]:
    """
    Full V5/V6 pipeline:
    1) Tier-1 routing: macro / sector / credit / portfolio / ...
    2) Tier-2 routing inside each Tier-1 domain.
    3) Context building from data providers.
    4) Run each specialized agent.
    5) Synthesis agent combines all into one professional note.
    6) Wrapper adds summary + risk warning.
    7) Append a Sources section built from underlying data/search context.
    """

    # 1) Tier-1 routing
    tags = route_tags(question)  # e.g. ["macro", "sector", "credit"]

    # 2) Tier-2 routing for relevant domains
    tier2_subtags: Dict[str, str] = {}
    for t in tags:
        if t in {"macro", "sector", "credit", "portfolio"}:
            tier2_subtags[t] = route_tier2(t, question)
        else:
            tier2_subtags[t] = ""

    # 3) Context
    ctx = build_context(question, ticker)
    ctx_text = format_context_for_llm(ctx)

    # 4) Run per-agent analysis
    agent_outputs: Dict[str, str] = {}
    for t in tags:
        agent_outputs[t] = _run_single_agent(t, tier2_subtags.get(t, ""), question, ctx_text)

    # 5) Synthesis agent
    pieces = []
    for t in tags:
        sub = tier2_subtags.get(t, "")
        txt = agent_outputs.get(t, "")
        header = f"[{t.upper()} | {sub}]".strip(" |")
        pieces.append(f"{header}\n{txt}\n")
    agents_block = "\n\n".join(pieces)

    tier2_summary_lines = [f"- {t}: {tier2_subtags.get(t, '') or 'none'}" for t in tags]
    tier2_summary = "\n".join(tier2_summary_lines)

    synth_user_prompt = f"""
User question:
{question}

Tier-1 analysis tags:
{', '.join(tags)}

Tier-2 specializations:
{tier2_summary}

Structured context (data & web):
{ctx_text}

Individual agent analyses:
{agents_block}

Now synthesize everything into ONE cohesive professional finance note
following the required structure (Executive Summary, Macro, Sector,
Credit, Portfolio, Scenarios, Risks & Monitoring).
"""

    raw_final = call_llm(SYNTH_AGENT_PROMPT, synth_user_prompt, temperature=0.15)

    # 6) Wrap with Summary + Risk Warning (your existing helper)
    wrapped = wrap_final_answer(raw_final)

    # 7) Build Sources section from context (web_search + news)
    sources = collect_sources(ctx)
    sources_section = format_sources_for_report(sources)

    answer_with_sources = wrapped + sources_section

    return {
        "tags": tags,
        "tier2_subtags": tier2_subtags,
        "context": ctx,
        "agent_outputs": agent_outputs,
        "raw_final": raw_final,
        "answer": answer_with_sources,
        "sources": sources,  # optional, for UI to render clickable list
    }
