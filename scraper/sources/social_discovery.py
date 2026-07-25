"""
DuckDuckGo Social Discovery — uses SearXNG (self-hosted) with DDG fallback.
Discovers LinkedIn/Facebook/Yelp/BBB presence for businesses via search.
"""
import os, logging, json, time
from typing import Dict, List, Optional

log = logging.getLogger("social_discovery")


def discover_social_presence(business_name: str, city: str) -> Dict:
    results = {
        "linkedin_url": None,
        "facebook_url": None,
        "yelp_url": None,
        "bbb_url": None,
        "social_presence_score": 0,
    }

    platforms = ["linkedin", "facebook", "yelp", "bbb"]
    presence_count = 0

    try:
        from scraper.searxng_search import search_social
        for platform in platforms:
            try:
                url = search_social(business_name, city, platform)
                if url:
                    results[f"{platform}_url"] = url
                    presence_count += 1
            except Exception as e:
                log.debug(f"Social discovery for {platform} failed: {e}")
    except ImportError:
        for platform in platforms:
            try:
                url = _ddg_fallback_social(business_name, city, platform)
                if url:
                    results[f"{platform}_url"] = url
                    presence_count += 1
            except Exception as e:
                log.debug(f"Social discovery fallback for {platform} failed: {e}")

    results["social_presence_score"] = presence_count
    results["social_platforms_found"] = [p for p in ["linkedin", "facebook", "yelp", "bbb"] if results.get(f"{p}_url")]

    return results


def _ddg_fallback_social(business_name: str, city: str, platform: str) -> Optional[str]:
    """Fallback to DDG if SearXNG is down."""
    try:
        from duckduckgo_search import DDGS
        site_filter = {
            "linkedin": "site:linkedin.com/company",
            "facebook": "site:facebook.com",
            "yelp": "site:yelp.com",
            "bbb": "site:bbb.org",
        }.get(platform, "")

        query = f'"{business_name}" {city} {site_filter}'
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=2):
                url = r.get("href", "")
                if platform == "linkedin" and "linkedin.com/company" in url:
                    return url
                elif platform == "facebook" and "facebook.com" in url:
                    return url
                elif platform == "yelp" and "yelp.com" in url:
                    return url
                elif platform == "bbb" and "bbb.org" in url:
                    return url
    except Exception:
        pass
    return None


def discover_batch(businesses: List[Dict]) -> List[Dict]:
    enriched = []
    for biz in businesses:
        name = biz.get("name", "")
        city = biz.get("city", "")
        if name and city:
            social = discover_social_presence(name, city)
            biz.update(social)
            enriched.append(biz)
    return enriched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = discover_social_presence("Abccollision", "Miami")
    print(json.dumps(result, indent=2))
