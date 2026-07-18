"""
FindLeads — Business Finder (curl_cffi)
Lightweight HTTP-based scraper. No Playwright. No browser.
Strategy: DuckDuckGo HTML search + website crawling for details.
Extracts: rating, review_count, owner_name, social links from DDG snippets.
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

def search_businesses(city: str, business_type: str, limit: int = 20) -> List[Dict]:
    """
    Search for businesses using DuckDuckGo HTML.
    Returns list of business dicts with rating, review_count, etc.
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
                if not biz.get("owner_name") and details.get("owner_name"):
                    biz["owner_name"] = details["owner_name"]
                for link_type in ["instagram", "facebook", "twitter"]:
                    if not biz.get(link_type) and details.get(link_type):
                        biz[link_type] = details[link_type]
            except Exception:
                pass
            time.sleep(random.uniform(0.2, 0.5))

    logger.info(f"Final: {len(businesses)} businesses")
    return businesses


# ════════════════════════════════════════════════════════════════
# DUCKDUCKGO SEARCH
# ════════════════════════════════════════════════════════════════

def _search_ddg(session, query: str, limit: int) -> List[Dict]:
    """Search DuckDuckGo HTML version."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    resp = session.get(url, headers=HEADERS, timeout=5)

    if resp.status_code != 200:
        return []

    html = resp.text
    businesses = []

    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
    links = re.findall(r'class="result__url"[^>]*>\s*(.*?)\s*</a>', html, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

    for i in range(min(len(titles), limit)):
        name = _clean_html(titles[i]).strip() if i < len(titles) else ""
        url_raw = _clean_html(links[i]).strip() if i < len(links) else ""
        snippet = _clean_html(snippets[i]).strip() if i < len(snippets) else ""

        if not name or not url_raw:
            continue

        website = url_raw.split("?")[0].rstrip("/")
        if not website.startswith("http"):
            website = "https://" + website

        skip_domains = [
            "yelp.com", "tripadvisor.com", "facebook.com", "linkedin.com",
            "wikipedia.org", "yellowpages.com", "google.com", "bing.com",
            "duckduckgo.com", "instagram.com", "twitter.com",
        ]
        if any(d in website for d in skip_domains):
            continue

        phone = ""
        phone_match = PHONE_REGEX.search(snippet)
        if phone_match:
            phone = phone_match.group(0)

        rating, review_count = _extract_rating_from_snippet(snippet)

        name = re.sub(r'\s*[-–|]\s*(?:Best|Top|All|Dubai|Riyadh|Austin|Miami).*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*[-–|]\s*\w+\.(?:com|ae|sa|net|org).*', '', name)
        name = name.strip(" -–|")

        if len(name) > 3:
            businesses.append({
                "name": name,
                "rating": rating,
                "review_count": review_count,
                "website": website,
                "phone": phone,
                "address": "",
                "google_url": "",
                "place_id": "",
                "category": "",
                "owner_name": "",
                "instagram": "",
                "facebook": "",
                "twitter": "",
            })

    return businesses


def _extract_rating_from_snippet(snippet: str) -> tuple:
    """Extract star rating and review count from DDG snippet."""
    rating = 0
    review_count = 0

    # Pattern: "4.5" or "4.5/5" or "4.5 stars"
    star_match = re.search(r'(\d+\.?\d*)\s*(?:out of 5|stars?|★|/5)', snippet, re.IGNORECASE)
    if star_match:
        try:
            r = float(star_match.group(1))
            if 1 <= r <= 5:
                rating = r
        except ValueError:
            pass

    # Pattern: "123 reviews" or "123 Google reviews"
    rev_match = re.search(r'(\d+)\s*(?:Google\s+)?reviews?', snippet, re.IGNORECASE)
    if rev_match:
        try:
            review_count = int(rev_match.group(1))
        except ValueError:
            pass

    return rating, review_count


def _search_ddg_ratings(session, query: str, limit: int) -> Dict[str, Dict]:
    """Search DDG for Google Maps ratings."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    resp = session.get(url, headers=HEADERS, timeout=5)

    if resp.status_code != 200:
        return {}

    html = resp.text
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)

    results = {}
    for i in range(min(len(titles), limit)):
        name = _clean_html(titles[i]).strip() if i < len(titles) else ""
        snippet = _clean_html(snippets[i]).strip() if i < len(snippets) else ""

        rating, review_count = _extract_rating_from_snippet(snippet)

        if rating > 0 or review_count > 0:
            # Try to match to existing business by name similarity
            key = name.lower().strip()
            key = re.sub(r'\s*[-–|].*', '', key)
            if len(key) > 3:
                results[key] = {"rating": rating, "review_count": review_count}

    return results


