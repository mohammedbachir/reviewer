"""
Crisora — Review Intelligence Engine v4
Uses ddgs (multi-engine: DDG+Bing+Brave+Google) for review search.
Falls back gracefully when one engine is blocked.
"""

import json
import re
import logging
from typing import Dict, List
from urllib.parse import quote_plus

logger = logging.getLogger("review_engine")

POSITIVE_WORDS = [
    "great", "excellent", "amazing", "best", "love", "perfect", "fantastic",
    "wonderful", "awesome", "outstanding", "friendly", "professional", "clean",
    "recommend", "helpful", "caring", "thorough", "gentle", "satisfied",
    "happy", "pleased", "impressed", "comfortable", "trust", "top-notch",
]

NEGATIVE_WORDS = [
    "bad", "worst", "terrible", "awful", "poor", "rude", "dirty", "slow",
    "expensive", "disappointing", "horrible", "never", "waste", "avoid",
    "complaint", "problem", "unprofessional", "rushed", "wait", "overpriced",
    "painful", "negligent", "unethical", "fraud", "scam", "liar",
]

COMPLAINT_KEYWORDS = [
    "complaint", "problem", "issue", "never again", "worst", "terrible",
    "avoid", "scam", "fraud", "unprofessional", "rude", "negligent",
    "malpractice", "botched", "lawsuit",
]


def analyze_reviews(business_name: str, city: str, website: str = "") -> Dict:
    result = {
        "rating": 0,
        "review_count": 0,
        "sentiment": "neutral",
        "responds_to_reviews": False,
        "recent_complaints": [],
        "has_recent_reviews": False,
        "review_snippets": [],
        "review_sources": [],
    }

    all_snippets = []

    # ── Search 1: General reviews ──
    try:
        data1 = _ddgs_search(f'"{business_name}" {city} reviews rating')
        all_snippets.extend(data1.get("snippets", []))
        if data1.get("review_count", 0) > result["review_count"]:
            result["review_count"] = data1["review_count"]
        if data1.get("rating", 0) > result["rating"]:
            result["rating"] = data1["rating"]
        if data1.get("source"):
            result["review_sources"].append(data1["source"])
        logger.info(f"  ddgs-1: rating={data1.get('rating',0)}, reviews={data1.get('review_count',0)}, source={data1.get('source','')}")
    except Exception as e:
        logger.debug(f"  ddgs-1 error: {e}")

    # ── Search 2: Yelp-specific ──
    try:
        data2 = _ddgs_search(f'"{business_name}" {city} yelp reviews')
        all_snippets.extend(data2.get("snippets", []))
        if data2.get("review_count", 0) > result["review_count"]:
            result["review_count"] = data2["review_count"]
        if data2.get("rating", 0) > result["rating"]:
            result["rating"] = data2["rating"]
        logger.info(f"  ddgs-yelp: rating={data2.get('rating',0)}, reviews={data2.get('review_count',0)}")
    except Exception as e:
        logger.debug(f"  ddgs-yelp error: {e}")

    # ── Search 3: Owner response check ──
    try:
        data3 = _ddgs_search(f'"{business_name}" {city} owner response review reply')
        if any("owner" in s.lower() and "response" in s.lower() for s in data3.get("snippets", [])):
            result["responds_to_reviews"] = True
        all_snippets.extend(data3.get("snippets", []))
    except Exception as e:
        logger.debug(f"  ddgs-response error: {e}")

    # ── Analyze sentiment ──
    if all_snippets:
        result["review_snippets"] = all_snippets[:15]
        result["sentiment"] = _analyze_sentiment(all_snippets)
        result["recent_complaints"] = _find_complaints(all_snippets)
        result["has_recent_reviews"] = _has_recent_dates(all_snippets)

    logger.info(f"  Final: rating={result['rating']}, reviews={result['review_count']}, sentiment={result['sentiment']}, responds={result['responds_to_reviews']}, snippets={len(result['review_snippets'])}")
    return result


def _ddgs_search(query: str) -> Dict:
    """Search using ddgs multi-engine (DDG → Bing → Brave → Google)."""
    result = {"rating": 0, "review_count": 0, "source": "", "snippets": []}

    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except ImportError:
        logger.debug("ddgs not installed")
        return result
    except Exception as e:
        logger.debug(f"ddgs error: {e}")
        return result

    if not results:
        return result

    # Combine all text
    all_text = " ".join([r.get("title", "") + " " + r.get("body", "") for r in results])

    # Extract snippets
    for r in results:
        body = r.get("body", "")
        title = r.get("title", "")
        if len(body) > 30:
            result["snippets"].append(body[:200])
        if len(title) > 10:
            result["snippets"].append(title[:200])

    # Extract review count
    count_patterns = [
        r'(\d[\d,]*)\s*(?:Google\s+)?reviews?',
        r'(\d[\d,]*)\s*customer\s+reviews?',
        r'(\d[\d,]*)\s*reviews?\s+on\s+',
    ]
    for pat in count_patterns:
        for m in re.findall(pat, all_text, re.IGNORECASE):
            try:
                n = int(m.replace(",", ""))
                if n > result["review_count"]:
                    result["review_count"] = n
                    result["source"] = _detect_source(all_text)
            except ValueError:
                continue

    # Extract rating
    rating_patterns = [
        r'(\d+\.?\d*)\s*\(\s*(\d[\d,]*)\s*\)',  # "4.5 (236)"
        r'(\d+\.?\d*)\s*star\s*rating',  # "4.9 star rating"
        r'(\d+\.?\d*)\s*/\s*5',  # "4.5/5"
        r'Rated\s+(\d+\.?\d*)',  # "Rated 4.5"
        r'(\d+\.?\d*)-star',  # "4.5-star"
        r'rating[:\s]+(\d+\.?\d*)',  # "rating: 4.5"
    ]
    for pat in rating_patterns:
        match = re.search(pat, all_text, re.IGNORECASE)
        if match:
            try:
                r = float(match.group(1))
                if 1 <= r <= 5:
                    result["rating"] = r
                    break
            except ValueError:
                continue

    return result


def _detect_source(text: str) -> str:
    text_lower = text.lower()
    if "birdeye" in text_lower:
        return "Birdeye"
    elif "yelp" in text_lower:
        return "Yelp"
    elif "google" in text_lower:
        return "Google"
    return "Search"


def _analyze_sentiment(snippets: List[str]) -> str:
    all_text = " ".join(snippets).lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in all_text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in all_text)
    if pos > neg * 1.5:
        return "positive"
    elif neg > pos * 1.5:
        return "negative"
    return "neutral"


def _find_complaints(snippets: List[str]) -> List[str]:
    complaints = []
    for snippet in snippets:
        lower = snippet.lower()
        if any(kw in lower for kw in COMPLAINT_KEYWORDS):
            complaints.append(snippet[:120])
    return complaints


def _has_recent_dates(snippets: List[str]) -> bool:
    date_patterns = [
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}',
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{1,2}\s+(?:hours?|days?|weeks?|months?)\s+ago',
        r'Updated\s+\w+\s+\d{4}',
    ]
    for snippet in snippets:
        for pattern in date_patterns:
            if re.search(pattern, snippet, re.IGNORECASE):
                return True
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = analyze_reviews("Bella Family Dental", "Dallas")
    print(json.dumps(result, indent=2, default=str))
