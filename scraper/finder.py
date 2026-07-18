"""
FindLeads — Business Finder (curl_cffi)
Lightweight HTTP-based scraper. No Playwright. No browser.
Strategy: DuckDuckGo HTML search + website crawling for details.
"""

import json
import os
import re
import time
import random
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlparse, urljoin

from curl_cffi import requests as cffi_requests

logger = logging.getLogger("finder")

# ════════════════════════════════════════════════════════════════
# SESSION
# ════════════════════════════════════════════════════════════════

def _create_session():
    return cffi_requests.Session(impersonate="chrome120")


HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

PHONE_REGEX = re.compile(
    r'(?:\+971|00971|971|050|052|055|056|058|02|04|06|07|09)[\s\-]?\d{3,4}[\s\-]?\d{3,4}'
    r'|(?:\+1|001)[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4}'
    r'|(?:\+44|0044)[\s\-]?\d{4}[\s\-]?\d{6}'
    r'|(?:\+966|00966|05)[\s\-]?\d{4}[\s\-]?\d{4}'
)


# ════════════════════════════════════════════════════════════════
# MAIN SEARCH
# ════════════════════════════════════════════════════════════════

def search_google_maps(city: str, business_type: str, limit: int = 20) -> List[Dict]:
    """
    Search for businesses using DuckDuckGo HTML.
    Returns list of business dicts.
    """
    query = f"{business_type} in {city} phone number website"
    logger.info(f"Searching: {query}")

    session = _create_session()
    businesses = []

    # Source 1: DuckDuckGo HTML search
    try:
        ddg_results = _search_ddg(session, query, limit)
        businesses.extend(ddg_results)
        logger.info(f"DDG: found {len(ddg_results)} results")
    except Exception as e:
        logger.error(f"DDG error: {e}")

    # Source 2: Google Search (local pack)
    try:
        google_results = _search_google(session, query, limit)
        businesses.extend(google_results)
        logger.info(f"Google: found {len(google_results)} results")
    except Exception as e:
        logger.error(f"Google error: {e}")

    # Deduplicate by name
    businesses = _deduplicate(businesses)
    businesses = businesses[:limit]

    # Enrich each business with website details
    for biz in businesses:
        if biz.get("website"):
            try:
                details = _scrape_website_details(session, biz["website"])
                if not biz.get("phone") and details.get("phone"):
                    biz["phone"] = details["phone"]
                if not biz.get("address") and details.get("address"):
                    biz["address"] = details["address"]
                if not biz.get("email") and details.get("email"):
                    biz["email"] = details["email"]
            except Exception:
                pass
            time.sleep(random.uniform(0.3, 0.8))

    logger.info(f"Final: {len(businesses)} businesses")
    return businesses


# ════════════════════════════════════════════════════════════════
# DUCKDUCKGO SEARCH
# ════════════════════════════════════════════════════════════════