def _merge_ratings(businesses: List[Dict], ratings: Dict[str, Dict]):
    """Merge DDG ratings into business list."""
    for biz in businesses:
        biz_key = biz["name"].lower().strip()
        biz_key = re.sub(r'\s*[-–|].*', '', biz_key)

        for rating_key, rating_data in ratings.items():
            if biz_key in rating_key or rating_key in biz_key:
                if not biz.get("rating") and rating_data.get("rating"):
                    biz["rating"] = rating_data["rating"]
                if not biz.get("review_count") and rating_data.get("review_count"):
                    biz["review_count"] = rating_data["review_count"]
                break


# ════════════════════════════════════════════════════════════════
# GOOGLE SEARCH
# ════════════════════════════════════════════════════════════════

def _search_google(session, query: str, limit: int) -> List[Dict]:
    """Search Google for business listings."""
    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"
    resp = session.get(url, headers=HEADERS, timeout=5)

    if resp.status_code != 200:
        return []

    html = resp.text
    businesses = []

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
                "owner_name": "",
                "instagram": "",
                "facebook": "",
                "twitter": "",
            })

    links = re.findall(r'href="(https?://[^"]*)"', html)
    skip_domains = ["google.com", "gstatic.com", "googleapis.com", "youtube.com",
                    "facebook.com", "twitter.com", "instagram.com"]
    website_links = [l for l in links if not any(d in l for d in skip_domains)]

    for i, biz in enumerate(businesses):
        if i < len(website_links):
            biz["website"] = website_links[i].split("?")[0]

    return businesses


# ════════════════════════════════════════════════════════════════
# WEBSITE DETAIL SCRAPING
# ════════════════════════════════════════════════════════════════

def _scrape_website_details(session, website_url: str) -> Dict:
    """Scrape phone, address, email, owner_name, social links from business website."""
    result = {
        "phone": "", "address": "", "email": "",
        "owner_name": "", "instagram": "", "facebook": "", "twitter": "",
    }

    try:
        resp = session.get(website_url, headers=HEADERS, timeout=6)
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

        # Owner name (look for common patterns)
        owner_patterns = [
            r'(?:founder|owner|ceo|director|manager)[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'(?:founded by|owned by|managed by)[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'"name"\s*:\s*"([A-Z][a-z]+ [A-Z][a-z]+)"',
        ]
        for pattern in owner_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result["owner_name"] = match.group(1).strip()
                break

        # Social links
        social_patterns = {
            "instagram": r'instagram\.com/([a-zA-Z0-9_.]+)',
            "facebook": r'facebook\.com/([a-zA-Z0-9_.]+)',
            "twitter": r'twitter\.com/([a-zA-Z0-9_.]+)',
        }
        for platform, pattern in social_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result[platform] = f"https://{platform}.com/{match.group(1)}"

    except Exception:
        pass

    return result


# ════════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════════

def _clean_html(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#x27;', "'").replace('&quot;', '"').replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _deduplicate(businesses: List[Dict]) -> List[Dict]:
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
    return search_businesses(city, business_type, limit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = find_businesses("Dubai", "dental clinic", 5)
    print(f"\nResults: {len(results)}")
    for r in results:
        print(f"  - {r['name']}")
        print(f"    Website: {r.get('website', 'N/A')}")
        print(f"    Phone: {r.get('phone', 'N/A')}")
        print(f"    Email: {r.get('email', 'N/A')}")
        print(f"    Rating: {r.get('rating', 0)}")
        print(f"    Reviews: {r.get('review_count', 0)}")
        print(f"    Owner: {r.get('owner_name', 'N/A')}")
