"""
FindLeads — Vercel Entry Point (v4)
Dashboard + API + Scraper + Kimi AI.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

SCRAPE_SECRET = os.environ.get("SCRAPE_SECRET_KEY", "findleads2026")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SCRAPE_SECRET_KEY", "findleads2026")

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
        tech = biz.get("tech_stack", [])
        if isinstance(tech, list):
            tech = json.dumps(tech)
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
            "tech_stack": tech,
            "lead_temperature": biz.get("lead_temperature", "COLD"),
            "outreach_hook": biz.get("outreach_hook", ""),
            "email_confidence": biz.get("email_confidence", 0),
            "email_source": biz.get("email_source", ""),
            "sentiment": biz.get("sentiment", "neutral"),
        }
        resp = cffi_requests.post(
            f"{SUPABASE_URL}/rest/v1/businesses",
            json=data,
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "resolution=merge-duplicates"},
            timeout=10,
        )
        if resp.status_code >= 400:
            logger.warning(f"Upsert failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Upsert exception: {e}")


def _score_lead(biz):
    ssl = biz.get("ssl_grade", "F")
    rating = biz.get("rating", 0)
    health = biz.get("health_score", 50)
    techs = biz.get("tech_stack", [])
    responds = biz.get("responds_to_reviews", False)
    sentiment = biz.get("sentiment", "neutral")
    score = 0
    ssl_scores = {"F": 4, "D": 3, "C": 2, "B": 1, "A": 0}
    score += ssl_scores.get(ssl, 2)
    if rating > 0:
        if rating < 2.0: score += 4
        elif rating < 3.5: score += 3
        elif rating < 4.0: score += 2
        elif rating < 4.5: score += 1
    if health < 40: score += 3
    elif health < 60: score += 2
    elif health < 80: score += 1
    outdated = [t for t in techs if "Outdated" in t or "Legacy" in t]
    score += min(len(outdated), 3)
    if not responds: score += 2
    if sentiment == "negative": score += 2
    elif sentiment == "neutral": score += 1
    if score >= 7: return "HOT"
    elif score >= 4: return "WARM"
    else: return "COLD"


def _generate_outreach_hook(biz, temperature):
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


def _enrich_business(biz):
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
    if website:
        try:
            email_result = find_best_email(website, biz.get("name", ""))
            if email_result.get("email"):
                biz["email"] = email_result["email"]
                biz["email_confidence"] = email_result.get("confidence", 0)
                biz["email_source"] = email_result.get("source", "")
        except Exception as e:
            logger.debug(f"  Email error: {e}")
    if domain:
        try:
            osint = analyze_domain(domain, biz.get("rating", 0), biz.get("review_count", 0))
            biz["health_score"] = osint["health_score"]
            biz["ssl_grade"] = osint["ssl_grade"]
            biz["tech_stack"] = osint["tech_stack"]
        except Exception as e:
            logger.debug(f"  OSINT error: {e}")
    try:
        review_data = analyze_reviews(biz.get("name", ""), biz.get("city", ""), website)
        biz["sentiment"] = review_data.get("sentiment", "neutral")
        biz["responds_to_reviews"] = review_data.get("responds_to_reviews", False)
        if review_data.get("rating") and not biz.get("rating"):
            biz["rating"] = review_data["rating"]
        if review_data.get("review_count") and not biz.get("review_count"):
            biz["review_count"] = review_data["review_count"]
    except Exception as e:
        logger.debug(f"  Review error: {e}")
    temperature = _score_lead(biz)
    biz["lead_temperature"] = temperature
    biz["outreach_hook"] = _generate_outreach_hook(biz, temperature)
    return biz


def run_scrape():
    from scraper.finder import search_businesses
    from concurrent.futures import ThreadPoolExecutor, as_completed
    t0 = time.time()
    HARD_DEADLINE = 52
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
        future_to_biz = {executor.submit(_enrich_business, biz): biz for biz in businesses}
        for future in as_completed(future_to_biz):
            if time.time() - t0 > HARD_DEADLINE:
                for f in future_to_biz: f.cancel()
                break
            try:
                result = future.result(timeout=per_biz_timeout)
                enriched.append(result)
            except Exception as e:
                logger.debug(f"  Enrichment error: {e}")
    for biz in enriched:
        if time.time() - t0 > HARD_DEADLINE: break
        _upsert_business(biz, target)
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


def _parse_query(path):
    if "?" in path:
        return parse_qs(path.split("?", 1)[1])
    return {}


class handler(BaseHTTPRequestHandler):
    def _path_base(self):
        return self.path.split("?")[0] if self.path else "/"

    def do_GET(self):
        p = self._path_base()
        q = _parse_query(self.path)

        if p == "/api/scrape":
            self._handle_scrape()
        elif p == "/api/health":
            self._respond(200, {"status": "ok", "version": "4.0", "supabase_url_set": bool(SUPABASE_URL), "supabase_key_set": bool(SUPABASE_KEY), "openrouter_set": bool(os.environ.get("OPENROUTER_API_KEY", ""))})
        elif p == "/dashboard" or p == "/dashboard/":
            self._serve_dashboard()
        elif p.startswith("/api/dashboard/"):
            self._handle_dashboard_api(p, q)
        elif p == "/api/dashboard/login":
            self._respond(405, {"error": "Use POST"})
        elif p == "/":
            self._respond(200, {"name": "FindLeads", "version": "4.0", "architecture": "serverless", "dashboard": "/dashboard"})
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        p = self._path_base()
        q = _parse_query(self.path)
        if p == "/api/scrape":
            self._handle_scrape()
        elif p == "/api/dashboard/login":
            self._handle_login(q)
        elif p.startswith("/api/dashboard/"):
            self._handle_dashboard_api_post(p, q)
        else:
            self._respond(404, {"error": "Not found"})

    def _handle_login(self, query):
        from dashboard_api import login
        password = query.get("password", [""])[0]
        token = login(password)
        if token:
            self._respond(200, {"token": token, "status": "ok"})
        else:
            self._respond(401, {"error": "Invalid password"})

    def _handle_dashboard_api(self, path, query):
        from dashboard_api import verify_token, get_stats, get_algorithms, get_companies, get_company, get_analytics, get_cities, get_sectors
        token = query.get("token", [""])[0]
        if not verify_token(token):
            self._respond(401, {"error": "Unauthorized"})
            return
        try:
            if path == "/api/dashboard/stats":
                self._respond(200, get_stats())
            elif path == "/api/dashboard/algorithms":
                self._respond(200, get_algorithms())
            elif path == "/api/dashboard/companies":
                page = int(query.get("page", ["1"])[0])
                per_page = int(query.get("per_page", ["20"])[0])
                city = query.get("city", [""])[0]
                sector = query.get("sector", [""])[0]
                temp = query.get("temp", [""])[0]
                email_filter = query.get("email", [""])[0]
                search = query.get("search", [""])[0]
                self._respond(200, get_companies(page, per_page, city, sector, temp, email_filter, search))
            elif path.startswith("/api/dashboard/company/"):
                cid = path.split("/")[-1]
                company = get_company(cid)
                if company:
                    self._respond(200, company)
                else:
                    self._respond(404, {"error": "Company not found"})
            elif path == "/api/dashboard/analytics":
                self._respond(200, get_analytics())
            elif path == "/api/dashboard/cities":
                self._respond(200, get_cities())
            elif path == "/api/dashboard/sectors":
                self._respond(200, get_sectors())
            else:
                self._respond(404, {"error": "Not found"})
        except Exception as e:
            logger.error(f"Dashboard API error: {e}")
            self._respond(500, {"error": str(e)})

    def _handle_dashboard_api_post(self, path, query):
        import importlib
        import dashboard_api as _da
        importlib.reload(_da)
        from dashboard_api import verify_token, ask_kimi, send_digest_email
        token = query.get("token", [""])[0]
        if not verify_token(token):
            self._respond(401, {"error": "Unauthorized"})
            return
        try:
            if path == "/api/dashboard/ask-ai":
                question = query.get("question", [""])[0]
                if not question:
                    self._respond(400, {"error": "No question provided"})
                else:
                    self._respond(200, ask_kimi(question, os.environ.get("OPENROUTER_API_KEY", ""), os.environ.get("KIMI_API_KEY", "")))
            elif path == "/api/dashboard/digest":
                self._respond(200, send_digest_email())
            else:
                self._respond(404, {"error": "Not found"})
        except Exception as e:
            logger.error(f"Dashboard POST error: {e}")
            self._respond(500, {"error": str(e)})

    def _serve_dashboard(self):
        candidates = [
            os.path.join(ROOT_DIR, "public", "dashboard.html"),
            os.path.join(ROOT_DIR, "dashboard.html"),
            os.path.join("/var/task", "public", "dashboard.html"),
        ]
        for dashboard_path in candidates:
            if os.path.exists(dashboard_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(dashboard_path, "rb") as f:
                    self.wfile.write(f.read())
                return
        self._respond(404, {"error": "Dashboard not found", "tried": candidates})

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
