"""
BBB (Better Business Bureau) API — free public data.

Discovers business complaints, ratings, and accreditation status.
"""
import os, logging, re, json, time
from typing import Dict, List, Optional

log = logging.getLogger("bbb_api")

try:
    import requests as _req
except ImportError:
    from curl_cffi import requests as _req

BBG_SEARCH_URL = "https://www.bbb.org/search"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def search_business(name: str, city: str, state: str = "") -> Dict:
    results = {
        "bbb_url": None,
        "bbb_rating": None,
        "bbb_accredited": None,
        "bbb_complaints": 0,
        "bbb_complaints_last3yrs": 0,
        "bbb_found": False,
    }

    query = f"{name} {city}"
    if state:
        query += f" {state}"

    try:
        r = _req.get(
            BBG_SEARCH_URL,
            params={"find_country": "US", "find_loc": city, "find_text": name, "find_type": "Category"},
            headers=_HEADERS,
            timeout=15,
        )
        if r.status_code != 200:
            return results

        text = r.text

        rating_match = re.search(r'class="bds-rating[^"]*"[^>]*>\s*([A-F][+-]?)\s*</span>', text)
        if rating_match:
            results["bbb_rating"] = rating_match.group(1).strip()
            results["bbb_found"] = True

        accred_match = re.search(r'BBB Accredited', text, re.IGNORECASE)
        if accred_match:
            results["bbb_accredited"] = True
        elif results["bbb_found"]:
            results["bbb_accredited"] = False

        complaint_match = re.search(r'(\d+)\s*(?:complaints?|BBB\s*complaints?)', text, re.IGNORECASE)
        if complaint_match:
            results["bbb_complaints"] = int(complaint_match.group(1))

        url_match = re.search(r'href="(https://www\.bbb\.org/profile/[^"]+)"', text)
        if url_match:
            results["bbb_url"] = url_match.group(1)

        if results["bbb_url"]:
            try:
                r2 = _req.get(results["bbb_url"], headers=_HEADERS, timeout=15)
                if r2.status_code == 200:
                    comp3 = re.search(r'(\d+)\s*complaints?\s*/?\s*(?:filed\s+)?(?:over\s+)?(?:the\s+)?last\s*3\s*years', r2.text, re.IGNORECASE)
                    if comp3:
                        results["bbb_complaints_last3yrs"] = int(comp3.group(1))
            except Exception:
                pass

    except Exception as e:
        log.debug(f"BBB search failed: {e}")

    return results


def search_batch(businesses: List[Dict]) -> List[Dict]:
    for biz in businesses:
        name = biz.get("name", "")
        city = biz.get("city", "")
        if name and city:
            bbb = search_business(name, city)
            biz.update(bbb)
            time.sleep(0.5)
    return businesses


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = search_business("Abccollision", "Miami", "FL")
    print(json.dumps(result, indent=2))