def _search_ddg(session, query: str, limit: int) -> List[Dict]:
    """Search DuckDuckGo HTML version."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    resp = session.get(url, headers=HEADERS, timeout=15)

    if resp.status_code != 200:
        return []

    html = resp.text
    businesses = []

    # Extract result titles, URLs, and snippets
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
    links = re.findall(r'class="result__url"[^>]*>\s*(.*?)\s*</a>', html, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

    for i in range(min(len(titles), limit)):
        name = _clean_html(titles[i]).strip() if i < len(titles) else ""
        url_raw = _clean_html(links[i]).strip() if i < len(links) else ""
        snippet = _clean_html(snippets[i]).strip() if i < len(snippets) else ""

        if not name or not url_raw:
            continue

        # Clean URL
        website = url_raw.split("?")[0].rstrip("/")
        if not website.startswith("http"):
            website = "https://" + website

        # Skip large directories (Yelp, TripAdvisor, etc.)
        skip_domains = [
            "yelp.com", "tripadvisor.com", "facebook.com", "linkedin.com",
            "wikipedia.org", "yellowpages.com", "google.com", "bing.com",
            "duckduckgo.com", "instagram.com", "twitter.com",
        ]
        if any(d in website for d in skip_domains):
            continue

        # Extract phone from snippet
        phone = ""
        phone_match = PHONE_REGEX.search(snippet)
        if phone_match:
            phone = phone_match.group(0)

        # Clean name (remove "- Domain.com" suffix)
        name = re.sub(r'\s*[-–|]\s*(?:Best|Top|All|Dubai|Riyadh|Austin|Miami).*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*[-–|]\s*\w+\.(?:com|ae|sa|net|org).*', '', name)
        name = name.strip(" -–|")

        if len(name) > 3:
            businesses.append({
                "name": name,
                "rating": 0,
                "review_count": 0,
                "website": website,
                "phone": phone,
                "address": "",
                "google_url": "",
                "place_id": "",
                "category": "",
            })

    return businesses


# ════════════════════════════════════════════════════════════════
# GOOGLE SEARCH
# ════════════════════════════════════════════════════════════════

def _search_google(session, query: str, limit: int) -> List[Dict]:
    """Search Google for business listings."""
    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"
    resp = session.get(url, headers=HEADERS, timeout=15)

    if resp.status_code != 200:
        return []

    html = resp.text
    businesses = []

    # Extract from Google's local pack / organic results
    # Pattern: look for business names in h3 tags
    h3_pattern = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
    for h3 in h3_pattern[:limit]:
        name = _clean_html(h3).strip()
        if len(name) > 3 and len(name) < 100:
            businesses.append({
                "name": name,
                "rating": 0,
                "review_count": 0,
                "website": "",
                "phone": "",
                "address": "",
                "google_url": "",
                "place_id": "",
                "category": "",
            })

    # Try to find website links near the h3 tags
    links = re.findall(r'href="(https?://[^"]*)"', html)
    skip_domains = ["google.com", "gstatic.com", "googleapis.com", "youtube.com",
                    "facebook.com", "twitter.com", "instagram.com"]
    website_links = [l for l in links if not any(d in l for d in skip_domains)]

    # Match websites to businesses (rough heuristic)
    for i, biz in enumerate(businesses):
        if i < len(website_links):
            biz["website"] = website_links[i].split("?")[0]

    return businesses


# ════════════════════════════════════════════════════════════════
# WEBSITE DETAIL SCRAPING
# ════════════════════════════════════════════════════════════════

def _scrape_website_details(session, website_url: str) -> Dict:
    """Scrape phone, address, email from business website."""
    result = {"phone": "", "address": "", "email": ""}

    try:
        resp = session.get(website_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return result

        content = resp.text
        content_lower = content.lower()

        # Phone
        phone_match = PHONE_REGEX.search(content)
        if phone_match:
            result["phone"] = phone_match.group(0)

        # Email
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
        if emails:
            # Prefer info@, contact@, etc.
            domain = urlparse(website_url).netloc.replace("www.", "")
            domain_emails = [e for e in emails if domain in e]
            if domain_emails:
                result["email"] = domain_emails[0]
            elif emails:
                result["email"] = emails[0]

        # Address (look for common patterns)
        addr_patterns = [
            r'(?:address|location|directions)[:\s]*([A-Z][^<\n]{10,100})',
            r'data-tooltip="([^"]*(?:street|road|avenue|suite|floor|building)[^"]*)"',
            r'"streetAddress"\s*:\s*"([^"]+)"',
        ]
        for pattern in addr_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result["address"] = _clean_html(match.group(1)).strip()
                break

    except Exception:
        pass

    return result


# ════════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════════

def _clean_html(text: str) -> str:
    """Remove HTML tags and entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#x27;', "'").replace('&quot;', '"').replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _deduplicate(businesses: List[Dict]) -> List[Dict]:
    """Remove duplicate businesses by name similarity."""
    seen = set()
    unique = []
    for biz in businesses:
        key = biz["name"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(biz)
    return unique


def find_businesses(city: str, business_type: str, limit: int = 20) -> List[Dict]:
    """Main entry point."""
    return search_google_maps(city, business_type, limit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = find_businesses("Dubai", "dental clinic", 5)
    print(f"\nResults: {len(results)}")
    for r in results:
        print(f"  - {r['name']}")
        print(f"    Website: {r.get('website', 'N/A')}")
        print(f"    Phone: {r.get('phone', 'N/A')}")
        print(f"    Email: {r.get('email', 'N/A')}")
