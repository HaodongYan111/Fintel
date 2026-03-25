"""
yahoo_client.py
-------------------------------------------------
轻量级 Yahoo Finance 客户端：

- 提供 YahooFinanceClient.lookup_and_snapshot(bank_name) -> str
- 尽量用 yfinance 抓取简介信息
- 如果失败 / 没装 yfinance / 无 ticker，就返回可读的 fallback 文本
- 永远不抛异常，只返回字符串
-------------------------------------------------
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
except ImportError:
    yf = None


# 你可以根据需要补充/修改映射
BANK_TICKERS = {
    "ING Group": "INGA.AS",   # ING Groep N.V. 在阿姆斯特丹上市
    "ABN AMRO": "ABN.AS",
    # Rabobank 非上市合作制银行，没有公开 ticker
}


class YahooFinanceClient:
    def __init__(self) -> None:
        if yf is None:
            logger.warning(
                "[YahooFinanceClient] yfinance not installed; will use fallback text only."
            )

    def _snapshot_from_ticker(self, ticker: str) -> str:
        if yf is None:
            return (
                f"Yahoo Finance data unavailable because 'yfinance' is not installed. "
                f"Ticker={ticker}."
            )

        try:
            t = yf.Ticker(ticker)
            info = t.info  # 网络请求
        except Exception as e:
            logger.warning(f"[YahooFinanceClient] Failed to fetch info for {ticker}: {e}")
            return f"Yahoo Finance snapshot unavailable for ticker {ticker}."

        name = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector", "N/A")
        country = info.get("country", "N/A")
        employees = info.get("fullTimeEmployees", "N/A")
        summary = info.get("longBusinessSummary", "")

        snapshot = (
            f"Name: {name}\n"
            f"Ticker: {ticker}\n"
            f"Sector: {sector}\n"
            f"Country: {country}\n"
            f"Employees: {employees}\n"
            f"Summary: {summary}"
        )
        return snapshot

    def lookup_and_snapshot(self, bank: str) -> str:
        """
        给定银行名称，返回一段简短 snapshot 文本。
        不会抛异常。
        """
        bank_norm = bank.strip()
        ticker = BANK_TICKERS.get(bank_norm)

        if ticker:
            return self._snapshot_from_ticker(ticker)

        # 没有 ticker（如 Rabobank）
        return (
            f"No direct stock ticker mapping found for bank '{bank_norm}'. "
            "Bank may be privately held or not listed. "
            "Proceeding with ESG PDF text and news only."
        )
