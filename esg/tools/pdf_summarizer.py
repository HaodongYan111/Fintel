# tools/pdf_summarizer.py
from __future__ import annotations
"""
PDFSummarizer
-------------

This helper does **not** fetch PDFs from the web – it only takes raw text
that has already been extracted from a PDF (for example by `Server.read_pdf`)
and compresses it into a bank/year–specific summary.

The goal is to:
- keep key ESG / climate / risk information,
- drop tables / appendices / boilerplate,
- and keep the final summary short enough to fit comfortably in the LLM context.
"""

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class PDFSummarizer:
    llm: Any
    max_chars_per_chunk: int = 8000
    max_chunks: int = 3

    def _split_into_chunks(self, text: str) -> List[str]:
        text = text.replace("\r", "\n")
        if len(text) <= self.max_chars_per_chunk:
            return [text]

        chunks: List[str] = []
        start = 0
        n = len(text)
        while start < n and len(chunks) < self.max_chunks:
            end = min(start + self.max_chars_per_chunk, n)
            # try to cut at a paragraph boundary
            cut = text.rfind("\n\n", start, end)
            if cut == -1 or cut <= start + 1000:
                cut = end
            chunk = text[start:cut].strip()
            if chunk:
                chunks.append(chunk)
            start = cut
        return chunks

    def summarize(self, raw_text: str, bank: str, year: Optional[str]) -> str:
        """
        Summarise long PDF text into a compact ESG-focused context.

        Parameters
        ----------
        raw_text : str
            Full text extracted from a PDF.
        bank : str
            Bank name (used only to make the prompt more specific).
        year : str, optional
            Reporting period, if known.

        Returns
        -------
        str
            Short ESG-focused summary suitable for feeding into ESGAgent.
        """
        raw_text = (raw_text or "").strip()
        if not raw_text:
            return ""

        chunks = self._split_into_chunks(raw_text)
        year_text = year or "latest available period"

        if len(chunks) == 1:
            prompt = f"""
You are preparing an ESG supervision briefing.

Bank: {bank}
Reporting period: {year_text}

Below is raw text extracted from an official PDF (annual report / sustainability report).
Please summarise ONLY the parts relevant to:
  - climate strategy and transition plans,
  - financed emissions and fossil-fuel exposure,
  - ESG risk management and governance,
  - controversies, fines, or enforcement actions,
  - disclosures and alignment with EU taxonomy / CSRD / SFDR.

Ignore tables of numbers, generic marketing language, disclaimers, or boilerplate.

Return a concise markdown bullet list (max ~300 words).

RAW PDF TEXT:
{chunks[0]}
"""
            return self.llm.ask(prompt, bank_name=bank, question=None, pdf_text=raw_text)

        # Multi-chunk: summarise each chunk first, then summarise the summaries
        partial_summaries: List[str] = []
        for i, ch in enumerate(chunks, start=1):
            prompt = f"""
You are preparing an ESG supervision briefing.

Bank: {bank}
Reporting period: {year_text}
Chunk {i} of {len(chunks)}.

The following is a fragment of an official PDF report.
Summarise ONLY ESG-relevant content as bullet points (max ~150 words).

CHUNK TEXT:
{ch}
"""
            partial = self.llm.ask(prompt, bank_name=bank, question=None, pdf_text=ch)
            partial_summaries.append(partial.strip())

        joined = "\n\n".join(partial_summaries)

        final_prompt = f"""
You are preparing an ESG supervision briefing.

Bank: {bank}
Reporting period: {year_text}

You are given several preliminary bullet lists produced from different parts
of the bank's official reports.

Please merge them into a single, deduplicated ESG summary (markdown bullets),
covering climate strategy, financed emissions, governance, controversies and
regulatory alignment. Max ~350 words.

PARTIAL BULLETS:
{joined}
"""
        return self.llm.ask(final_prompt, bank_name=bank, question=None, pdf_text=joined)
