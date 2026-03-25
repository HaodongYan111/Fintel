# router.py
from typing import List
from llm import call_llm

ALLOWED_TAGS = [
    "macro",
    "sector",
    "credit",
    "portfolio",
    "single_stock",
    "multi_stock",
    "general",
]

ROUTER_SYSTEM_PROMPT = """
You are an institutional-grade FINANCE ROUTING MODEL.

Your goal:
Given a user's question, return ALL applicable analysis tags.
Return a comma-separated list (no explanation).

==================================================================
DETECTION RULES (STRONG VERSION)
==================================================================

1. MACRO  → ALWAYS include if question mentions:
   - interest rates (“higher-for-longer”, cuts, hikes, Fed)
   - inflation, CPI, PCE
   - recession, growth slowdown, macro conditions
   - monetary policy, central bank decisions
   - broad economy, liquidity, funding environment

2. SECTOR  → include if question mentions:
   - an industry (e.g., banks, tech, energy, CRE)
   - commercial real estate (CRE)
   - financial system stability, bank behavior, lending

3. CREDIT  → include if question mentions:
   - funding structure / funding cost
   - credit risk / credit cycle
   - asset quality / NPL
   - wholesale funding / deposit flight
   - capital ratios, solvency, financial stability

4. PORTFOLIO  → include if question mentions:
   - asset allocation
   - portfolio construction
   - exposure management
   - risk positioning
   - implications for investors

5. SINGLE_STOCK or MULTI_STOCK:
   - ONLY if user explicitly asks about specific ticker(s).
   - If question is about “banks” or “financials” as a whole → NOT stock tags.

6. GENERAL:
   - Use ONLY if the question is purely definitional (“What is duration?”).

==================================================================
CRITICAL RULE:
If the question includes macro drivers AND a sector AND credit words,
you MUST output: “macro, sector, credit”.

==================================================================
Output format:
Return only tags, comma-separated.
Example:  macro, sector, credit
Do NOT explain.
"""

def route_tags(question: str) -> List[str]:
    raw = call_llm(ROUTER_SYSTEM_PROMPT, question, temperature=0.0)

    parts = [p.strip().lower() for p in raw.replace("\n", ",").split(",")]

    tags = [p for p in parts if p in ALLOWED_TAGS]

    if not tags:
        return ["general"]

    seen = set()
    ordered = []
    for t in tags:
        if t not in seen:
            ordered.append(t)
            seen.add(t)

    return ordered
