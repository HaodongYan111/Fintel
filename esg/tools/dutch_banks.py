# tools/dutch_banks.py
"""
Dutch banks metadata & helper utilities.

This module centralises all information about the Dutch banks we support.
It is intentionally self-contained and has **no external dependencies**
beyond the Python standard library.

Public API
----------
- list_dutch_banks() -> List[str]
    Return the canonical bank names used everywhere else in the app.

- resolve_bank(name: str) -> Optional[str]
    Map user input (e.g. "ing", "ing group", "ING Groep N.V.") to
    a canonical bank name, or None if not recognised.

- get_bank_metadata(name: str) -> Optional[dict]
    Return the full metadata dict for a bank (ISIN, HQ, employees, assets,
    Yahoo symbol, RSS keywords, etc.), or None if not found.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional


# ======================================================================
# Core metadata table
# ======================================================================

# 每个 bank 一行，保证 key 名称稳定，方便后面 Yahoo / News / ESG 引用
_BANKS: Dict[str, Dict[str, Any]] = {
    "ING Group": {
        "canonical": "ING Group",
        "aliases": [
            "ing",
            "ing bank",
            "ing groep",
            "ing groep n.v.",
            "ing group n.v.",
            "ing nl",
        ],
        # 基本公司信息（可以在 UI / 报告中显示）
        "country": "Netherlands",
        "hq_city": "Amsterdam",
        "website": "https://www.ing.com/",
        # 证券 / 标识
        "isin": "NL0011821202",
        "ticker_euronext": "INGA.AS",
        "ticker_nyse": "ING",
        "yahoo_symbol": "INGA.AS",  # 推荐给 Yahoo Finance 使用
        # 大致规模（可以写在 metadata 卡片，不要用于精确财报）
        "employees": 59000,  # approx
        "total_assets_eur_bn": 1000.0,  # approx, illustrative
        # 新闻搜索关键词（给 free_news / Google News RSS 用）
        "rss_keywords": ["ING", "ING Group", "ING Bank"],
        # 简短介绍，可做 fallback
        "short_profile": (
            "ING Group is a Dutch multinational banking and financial services "
            "corporation, offering retail and wholesale banking with a strong "
            "focus on digital channels and sustainability."
        ),
    },

    "ABN AMRO": {
        "canonical": "ABN AMRO",
        "aliases": [
            "abn",
            "abn amro bank",
            "abn amro nv",
            "abn amro group",
        ],
        "country": "Netherlands",
        "hq_city": "Amsterdam",
        "website": "https://www.abnamro.com/",
        "isin": "NL0011540547",
        "ticker_euronext": "ABN.AS",
        "ticker_nyse": None,
        "yahoo_symbol": "ABN.AS",
        "employees": 19000,  # approx
        "total_assets_eur_bn": 400.0,
        "rss_keywords": ["ABN AMRO", "ABN AMRO Bank"],
        "short_profile": (
            "ABN AMRO is a Dutch bank with a focus on retail, private and "
            "corporate banking in Northwest Europe, with sustainability and "
            "client due diligence as key pillars."
        ),
    },

    "Rabobank": {
        "canonical": "Rabobank",
        "aliases": [
            "rabo",
            "rabo bank",
            "cooperatieve rabobank",
            "coöperatieve rabobank",
            "rabobank group",
        ],
        "country": "Netherlands",
        "hq_city": "Utrecht",
        "website": "https://www.rabobank.com/",
        "isin": None,  # cooperative; listed debt instead of equity
        "ticker_euronext": None,
        "ticker_nyse": None,
        "yahoo_symbol": None,  # 对 co-op 可能没有简单 equity symbol
        "employees": 43000,
        "total_assets_eur_bn": 600.0,
        "rss_keywords": ["Rabobank"],
        "short_profile": (
            "Rabobank is a Dutch cooperative bank with an international focus "
            "on food and agriculture financing, and strong roots in the "
            "domestic retail and SME market."
        ),
    },

    "De Volksbank": {
        "canonical": "De Volksbank",
        "aliases": [
            "volksbank",
            "sns bank",
            "de volksbank nv",
        ],
        "country": "Netherlands",
        "hq_city": "Utrecht",
        "website": "https://www.devolksbank.nl/",
        "isin": None,
        "ticker_euronext": None,
        "ticker_nyse": None,
        "yahoo_symbol": None,
        "employees": 3500,
        "total_assets_eur_bn": 70.0,
        "rss_keywords": ["De Volksbank", "SNS Bank"],
        "short_profile": (
            "De Volksbank is a Dutch state-owned retail bank, operating brands "
            "such as SNS, ASN Bank, RegioBank and BLG Wonen, with a strong "
            "focus on social impact and sustainable banking."
        ),
    },

    "Triodos Bank": {
        "canonical": "Triodos Bank",
        "aliases": [
            "triodos",
            "triodos bank nv",
        ],
        "country": "Netherlands",
        "hq_city": "Zeist",
        "website": "https://www.triodos.com/",
        "isin": "NL0000400677",  # depository receipts
        "ticker_euronext": None,
        "ticker_nyse": None,
        "yahoo_symbol": None,  # 不一定有标准 symbol
        "employees": 1500,
        "total_assets_eur_bn": 20.0,
        "rss_keywords": ["Triodos Bank", "Triodos"],
        "short_profile": (
            "Triodos Bank is a Dutch ethical bank that only finances companies, "
            "institutions and projects that add social, environmental or "
            "cultural value, positioning itself as a pioneer in sustainable finance."
        ),
    },
}


# ======================================================================
# Public helper functions
# ======================================================================

def list_dutch_banks() -> List[str]:
    """
    Return the list of canonical Dutch bank names used everywhere else.

    Example:
        >>> list_dutch_banks()
        ["ING Group", "ABN AMRO", "Rabobank", "De Volksbank", "Triodos Bank"]
    """
    # 保证稳定排序，方便 UI 显示
    return sorted(_BANKS.keys())


def _normalise(s: str) -> str:
    """Simple normalisation for matching user input."""
    return "".join(s.lower().replace(".", "").replace(",", "").split())


def resolve_bank(name: str) -> Optional[str]:
    """
    Map a free-form user input => canonical bank name.

    Examples:
        "ing" -> "ING Group"
        "ing bank" -> "ING Group"
        "abn amro bank" -> "ABN AMRO"
        "triodos" -> "Triodos Bank"

    Returns
    -------
    canonical_name : str or None
    """
    if not isinstance(name, str):
        return None

    raw = name.strip()
    if not raw:
        return None

    norm = _normalise(raw)

    # 1) Exact match on canonical names
    for canonical in _BANKS.keys():
        if norm == _normalise(canonical):
            return canonical

    # 2) Match on aliases
    for canonical, meta in _BANKS.items():
        for alias in meta.get("aliases", []):
            if norm == _normalise(alias):
                return canonical

    # 3) Fallback: contains check（例如 "ING Groep N.V." 包含 "ing groep"）
    for canonical, meta in _BANKS.items():
        if norm in _normalise(canonical):
            return canonical
        for alias in meta.get("aliases", []):
            if norm in _normalise(alias) or _normalise(alias) in norm:
                return canonical

    return None


def get_bank_metadata(name: str) -> Optional[Dict[str, Any]]:
    """
    Return the full metadata dict for a bank.

    `name` can be:
        - canonical name ("ING Group")
        - any known alias ("ing", "ing bank", "ING Groep N.V.")

    Returns
    -------
    metadata : dict or None

    Example:
        >>> meta = get_bank_metadata("ing")
        >>> meta["isin"]
        'NL0011821202'
    """
    canonical = resolve_bank(name) if name else None
    if not canonical:
        return None
    return _BANKS.get(canonical, {}).copy()
