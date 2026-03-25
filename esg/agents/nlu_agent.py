from __future__ import annotations

import re
from typing import Optional, Dict, Any, List


class NLUAgent:
    """
    Natural Language Understanding Agent.
    Extracts:
      - bank name (if user overrides)
      - year or year range
      - ESG focus areas
      - user intent
      - clean question to forward to ESG agent
    """

    def __init__(self, llm):
        self.llm = llm

    # -------------------------
    # 1. Regex helper: extract year(s)
    # -------------------------
    def _extract_year(self, text: str) -> Optional[str]:
        if not text:
            return None

        # Range like 2020-2023
        m = re.search(r"(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}", text)
        if m:
            yr = m.group(0).replace(" ", "")
            return yr

        # Single year
        m = re.search(r"(19|20)\d{2}", text)
        if m:
            return m.group(0)

        return None

    # -------------------------
    # 2. Regex helper: extract possible bank
    # -------------------------
    def _extract_bank_candidate(self, text: str) -> Optional[str]:
        if not text:
            return None

        # Capture capitalized word sequences (ING, ABN AMRO, etc.)
        candidates = re.findall(r"[A-Za-z][A-Za-z\s&\-]{1,30}", text)

        if not candidates:
            return None

        # Return best guess (LLM will refine)
        longest = max(candidates, key=len)
        return longest.strip()

    # -------------------------
    # 3. Build LLM prompt
    # -------------------------
    def _build_prompt(self, user_question: str) -> str:
        return f"""
You are an NLU (Natural Language Understanding) extraction model.

User question:
\"\"\"{user_question}\"\"\"

Extract the following fields in STRICT JSON:

{{
  "bank_override":  (null or exact bank name),
  "year":           (null or "2023" or "2020-2024"),
  "focus":          (null or short comma-separated keywords),
  "intent":         ("single-esg" | "compare" | "controversy" | "regulatory" | "scoring" | "financial" | "general"),
  "clean_question": (short clean summary of the user's real question)
}}

Rules:
- DO NOT invent nonexistent banks.
- "bank_override" is null unless user explicitly names a bank.
- "focus" must be a comma-separated list of short ESG topics.
- Keep output minimal and machine-friendly.
- The "clean_question" must be 1–2 short sentences, no fluff.
"""

    # -------------------------
    # 4. Main entry
    # -------------------------
    def run(self, user_question: str) -> Dict[str, Any]:
        if not user_question or not user_question.strip():
            return {
                "bank_override": None,
                "year": None,
                "focus": None,
                "intent": "general",
                "clean_question": None,
            }

        # Basic regex first
        regex_year = self._extract_year(user_question)
        regex_bank = self._extract_bank_candidate(user_question)

        # LLM extraction
        prompt = self._build_prompt(user_question)
        llm_json = self.llm.ask(prompt).strip()

        # Ensure valid JSON (fallback)
        try:
            import json
            data = json.loads(llm_json)
        except Exception:
            # Fallback minimal
            data = {
                "bank_override": regex_bank,
                "year": regex_year,
                "focus": None,
                "intent": "general",
                "clean_question": user_question.strip(),
            }

        # Merge regex fallback
        if not data.get("year"):
            data["year"] = regex_year
        if not data.get("bank_override"):
            data["bank_override"] = regex_bank

        return data
