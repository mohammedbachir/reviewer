"""
DuckDuckGo Social Discovery — completely free, no API key.

Discovers LinkedIn/Facebook/Yelp presence for businesses via search.
Reads only publicly indexed data, no scraping of private pages.
"""
import os, logging, json, time
from typing import Dict, List, Optional

log = logging.getLogger("social_discovery")

try:
    from duckduckgo_search import DDGS
    _HAS_DDGS = True
except ImportError:
    _HAS_DDGS = False


def _ddg_search(query: str, max_results: int = 5) -> List[Dict]:
    if not _HAS_DDGS:
        log.debug("duckduckgo-search not installed")
        return []

    try:
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "url": r.get("href", ""),
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                })
            return results
    except Exception as e:
        log.debug(f"DDG search failed: {e}")
        return []


_SITES = {
    "linkedin": "site:linkedin.com/company",
    "facebook": "site:facebook.com",
    "yelp": "site:yelp.com",
    "bbb": "site:bbb.org",
}


def discover_social_presence(business_name: str, city: str) -> Dict:
    results = {
        "linkedin_url": None,
        "facebook_url": None,
        "yelp_url": None,
        "bbb_url": None,
        "social_presence_score": 0,
    }

    query = f'"{business_name}" {city}'
    presence_count = 0

    for platform, site_filter in _SITES.items():
        try:
            platform_query = f"{query} {site_filter}"
            ddg_results = _ddg_search(platform_query, max_results=2)

            if ddg_results:
                best = ddg_results[0]
                url = best.get("url", "")

                if platform == "linkedin" and "linkedin.com/company" in url:
                    results["linkedin_url"] = url
                    presence_count += 1
                elif platform == "facebook" and "facebook.com" in url:
                    results["facebook_url"] = url
                    presence_count += 1
                elif platform == "yelp" and "yelp.com" in url:
                    results["yelp_url"] = url
                    presence_count += 1
                elif platform == "bbb" and "bbb.org" in url:
                    results["bbb_url"] = url
                    presence_count += 1

            time.sleep(0.5)

        except Exception as e:
            log.debug(f"Social discovery for {platform} failed: {e}")
            continue

    results["social_presence_score"] = presence_count
    results["social_platforms_found"] = [p for p in ["linkedin", "facebook", "yelp", "bbb"] if results.get(f"{p}_url")]

    return results


def discover_batch(businesses: List[Dict]) -> List[Dict]:
    enriched = []
    for biz in businesses:
        name = biz.get("name", "")
        city = biz.get("city", "")
        if name and city:
            social = discover_social_presence(name, city)
            biz.update(social)
            enriched.append(biz)
            time.sleep(0.3)
    return enriched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = discover_social_presence("Abccollision", "Miami")
    print(json.dumps(result, indent=2))
