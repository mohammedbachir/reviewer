"""
FindLeads — Vercel Entry Point (v9)
Dashboard + API + Scraper + Kimi AI + Crisis Predictor AI.
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
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

logger = logging.getLogger("app")


def _get_target():
    targets_path = os.path.join(ROOT_DIR, "targets.json")
    with open(targets_path) as f:
        raw = json.load(f)
    targets = raw if isinstance(raw, list) else raw.get("targets", [])
    for t in targets:
        if "sector" not in t and "category" in t:
            t["sector"] = t["category"]

    try:
        from exhaustion import SmartRotator
        rotator = SmartRotator(targets_path)
        try:
            from curl_cffi import requests as cffi_requests
            resp = cffi_requests.get(
                f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=10,
            )
            row = resp.json()[0]
            current_idx = row["current_index"]
        except Exception:
            current_idx = int(time.time()) % len(targets)

        target, idx = rotator.get_next(current_idx)
    except Exception:
        idx = int(time.time()) % len(targets)
        target = targets[idx]

    try:
        from curl_cffi import requests as cffi_requests
        cffi_requests.patch(
            f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
            json={"current_index": idx, "last_target": f"{target['city']}/{target.get('sector', target.get('category', ''))}"},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=minimal"},
            timeout=10,
        )
    except Exception:
        pass
    return target


def _load_model_state():
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(
            f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=5,
        )
        rows = resp.json()
        if rows:
            return rows[0].get("model_state", "")
    except Exception:
        pass
    return ""


def _save_model_state(model_b64):
    if not model_b64:
        return
    try:
        from curl_cffi import requests as cffi_requests
        cffi_requests.patch(
            f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
            json={"model_state": model_b64},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=minimal"},
            timeout=5,
        )
    except Exception:
        pass


def _save_snapshot(biz_id, biz):
    try:
        from curl_cffi import requests as cffi_requests
        cffi_requests.post(
            f"{SUPABASE_URL}/rest/v1/snapshots",
            json={
                "business_id": biz_id,
                "rating": biz.get("rating"),
                "review_count": biz.get("review_count"),
                "health_score": biz.get("health_score"),
                "sentiment_score": 1.0 if biz.get("sentiment") == "positive" else -1.0 if biz.get("sentiment") == "negative" else 0.0,
            },
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=minimal"},
            timeout=5,
        )
    except Exception:
        pass


def _get_snapshots(biz_id):
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(
            f"{SUPABASE_URL}/rest/v1/snapshots?business_id=eq.{biz_id}&order=scan_date.desc&limit=10",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=5,
        )
        return resp.json()
    except Exception:
        return []


def _get_all_businesses_for_graph():
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(
            f"{SUPABASE_URL}/rest/v1/businesses?select=id,name,city,sector,tech_stack,health_score,ssl_grade,breach_count,vulnerabilities,open_ports,breach_names,security_warnings",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=10,
        )
        data = resp.json()
        for biz in data:
            for field in ["vulnerabilities", "open_ports", "security_warnings", "breach_names", "tech_stack"]:
                val = biz.get(field)
                if isinstance(val, str):
                    try:
                        biz[field] = json.loads(val)
                    except Exception:
                        biz[field] = []
        return data
    except Exception:
        return []


def _save_crisis_prediction(biz_id, prediction):
    try:
        from curl_cffi import requests as cffi_requests
        cffi_requests.patch(
            f"{SUPABASE_URL}/rest/v1/businesses?id=eq.{biz_id}",
            json={
                "crisis_probability": prediction.get("crisis_probability", 0),
                "crisis_risk_level": prediction.get("risk_level", "UNKNOWN"),
                "crisis_recommendations": json.dumps(prediction.get("recommendations", [])),
                "cvss_severity": prediction.get("cvss", {}).get("severity", "NONE"),
                "cvss_max": prediction.get("cvss", {}).get("cvss_max", 0),
            },
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=minimal"},
            timeout=5,
        )
    except Exception:
        pass


def _validate_phone(phone):
    """Validate US/Canada phone: must be exactly 10 digits. Returns formatted or None."""
    import re as _re
    if not phone:
        return None
    digits = _re.sub(r'[^0-9]', '', str(phone))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "23456789":
        return digits
    return None


def _is_duplicate(biz, city, sector):
    """Check if business already exists in DB by website or phone."""
    import re as _re
    website = (biz.get("website") or "").strip().rstrip("/").replace("www.", "").lower()
    phone = biz.get("phone") or ""
    phone_digits = _re.sub(r'[^0-9]', '', str(phone))
    if len(phone_digits) == 11 and phone_digits.startswith("1"):
        phone_digits = phone_digits[1:]

    checks = []
    if website:
        checks.append(f"website=eq.{website}")
    if len(phone_digits) == 10:
        checks.append(f"phone=eq.{phone_digits}")
    if not checks:
        return False

    try:
        from curl_cffi import requests as cffi_requests
        query = "|".join(checks)
        resp = cffi_requests.get(
            f"{SUPABASE_URL}/rest/v1/businesses?select=id&{query}&limit=1",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=5,
        )
        rows = resp.json()
        return isinstance(rows, list) and len(rows) > 0
    except Exception:
        return False


def _upsert_business(biz, target):
    try:
        from curl_cffi import requests as cffi_requests
        tech = biz.get("tech_stack", [])
        if isinstance(tech, list):
            tech = json.dumps(tech)
        vulns = biz.get("vulnerabilities", [])
        if isinstance(vulns, list):
            vulns = json.dumps(vulns)
        open_ports = biz.get("open_ports", [])
        if isinstance(open_ports, list):
            open_ports = json.dumps(open_ports)
        security_warnings = biz.get("security_warnings", [])
        if isinstance(security_warnings, list):
            security_warnings = json.dumps(security_warnings)
        data = {
            "name": biz["name"],
            "city": target["city"],
            "sector": target["sector"],
            "website": biz.get("website", ""),
            "phone": _validate_phone(biz.get("phone", "")),
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
            "responds_to_reviews": biz.get("responds_to_reviews", False),
            "vulnerabilities": vulns,
            "open_ports": open_ports,
            "security_warnings": security_warnings,
            "breach_count": biz.get("breach_count", 0),
            "breach_names": json.dumps(biz.get("breach_names", [])),
            "crisis_probability": biz.get("crisis_probability", 0),
            "crisis_risk_level": biz.get("crisis_risk_level", "UNKNOWN"),
            "crisis_recommendations": json.dumps(biz.get("crisis_recommendations", [])),
            "cvss_severity": biz.get("cvss_severity", "NONE"),
            "cvss_max": biz.get("cvss_max", 0),
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
    vulns = biz.get("vulnerabilities", [])
    open_ports = biz.get("open_ports", [])
    breach_count = biz.get("breach_count", 0)

    if breach_count > 0:
        return "HOT"
    if ssl == "F":
        return "HOT"
    if health < 50:
        return "HOT"

    score = 0
    ssl_scores = {"F": 4, "D": 3, "C": 2, "B": 1, "A": 0}
    score += ssl_scores.get(ssl, 2)
    if rating > 0:
        if rating < 2.0: score += 4
        elif rating < 3.5: score += 3
        elif rating < 4.0: score += 2
        elif rating < 4.5: score += 1
    if health < 60: score += 2
    elif health < 80: score += 1
    outdated = [t for t in techs if "Outdated" in t or "Legacy" in t]
    score += min(len(outdated), 3)
    if not responds: score += 2
    if sentiment == "negative": score += 2
    elif sentiment == "neutral": score += 1
    if len(vulns) >= 3: score += 4
    elif len(vulns) >= 1: score += 2
    dangerous_ports = [p for p in open_ports if p in (3306, 5432, 6379, 27017, 9200, 11211)]
    if dangerous_ports: score += min(len(dangerous_ports), 3)
    if score >= 7: return "HOT"
    elif score >= 4: return "WARM"
    else: return "COLD"


def _generate_outreach_hook(biz, temperature):
    name = biz.get("name", "your business")
    ssl = biz.get("ssl_grade", "")
    rating = biz.get("rating", 0)
    review_count = biz.get("review_count", 0)
    health = biz.get("health_score", 50)
    vulns = biz.get("vulnerabilities", [])
    open_ports = biz.get("open_ports", [])
    breach_count = biz.get("breach_count", 0)
    breach_names = biz.get("breach_names", [])

    clean_name = _clean_name_for_hook(name)

    if breach_count > 0:
        breach_list = ", ".join(breach_names[:2]) if breach_names else "known breaches"
        ssl_note = f" and your SSL certificate needs attention (Grade {ssl})" if ssl in ("C", "D", "F") else ""
        return f"Hi {clean_name}/Team! I noticed your domain was involved in {breach_count} data breaches ({breach_list}){ssl_note}. We help businesses secure their data and improve their online presence. Reply to learn how."

    if ssl in ("F", "D"):
        health_note = f"and your website health score is {health}/100" if health < 60 else ""
        return f"Hi {clean_name}! Your SSL certificate has a failing grade ({ssl}) {health_note}. This drives customers away and hurts your rankings. We can fix that — reply to learn how."

    if ssl == "C" and health < 60:
        return f"Hi {clean_name}! Your site scored {health}/100 with SSL Grade {ssl} — both need improvement. We help businesses like yours get found and trusted online. Reply for a free audit."

    if health < 50:
        return f"Hi {clean_name}! Your website health score is {health}/100 — that's leaving money on the table. Let us help you fix it and attract more customers. Reply for a free review."

    if len(vulns) >= 1:
        return f"Hi {clean_name}! Your website has {len(vulns)} known security vulnerabilities that could cost you customers. We can secure your online presence — reply to learn how."

    dangerous = [p for p in open_ports if p in (3306, 5432, 6379, 27017)]
    if dangerous:
        return f"Hi {clean_name}! Critical services are exposed on your server (ports: {', '.join(str(p) for p in dangerous[:2])}). This is a security risk. We can help lock it down — reply for details."

    if rating > 0 and rating < 3.5:
        return f"Hi {clean_name}! Your Google rating ({rating}/5) is costing you potential customers. We help businesses like yours turn their online reputation into a growth engine. Reply to see how."

    if temperature == "HOT":
        return f"Hi {clean_name}! We help businesses like yours turn their online presence into a lead machine. Your competitors are already investing in this. Reply if you want to see how."

    if temperature == "WARM":
        return f"Hi {clean_name}! We help businesses like yours improve customer engagement through better online reputation. Reply if you're interested in a free assessment."

    return f"Hi {clean_name}! We help businesses improve their online presence and customer satisfaction. Reply for a free consultation."


def _clean_name_for_hook(name: str) -> str:
    if not name:
        return "there"
    skip = ["home", "contact", "about", "services", "welcome"]
    if name.lower().strip() in skip:
        return "there"
    if len(name) > 50 or "|" in name or "near" in name.lower() or "yellowpages" in name.lower():
        return "there"
    return name.strip()


def _enrich_business(biz):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    website = biz.get("website", "")
    domain = ""
    if website:
        try:
            domain = urlparse(website).netloc.replace("www.", "")
        except Exception:
            pass

    def _do_email():
        from scraper.email_finder import find_best_email
        try:
            return find_best_email(website, biz.get("name", ""))
        except Exception:
            return {}

    def _do_osint():
        from scraper.osint_engine import analyze_domain
        try:
            return analyze_domain(domain, biz.get("rating", 0), biz.get("review_count", 0))
        except Exception:
            return {}

    def _do_reviews():
        from scraper.review_engine import analyze_reviews
        try:
            return analyze_reviews(biz.get("name", ""), biz.get("city", ""), website)
        except Exception:
            return {}

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_email = ex.submit(_do_email) if website else None
        f_osint = ex.submit(_do_osint) if domain else None
        f_reviews = ex.submit(_do_reviews) if biz.get("name") else None
        email_result = f_email.result(timeout=8) if f_email else {}
        osint = f_osint.result(timeout=8) if f_osint else {}
        reviews = f_reviews.result(timeout=8) if f_reviews else {}

    if email_result.get("email"):
        biz["email"] = email_result["email"]
        biz["email_confidence"] = email_result.get("confidence", 0)
        biz["email_source"] = email_result.get("source", "")
    biz["breach_count"] = email_result.get("breach_count", 0)
    biz["breach_names"] = email_result.get("breach_names", [])

    if osint:
        biz["health_score"] = osint.get("health_score", 50)
        biz["ssl_grade"] = osint.get("ssl_grade", "C")
        biz["tech_stack"] = osint.get("tech_stack", [])
        biz["vulnerabilities"] = osint.get("vulnerabilities", [])
        biz["open_ports"] = osint.get("open_ports", [])
        biz["security_warnings"] = osint.get("security_warnings", [])
        biz["ssl_deep"] = osint.get("ssl_deep", {})
        biz["security_headers"] = osint.get("security_headers", {})
        biz["abuseipdb"] = osint.get("abuseipdb", {})

    if reviews:
        biz["sentiment"] = reviews.get("sentiment", "neutral")
        biz["responds_to_reviews"] = reviews.get("responds_to_reviews", False)
        if reviews.get("rating"):
            biz["rating"] = reviews["rating"]
        if reviews.get("review_count"):
            biz["review_count"] = reviews["review_count"]

    temperature = _score_lead(biz)
    biz["lead_temperature"] = temperature
    biz["outreach_hook"] = _generate_outreach_hook(biz, temperature)

    try:
        from scraper.crisis_predictor import predict_crisis
        model_b64 = _load_model_state()
        snapshots = []
        biz_id = biz.get("id")
        if biz_id:
            snapshots = _get_snapshots(biz_id)
        all_biz = _get_all_businesses_for_graph()
        crisis = predict_crisis(biz, all_businesses=all_biz, snapshots=snapshots, model_state_b64=model_b64)
        biz["crisis_probability"] = crisis.get("crisis_probability", 0)
        biz["crisis_risk_level"] = crisis.get("risk_level", "UNKNOWN")
        biz["crisis_recommendations"] = crisis.get("recommendations", [])
        biz["cvss_severity"] = crisis.get("cvss", {}).get("severity", "NONE")
        biz["cvss_max"] = crisis.get("cvss", {}).get("cvss_max", 0)
        new_model_b64 = crisis.get("model_state_b64")
        if new_model_b64:
            _save_model_state(new_model_b64)
    except Exception as e:
        logger.debug(f"Crisis prediction skipped: {e}")

    return biz


def _log_scan_run(city, sector, businesses_found, emails_found, osint_scanned, duration, status):
    try:
        from curl_cffi import requests as cffi_requests
        cffi_requests.post(
            f"{SUPABASE_URL}/rest/v1/scan_runs",
            json={"city": city, "sector": sector, "businesses_found": businesses_found, "emails_found": emails_found, "osint_scanned": osint_scanned, "duration_seconds": round(duration, 1), "status": status},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=minimal"},
            timeout=8,
        )
    except Exception:
        pass


def run_scrape():
    from scraper.finder import search_businesses
    t0 = time.time()
    HARD_DEADLINE = 22
    target = _get_target()
    city, sector = target["city"], target["sector"]
    businesses = search_businesses(city, sector, 1)
    if not businesses:
        _log_scan_run(city, sector, 0, 0, 0, time.time() - t0, "no_results")
        return {"status": "no_results", "target": f"{city} / {sector}", "elapsed_seconds": round(time.time() - t0, 1)}
    biz = businesses[0]
    if _is_duplicate(biz, city, sector):
        return {"status": "duplicate", "target": f"{city} / {sector}", "elapsed_seconds": round(time.time() - t0, 1)}
    if time.time() - t0 > HARD_DEADLINE:
        _log_scan_run(city, sector, 0, 0, 0, time.time() - t0, "timeout")
        return {"status": "timeout", "target": f"{city} / {sector}", "elapsed_seconds": round(time.time() - t0, 1)}
    enriched = _enrich_business(biz)
    _upsert_business(enriched, target)
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(
            f"{SUPABASE_URL}/rest/v1/businesses?select=id&name=eq.{enriched['name']}&city=eq.{city}&sector=eq.{sector}&limit=1",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=5,
        )
        rows = resp.json()
        if rows:
            _save_snapshot(rows[0]["id"], enriched)
    except Exception:
        pass
    has_email = 1 if enriched.get("email") else 0
    _log_scan_run(city, sector, 1, has_email, 1, time.time() - t0, "completed")
    return {
        "status": "completed",
        "target": f"{city} / {sector}",
        "business_name": enriched.get("name", ""),
        "email": enriched.get("email", ""),
        "lead_temperature": enriched.get("lead_temperature", ""),
        "health_score": enriched.get("health_score", 0),
        "crisis_risk_level": enriched.get("crisis_risk_level", "UNKNOWN"),
        "crisis_probability": enriched.get("crisis_probability", 0),
        "elapsed_seconds": round(time.time() - t0, 1),
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
        from dashboard_api import verify_token, get_stats, get_algorithms, get_companies, get_company, get_analytics, get_cities, get_sectors, get_security, get_crisis, get_osint_stats, get_osint_export, get_export_data, get_review_queue, approve_review, dismiss_review, get_exhaustion_status
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
            elif path == "/api/dashboard/security":
                self._respond(200, get_security())
            elif path == "/api/dashboard/crisis":
                self._respond(200, get_crisis())
            elif path == "/api/dashboard/osint":
                self._respond(200, get_osint_stats())
            elif path == "/api/dashboard/review-queue":
                self._respond(200, get_review_queue())
            elif path == "/api/dashboard/review-approve":
                biz_id = query.get("id", [""])[0]
                self._respond(200, approve_review(biz_id))
            elif path == "/api/dashboard/review-dismiss":
                biz_id = query.get("id", [""])[0]
                self._respond(200, dismiss_review(biz_id))
            elif path == "/api/dashboard/exhaustion":
                self._respond(200, get_exhaustion_status())
            elif path == "/api/dashboard/osint-export":
                firebase = query.get("firebase", [""])[0]
                archive_risk = query.get("archive_risk", [""])[0]
                api_risk = query.get("api_risk", [""])[0]
                sherlock_risk = query.get("sherlock_risk", [""])[0]
                crtsh_min = query.get("crtsh_min", [""])[0]
                min_keys = query.get("min_keys", [""])[0]
                min_profiles = query.get("min_profiles", [""])[0]
                min_subs = query.get("min_subs", [""])[0]
                temp = query.get("temp", [""])[0]
                city = query.get("city", [""])[0]
                sector = query.get("sector", [""])[0]
                ssl = query.get("ssl", [""])[0]
                search = query.get("search", [""])[0]
                min_risk_score = query.get("min_risk_score", [""])[0]
                columns = query.get("columns", [""])[0]
                self._respond(200, get_osint_export(firebase, archive_risk, api_risk, sherlock_risk, crtsh_min, min_keys, min_profiles, min_subs, temp, city, sector, ssl, search, min_risk_score, columns))
            elif path == "/api/dashboard/export":
                temp = query.get("temp", [""])[0]
                city = query.get("city", [""])[0]
                sector = query.get("sector", [""])[0]
                ssl = query.get("ssl", [""])[0]
                email = query.get("email", [""])[0]
                search = query.get("search", [""])[0]
                health_min = query.get("health_min", [""])[0]
                health_max = query.get("health_max", [""])[0]
                min_crisis = query.get("min_crisis", [""])[0]
                columns = query.get("columns", [""])[0]
                self._respond(200, get_export_data(temp, city, sector, ssl, email, search, health_min, health_max, min_crisis, columns))
            else:
                self._respond(404, {"error": "Not found"})
        except Exception as e:
            logger.error(f"Dashboard API error: {e}")
            self._respond(500, {"error": str(e)})

    def _handle_dashboard_api_post(self, path, query):
        import importlib
        import dashboard_api as _da
        importlib.reload(_da)
        from dashboard_api import verify_token, ask_ai, send_digest_email
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
                    self._respond(200, ask_ai(question, os.environ.get("OPENROUTER_API_KEY", ""), os.environ.get("KIMI_API_KEY", "")))
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
