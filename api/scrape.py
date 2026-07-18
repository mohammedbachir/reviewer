"""
FindLeads — Vercel Serverless Function
Entry point: /api/scrape?key=SECRET_KEY
Cycles through targets.json, scrapes one city+sector per invocation.
Stores results in Supabase PostgreSQL.
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

# Add scraper to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scraper"))

from finder import find_businesses
from email_finder import find_email_from_website
from osint_engine import analyze_domain

# ════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════

SECRET_KEY = os.environ.get("SCRAPE_SECRET_KEY", "findleads-default-key")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

LIMIT_PER_RUN = 10


# ════════════════════════════════════════════════════════════════
# SUPABASE CLIENT (lightweight — no SDK needed)
# ════════════════════════════════════════════════════════════════

from curl_cffi import requests as cffi_requests


def _supabase_get(table: str, query: str = ""):
    """GET from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{query}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    resp = cffi_requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
    return resp.json() if resp.status_code in (200, 201) else []


def _supabase_post(table: str, data: dict):
    """POST to Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation,resolution=merge-duplicates",
    }
    resp = cffi_requests.post(url, json=data, headers=headers, impersonate="chrome120", timeout=15)
    return resp.json() if resp.status_code in (200, 201) else []


def _supabase_patch(table: str, match: dict, data: dict):
    """PATCH/UPSERT in Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    # Build query params for matching
    params = "&".join(f"{k}=eq.{v}" for k, v in match.items())
    resp = cffi_requests.patch(f"{url}?{params}", json=data, headers=headers, impersonate="chrome120", timeout=15)
    return resp.json() if resp.status_code in (200, 201) else []


def _supabase_upsert(table: str, data: dict):
    """UPSERT to Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation,resolution=merge-duplicates",
    }
    resp = cffi_requests.post(url, json=[data], headers=headers, impersonate="chrome120", timeout=15)
    return resp.json() if resp.status_code in (200, 201) else []


# ════════════════════════════════════════════════════════════════
# TARGET ROTATION
# ════════════════════════════════════════════════════════════════

def _load_targets():
    """Load targets from targets.json."""
    targets_path = os.path.join(ROOT, "targets.json")
    with open(targets_path) as f:
        return json.load(f)["targets"]


def _get_current_index() -> int:
    """Get current target index from Supabase."""
    result = _supabase_get("system_state", "id=eq.1")
    if result and len(result) > 0:
        return result[0].get("current_index", 0)
    return 0


def _update_index(new_index: int, total_biz: int = 0):
    """Update target index and stats in Supabase."""
    _supabase_patch("system_state", {"id": 1}, {
        "current_index": new_index,
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "total_runs": f"total_runs+1",  # This won't work directly, need raw SQL
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


# ════════════════════════════════════════════════════════════════
# MAIN SCRAPE LOGIC
# ════════════════════════════════════════════════════════════════

def run_scrape():
    """Main scrape function. Called by Vercel serverless."""
    start_time = time.time()

    # Load targets and get current index
    targets = _load_targets()
    idx = _get_current_index() % len(targets)
    target = targets[idx]

    city = target["city"]
    sector = target["sector"]

    print(f"[Scrape] Target: {sector} in {city} (index {idx}/{len(targets)})")

    # 1. Record scan run
    run_data = {
        "city": city,
        "sector": sector,
        "status": "running",
    }

    # 2. Find businesses
    businesses = find_businesses(city, sector, limit=LIMIT_PER_RUN)
    print(f"[Scrape] Found {len(businesses)} businesses")

    # 3. Enrich each business
    emails_found = 0
    osint_scanned = 0

    for biz in businesses:
        biz["city"] = city
        biz["sector"] = sector

        # Find email
        if biz.get("website"):
            try:
                email = find_email_from_website(biz["website"])
                biz["email"] = email or ""
                if email:
                    emails_found += 1
            except Exception as e:
                print(f"  Email error for {biz['name']}: {e}")
                biz["email"] = ""

        # Run OSINT
        domain = ""
        if biz.get("website"):
            try:
                domain = urlparse(biz["website"]).netloc or biz["website"]
                domain = domain.replace("www.", "")
            except Exception:
                pass

        if domain:
            try:
                osint = analyze_domain(
                    domain,
                    rating=biz.get("rating", 0),
                    review_count=biz.get("review_count", 0),
                )
                biz["health_score"] = osint.get("health_score", 50)
                biz["ssl_grade"] = osint.get("ssl_grade", "")
                biz["tech_stack"] = json.dumps(osint.get("tech_stack", []))
                biz["dns_data"] = json.dumps(osint.get("dns", {}))
                biz["page_speed"] = json.dumps(osint.get("page_speed", {}))
                osint_scanned += 1
            except Exception as e:
                print(f"  OSINT error for {domain}: {e}")
                biz["health_score"] = 50

        # Upsert to Supabase
        try:
            _supabase_upsert("businesses", {
                "name": biz["name"],
                "city": biz["city"],
                "sector": biz["sector"],
                "rating": biz.get("rating", 0),
                "review_count": biz.get("review_count", 0),
                "website": biz.get("website", ""),
                "email": biz.get("email", ""),
                "phone": biz.get("phone", ""),
                "address": biz.get("address", ""),
                "category": biz.get("category", ""),
                "health_score": biz.get("health_score", 50),
                "ssl_grade": biz.get("ssl_grade", ""),
                "tech_stack": biz.get("tech_stack", "[]"),
                "dns_data": biz.get("dns_data", "{}"),
                "page_speed": biz.get("page_speed", "{}"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            print(f"  DB error for {biz['name']}: {e}")

    # 4. Record scan run completion
    duration = round(time.time() - start_time, 1)
    try:
        _supabase_post("scan_runs", {
            "city": city,
            "sector": sector,
            "businesses_found": len(businesses),
            "emails_found": emails_found,
            "osint_scanned": osint_scanned,
            "duration_seconds": duration,
            "status": "completed",
        })
    except Exception as e:
        print(f"  Scan run record error: {e}")

    # 5. Advance to next target
    next_idx = (idx + 1) % len(targets)
    _update_index(next_idx, len(businesses))

    return {
        "status": "success",
        "target": f"{sector} in {city}",
        "index": f"{idx}/{len(targets)}",
        "businesses": len(businesses),
        "emails": emails_found,
        "osint": osint_scanned,
        "duration": f"{duration}s",
        "next_target": f"{targets[next_idx]['sector']} in {targets[next_idx]['city']}",
    }


# ════════════════════════════════════════════════════════════════
# VERCEL HANDLER
# ════════════════════════════════════════════════════════════════

def handler(request, response):
    """Vercel Python serverless handler."""
    # CORS
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Content-Type"] = "application/json"

    # Check secret key
    params = request.args if hasattr(request, "args") else {}
    key = params.get("key", "") if params else ""

    if key != SECRET_KEY:
        response.status_code = 401
        return {"error": "Unauthorized"}

    # Health check
    path = request.path if hasattr(request, "path") else "/"
    if path == "/health" or path == "/api/health":
        return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

    # Stats
    if path == "/stats" or path == "/api/stats":
        try:
            businesses = _supabase_get("businesses", "select=count&limit=1")
            return {"total": len(businesses) if isinstance(businesses, list) else 0}
        except Exception:
            return {"total": 0}

    # Main scrape
    try:
        result = run_scrape()
        response.status_code = 200
        return result
    except Exception as e:
        response.status_code = 500
        return {"error": str(e)}


# For local testing
if __name__ == "__main__":
    # Load env from .env if exists
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

    result = run_scrape()
    print(json.dumps(result, indent=2))
