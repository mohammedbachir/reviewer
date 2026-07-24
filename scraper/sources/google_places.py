"""
Google Maps Business Discovery — no API key needed.

Uses DDG search to discover businesses listed on Google Maps.
Falls back to Google Places API if key is available.
"""
import os, logging, time, re
from typing import Dict, List

log = logging.getLogger("google_places")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

GOOGLE_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

try:
    from duckduckgo_search import DDGS
    _HAS_DDGS = True
except ImportError:
    _HAS_DDGS = False

try:
    import requests as _req
except ImportError:
    from curl_cffi import requests as _req


def search_businesses(city: str, sector: str, max_results: int = 20) -> List[Dict]:
    if GOOGLE_API_KEY:
        return _search_via_api(city, sector, max_results)
    return _search_via_ddg(city, sector, max_results)


def _search_via_ddg(city: str, sector: str, max_results: int = 20) -> List[Dict]:
    if not _HAS_DDGS:
        log.debug("duckduckgo-search not installed")
        return []

    query = f"{sector} in {city} google maps"
    results = []

    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=min(max_results, 10)):
                url = r.get("href", "")
                title = r.get("title", "")
                snippet = r.get("body", "")

                if not title or "google" not in url.lower():
                    if not any(kw in url.lower() for kw in ["google.com/maps", "goo.gl/maps"]):
                        continue

                biz = {
                    "name": title.split(" - ")[0].split(" | ")[0].strip(),
                    "address": _extract_address(snippet, city),
                    "google_url": url,
                    "source": "google_maps_ddg",
                }

                rating_match = re.search(r'(\d+\.?\d*)\s*(?:stars?|rating| reviews?)', snippet, re.IGNORECASE)
                if rating_match:
                    try:
                        biz["google_rating"] = float(rating_match.group(1))
                    except ValueError:
                        pass

                phone_match = re.search(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', snippet)
                if phone_match:
                    biz["phone"] = phone_match.group(1)

                if city.lower() in snippet.lower() or city.lower() in biz["name"].lower():
                    results.append(biz)

                if len(results) >= max_results:
                    break

    except Exception as e:
        log.debug(f"DDG Google Maps search failed: {e}")

    return results


def _extract_address(snippet: str, city: str) -> str:
    addr_match = re.search(rf'(\d+\s+[\w\s]+(?:St|Ave|Blvd|Rd|Dr|Ln|Way|Ct|Pl)\b[^,]*,\s*{re.escape(city)}[^,]*(?:,\s*\w{{2}}\s*\d{{5}})?)', snippet, re.IGNORECASE)
    if addr_match:
        return addr_match.group(1).strip()
    return ""


def _search_via_api(city: str, sector: str, max_results: int = 20) -> List[Dict]:
    query = f"{sector} in {city}"
    results = []
    params = {
        "query": query,
        "key": GOOGLE_API_KEY,
        "type": "establishment",
    }

    try:
        r = _req.get("https://maps.googleapis.com/maps/api/place/textsearch/json", params=params, timeout=15)
        data = r.json()
        if data.get("status") != "OK":
            log.debug(f"Google Places status: {data.get('status')}")
            return []

        for place in data.get("results", [])[:max_results]:
            biz = {
                "name": place.get("name", ""),
                "address": place.get("formatted_address", ""),
                "google_rating": place.get("rating", 0),
                "google_reviews": place.get("user_ratings_total", 0),
                "google_place_id": place.get("place_id", ""),
                "google_url": place.get("url", ""),
                "source": "google_places_api",
            }
            if city.lower() not in biz["address"].lower():
                continue
            results.append(biz)

    except Exception as e:
        log.debug(f"Google Places API failed: {e}")

    return results


def get_place_details(place_id: str) -> Dict:
    if not GOOGLE_API_KEY or not place_id:
        return {}

    fields = "name,formatted_phone_number,website,url,rating,user_ratings_total,opening_hours,formatted_address,types,price_level,business_status"
    params = {
        "place_id": place_id,
        "fields": fields,
        "key": GOOGLE_API_KEY,
    }

    try:
        r = _req.get("https://maps.googleapis.com/maps/api/place/details/json", params=params, timeout=15)
        data = r.json()
        if data.get("status") != "OK":
            return {}

        result = data.get("result", {})
        return {
            "phone": result.get("formatted_phone_number", ""),
            "website": result.get("website", ""),
            "google_rating": result.get("rating", 0),
            "google_reviews": result.get("user_ratings_total", 0),
            "google_price_level": result.get("price_level"),
            "google_business_status": result.get("business_status", "OPERATIONAL"),
            "google_hours": result.get("opening_hours", {}).get("weekday_text", []),
        }
    except Exception as e:
        log.debug(f"Google Places details failed: {e}")
        return {}
