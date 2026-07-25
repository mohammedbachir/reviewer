"""
Crisora — Review Intelligence Engine v5
Uses SearXNG (self-hosted meta-search) with DDG fallback.
"""
import json
import re
import logging
from typing import Dict, List

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

    try:
        from scraper.searxng_search import search_reviews
        data1 = search_reviews(business_name, city, "reviews rating")
        all_snippets.extend(data1.get("snippets", []))
        if data1.get("review_count", 0) > result["review_count"]:
            result["review_count"] = data1["review_count"]
        if data1.get("rating", 0) > result["rating"]:
            result["rating"] = data1["rating"]
        if data1.get("source"):
            result["review_sources"].append(data1["source"])
        logger.info(f"  searxng-1: rating={data1.get('rating',0)}, reviews={data1.get('review_count',0)}, source={data1.get('source','')}")
    except Exception as e:
        logger.debug(f"  searxng-1 error: {e}")

    try:
        data2 = search_reviews(business_name, city, "yelp reviews")
        all_snippets.extend(data2.get("snippets", []))
        if data2.get("review_count", 0) > result["review_count"]:
            result["review_count"] = data2["review_count"]
        if data2.get("rating", 0) > result["rating"]:
            result["rating"] = data2["rating"]
        logger.info(f"  searxng-yelp: rating={data2.get('rating',0)}, reviews={data2.get('review_count',0)}")
    except Exception as e:
        logger.debug(f"  searxng-yelp error: {e}")

    try:
        data3 = search_reviews(business_name, city, "owner response review reply")
        if any("owner" in s.lower() and "response" in s.lower() for s in data3.get("snippets", [])):
            result["responds_to_reviews"] = True
        all_snippets.extend(data3.get("snippets", []))
    except Exception as e:
        logger.debug(f"  searxng-response error: {e}")

    if all_snippets:
        result["review_snippets"] = all_snippets[:15]
        result["sentiment"] = _analyze_sentiment(all_snippets)
        result["recent_complaints"] = _find_complaints(all_snippets)
        result["has_recent_reviews"] = _has_recent_dates(all_snippets)

    logger.info(f"  Final: rating={result['rating']}, reviews={result['review_count']}, sentiment={result['sentiment']}, responds={result['responds_to_reviews']}, snippets={len(result['review_snippets'])}")
    return result


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
