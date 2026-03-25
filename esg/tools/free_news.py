# tools/free_news.py
"""
Free ESG news fetcher using Google News RSS.
No API key required.

It retrieves:
- title
- source
- link
- snippet
- publication date

And supports bank-specific + ESG-specific search queries.
"""

from __future__ import annotations

import feedparser
from typing import List, Dict
import html
import re
import datetime


class FreeNewsClient:

    # ============================================================
    # PUBLIC API
    # ============================================================
    def search(self, bank: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Search Google News RSS for ESG-related articles about the bank.

        Returns a list of dicts:
        [
          {
            "title": "...",
            "source": "...",
            "link": "...",
            "published": "...",
            "snippet": "..."
          }
        ]
        """
        queries = self._build_queries(bank)
        results = []

        for q in queries:
            url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)

            for entry in feed.entries:
                item = self._parse_entry(entry)
                if item:
                    results.append(item)

        # Remove duplicates
        unique = self._dedupe(results)

        # Limit size
        return unique[:limit]

    # ============================================================
    # Internal Helpers
    # ============================================================
    def _build_queries(self, bank: str) -> List[str]:
        """Build multi-keyword Google News search queries."""
        base = [bank]

        esg_terms = [
            "ESG",
            "sustainability",
            "climate",
            "governance",
            "AML",
            "KYC",
            "risk",
            "regulator",
            "EU taxonomy",
            "CSRD",
            "SFDR",
        ]

        # Generate combinations: (bank + term)
        queries = [f"{bank} {term}" for term in esg_terms]

        return queries

    def _parse_entry(self, e) -> Dict[str, str]:
        """Safely parse a single RSS entry."""
        try:
            title = html.unescape(e.title)
            link = e.link
            published = e.get("published", "")

            # Rarely missing summary
            snippet = html.unescape(getattr(e, "summary", "")).strip()

            # Clean snippet: remove HTML tags
            snippet = re.sub(r"<.*?>", "", snippet)

            # Convert date → readable
            if published:
                try:
                    dt = datetime.datetime(*e.published_parsed[:6])
                    published = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

            return {
                "title": title,
                "source": e.get("source", {}).get("title", ""),
                "link": link,
                "published": published,
                "snippet": snippet,
            }

        except Exception:
            return None

    def _dedupe(self, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove duplicate articles."""
        seen = set()
        unique = []
        for item in items:
            key = item["title"] + item["link"]
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique
