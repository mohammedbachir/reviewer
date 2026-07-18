"""
FindLeads — Vercel Entry Point (v3)
Lead scoring (HOT/WARM/COLD) + concurrent.futures + outreach hooks.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

SCRAPE_SECRET = os.environ.get("SCRAPE_SECRET_KEY", "findleads2026")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

logger = logging.getLogger("app")


def _get_target():
    targets_path = os.path.join(ROOT_DIR, "targets.json")
    with open(targets_path) as f:
        raw = json.load(f)
    targets = raw if isinstance(raw, list) else raw.get("targets", [])
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(
            f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
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
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=minimal"},
            timeout=10,
        )
    except Exception:
        pass
    return target


def _upsert_business(biz, target):
    try:
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
            "lead_temperature": biz.get("lead_temperature", "COLD"),
            "outreach_hook": biz.get("outreach_hook", ""),
            "email_confidence": biz.get("email_confidence", 0),
            "email_source": biz.get("email_source", ""),
            "sentiment": biz.get("sentiment", "neutral"),
        }
        cffi_requests.post(
            f"{SUPABASE_URL}/rest/v1/businesses",
            json=data,
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "resolution=merge-duplicates"},
            timeout=10,
        )
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════
# LEAD SCORING (HOT / WARM / COLD)
# ════════════════════════════════════════════════════════════════

def _score_lead(biz: dict) -> str:
    """
    Classify lead temperature based on multiple signals.
    HOT: SSL < B, rating < 3.5, ignoring reviews → easy sell
    WARM: SSL B, rating 3.5-4.0, slow site → moderate opportunity
    COLD: SSL A, rating > 4.5, modern tech → hard sell
    """
    ssl = biz.get("ssl_grade", "F")
    rating = biz.get("rating", 0)
    health = biz.get("health_score", 50)
    techs = biz.get("tech_stack", [])
    responds = biz.get("responds_to_reviews", False)
    sentiment = biz.get("sentiment", "neutral")

    score = 0

    # SSL grading (higher score = more vulnerable)
    ssl_scores = {"F": 4, "D": 3, "C": 2, "B": 1, "A": 0}
    score += ssl_scores.get(ssl, 2)

    # Rating (lower = more negative reviews = easier to approach)
    if rating > 0:
        if rating < 2.0:
            score += 4
        elif rating < 3.5:
            score += 3
        elif rating < 4.0:
            score += 2
        elif rating < 4.5:
            score += 1

    # Health score (lower = more outdated = easier to approach)
    if health < 40:
        score += 3
    elif health < 60:
        score += 2
    elif health < 80:
        score += 1

    # Tech stack (outdated = easier)
    outdated = [t for t in techs if "Outdated" in t or "Legacy" in t]
    score += min(len(outdated), 3)

    # Does NOT respond to reviews = HOT signal
    if not responds:
        score += 2

    # Negative sentiment = HOT signal
    if sentiment == "negative":
        score += 2
    elif sentiment == "neutral":
        score += 1

    # Classify
    if score >= 7:
        return "HOT"
    elif score >= 4:
        return "WARM"
    else:
        return "COLD"


def _generate_outreach_hook(biz: dict, temperature: str) -> str:
    """Generate a personalized outreach hook."""
    name = biz.get("name", "your business")
    ssl = biz.get("ssl_grade", "")
    rating = biz.get("rating", 0)
    techs = biz.get("tech_stack", [])
    health = biz.get("health_score", 50)

    hooks = []

    if ssl in ("D", "F"):
        hooks.append(f"Your website SSL certificate needs attention (grade {ssl})")
    if rating > 0 and rating < 3.5:
        hooks.append(f"Your Google rating ({rating}/5) could be improved")
    outdated = [t for t in techs if "Outdated" in t or "Legacy" in t]
    if outdated:
        hooks.append(f"Your website uses outdated technology ({', '.join(outdated[:2])})")
    if health < 50:
        hooks.append(f"Your website health score is {health}/100")

    if hooks:
        return f"Hi {name}! I noticed: {'; '.join(hooks[:2])}. We help businesses improve their online presence."
    elif temperature == "WARM":
        return f"Hi {name}! We help businesses like yours improve customer engagement through better online reputation."
    else:
        return f"Hi {name}! We help businesses improve their online presence and customer satisfaction."


# ════════════════════════════════════════════════════════════════
# PARALLEL ENRICHMENT
# ════════════════════════════════════════════════════════════════

def _enrich_business(biz: dict) -> dict:
    """Enrich a single business with email + OSINT + review data."""
    from scraper.email_finder import find_best_email
    from scraper.osint_engine import analyze_domain
    from scraper.review_engine import analyze_reviews

    website = biz.get("website", "")
    domain = ""
    if website:
        try:
            domain = urlparse(website).netloc.replace("www.", "")
        except Exception:
            pass

    # Email discovery
    if website:
        try:
            email_result = find_best_email(website, biz.get("name", ""))
            if email_result.get("email"):
                biz["email"] = email_result["email"]
                biz["email_confidence"] = email_result.get("confidence", 0)
                biz["email_source"] = email_result.get("source", "")
        except Exception as e:
            logger.debug(f"  Email error for {biz['name']}: {e}")

    # OSINT
    if domain:
        try:
            osint = analyze_domain(domain, biz.get("rating", 0), biz.get("review_count", 0))
            biz["health_score"] = osint["health_score"]
            biz["ssl_grade"] = osint["ssl_grade"]
            biz["tech_stack"] = osint["tech_stack"]
        except Exception as e:
            logger.debug(f"  OSINT error for {biz['name']}: {e}")

    # Review analysis
    try:
        review_data = analyze_reviews(biz.get("name", ""), biz.get("city", ""), website)
        biz["sentiment"] = review_data.get("sentiment", "neutral")
        biz["responds_to_reviews"] = review_data.get("responds_to_reviews", False)
        if review_data.get("rating") and not biz.get("rating"):
            biz["rating"] = review_data["rating"]
        if review_data.get("review_count") and not biz.get("review_count"):
            biz["review_count"] = review_data["review_count"]
    except Exception as e:
        logger.debug(f"  Review error for {biz['name']}: {e}")

    # Lead scoring
    temperature = _score_lead(biz)
    biz["lead_temperature"] = temperature
    biz["outreach_hook"] = _generate_outreach_hook(biz, temperature)

    return biz


# ════════════════════════════════════════════════════════════════
# MAIN SCRAPE
# ════════════════════════════════════════════════════════════════

def run_scrape():
    from scraper.finder import search_businesses
    from concurrent.futures import ThreadPoolExecutor, as_completed

    t0 = time.time()
    HARD_DEADLINE = 52  # seconds — leave 8s buffer for Supabase upserts

    target = _get_target()
    city, sector = target["city"], target["sector"]
    max_results = min(target.get("max_results", 20), 20)

    businesses = search_businesses(city, sector, max_results)
    logger.info(f"Found {len(businesses)} businesses in {city}/{sector}")

    elapsed_search = time.time() - t0
    remaining = HARD_DEADLINE - elapsed_search
    per_biz_timeout = max(8, remaining / max(len(businesses), 1))

    enriched = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_biz = {
            executor.submit(_enrich_business, biz): biz
            for biz in businesses
        }
        for future in as_completed(future_to_biz):
            if time.time() - t0 > HARD_DEADLINE:
                for f in future_to_biz:
                    f.cancel()
                break
            try:
                result = future.result(timeout=per_biz_timeout)
                enriched.append(result)
            except Exception as e:
                logger.debug(f"  Enrichment timeout/error: {e}")

    # Upsert to Supabase (only within deadline)
    for biz in enriched:
        if time.time() - t0 > HARD_DEADLINE:
            break
        _upsert_business(biz, target)

    # Statistics
    emails_found = sum(1 for b in enriched if b.get("email"))
    hot = sum(1 for b in enriched if b.get("lead_temperature") == "HOT")
    warm = sum(1 for b in enriched if b.get("lead_temperature") == "WARM")
    cold = sum(1 for b in enriched if b.get("lead_temperature") == "COLD")
    avg_health = sum(b.get("health_score", 50) for b in enriched) / len(enriched) if enriched else 0

    elapsed = time.time() - t0

    return {
        "status": "completed",
        "target": f"{city} / {sector}",
        "businesses_found": len(enriched),
        "emails_found": emails_found,
        "avg_health_score": round(avg_health),
        "lead_temperatures": {"HOT": hot, "WARM": warm, "COLD": cold},
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class handler(BaseHTTPRequestHandler):
    def _path_base(self):
        return self.path.split("?")[0] if self.path else "/"

    def do_GET(self):
        p = self._path_base()
        if p == "/api/scrape":
            self._handle_scrape()
        elif p == "/api/health":
            self._respond(200, {"status": "ok", "version": "3.0"})
        elif p == "/":
            self._respond(200, {"name": "FindLeads", "version": "3.0", "architecture": "serverless"})
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        p = self._path_base()
        if p == "/api/scrape":
            self._handle_scrape()
        else:
            self._respond(404, {"error": "Not found"})

    def _handle_scrape(self):
        if self.path and "?" in self.path:
            query = self.path.split("?", 1)[1]
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            if params.get("key") != SCRAPE_SECRET:
                self._respond(403, {"error": "Invalid key"})
                return

        result = run_scrape()
        self._respond(200, result)

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
