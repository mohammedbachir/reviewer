"""
FindLeads — Review Intelligence Engine
Searches DDG for business reviews, extracts sentiment, star ratings, response status.
Inspired by gmaps-review-scraper + VADER sentiment.
"""

import json
import re
import logging
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from curl_cffi import requests as cffi_requests

logger = logging.getLogger("review_engine")


def _create_session():
    return cffi_requests.Session(impersonate="chrome120")


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


# ════════════════════════════════════════════════════════════════
# MAIN REVIEW ANALYSIS
# ════════════════════════════════════════════════════════════════

def analyze_reviews(business_name: str, city: str, website: str = "") -> Dict:
    """
    Analyze business reviews via DDG search.
    Returns: {
        "rating": float,
        "review_count": int,
        "sentiment": str (positive/neutral/negative),
        "responds_to_reviews": bool,
        "recent_complaints": list,
        "has_recent_reviews": bool,
    }
    """
    result = {
        "rating": 0,
        "review_count": 0,
        "sentiment": "neutral",
        "responds_to_reviews": False,
        "recent_complaints": [],
        "has_recent_reviews": False,
        "review_snippets": [],
    }

    session = _create_session()

    # Search 1: Google Maps reviews via DDG
    try:
        maps_data = _search_google_maps_reviews(session, business_name, city)
        if maps_data.get("rating"):
            result["rating"] = maps_data["rating"]
        if maps_data.get("review_count"):
            result["review_count"] = maps_data["review_count"]
        if maps_data.get("response_status"):
            result["responds_to_reviews"] = maps_data["response_status"]
        logger.info(f"  Maps: rating={result['rating']}, reviews={result['review_count']}")
    except Exception as e:
        logger.debug(f"  Maps search error: {e}")

    # Search 2: Review snippets from DDG
    try:
        review_data = _search_review_snippets(session, business_name, city)
        if review_data.get("sentiment"):
            result["sentiment"] = review_data["sentiment"]
        if review_data.get("recent_complaints"):
            result["recent_complaints"] = review_data["recent_complaints"]
        if review_data.get("has_recent_reviews"):
            result["has_recent_reviews"] = review_data["has_recent_reviews"]
        if review_data.get("snippets"):
            result["review_snippets"] = review_data["snippets"]
        logger.info(f"  Reviews: sentiment={result['sentiment']}, complaints={len(result['recent_complaints'])}")
    except Exception as e:
        logger.debug(f"  Review search error: {e}")

    # Search 3: Owner response check
    try:
        response_data = _check_owner_response(session, business_name, city)
        if response_data.get("responds"):
            result["responds_to_reviews"] = True
        logger.info(f"  Response: {result['responds_to_reviews']}")
    except Exception as e:
        logger.debug(f"  Response check error: {e}")

    return result


# ════════════════════════════════════════════════════════════════
# GOOGLE MAPS REVIEW SEARCH
# ════════════════════════════════════════════════════════════════

def _search_google_maps_reviews(session, business_name: str, city: str) -> Dict:
    """Search DDG for Google Maps review data."""
    result = {"rating": 0, "review_count": 0, "response_status": False}

    query = f'"{business_name}" {city} site:google.com/maps reviews'
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    resp = session.get(url, headers=HEADERS, timeout=8)
    if resp.status_code != 200:
        return result

    html = resp.text

    # Extract rating from Google Maps snippet
    # Pattern: "4.5 (123)" or "4.5/5 (123 reviews)"
    rating_patterns = [
        r'(\d+\.?\d*)\s*\((\d+)\)',  # "4.5 (123)"
        r'(\d+\.?\d*)\s*/\s*5.*?(\d+)\s*(?:Google\s+)?reviews?',  # "4.5/5 ... 123 reviews"
        r'Rated\s+(\d+\.?\d*).*?(\d+)\s*reviews?',  # "Rated 4.5 ... 123 reviews"
        r'(\d+\.?\d*)-star.*?(\d+)\s*(?:Google\s+)?reviews?',  # "4.8-star ... 123 reviews"
        r'(\d+\.?\d*)-star\s+(?:patient\s+)?rating',  # "4.8-star patient rating"
    ]

    for pattern in rating_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            try:
                r = float(match.group(1))
                if 1 <= r <= 5:
                    result["rating"] = r
                result["review_count"] = int(match.group(2))
                break
            except (ValueError, IndexError):
                continue

    # Check if owner responds to reviews
    if "owner" in html.lower() and "response" in html.lower():
        result["response_status"] = True
    if "回复" in html or "رد" in html:  # Chinese/Arabic for "reply"
        result["response_status"] = True

    return result


