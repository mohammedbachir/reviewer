"""
FindLeads — Local Scraper Daemon
Runs on your PC, scrapes every 2 hours in parallel with Vercel cron.
Direct Supabase writes — no timeout limit.
"""

import os
import sys
import json
import time
import socket
import logging
from datetime import datetime, timezone

from urllib.parse import urlparse

import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver()
dns.resolver.default_resolver.nameservers = ["8.8.8.8", "8.8.4.4"]

_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        answers = dns.resolver.resolve(host, "A")
        ip = str(answers[0])
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]
    except Exception:
        return _original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

from curl_cffi import requests as cffi_requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("daemon")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lgbzpwzpkzbquuwwhbin.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

STATE_FILE = os.path.join(ROOT_DIR, ".daemon_state.json")
INTERVAL_SECONDS = 30  # 30 seconds between runs (continuous mode)
MAX_WORKERS = 5


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"current_index": -1, "total_runs": 0, "total_businesses": 0, "total_emails": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_target():
    with open(os.path.join(ROOT_DIR, "targets.json")) as f:
        raw = json.load(f)
    targets = raw if isinstance(raw, list) else raw.get("targets", [])
    # Normalize 'category' → 'sector' for backward compatibility
    for t in targets:
        if "sector" not in t and "category" in t:
            t["sector"] = t["category"]
    state = load_state()
    idx = (state["current_index"] + 1) % len(targets)
    target = targets[idx]
    state["current_index"] = idx
    save_state(state)
    return target, idx, len(targets)


def upsert_business(biz, target):
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
        "vulnerabilities": vulns,
        "open_ports": open_ports,
        "breaches": biz.get("breaches", 0),
        "security_warnings": security_warnings,
        "breach_count": biz.get("breach_count", 0),
        "breach_names": json.dumps(biz.get("breach_names", [])),
    }
    resp = cffi_requests.post(
        f"{SUPABASE_URL}/rest/v1/businesses",
        json=data,
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
        timeout=10,
    )
    return resp.status_code < 400


def score_lead(biz):
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
        if rating < 2.0:
            score += 4
        elif rating < 3.5:
            score += 3
        elif rating < 4.0:
            score += 2
        elif rating < 4.5:
            score += 1
    if health < 60:
        score += 2
    elif health < 80:
        score += 1
    outdated = [t for t in techs if "Outdated" in t or "Legacy" in t]
    score += min(len(outdated), 3)
    if not responds:
        score += 2
    if sentiment == "negative":
        score += 2
    elif sentiment == "neutral":
        score += 1
    if len(vulns) >= 3:
        score += 4
    elif len(vulns) >= 1:
        score += 2
    dangerous_ports = [p for p in open_ports if p in (3306, 5432, 6379, 27017, 9200, 11211)]
    if dangerous_ports:
        score += min(len(dangerous_ports), 3)
    if score >= 7:
        return "HOT"
    elif score >= 4:
        return "WARM"
    return "COLD"


def generate_hook(biz, temperature):
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


def enrich_business(biz):
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
            result = find_best_email(website, biz.get("name", ""))
            if result.get("email"):
                biz["email"] = result["email"]
                biz["email_confidence"] = result.get("confidence", 0)
                biz["email_source"] = result.get("source", "")
            biz["breach_count"] = result.get("breach_count", 0)
            biz["breach_names"] = result.get("breach_names", [])
        except Exception as e:
            log.debug(f"  Email error: {e}")

    if domain:
        try:
            osint = analyze_domain(domain, biz.get("rating", 0), biz.get("review_count", 0))
            biz["health_score"] = osint["health_score"]
            biz["ssl_grade"] = osint["ssl_grade"]
            biz["tech_stack"] = osint["tech_stack"]
            biz["vulnerabilities"] = osint.get("vulnerabilities", [])
            biz["open_ports"] = osint.get("open_ports", [])
            biz["security_warnings"] = osint.get("security_warnings", [])
        except Exception as e:
            log.debug(f"  OSINT error: {e}")

    try:
        rv = analyze_reviews(biz.get("name", ""), biz.get("city", ""), website)
        biz["sentiment"] = rv.get("sentiment", "neutral")
        biz["responds_to_reviews"] = rv.get("responds_to_reviews", False)
        if rv.get("rating") and not biz.get("rating"):
            biz["rating"] = rv["rating"]
        if rv.get("review_count") and not biz.get("review_count"):
            biz["review_count"] = rv["review_count"]
    except Exception as e:
        log.debug(f"  Review error: {e}")

    biz["lead_temperature"] = score_lead(biz)
    biz["outreach_hook"] = generate_hook(biz, biz["lead_temperature"])
    return biz


def run_once():
    from scraper.finder import search_businesses

    t0 = time.time()
    target, idx, total = get_target()
    city, sector = target["city"], target["sector"]

    print()
    print(f"{'='*60}")
    print(f"  RUN #{idx + 1}/{total}  |  {city} / {sector}")
    print(f"{'='*60}")

    businesses = search_businesses(city, sector, 1)
    if not businesses:
        print(f"  [!] No businesses found. Skipping.")
        return

    biz = businesses[0]
    print(f"  Enriching: {biz.get('name', '?')[:40]}...")

    result = enrich_business(biz)
    upsert_business(result, target)
    emails = 1 if result.get("email") else 0
    temp = result.get("lead_temperature", "COLD")
    print(f"  [{temp}] {result.get('name', '?')[:35]}")
    if result.get("email"):
        print(f"  Email: {result.get('email')}")
    print(f"  Health: {result.get('health_score', 0)} | Vulns: {len(result.get('vulnerabilities', []))}")

    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s")

    state = load_state()
    state["total_runs"] = state.get("total_runs", 0) + 1
    state["total_businesses"] = state.get("total_businesses", 0) + 1
    state["total_emails"] = state.get("total_emails", 0) + (1 if result.get("email") else 0)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)


def main():
    print()
    print("  ========================================")
    print("  FindLeads Local Daemon — CONTINUOUS MODE")
    print("  Scraper + Enricher + Supabase Writer")
    print("  30 seconds between runs")
    print("  Press Ctrl+C to stop")
    print("  ========================================")
    print()

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            print("\n  Stopped by user.")
            break
        except Exception as e:
            log.error(f"Run failed: {e}")

        next_run = datetime.now().strftime("%H:%M:%S")
        target, idx, total = load_state(), 0, 0
        try:
            with open(os.path.join(ROOT_DIR, "targets.json")) as f:
                raw = json.load(f)
            targets = raw if isinstance(raw, list) else raw.get("targets", [])
            total = len(targets)
            next_idx = (load_state()["current_index"] + 1) % total
            next_target = targets[next_idx]
            print(f"  Next run in {INTERVAL_SECONDS}s ({next_target['city']}/{next_target['sector']})")
        except Exception:
            print(f"  Next run in {INTERVAL_SECONDS}s")

        print(f"  Sleeping {INTERVAL_SECONDS}s... (Ctrl+C to stop)")
        try:
            time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n  Stopped by user.")
            break


if __name__ == "__main__":
    main()
