# tools/score_engine.py
"""
Numeric ESG scoring engine (Hybrid: supports both LLM direct scores and Rubric calculation).

Updates:
- Detects if input is already integer scores (E/S/G) and passes them through.
- Generates dummy sub-scores for UI compatibility when using direct LLM scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class ScoreEngineConfig:
    # pillar weights (35/30/35)
    w_E: float = 0.35
    w_S: float = 0.30
    w_G: float = 0.35


class ScoreEngine:
    VERSION = "v3.0-hybrid"

    def __init__(self, cfg: ScoreEngineConfig | None = None) -> None:
        self.cfg = cfg or ScoreEngineConfig()

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    @staticmethod
    def _safe_str(x: Any) -> str:
        if x is None:
            return ""
        return str(x).strip()

    @staticmethod
    def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
        if x < lo:
            return lo
        if x > hi:
            return hi
        return x

    @staticmethod
    def _weighted_avg(items: Tuple[Tuple[float, float], ...]) -> float:
        """items = ((score, weight), ...)"""
        den = sum(w for _, w in items)
        if den <= 0:
            return 0.0
        num = sum(s * w for s, w in items)
        return num / den

    # ------------------------------------------------------------
    # Mapping Logic (Used for Fallback / Rubric mode)
    # ------------------------------------------------------------
    def _map_env(self, cats: Dict[str, str]) -> Dict[str, float]:
        climate_plan = self._safe_str(cats.get("climate_plan"))
        emission_disclosure = self._safe_str(cats.get("emission_disclosure"))
        financed_emissions = self._safe_str(cats.get("financed_emissions"))
        taxonomy_alignment = self._safe_str(cats.get("taxonomy_alignment"))
        risk_management = self._safe_str(cats.get("risk_management"))

        # Fallback values
        climate_plan_score = {"none": 10, "weak": 40, "science_based": 75, "sbt_aligned": 90}.get(climate_plan, 40)
        emission_score = {"none": 5, "scope1": 40, "scope1_2": 70, "scope1_2_3": 90}.get(emission_disclosure, 40)
        financed_emissions_score = {"none": 10, "partial": 60, "pcaf_full": 85}.get(financed_emissions, 60)
        taxonomy_score = {"none": 20, "low": 45, "medium": 65, "high": 80, "aligned": 90}.get(taxonomy_alignment, 45)
        risk_mgmt_score = {"none": 20, "weak": 45, "partial": 60, "full": 75, "strong": 90}.get(risk_management, 60)

        # Optional extras
        fossil_policy = self._safe_str(cats.get("fossil_policy"))
        fossil_score = {"none": 20, "weak": 40, "partial": 60, "strong": 80, "exit": 90}.get(fossil_policy, 60)

        sub_items = (
            (climate_plan_score, 0.20),
            (emission_score, 0.20),
            (financed_emissions_score, 0.20),
            (taxonomy_score, 0.15),
            (risk_mgmt_score, 0.15),
            (fossil_score, 0.10),
        )
        E = self._clamp(self._weighted_avg(sub_items))

        env_sub = {
            "Climate transition plan": climate_plan_score,
            "Emissions disclosure": emission_score,
            "Financed emissions": financed_emissions_score,
            "EU Taxonomy alignment": taxonomy_score,
            "Risk management": risk_mgmt_score,
            "Fossil policy": fossil_score,
        }
        return {"E": E, "env_sub": env_sub}

    def _map_soc(self, cats: Dict[str, str]) -> Dict[str, float]:
        diversity = self._safe_str(cats.get("diversity_inclusion"))
        labor = self._safe_str(cats.get("labor_rights"))
        customer = self._safe_str(cats.get("customer_protection"))
        aml = self._safe_str(cats.get("aml_maturity"))

        di_score = {"none": 20, "partial": 55, "full": 80}.get(diversity, 55)
        labor_score = {"none": 20, "weak": 45, "medium": 65, "strong": 85}.get(labor, 65)
        cust_score = {"fined": 30, "building": 60, "mature": 80}.get(customer, 60)
        aml_score = {"fined": 25, "weak": 40, "building": 60, "mature": 75, "leading": 90}.get(aml, 60)

        sub_items = ((di_score, 0.25), (labor_score, 0.25), (cust_score, 0.25), (aml_score, 0.25))
        S = self._clamp(self._weighted_avg(sub_items))

        soc_sub = {
            "Diversity & Inclusion": di_score,
            "Labor Rights": labor_score,
            "Customer Protection": cust_score,
            "AML Maturity": aml_score,
        }
        return {"S": S, "soc_sub": soc_sub}

    def _map_gov(self, cats: Dict[str, str]) -> Dict[str, float]:
        board = self._safe_str(cats.get("board_independence"))
        oversight = self._safe_str(cats.get("esg_oversight"))
        comp = self._safe_str(cats.get("exec_comp_esg"))
        transparency = self._safe_str(cats.get("transparency_csrd"))

        board_score = {"<33": 45, "33_50": 65, ">=50": 80}.get(board, 65)
        oversight_score = {"none": 30, "csr_dept": 60, "board_committee": 80}.get(oversight, 60)
        comp_score = {"none": 40, "<20": 60, ">=20": 80}.get(comp, 60)
        trans_score = {"non_compliant": 30, "partial": 60, "full": 80}.get(transparency, 60)

        sub_items = ((board_score, 0.25), (oversight_score, 0.25), (comp_score, 0.25), (trans_score, 0.25))
        G = self._clamp(self._weighted_avg(sub_items))

        gov_sub = {
            "Board Independence": board_score,
            "ESG Oversight": oversight_score,
            "Executive Comp": comp_score,
            "CSRD Transparency": trans_score,
        }
        return {"G": G, "gov_sub": gov_sub}

    # ------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------
    def from_categories(self, cats: Dict[str, Any], bank: str | None = None) -> Dict[str, Any]:
        """
        Smart entry point:
        1. Checks if input is DIRECT SCORES from LLM (Integers E/S/G).
        2. If not, falls back to RUBRIC MAPPING (Strings -> Integers).
        """
        cats = cats or {}

        # --- PATH A: DIRECT LLM SCORES ---
        # If the LLM returned specific numeric keys, trust them.
        # Check if "E" exists and is a number/numeric-string
        has_direct_scores = False
        try:
            if "E" in cats and "S" in cats and "G" in cats:
                # Basic check to see if they look like numbers
                float(cats["E"])
                has_direct_scores = True
        except:
            has_direct_scores = False

        if has_direct_scores:
            # Trust the LLM's judgment
            E = float(cats["E"])
            S = float(cats["S"])
            G = float(cats["G"])
            
            # Recalculate Final to ensure math consistency (35/30/35)
            final = self.cfg.w_E * E + self.cfg.w_S * S + self.cfg.w_G * G
            
            # Generate PLACEHOLDER sub-scores so the UI table isn't empty
            # This is crucial for app_v2.py to not crash or show blanks
            env_sub = {"Aggregate LLM Environmental Score": int(E)}
            soc_sub = {"Aggregate LLM Social Score": int(S)}
            gov_sub = {"Aggregate LLM Governance Score": int(G)}

            # Also check if LLM provided extra context like controversy
            controversy = float(cats.get("Controversy", 0))
            
            # Apply slight penalty to final if controversy is high (optional)
            if controversy > 50:
                final = final - (controversy * 0.1)

        else:
            # --- PATH B: RUBRIC CALCULATION (Fallback / Old Prompt) ---
            # Map strings (weak/strong) to numbers
            env_res = self._map_env(cats)
            soc_res = self._map_soc(cats)
            gov_res = self._map_gov(cats)

            E = env_res["E"]
            S = soc_res["S"]
            G = gov_res["G"]
            
            env_sub = env_res["env_sub"]
            soc_sub = soc_res["soc_sub"]
            gov_sub = gov_res["gov_sub"]

            final = self.cfg.w_E * E + self.cfg.w_S * S + self.cfg.w_G * G

        # --- Final Formatting ---
        final = float(self._clamp(final))
        
        if final >= 75:
            label = "Meet"
        elif final >= 50:
            label = "Almost Meet"
        else:
            label = "Not Meet"

        sub_scores = {
            "E": {k: int(round(v)) for k, v in env_sub.items()},
            "S": {k: int(round(v)) for k, v in soc_sub.items()},
            "G": {k: int(round(v)) for k, v in gov_sub.items()},
        }

        result = {
            "E": int(round(E)),
            "S": int(round(S)),
            "G": int(round(G)),
            "final": int(round(final)),
            "FINAL": int(round(final)),
            "label": label,
            "pillar_scores": {"E": int(round(E)), "S": int(round(S)), "G": int(round(G))},
            "sub_scores": sub_scores,
            "engine_version": self.VERSION,
        }
        return result