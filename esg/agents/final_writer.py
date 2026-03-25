# agents/final_writer.py
from __future__ import annotations

from typing import Dict, Any, Optional, List


class FinalWriterAgent:
    """
    Produces a polished, audit-grade ESG report.

    Inputs
    ------
    bank : str
        Bank name.
    analysis_text : str
        LLM ESG analysis narrative (from ESGAgent).
    scores : dict
        ScoreEngine output, with integer ESG pillar scores and rubric sub-scores.
    news_summary : str
        ESG news signals summary (optional).
    """

    def __init__(self, llm) -> None:
        self.llm = llm

    def _build_prompt(
        self,
        bank: str,
        analysis_text: str,
        scores: Dict[str, Any],
        news_summary: str = "",
    ) -> str:
        pillar = scores.get("pillar_scores", {}) or {}
        sub = scores.get("sub_scores", {}) or {}

        E = int(round(float(pillar.get("E", scores.get("E", 0)) or 0)))
        S = int(round(float(pillar.get("S", scores.get("S", 0)) or 0)))
        G = int(round(float(pillar.get("G", scores.get("G", 0)) or 0)))
        final = int(round(float(scores.get("final", 0) or 0)))
        label = scores.get("label", "N/A")

        env_rows = []
        for name, val in (sub.get("E", {}) or {}).items():
            env_rows.append(f"| {name} | {int(round(float(val or 0)))} |")

        soc_rows = []
        for name, val in (sub.get("S", {}) or {}).items():
            soc_rows.append(f"| {name} | {int(round(float(val or 0)))} |")

        gov_rows = []
        for name, val in (sub.get("G", {}) or {}).items():
            gov_rows.append(f"| {name} | {int(round(float(val or 0)))} |")

        env_table = "\n".join(["| Indicator | Score |", "|----------|-------|"] + env_rows) if env_rows else "N/A"
        soc_table = "\n".join(["| Indicator | Score |", "|----------|-------|"] + soc_rows) if soc_rows else "N/A"
        gov_table = "\n".join(["| Indicator | Score |", "|----------|-------|"] + gov_rows) if gov_rows else "N/A"

        news_block = news_summary.strip() or "No dedicated ESG news summary provided; rely on underlying analysis."

        return f"""
You are an ESG reporting specialist at a European financial supervisor.

Write a concise but professional ESG intelligence report for **{bank}**,
using the analysis, scores and rubric tables below.

The report will be consumed by risk managers and senior supervisors.
It should be factual, neutral, and clearly structured.

================== RAW ANALYSIS (FROM ESGAgent) ==================
{analysis_text}

================== NUMERIC SCORES (FROM ScoreEngine) =============
- Environmental (E): {E} / 100
- Social (S): {S} / 100
- Governance (G): {G} / 100
- Final ESG Score: {final} / 100   (Label: {label})

Environmental rubric sub-scores:
{env_table}

Social rubric sub-scores:
{soc_table}

Governance rubric sub-scores:
{gov_table}

================== ESG NEWS SIGNALS (IF ANY) =====================
{news_block}

================== TASK =========================================
Using all the information above, write the final ESG intelligence report in markdown.

Structure:
1. **Executive Summary**
   - 2–3 sentences summarising overall ESG profile and main risks.
2. **Environmental (E) Analysis**
   - Climate transition plan credibility (SBTi, targets, fossil policy)
   - Emissions disclosure & financed emissions coverage
   - EU Taxonomy alignment and climate risk management
3. **Social (S) Analysis**
   - AML/KYC maturity, customer protection & conduct risk
   - Labor practices, diversity & inclusion, community outcomes
4. **Governance (G) Analysis**
   - Board independence & ESG oversight
   - Executive remuneration alignment with ESG
   - Transparency (CSRD/SFDR) and risk/audit governance
5. **Regulatory Readiness & Outlook**
   - CSRD/SFDR readiness, key upcoming gaps or milestones
   - Short bullet list of supervisory focus points (3–5 bullets)

Requirements:
- Be specific: reference concrete signals (e.g. "Scope 1–3 disclosed", "SBTi validated", "subject to climate lawsuit").
- Avoid marketing language.
- Keep length within ~800–1200 words.
- Use markdown headings and bullet points for readability.
"""

    def run(
        self,
        bank: str,
        analysis_text: str,
        scores: Dict[str, Any],
        news_summary: str = "",
    ) -> str:
        prompt = self._build_prompt(
            bank=bank,
            analysis_text=analysis_text,
            scores=scores,
            news_summary=news_summary,
        )
        return self.llm.ask(prompt)