# ════════════════════════════════════════════════════════════════
# REVIEW SNIPPET SEARCH
# ════════════════════════════════════════════════════════════════

def _search_review_snippets(session, business_name: str, city: str) -> Dict:
    """Search DDG for review text snippets."""
    result = {
        "sentiment": "neutral",
        "recent_complaints": [],
        "has_recent_reviews": False,
        "snippets": [],
    }

    query = f'"{business_name}" {city} reviews opinions complaints'
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    resp = session.get(url, headers=HEADERS, timeout=8)
    if resp.status_code != 200:
        return result

    html = resp.text

    # Extract snippets
    snippets_raw = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
    snippets = []
    for s in snippets_raw[:10]:
        clean = re.sub(r'<[^>]+>', '', s).strip()
        if len(clean) > 30:
            snippets.append(clean)

    result["snippets"] = snippets

    if not snippets:
        return result

    # Simple sentiment analysis (VADER-lite)
    all_text = " ".join(snippets).lower()
    positive_words = ["great", "excellent", "amazing", "best", "love", "perfect", "fantastic", "wonderful", "awesome", "outstanding", "friendly", "professional", "clean", "recommend"]
    negative_words = ["bad", "worst", "terrible", "awful", "poor", "rude", "dirty", "slow", "expensive", "disappointing", "horrible", "never", "waste", "avoid", "complaint", "problem"]

    pos_count = sum(1 for w in positive_words if w in all_text)
    neg_count = sum(1 for w in negative_words if w in all_text)

    if pos_count > neg_count * 2:
        result["sentiment"] = "positive"
    elif neg_count > pos_count * 2:
        result["sentiment"] = "negative"
    else:
        result["sentiment"] = "neutral"

    # Check for recent complaints
    complaint_keywords = ["complaint", "problem", "issue", "never again", "worst", "terrible", "avoid"]
    for snippet in snippets:
        snippet_lower = snippet.lower()
        if any(kw in snippet_lower for kw in complaint_keywords):
            result["recent_complaints"].append(snippet[:100])

    # Check for recent reviews (date patterns)
    date_patterns = [
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}',
    ]
    for snippet in snippets:
        for pattern in date_patterns:
            if re.search(pattern, snippet):
                result["has_recent_reviews"] = True
                break

    return result


# ════════════════════════════════════════════════════════════════
# OWNER RESPONSE CHECK
# ════════════════════════════════════════════════════════════════

def _check_owner_response(session, business_name: str, city: str) -> Dict:
    """Check if business owner responds to reviews."""
    result = {"responds": False}

    query = f'"{business_name}" {city} owner response review reply'
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    resp = session.get(url, headers=HEADERS, timeout=8)
    if resp.status_code != 200:
        return result

    html = resp.text.lower()

    response_indicators = [
        "owner response",
        "owner reply",
        "responded to reviews",
        "回复了",
        "رد على",
        "management response",
        "business owner",
    ]

    for indicator in response_indicators:
        if indicator in html:
            result["responds"] = True
            break

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = analyze_reviews("Dental Nation", "Dubai", "https://www.dentalnation.com")
    print(json.dumps(result, indent=2, default=str))
