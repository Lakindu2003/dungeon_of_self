"""
web_search.py — Tavily search + fetch first 3 page contents.
Used only when tool_web skill is active. Counts as the pre-answer LLM call budget.
"""

from __future__ import annotations
import requests
from bs4 import BeautifulSoup
from backend.config import TAVILY_API_KEY, TAVILY_MAX_RESULTS


def _fetch_page_text(url: str, max_chars: int = 1500) -> str:
    """Fetch a URL and return stripped plain text (truncated)."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "DungeonOfSelf/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove script/style noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:max_chars]
    except Exception as exc:
        return f"[Could not fetch {url}: {exc}]"


def search_and_fetch(query: str) -> str:
    """
    Run a Tavily search, fetch the top TAVILY_MAX_RESULTS pages,
    and return a concatenated context string.
    Falls back gracefully if API key is missing.
    """
    if not TAVILY_API_KEY:
        return "[Web search unavailable — no TAVILY_API_KEY set]"

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        results = client.search(query, max_results=TAVILY_MAX_RESULTS)
        urls = [r["url"] for r in results.get("results", [])]
    except Exception as exc:
        return f"[Tavily search error: {exc}]"

    parts: list[str] = []
    for i, url in enumerate(urls[:TAVILY_MAX_RESULTS], 1):
        content = _fetch_page_text(url)
        parts.append(f"--- Source {i}: {url} ---\n{content}")

    return "\n\n".join(parts) if parts else "[No results found]"
