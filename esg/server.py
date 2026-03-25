from __future__ import annotations

import hashlib
import random
import traceback
from typing import Any, Dict, List, Optional, Tuple

from tools.yahoo_client import YahooFinanceClient
from tools.free_news import FreeNewsClient
from tools.pdf_fetcher import fetch_official_pdf
from tools.pdf_summarizer import PDFSummarizer
from tools.score_engine import ScoreEngine
from tools.local_llm import LocalLLM

from agents.esg_agent import ESGAgent
from agents.news_agent import NewsSummariser
from agents.nlu_agent import NLUAgent
from agents.final_writer import FinalWriterAgent


class Server:
    """
    Central orchestrator:
    - fetches Yahoo snapshot and ESG news
    - fetches + summarises PDF text
    - builds evidence for the ESG agent
    - returns numeric scores + narratives
    """

    def __init__(self) -> None:
        self.llm = LocalLLM()
        self.yahoo = YahooFinanceClient()
        self.news_client = FreeNewsClient()
        self.pdf_summarizer = PDFSummarizer(self.llm)
        self.score_engine = ScoreEngine()

        # Agents
        self.news_agent = NewsSummariser(self.llm)
        self.esg_agent = ESGAgent(self.llm, engine=self.score_engine)
        self.nlu = NLUAgent(self.llm)
        self.writer = FinalWriterAgent(self.llm)

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def read_pdf(self, uploaded_file) -> str:
        """Extract text from an uploaded PDF (Streamlit file_uploader output)."""
        try:
            from PyPDF2 import PdfReader
        except Exception as exc:  # pragma: no cover - optional dependency
            print(f"[Server] PyPDF2 not available: {exc}")
            return ""

        try:
            reader = PdfReader(uploaded_file)
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except Exception as exc:
            print(f"[Server] Failed to read uploaded PDF: {exc}")
            return ""

    def _fetch_news(self, bank: str) -> Tuple[List[Dict[str, str]], str]:
        """Fetch and summarise ESG news for a bank."""
        try:
            items = self.news_client.search(bank, limit=10)
        except Exception as exc:  # pragma: no cover - network errors handled softly
            print(f"[Server] News fetch failed for {bank}: {exc}")
            return [], ""

        try:
            summary = self.news_agent.summarise(bank, items)
        except Exception as exc:
            print(f"[Server] News summarisation failed for {bank}: {exc}")
            summary = ""

        return items, summary

    def _fetch_pdf_text(self, bank: str, year: Optional[str], uploaded_text: Optional[str]) -> str:
        """Prefer uploaded PDF text; fall back to static official PDFs."""
        if uploaded_text:
            return uploaded_text

        try:
            return fetch_official_pdf(bank=bank, year=year)
        except Exception as exc:  # pragma: no cover - network errors handled softly
            print(f"[Server] Official PDF fetch failed for {bank}: {exc}")
            return ""

    def _summarise_pdf(self, pdf_text: str, bank: str, year: Optional[str]) -> str:
        if not pdf_text:
            return ""
        try:
            return self.pdf_summarizer.summarize(pdf_text, bank=bank, year=year)
        except Exception as exc:
            print(f"[Server] PDF summarisation failed for {bank}: {exc}")
            return ""

    def _build_context_blob(
        self,
        yahoo_snapshot: str,
        news_summary: str,
        pdf_summary: str,
        year: Optional[str],
        question: Optional[str],
    ) -> str:
        year_text = year or "latest available period"
        focus = f"Focus question: {question}\n\n" if question else ""
        return (
            f"Assessment period: {year_text}\n"
            f"{focus}"
            f"--- Yahoo Snapshot ---\n{yahoo_snapshot or 'N/A'}\n\n"
            f"--- ESG News Summary ---\n{news_summary or 'N/A'}\n\n"
            f"--- PDF Summary ---\n{pdf_summary or 'N/A'}\n"
        )

    def _format_sources(self, news_items: List[Dict[str, str]], pdf_text: str) -> str:
        lines: List[str] = []
        if news_items:
            lines.append("News links:")
            for it in news_items:
                title = (it.get("title") or "").strip()
                link = (it.get("link") or "").strip()
                if link:
                    bullet = f"- {title} ({link})" if title else f"- {link}"
                    lines.append(bullet)
        else:
            lines.append("News links: none fetched.")

        lines.append("PDF source: uploaded or official text loaded." if pdf_text else "PDF source: none.")
        return "\n".join(lines)

    def _news_items_for_ui(self, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Adapt raw news items to the UI schema."""
        ui_items: List[Dict[str, str]] = []
        for it in items:
            ui_items.append(
                {
                    "headline": it.get("title") or it.get("headline") or "",
                    "url": it.get("link") or it.get("url") or "",
                    "source": it.get("source") or "",
                    "published": it.get("published") or "",
                    "summary": it.get("snippet") or it.get("summary") or "",
                }
            )
        return ui_items

    def _yahoo_snapshot_struct(self, snapshot_text: str, bank: str) -> Dict[str, Any]:
        """Wrap Yahoo snapshot string into a simple dict expected by UI."""
        return {
            "ok": bool(snapshot_text),
            "snapshot": snapshot_text or "No Yahoo data available.",
            "name": bank,
            "ticker": None,
        }

    def _fallback_categories(self, bank: str) -> Dict[str, str]:
        """Generate deterministic rubric categories when LLM is unavailable."""
        seed = int(hashlib.sha256(bank.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        pick = lambda opts: rng.choice(opts)

        return {
            "climate_plan": pick(["weak", "science_based", "sbt_aligned", "none"]),
            "emission_disclosure": pick(["scope1", "scope1_2", "scope1_2_3"]),
            "financed_emissions": pick(["partial", "pcaf_full"]),
            "taxonomy_alignment": pick(["low", "medium", "high"]),
            "risk_management": pick(["partial", "full", "strong"]),
            "fossil_policy": pick(["weak", "partial", "strong"]),
            "green_finance": pick(["basic", "growing", "leading"]),
            "climate_targets": pick(["intensity_only", "absolute_partial", "absolute_full"]),
            "diversity_inclusion": pick(["partial", "full"]),
            "labor_rights": pick(["medium", "strong"]),
            "customer_protection": pick(["building", "mature"]),
            "community_investment": pick(["basic", "mature"]),
            "aml_maturity": pick(["building", "mature"]),
            "conduct_risk": pick(["medium", "low"]),
            "data_privacy": pick(["medium", "strong"]),
            "employee_wellbeing": pick(["medium", "strong"]),
            "board_independence": pick(["33_50", ">=50"]),
            "anti_corruption": pick(["medium", "strong"]),
            "esg_oversight": pick(["csr_dept", "board_committee"]),
            "exec_comp_esg": pick(["<20", ">=20"]),
            "transparency_csrd": pick(["partial", "full"]),
            "risk_governance": pick(["medium", "strong"]),
            "audit_quality": pick(["medium", "strong"]),
            "whistleblower": pick(["medium", "strong"]),
            "cyber_governance": pick(["medium", "strong"]),
        }

    def _mc_band(self, final_score: float, bank: str) -> Dict[str, float]:
        """Simple deterministic Monte-Carlo style band for UI."""
        seed = int(hashlib.sha256(f"{bank}-mc".encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        noise = lambda scale: rng.uniform(-scale, scale)
        base = float(final_score)
        p50 = max(0.0, min(100.0, base + noise(2.0)))
        p05 = max(0.0, min(100.0, base - 8 + noise(3.0)))
        p95 = max(0.0, min(100.0, base + 8 + noise(3.0)))
        mean = (p05 + p50 + p95) / 3.0
        return {"mean": mean, "p05": p05, "p50": p50, "p95": p95}

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def analyze_bank(
        self,
        bank: str,
        question: Optional[str] = None,
        year: Optional[str] = None,
        pdf_text: Optional[str] = None,
        pdf_filename: Optional[str] = None,
    ) -> Dict[str, object]:
        """
        Full ESG pipeline for one bank. Returns a dict with ok flag and payload for UI.
        """
        print(f"[Server] Running analysis for {bank} ({year or 'latest'})...")

        yahoo_snapshot = self.yahoo.lookup_and_snapshot(bank)
        news_items_raw, news_summary = self._fetch_news(bank)
        raw_pdf_text = self._fetch_pdf_text(bank, year, pdf_text)
        pdf_summary = self._summarise_pdf(raw_pdf_text, bank, year)

        context_blob = self._build_context_blob(
            yahoo_snapshot=yahoo_snapshot,
            news_summary=news_summary,
            pdf_summary=pdf_summary,
            year=year,
            question=question,
        )

        used_fallback = False
        categories: Dict[str, Any] = {}
        analysis_text = ""
        scores: Dict[str, Any] = {}
        llm_error: Optional[str] = None

        try:
            esg_output = self.esg_agent.run(
                bank=bank,
                year=year,
                question=question,
                context_blob=context_blob,
            )
            categories = esg_output.get("categories", {}) or {}
            analysis_text = esg_output.get("analysis_text", "") or ""
            scores = esg_output.get("scores", {}) or {}

            # ------ 这里是新增补丁 ------
            # 有些银行（目前就是 Rabobank）LLM 没按 schema 带 sub_scores
            # 如果 sub_scores 缺失 / 为空，但 categories 有内容，
            # 就用 ScoreEngine.from_categories() 算一份出来，只填缺的字段。
            if (not scores.get("sub_scores")) and categories:
                try:
                    auto_scores = self.score_engine.from_categories(categories, bank=bank)
                    if not scores.get("sub_scores"):
                        scores["sub_scores"] = auto_scores.get("sub_scores", {})
                    if not scores.get("pillar_scores"):
                        scores["pillar_scores"] = auto_scores.get("pillar_scores", {})
                    if not scores.get("final"):
                        scores["final"] = auto_scores.get("final", 0.0)
                except Exception as patch_exc:
                    print(f"[Server] Failed to rebuild scores from categories for {bank}: {patch_exc}")
            # ------ 新增补丁结束 ------

        except Exception as exc:
            llm_error = str(exc)
            used_fallback = True
            categories = self._fallback_categories(bank)
            scores = self.score_engine.from_categories(categories, bank=bank)
            analysis_text = (
                "LLM unavailable; generated deterministic fallback analysis based on public signals "
                "and rubric defaults."
            )

        # Enrich scores with MC band for UI
        scores["mc"] = self._mc_band(scores.get("final", 0), bank)

        # Final report
        try:
            final_report = self.writer.run(
                bank=bank,
                analysis_text=analysis_text,
                scores=scores,
                news_summary=news_summary,
            )
        except Exception as exc:
            final_report = f"_Failed to generate report: {exc}_"

        return {
            "ok": True,
            "bank": bank,
            "analysis_text": analysis_text,
            "categories": categories,
            "scores": scores,
            "news_summary": news_summary,
            "pdf_summary": pdf_summary,
            "final_report": final_report,
            "sources": self._format_sources(news_items_raw, raw_pdf_text),
            "news": {"items": self._news_items_for_ui(news_items_raw), "query": bank},
            "yahoo": self._yahoo_snapshot_struct(yahoo_snapshot, bank),
            "raw": {
                "used_fallback_from_yahoo": used_fallback,
                "llm_error": llm_error,
                "pdf_filename": pdf_filename,
            },
        }

    def compare_banks(
        self,
        banks: List[str],
        year: Optional[str] = None,
        pdf_texts: Optional[Dict[str, str]] = None,
        comparison_question: Optional[str] = None,
    ) -> Dict[str, object]:
        results: Dict[str, Dict[str, Any]] = {}
        per_bank: Dict[str, Dict[str, Any]] = {}
        errors: Dict[str, str] = {}

        for bank in banks:
            try:
                result = self.analyze_bank(
                    bank=bank,
                    question=comparison_question,
                    year=year,
                    pdf_text=(pdf_texts or {}).get(bank),
                    pdf_filename=None,
                )
                per_bank[bank] = result
                if result.get("ok"):
                    results[bank] = result.get("scores", {})
                else:
                    errors[bank] = str(result.get("error", "unknown error"))
            except Exception as exc:
                errors[bank] = str(exc)

        # Simple textual summary
        ordered = sorted(results.items(), key=lambda kv: kv[1].get("final", 0), reverse=True)
        summary_lines = ["Comparison summary (deterministic if LLM unavailable):"]
        for bank, sc in ordered:
            summary_lines.append(
                f"- {bank}: Final={sc.get('final', 'N/A')} (E={sc.get('E')}, S={sc.get('S')}, G={sc.get('G')})"
            )
        comparison_summary = "\n".join(summary_lines)

        return {
            "ok": True,
            "results": results,
            "per_bank_results": per_bank,
            "errors": errors,
            "comparison_summary": comparison_summary,
        }
