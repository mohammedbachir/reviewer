"""
SearXNG Meta-Search Wrapper — replaces DDG rate-limited searches.
Self-hosted, no API key, no rate limits, aggregates 70+ engines.
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional

log = logging.getLogger("searxng")

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://searxng:8080")

try:
    from curl_cffi import requests as cffi_requests
    _HAS_CFFI = True
except ImportError:
    _HAS_CFFI = False

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

_session = None


def _get_session():
    global _session
    if _session is None:
        if _HAS_CFFI:
            _session = cffi_requests.Session(impersonate="chrome120")
        elif _HAS_REQUESTS:
            _session = _requests.Session()
    return _session


def search(query: str, max_results: int = 10, categories: str = "general",
           timeout: float = 8) -> List[Dict]:
    """
    Search via SearXNG. Returns list of {title, url, snippet, engine}.
    Falls back to DDG if SearXNG is unreachable.
    """
    results = _searxng_search(query, max_results, categories, timeout)
    if not results:
        results = _ddg_fallback(query, max_results)
    return results


def search_reviews(business_name: str, city: str, query_suffix: str = "reviews rating",
                   max_results: int = 10) -> Dict:
    """
    Specialized review search. Returns {rating, review_count, source, snippets}.
    """
    query = f'"{business_name}" {city} {query_suffix}'
    results = search(query, max_results=max_results)

    if not results:
        return {"rating": 0, "review_count": 0, "source": "", "snippets": []}

    all_text = " ".join(r.get("title", "") + " " + r.get("snippet", "") for r in results)
    snippets = [r["snippet"][:200] for r in results if len(r.get("snippet", "")) > 30]

    import re
    rating = 0
    review_count = 0
    source = ""

    for pat in [r'(\d+\.?\d*)\s*\(\s*(\d[\d,]*)\)', r'(\d+\.?\d*)\s*/\s*5',
                r'Rated\s+(\d+\.?\d*)', r'(\d+\.?\d*)-star']:
        match = re.search(pat, all_text, re.IGNORECASE)
        if match:
            try:
                r = float(match.group(1))
                if 1 <= r <= 5:
                    rating = r
                    break
            except ValueError:
                continue

    for pat in [r'(\d[\d,]*)\s*(?:Google\s+)?reviews?', r'(\d[\d,]*)\s*customer\s+reviews?']:
        for m in re.findall(pat, all_text, re.IGNORECASE):
            try:
                n = int(m.replace(",", ""))
                if n > review_count:
                    review_count = n
            except ValueError:
                continue

    text_lower = all_text.lower()
    if "yelp" in text_lower:
        source = "Yelp"
    elif "google" in text_lower:
        source = "Google"
    elif "birdeye" in text_lower:
        source = "Birdeye"
    elif results:
        source = "Search"

    return {"rating": rating, "review_count": review_count, "source": source, "snippets": snippets}


def search_social(business_name: str, city: str, platform: str,
                  max_results: int = 5) -> Optional[str]:
    """
    Search for a social platform URL. Returns first matching URL or None.
    """
    site_filter = {
        "linkedin": "site:linkedin.com/company",
        "facebook": "site:facebook.com",
        "yelp": "site:yelp.com",
        "bbb": "site:bbb.org",
    }.get(platform, "")

    query = f'"{business_name}" {city} {site_filter}'
    results = search(query, max_results=max_results)

    for r in results:
        url = r.get("url", "")
        if platform == "linkedin" and "linkedin.com/company" in url:
            return url
        elif platform == "facebook" and "facebook.com" in url:
            return url
        elif platform == "yelp" and "yelp.com" in url:
            return url
        elif platform == "bbb" and "bbb.org" in url:
            return url
    return None


def search_google_maps(business_name: str, city: str, sector: str,
                       max_results: int = 10) -> List[Dict]:
    """
    Search for Google Maps listings.
    """
    query = f'{sector} in {city} google maps'
    results = search(query, max_results=max_results)
    return [r for r in results if "google.com/maps" in r.get("url", "") or "goo.gl/maps" in r.get("url", "")]


def _searxng_search(query: str, max_results: int, categories: str,
                    timeout: float) -> List[Dict]:
    """Core SearXNG search via /search?format=json"""
    session = _get_session()
    if not session:
        return []

    try:
        params = {
            "q": query,
            "format": "json",
            "categories": categories,
            "engines": "google,bing,duckduckgo,brave,startpage",
        }
        url = f"{SEARXNG_URL}/search"

        if _HAS_CFFI:
            resp = session.get(url, params=params, timeout=timeout)
        else:
            resp = session.get(url, params=params, timeout=timeout)

        if resp.status_code != 200:
            log.debug(f"SearXNG HTTP {resp.status_code}")
            return []

        data = resp.json()
        results = []
        for r in data.get("results", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
                "engine": r.get("engine", ""),
            })
        return results

    except Exception as e:
        log.debug(f"SearXNG search failed: {e}")
        return []


def _ddg_fallback(query: str, max_results: int) -> List[Dict]:
    """Fallback to DDG if SearXNG is down."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "engine": "duckduckgo",
                })
            return results
    except Exception:
        return []


def health_check() -> bool:
    """Check if SearXNG is reachable."""
    session = _get_session()
    if not session:
        return False
    try:
        if _HAS_CFFI:
            resp = session.get(f"{SEARXNG_URL}/healthz", timeout=3)
        else:
            resp = session.get(f"{SEARXNG_URL}/healthz", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False
