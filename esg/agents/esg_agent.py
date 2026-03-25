# agents/esg_agent.py
from __future__ import annotations

"""
ESGAgent
========

High-level responsibilities
---------------------------
1. Take **bank-specific context blob** (PDF summary + Yahoo snapshot + news).
2. Ask the local LLM to:
   - write a short supervisory-style analysis; and
   - produce a strict JSON object with **rubric-level categorical ratings**
     (climate_plan, emission_disclosure, board_independence, etc.).
3. Parse the JSON safely.
4. Pass it through :class:`ScoreEngine` to obtain stable integer scores
   and detailed sub-scores for the UI.

This file intentionally contains **no network access** – all data fetching
is handled by :mod:`server` and the various tools under ``tools/``.
"""

from typing import Any, Dict, Optional, Tuple
import json
import re

from tools.score_engine import ScoreEngine

try:  # optional, only used to enrich the prompt if available
    from tools.dutch_banks import get_bank_metadata
except Exception:  # pragma: no cover - defensive fallback
    get_bank_metadata = None  # type: ignore


class ESGAgent:
    """
    LLM-based ESG analysis agent.

    Parameters
    ----------
    llm :
        Any object exposing ``ask(prompt: str, bank_name=None, question=None, pdf_text=None) -> str``.
        In your project this is implemented by :class:`LocalLLM` in ``tools/local_llm.py``.
    engine : ScoreEngine, optional
        Deterministic numeric scoring engine.  If omitted, a fresh one is created.
    """

    def __init__(self, llm, engine: Optional[ScoreEngine] = None) -> None:
        self.llm = llm
        self.engine = engine or ScoreEngine()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def run(
        self,
        bank: str,
        year: Optional[str],
        question: Optional[str],
        context_blob: str,
    ) -> Dict[str, Any]:
        """
        Run the full ESG pipeline for a single bank.

        Parameters
        ----------
        bank : str
            Bank name (canonical if possible).
        year : str, optional
            Year or reporting period.
        question : str, optional
            User focus question (e.g. "Which bank is best prepared for CSRD?").
        context_blob : str
            Bank-specific evidence text assembled by :class:`Server`.

        Returns
        -------
        dict
            {
              "bank": bank,
              "analysis_text": str,
              "categories": dict,  # rubric categories (strings)
              "scores": dict       # output of ScoreEngine.from_categories(...)
            }
        """
        prompt = self._build_prompt(bank=bank, year=year, question=question, evidence=context_blob)
        raw = self.llm.ask(prompt, bank_name=bank, question=question, pdf_text=context_blob)

        analysis_text, categories = self._split_analysis_and_categories(raw)
        scores = self.engine.from_categories(categories, bank=bank)

        return {
            "bank": bank,
            "analysis_text": analysis_text,
            "categories": categories,
            "scores": scores,
        }

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------
    def _build_prompt(self, bank: str, year: Optional[str], question: Optional[str], evidence: str) -> str:
        meta_block = ""
        if get_bank_metadata is not None:
            try:
                meta = get_bank_metadata(bank) or {}
            except Exception:
                meta = {}
            if meta:
                meta_lines = [f"- {k}: {v}" for k, v in meta.items() if v]
                if meta_lines:
                    meta_block = "Known static metadata about the bank:\n" + "\n".join(meta_lines)

        year_text = year or "latest available period"
        focus = question.strip() if question else "overall ESG risk profile and transition credibility"

        # 关键：只要 rubric 字段，不要 E/S/G 数值
        return f"""
You are a senior EU sustainability supervisor (EBA/ECB/CSRD).

Your task is to assess the ESG profile of the bank below using ONLY the evidence
that follows. You MUST NOT invent facts. If data is missing or weak, you should
downgrade the categories conservatively.

Bank: {bank}
Assessment period: {year_text}
User focus: {focus}

{meta_block}

==================== EVIDENCE (bank-specific) ====================
The following text is all the evidence you have for this bank, compiled from:
- Official annual / sustainability / CSRD reports (summarised);
- Yahoo Finance business profile and risk hints;
- ESG / regulatory news headlines.

Read it carefully and use it as the ONLY basis for your judgement.

{evidence}
===============================================================

RUBRIC CLASSIFICATION
---------------------
You must classify the bank on the following discrete categories.
Pick exactly ONE value from the allowed options for each key:

Environmental (E):
- "climate_plan":        one of ["none", "weak", "science_based", "sbt_aligned"]
- "emission_disclosure": one of ["none", "scope1", "scope1_2", "scope1_2_3"]
- "financed_emissions":  one of ["none", "partial", "pcaf_full"]
- "taxonomy_alignment":  one of ["none", "low", "medium", "high", "aligned"]
- "risk_management":     one of ["none", "weak", "partial", "full", "strong"]
- "fossil_policy":       one of ["none", "weak", "partial", "strong", "exit"]

Social (S):
- "diversity_inclusion": one of ["none", "partial", "full"]
- "labor_rights":        one of ["none", "weak", "medium", "strong"]
- "customer_protection": one of ["fined", "building", "mature"]
- "aml_maturity":        one of ["fined", "weak", "building", "mature", "leading"]

Governance (G):
- "board_independence":  one of ["<33", "33_50", ">=50"]
- "esg_oversight":       one of ["none", "csr_dept", "board_committee"]
- "exec_comp_esg":       one of ["none", "<20", ">=20"]
- "transparency_csrd":   one of ["non_compliant", "partial", "full"]

If the evidence is ambiguous or weak, you MUST choose the more conservative
(weaker) option.

Output requirements
-------------------
1. First, write a short narrative analysis (max ~300 words) in plain English,
   in the voice of a prudent EU supervisor. Comment on E/S/G strengths,
   weaknesses, transition risks and data quality.
2. Then on a NEW LINE, output a single JSON object ONLY (no backticks, no commentary)
   with exactly these keys and string values:

{{
  "climate_plan":        "...",
  "emission_disclosure": "...",
  "financed_emissions":  "...",
  "taxonomy_alignment":  "...",
  "risk_management":     "...",
  "fossil_policy":       "...",
  "diversity_inclusion": "...",
  "labor_rights":        "...",
  "customer_protection": "...",
  "aml_maturity":        "...",
  "board_independence":  "...",
  "esg_oversight":       "...",
  "exec_comp_esg":       "...",
  "transparency_csrd":   "..."
}}

Do NOT include numeric E/S/G scores in the JSON.
The scoring engine will convert these categories into 0–100 pillar scores
and detailed rubric sub-scores.
"""

    # ------------------------------------------------------------------
    # Output parsing helpers
    # ------------------------------------------------------------------
    def _split_analysis_and_categories(self, raw: str) -> Tuple[str, Dict[str, Any]]:
        """
        Split the LLM output into:
          - free-form analysis text
          - parsed JSON categories dict
        """
        raw = (raw or "").strip()
        if not raw:
            return "", {}

        # Find the last JSON object in the text
        json_obj = None
        json_text = ""
        last_open = raw.rfind("{")
        last_close = raw.rfind("}")
        if last_open != -1 and last_close != -1 and last_close > last_open:
            candidate = raw[last_open : last_close + 1]
            try:
                json_obj = json.loads(candidate)
                json_text = candidate
            except Exception:
                json_obj = None

        if json_obj is None:
            # Fallback: try first JSON-like block
            m = re.search(r"\\{.*\\}", raw, flags=re.DOTALL)
            if m:
                candidate = m.group(0)
                try:
                    json_obj = json.loads(candidate)
                    json_text = candidate
                except Exception:
                    json_obj = None

        if json_obj is None:
            # No valid JSON found
            return raw, {}

        analysis = raw.replace(json_text, "").strip()
        if not analysis:
            analysis = raw.strip()

        if not isinstance(json_obj, dict):
            json_obj = {}

        return analysis, json_obj
