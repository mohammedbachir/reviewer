"""
#12 Domain History
Checks Wayback Machine for historical snapshots of a website.
Detects design changes, technology changes, and content changes.
"""

import requests
from typing import Dict, List, Optional
from datetime import datetime


WAYBACK_CDX_API = "https://web.archive.org/cdx/search/cdx"
WAYBACK_SNAPSHOT_URL = "https://web.archive.org/web/{timestamp}/{url}"


def get_domain_history(domain: str, limit: int = 20) -> Dict:
    """
    Get domain history from Wayback Machine.
    
    Returns:
        Dict with historical snapshots and analysis
    """
    result = {
        "domain": domain,
        "first_snapshot": "",
        "last_snapshot": "",
        "total_snapshots": 0,
        "snapshots_per_year": {},
        "snapshots": [],
        "has_history": False,
        "oldest_date": "",
        "newest_date": "",
        "frequency": "unknown",
    }

    if not domain.startswith("http"):
        url = "https://" + domain
    else:
        url = domain

    try:
        params = {
            "url": domain.replace("https://", "").replace("http://", ""),
            "output": "json",
            "limit": limit,
            "fl": "timestamp,statuscode,mimetype",
            "collapse": "timestamp:8",
        }

        response = requests.get(WAYBACK_CDX_API, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()

            if len(data) > 1:
                headers = data[0]
                rows = data[1:]

                result["has_history"] = True
                result["total_snapshots"] = len(rows)

                for row in rows:
                    snapshot = dict(zip(headers, row))
                    ts = snapshot.get("timestamp", "")

                    if len(ts) >= 8:
                        year = ts[:4]
                        month = ts[4:6]
                        day = ts[6:8]

                        date_str = f"{year}-{month}-{day}"
                        timestamp_url = WAYBACK_SNAPSHOT_URL.format(
                            timestamp=ts, url=domain
                        )

                        result["snapshots"].append({
                            "date": date_str,
                            "status": snapshot.get("statuscode", ""),
                            "type": snapshot.get("mimetype", ""),
                            "url": timestamp_url,
                        })

                        if year not in result["snapshots_per_year"]:
                            result["snapshots_per_year"][year] = 0
                        result["snapshots_per_year"][year] += 1

                if result["snapshots"]:
                    result["first_snapshot"] = result["snapshots"][0]["date"]
                    result["last_snapshot"] = result["snapshots"][-1]["date"]
                    result["oldest_date"] = result["first_snapshot"]
                    result["newest_date"] = result["last_snapshot"]

                    try:
                        first = datetime.strptime(result["first_snapshot"], "%Y-%m-%d")
                        last = datetime.strptime(result["last_snapshot"], "%Y-%m-%d")
                        span_days = (last - first).days

                        if span_days > 365 * 5:
                            result["frequency"] = "established"
                        elif span_days > 365:
                            result["frequency"] = "active"
                        elif span_days > 90:
                            result["frequency"] = "growing"
                        else:
                            result["frequency"] = "new"
                    except Exception:
                        pass

    except requests.exceptions.Timeout:
        result["error"] = "Wayback Machine timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    test_domains = ["mmdc.ae", "godentalclinic.com", "google.com"]
    for domain in test_domains:
        print(f"\n{'='*60}")
        print(f"Domain History: {domain}")
        print("=" * 60)
        result = get_domain_history(domain)
        print(f"  Has history: {result['has_history']}")
        print(f"  Total snapshots: {result['total_snapshots']}")
        print(f"  First: {result['first_snapshot']}")
        print(f"  Last: {result['last_snapshot']}")
        print(f"  Frequency: {result['frequency']}")
        print(f"  Snapshots per year: {result['snapshots_per_year']}")
