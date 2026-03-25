# data_providers.py
import os
from datetime import date, timedelta
from typing import Any, Dict, List

from dotenv import load_dotenv
import finnhub
from tavily import TavilyClient

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# ---- Finnhub client ----
if FINNHUB_API_KEY:
    _finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
else:
    _finnhub_client = None

# ---- Tavily client ----
if TAVILY_API_KEY:
    _tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
else:
    _tavily_client = None


def _safe_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return {"error": str(e)}


def get_company_profile(symbol: str) -> Dict[str, Any]:
    if not _finnhub_client:
        return {}
    return _safe_call(_finnhub_client.company_profile2, symbol=symbol.upper()) or {}


def get_realtime_quote(symbol: str) -> Dict[str, Any]:
    if not _finnhub_client:
        return {}
    return _safe_call(_finnhub_client.quote, symbol.upper()) or {}


def get_recommendation_trends(symbol: str) -> List[Dict[str, Any]]:
    if not _finnhub_client:
        return []
    res = _safe_call(_finnhub_client.recommendation_trends, symbol.upper())
    return res or []


def get_latest_financials(symbol: str) -> Dict[str, Any]:
    if not _finnhub_client:
        return {}
    return _safe_call(_finnhub_client.company_basic_financials, symbol.upper(), "all") or {}


def get_company_news(symbol: str, days: int = 7) -> List[Dict[str, Any]]:
    if not _finnhub_client:
        return []
    end = date.today()
    start = end - timedelta(days=days)
    res = _safe_call(
        _finnhub_client.company_news,
        symbol.upper(),
        start.isoformat(),
        end.isoformat(),
    )
    return res or []


def search_finance_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    if not _tavily_client:
        return [{"warning": "Tavily is not configured"}]
    try:
        res = _tavily_client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
        )
        return res.get("results", [])[:max_results]
    except Exception as e:
        return [{"error": str(e)}]
