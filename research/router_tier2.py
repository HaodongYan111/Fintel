# router_tier2.py
from llm import call_llm

MACRO_SUBTAGS = [
    "macro_rates",
    "macro_inflation",
    "macro_growth",
    "macro_liquidity",
    "macro_fx",
]

SECTOR_SUBTAGS = [
    "sector_banking",
    "sector_tech",
    "sector_energy",
    "sector_cre",
    "sector_consumer"
]

CREDIT_SUBTAGS = [
    "credit_bank",
    "credit_corporate",
    "credit_sovereign",
    "credit_liquidity"
]

PORTFOLIO_SUBTAGS = [
    "portfolio_multiasset",
    "portfolio_rates",
    "portfolio_equity",
    "portfolio_credit",
    "portfolio_risk"
]

TIER2_SYSTEM_PROMPT = """
You are a Tier-2 institutional FINANCE router.

Given a user question AND a Tier-1 tag, classify the question further into ONE subtype.
Do NOT output anything else.

======================
MACRO → choose:
----------------------
macro_rates        → rate path, yield curve, duration, monetary policy
macro_inflation    → CPI, PCE, inflation dynamics, price stability
macro_growth       → recession/soft landing, GDP, labor market
macro_liquidity    → liquidity conditions, funding environment, FCI
macro_fx           → USD strength, currency divergence, global flows

======================
SECTOR → choose:
----------------------
sector_banking     → banks, NIM, deposits, regulation, risk
sector_tech        → technology, AI, capex, valuation
sector_energy      → oil, commodities, OPEC, energy cycle
sector_cre         → commercial real estate, housing, cap rates
sector_consumer    → retail, consumption, services

======================
CREDIT → choose:
----------------------
credit_bank        → bank funding, deposit flight, asset quality
credit_corporate   → HY/IG credit spreads, refinancing, leverage
credit_sovereign   → government debt, yield risk, fiscal stability
credit_liquidity   → liquidity stress, wholesale funding risk

======================
PORTFOLIO → choose:
----------------------
portfolio_multiasset → broad asset allocation frameworks
portfolio_rates       → duration, fixed-income strategy
portfolio_equity      → sector weights, factors, style tilts
portfolio_credit      → HY/IG allocation, credit premium
portfolio_risk        → risk regime, correlation, stress tests

Rule:
Output only 1 subtype for each Tier-1 input.
No explanation.
"""


def route_tier2(tier1_tag: str, question: str) -> str:
    """Return one subtype for the given Tier-1 tag."""
    if tier1_tag == "macro":
        domain = "MACRO"
    elif tier1_tag == "sector":
        domain = "SECTOR"
    elif tier1_tag == "credit":
        domain = "CREDIT"
    elif tier1_tag == "portfolio":
        domain = "PORTFOLIO"
    else:
        return ""

    prompt = f"""
Tier-1 tag: {tier1_tag}
Domain: {domain}

User question:
{question}

Select ONE subtype from the domain.
Return only the subtype.
"""

    raw = call_llm(TIER2_SYSTEM_PROMPT, prompt, temperature=0.0)
    return raw.strip()
