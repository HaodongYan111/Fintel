# agents/news_agent.py
from __future__ import annotations

from typing import Any, Dict, List

import textwrap


class NewsSummariser:
    """
    把一堆 raw news items（title / snippet / link）压缩成一小段 ESG signal 文本，
    供 ESGAgent / FinalWriter 使用。
    """

    def __init__(self, llm) -> None:
        self.llm = llm

    def summarise(self, bank: str, items: List[Dict[str, Any]]) -> str:
        if not items:
            return ""

        lines = []
        for it in items:
            title = it.get("title", "")
            snippet = it.get("summary", "") or it.get("snippet", "")
            source = it.get("source", "")
            if title:
                line = f"- {title}"
                if source:
                    line += f" ({source})"
                if snippet:
                    line += f": {snippet}"
                lines.append(line)

        bullet_text = "\n".join(lines)
        prompt = textwrap.dedent(
            f"""
            You are an ESG news analyst.

            Bank: {bank}

            Below are recent news bullets (some may be irrelevant to ESG). Your tasks:

            1. Identify which bullets are clearly ESG-relevant
               (climate, emissions, ESG regulation, controversies, AML/fines, governance failures, green finance).
            2. Summarise them into 3–6 concise signals:
               - Positive ESG actions (e.g., SBTi-validated targets, green bond issuance)
               - Negative ESG events (e.g., climate lawsuits, AML fines, conduct scandals)
               - Regulatory alignment (CSRD, SFDR, EU Taxonomy)
            3. Ignore pure financial / market commentary if not ESG-related.

            News bullets:
            {bullet_text}

            Now write a short markdown bullet list of ESG-relevant signals only.
            If nothing is clearly ESG-related, say: "- No clearly ESG-related news detected in this batch."
            """
        ).strip()

        return self.llm.ask(prompt)
