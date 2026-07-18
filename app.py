"""
FindLeads — Vercel Entry Point
Serverless micro-scraping: curl_cffi + DuckDuckGo + Supabase
"""

import os
import sys
import json
import hashlib
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

SCRAPE_SECRET = os.environ.get("SCRAPE_SECRET_KEY", "findleads2026")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

from scraper.finder import find_businesses
from scraper.email_finder import find_email_from_website
from scraper.osint_engine import analyze_domain
from urllib.parse import urlparse


def _get_target():
    with open(os.path.join(ROOT_DIR, "targets.json")) as f:
        raw = json.load(f)
    targets = raw if isinstance(raw, list) else raw.get("targets", [])
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(
            f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            timeout=10,
        )
        row = resp.json()[0]
        idx = (row["current_index"] + 1) % len(targets)
    except Exception:
        idx = int(time.time()) % len(targets)

    target = targets[idx]
    try:
        from curl_cffi import requests as cffi_requests
        cffi_requests.patch(
            f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
            json={"current_index": idx, "last_target": f"{target['city']}/{target['sector']}"},
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Prefer": "return=minimal",
            },
            timeout=10,
        )
    except Exception:
        pass

    return target


def _upsert_business(biz, target):
    from curl_cffi import requests as cffi_requests
    data = {
        "name": biz["name"],
        "city": target["city"],
        "sector": target["sector"],
        "website": biz.get("website", ""),
        "phone": biz.get("phone", ""),
        "rating": biz.get("rating"),
        "review_count": biz.get("review_count"),
        "health_score": biz.get("health_score"),
        "email": biz.get("email"),
        "ssl_grade": biz.get("ssl_grade", ""),
        "tech_stack": biz.get("tech_stack", []),
    }
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "resolution=merge-duplicates",
    }
    try:
        cffi_requests.post(
            f"{SUPABASE_URL}/rest/v1/businesses",
            json=data,
            headers=headers,
            timeout=10,
        )
    except Exception:
        pass


def run_scrape():
    t0 = time.time()
    target = _get_target()
    city, sector = target["city"], target["sector"]

    businesses = find_businesses(city, sector, target.get("max_results", 20))
    emails = 0
    healths = []

    for biz in businesses:
        website = biz.get("website", "")
        if website:
            email = find_email_from_website(website)
            if email:
                biz["email"] = email
                emails += 1

            domain = urlparse(website).netloc.replace("www.", "")
            osint = analyze_domain(domain, biz.get("rating"), biz.get("review_count"))
            biz["health_score"] = osint["health_score"]
            biz["ssl_grade"] = osint["ssl_grade"]
            biz["tech_stack"] = osint["tech_stack"]
            healths.append(osint["health_score"])

            _upsert_business(biz, target)

    elapsed = time.time() - t0
    avg_health = sum(healths) / len(healths) if healths else 0

    return {
        "status": "completed",
        "target": f"{city} / {sector}",
        "businesses_found": len(businesses),
        "emails_found": emails,
        "avg_health_score": round(avg_health),
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/scrape":
            self._handle_scrape()
        elif self.path == "/api/health":
            self._respond(200, {"status": "ok", "version": "2.0"})
        elif self.path == "/":
            self._respond(200, {"name": "FindLeads", "version": "2.0", "architecture": "serverless"})
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/api/scrape":
            self._handle_scrape()
        else:
            self._respond(404, {"error": "Not found"})

    def _handle_scrape(self):
        if self.path and "?" in self.path:
            query = self.path.split("?", 1)[1]
            params = dict(p.split("=") for p in query.split("&") if "=" in p)
            if params.get("key") != SCRAPE_SECRET:
                self._respond(403, {"error": "Invalid key"})
                return
        elif not SUPABASE_URL:
            self._respond(500, {"error": "Missing SUPABASE_URL"})
            return

        result = run_scrape()
        self._respond(200, result)

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
