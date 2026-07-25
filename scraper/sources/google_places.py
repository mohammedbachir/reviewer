"""
Google Maps Business Discovery — uses SearXNG (self-hosted) with DDG fallback.
No API key needed for SearXNG path. Falls back to Google Places API if key available.
"""
import os, logging, re
from typing import Dict, List

log = logging.getLogger("google_places")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

GOOGLE_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")


def search_businesses(city: str, sector: str, max_results: int = 20) -> List[Dict]:
    if GOOGLE_API_KEY:
        return _search_via_api(city, sector, max_results)
    return _search_via_searxng(city, sector, max_results)


def _search_via_searxng(city: str, sector: str, max_results: int = 20) -> List[Dict]:
    results = []
    try:
        from scraper.searxng_search import search
        query = f"{sector} in {city} google maps"
        raw = search(query, max_results=min(max_results, 15))

        for r in raw:
            url = r.get("url", "")
            title = r.get("title", "")
            snippet = r.get("snippet", "")

            if not title or not any(kw in url.lower() for kw in ["google.com/maps", "goo.gl/maps"]):
                continue

            biz = {
                "name": title.split(" - ")[0].split(" | ")[0].strip(),
                "address": _extract_address(snippet, city),
                "google_url": url,
                "source": "google_maps_searxng",
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
        log.debug(f"SearXNG Google Maps search failed: {e}")

    if not results:
        results = _ddg_fallback(city, sector, max_results)

    return results


def _ddg_fallback(city: str, sector: str, max_results: int) -> List[Dict]:
    """Fallback to DDG if SearXNG is down."""
    try:
        from duckduckgo_search import DDGS
        query = f"{sector} in {city} google maps"
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=min(max_results, 10)):
                url = r.get("href", "")
                title = r.get("title", "")
                snippet = r.get("body", "")

                if not title or not any(kw in url.lower() for kw in ["google.com/maps", "goo.gl/maps"]):
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
        return results
    except Exception:
        return []


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
        try:
            from curl_cffi import requests as cffi_requests
            r = cffi_requests.get("https://maps.googleapis.com/maps/api/place/textsearch/json", params=params, timeout=15)
        except ImportError:
            import requests
            r = requests.get("https://maps.googleapis.com/maps/api/place/textsearch/json", params=params, timeout=15)
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
        try:
            from curl_cffi import requests as cffi_requests
            r = cffi_requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=params, timeout=15)
        except ImportError:
            import requests
            r = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=params, timeout=15)
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
