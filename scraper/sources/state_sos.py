"""
State Secretary of State Business Registry — free bulk downloads.

Discovers recently registered businesses by state.
Data is public record and free to access.
"""
import os, logging, json, csv, io, time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

log = logging.getLogger("state_sos")

try:
    import requests as _req
except ImportError:
    from curl_cffi import requests as _req


STATE_REGISTRY_URLS = {
    "FL": "https://search.sunbiz.org/Inquiry/CorporationSearch/SearchByName",
    "TX": "https://mycpa.cpa.state.tx.us/coa/srchTypeAction.do",
    "CA": "https://bizfileonline.sos.ca.gov/search/business",
    "NY": "https://appext20.dos.ny.gov/corp_public/CORPSEARCH.ETR",
    "IL": "https://www.ilsos.gov/corporatellc/LLC120.201?P=1",
    "AZ": "https://ecorp.azcc.gov/EntitySearch/Index",
    "CO": "https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do",
    "GA": "https://ecorp.sos.ga.gov/BusinessSearch",
    "WA": "https://ccfs.sos.wa.gov/search/NameSearch",
    "NV": "https://esos.nv.gov/EntitySearch/BusinessSearch",
}

STATE_CODES = {
    "Miami": "FL", "Tampa": "FL", "Orlando": "FL", "Jacksonville": "FL",
    "Houston": "TX", "Dallas": "TX", "San Antonio": "TX", "Austin": "TX",
    "Los Angeles": "CA", "San Diego": "CA", "San Francisco": "CA", "Scottsdale": "CA",
    "Beverly Hills": "CA",
    "New York": "NY",
    "Chicago": "IL", "Minneapolis": "IL",
    "Phoenix": "AZ", "Scottsdale": "AZ",
    "Denver": "CO", "Salt Lake City": "CO",
    "Atlanta": "GA",
    "Seattle": "WA", "Portland": "WA",
    "Las Vegas": "NV",
    "Charlotte": "NC", "Nashville": "TN", "Washington": "DC",
    "Boston": "MA", "Philadelphia": "PA",
}


def discover_recent_businesses(state: str, days_back: int = 30, max_results: int = 50) -> List[Dict]:
    if state not in STATE_REGISTRY_URLS:
        log.debug(f"No registry URL for state: {state}")
        return []

    results = []

    if state == "FL":
        try:
            r = _req.get(
                "https://search.sunbiz.org/Inquiry/CorporationSearch/GetResultList",
                params={
                    "SearchNameOrder": "",
                    "SearchTerm": "",
                    "SearchType": "Contains",
                    "FilingType": "ALL",
                    "ListNameType": "L",
                    "DateFrom": (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y"),
                    "DateTo": datetime.now().strftime("%m/%d/%Y"),
                },
                timeout=15,
            )
            if r.status_code == 200:
                import re
                names = re.findall(r'<span class="resultText">(.*?)</span>', r.text)
                for name in names[:max_results]:
                    results.append({
                        "name": name.strip(),
                        "state": "FL",
                        "source": "state_sos",
                        "registration_recency": f"last_{days_back}_days",
                    })
        except Exception as e:
            log.debug(f"FL registry failed: {e}")

    elif state == "TX":
        try:
            r = _req.get(
                "https://mycpa.cpa.state.tx.us/coa/srchTypeAction.do",
                params={
                    "p_oid": "",
                    "p_display_detail": "list",
                    "p_sort": "name",
                    "search_type": "entity",
                    "search_term": "",
                    "p_filing_from": (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y"),
                    "p_filing_to": datetime.now().strftime("%m/%d/%Y"),
                },
                timeout=15,
            )
            if r.status_code == 200:
                import re
                rows = re.findall(r'<td class="leftCol">(.*?)</td>', r.text)
                for name in rows[:max_results]:
                    results.append({
                        "name": name.strip(),
                        "state": "TX",
                        "source": "state_sos",
                        "registration_recency": f"last_{days_back}_days",
                    })
        except Exception as e:
            log.debug(f"TX registry failed: {e}")

    elif state == "NV":
        try:
            r = _req.get(
                "https://esos.nv.gov/api/BusinessSearch/SearchBusiness",
                params={
                    "searchType": "EntityName",
                    "searchValue": "",
                    "sortColumn": "EntityName",
                    "sortOrder": "asc",
                    "startDate": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d"),
                    "endDate": datetime.now().strftime("%Y-%m-%d"),
                    "pageSize": str(max_results),
                    "page": "1",
                },
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                for biz in data.get("data", [])[:max_results]:
                    results.append({
                        "name": biz.get("EntityName", ""),
                        "state": "NV",
                        "source": "state_sos",
                        "registration_recency": f"last_{days_back}_days",
                    })
        except Exception as e:
            log.debug(f"NV registry failed: {e}")

    log.info(f"Discovered {len(results)} recent businesses in {state}")
    return results


def discover_for_city(city: str, days_back: int = 30) -> List[Dict]:
    state = STATE_CODES.get(city)
    if not state:
        return []
    return discover_recent_businesses(state, days_back=days_back)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = discover_for_city("Miami", days_back=7)
    for r in results[:5]:
        print(f"  {r['name']} ({r['state']})")
    print(f"Total: {len(results)}")
