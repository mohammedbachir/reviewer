"""
Crisora Engine — Self-Healing Daemon v2
Zero-sleep continuous loop + watchdog + parallel enrichment + graph cache.
"""

import os
import sys
import json
import time
import socket
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from steindamm import SyncSemaphore as _SyncSemaphoreBase

def _make_semaphore(name, capacity):
    return _SyncSemaphoreBase.create(name=name, capacity=capacity)

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
TOOLS_HEALTH_FILE = os.path.join(ROOT_DIR, ".tools_health.json")
MAX_WORKERS = 5
GRAPH_CACHE_TTL = 300  # 5 minutes
STALL_TIMEOUT = 60     # 60 seconds = stall
WATCHDOG_INTERVAL = 10 # check every 10 seconds
BACKFILL_FIRST = True  # always backfill before adding new


class CircuitBreaker:
    def __init__(self, name, failure_threshold=2, cooldown=600):
        self.name = name
        self.failures = 0
        self.threshold = failure_threshold
        self.cooldown = cooldown
        self.disabled_until = 0

    def is_available(self):
        if self.disabled_until and time.time() < self.disabled_until:
            remaining = int(self.disabled_until - time.time())
            log.debug(f"  CircuitBreaker [{self.name}] OPEN — {remaining}s remaining")
            return False
        return True

    def record_success(self):
        self.failures = 0
        self.disabled_until = 0

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.threshold:
            self.disabled_until = time.time() + self.cooldown
            log.warning(f"  CircuitBreaker [{self.name}] OPENED — {self.failures} failures, cooling down {self.cooldown}s")
            self.failures = 0

    def get_state(self):
        if self.disabled_until and time.time() < self.disabled_until:
            return "OPEN"
        return "CLOSED"


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"current_index": -1, "total_runs": 0, "total_businesses": 0, "total_emails": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_targets():
    with open(os.path.join(ROOT_DIR, "targets.json")) as f:
        raw = json.load(f)
    targets = raw if isinstance(raw, list) else raw.get("targets", [])
    for t in targets:
        if "sector" not in t and "category" in t:
            t["sector"] = t["category"]
    return targets


# ════════════════════════════════════════════════════════════════
# SCORE LEAD
# ════════════════════════════════════════════════════════════════

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


def _clean_name_for_hook(name):
    if not name:
        return "there"
    skip = ["home", "contact", "about", "services", "welcome"]
    if name.lower().strip() in skip:
        return "there"
    if len(name) > 50 or "|" in name or "near" in name.lower() or "yellowpages" in name.lower():
        return "there"
    return name.strip()


def generate_hook(biz, temperature):
    name = biz.get("name", "your business")
    ssl = biz.get("ssl_grade", "")
    rating = biz.get("rating", 0)
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


# ════════════════════════════════════════════════════════════════
# CRISORA DAEMON (Self-Healing)
# ════════════════════════════════════════════════════════════════

class CrisoraDaemon:
    def __init__(self):
        self._graph_cache = None
        self._graph_cache_time = 0
        self._graph_cache_lock = threading.Lock()
        self._model_cache = ""
        self._model_cache_time = 0

        self._lock = threading.Lock()
        self._running = False
        self._current_target = ""
        self._current_run = 0
        self._total_runs = 0
        self._total_businesses = 0
        self._total_emails = 0
        self._errors = 0
        self._stall_count = 0
        self._last_db_write = time.time()
        self._last_db_count = 0
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._diagnostics = []
        self._tools_health = {}
        self._tools_health_time = 0
        self._backfill_queue = []
        self._total_backfilled = 0
        self._circuit_breakers = {
            "certspotter": CircuitBreaker("certspotter", failure_threshold=2, cooldown=600),
            "crtsh": CircuitBreaker("crtsh", failure_threshold=2, cooldown=600),
            "internetdb": CircuitBreaker("internetdb", failure_threshold=3, cooldown=300),
        }
        self._rate_limiters = {
            "certspotter": _make_semaphore("certspotter", capacity=2),
            "crtsh": _make_semaphore("crtsh", capacity=1),
            "internetdb": _make_semaphore("internetdb", capacity=3),
            "supabase": _make_semaphore("supabase", capacity=5),
        }

    def get_status(self):
        with self._lock:
            return {
                "running": self._running,
                "started_at": self._started_at,
                "current_target": self._current_target,
                "current_run": self._current_run,
                "total_runs": self._total_runs,
                "total_businesses": self._total_businesses,
                "total_emails": self._total_emails,
                "total_backfilled": self._total_backfilled,
                "errors": self._errors,
                "stall_count": self._stall_count,
                "last_db_write": self._last_db_write,
                "tools_health": self._tools_health,
                "last_diag": self._diagnostics[-5:] if self._diagnostics else [],
            }

    def _sb_req(self, method, url, **kwargs):
        with self._rate_limiters["supabase"]:
            return getattr(cffi_requests, method)(url, headers=HEADERS, timeout=kwargs.get("timeout", 15), **{k: v for k, v in kwargs.items() if k != "timeout"})

    # ── Tool Health Checker (once per batch) ─────────────────────
    def check_tools_health(self):
        session = cffi_requests.Session(impersonate="chrome120")
        health = {}

        # CertSpotter — respect circuit breaker + rate limiter
        cb_cs = self._circuit_breakers["certspotter"]
        if not cb_cs.is_available():
            health["certspotter"] = False
            health["certspotter_code"] = "CIRCUIT_OPEN"
        else:
            try:
                with self._rate_limiters["certspotter"]:
                    r = session.get(
                        "https://api.certspotter.com/v1/issuances?domain=google.com&include_subdomains=true&expand=dns_names&limit=1",
                        timeout=8
                    )
                health["certspotter"] = r.status_code == 200
                health["certspotter_code"] = r.status_code
                if r.status_code == 200:
                    cb_cs.record_success()
                else:
                    cb_cs.record_failure()
            except Exception:
                health["certspotter"] = False
                health["certspotter_code"] = 0
                cb_cs.record_failure()

        # crt.sh — respect circuit breaker + rate limiter
        cb_ct = self._circuit_breakers["crtsh"]
        if not cb_ct.is_available():
            health["crtsh"] = False
            health["crtsh_code"] = "CIRCUIT_OPEN"
        else:
            try:
                with self._rate_limiters["crtsh"]:
                    r = session.get("https://crt.sh/?q=%.google.com&output=json", timeout=8)
                health["crtsh"] = r.status_code == 200
                health["crtsh_code"] = r.status_code
                if r.status_code == 200:
                    cb_ct.record_success()
                else:
                    cb_ct.record_failure()
            except Exception:
                health["crtsh"] = False
                health["crtsh_code"] = 0
                cb_ct.record_failure()

        # InternetDB — respect circuit breaker + rate limiter
        cb_idb = self._circuit_breakers["internetdb"]
        if not cb_idb.is_available():
            health["internetdb"] = False
        else:
            try:
                with self._rate_limiters["internetdb"]:
                    r = session.get("https://internetdb.shodan.io/1.1.1.1", timeout=5)
                health["internetdb"] = r.status_code == 200
                if r.status_code == 200:
                    cb_idb.record_success()
                else:
                    cb_idb.record_failure()
            except Exception:
                health["internetdb"] = False
                cb_idb.record_failure()

        # Supabase — rate limited
        try:
            with self._rate_limiters["supabase"]:
                r = cffi_requests.get(
                    f"{SUPABASE_URL}/rest/v1/businesses?select=id&limit=1",
                    headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                    timeout=5,
                )
            health["supabase"] = r.status_code == 200
        except Exception:
            health["supabase"] = False

        # DNS
        try:
            dns.resolver.resolve("supabase.co", "A")
            health["dns"] = True
        except Exception:
            health["dns"] = False

        self._tools_health = health
        self._tools_health_time = time.time()

        ok = sum(1 for k, v in health.items() if isinstance(v, bool) and v)
        total = sum(1 for k, v in health.items() if isinstance(v, bool))
        cb_states = {k: v.get_state() for k, v in self._circuit_breakers.items()}
        log.info(f"Tools health: {ok}/{total} OK | certspotter={health.get('certspotter')} crtsh={health.get('crtsh')} dns={health.get('dns')} | circuits={cb_states}")
        return health

    # ── Backfill Incomplete Businesses ───────────────────────────
    def backfill_incomplete(self):
        health = self.check_tools_health()
        available_tools = [k for k, v in health.items() if isinstance(v, bool) and v]

        if not available_tools:
            log.warning("No tools available. Skipping backfill.")
            return 0

        incomplete = []

        # Fetch businesses with potentially incomplete data
        offset = 0
        while True:
            try:
                r = cffi_requests.get(
                    f"{SUPABASE_URL}/rest/v1/businesses?select=id,name,website,firebase,crtsh,api_keys,archive,sherlock&website=not.is.null&order=id.desc&limit=100&offset={offset}",
                    headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                    timeout=30
                )
                batch = r.json()
                if not batch:
                    break
                for b in batch:
                    needs_backfill = False

                    crtsh = b.get("crtsh") or {}
                    if isinstance(crtsh, str):
                        try: crtsh = json.loads(crtsh)
                        except: crtsh = {}
                    if not crtsh.get("checked") and "certspotter" in available_tools:
                        needs_backfill = True

                    firebase = b.get("firebase") or {}
                    if isinstance(firebase, str):
                        try: firebase = json.loads(firebase)
                        except: firebase = {}
                    if not firebase and "firebase" not in str(b.get("id", "")):
                        needs_backfill = True

                    api_keys = b.get("api_keys") or {}
                    if isinstance(api_keys, str):
                        try: api_keys = json.loads(api_keys)
                        except: api_keys = {}
                    if not api_keys:
                        needs_backfill = True

                    if needs_backfill:
                        incomplete.append(b)

                if len(batch) < 100:
                    break
                offset += 100
            except Exception as e:
                log.error(f"Backfill fetch error: {e}")
                break

        if not incomplete:
            log.info("No incomplete businesses found. All data is complete.")
            return 0

        log.info(f"Backfill: {len(incomplete)} businesses need data update")
        backfilled = 0

        for b in incomplete[:20]:
            biz_id = b["id"]
            name = (b.get("name") or "")[:30]
            website = b.get("website", "")

            try:
                from urllib.parse import urlparse
                parsed = urlparse(website)
                domain = parsed.netloc or parsed.path
                if domain.startswith("www."):
                    domain = domain[4:]
                domain = domain.split("/")[0].split(":")[0]
            except Exception:
                continue

            if not domain or "." not in domain:
                continue

            patch = {}

            crtsh = b.get("crtsh") or {}
            if isinstance(crtsh, str):
                try: crtsh = json.loads(crtsh)
                except: crtsh = {}
            if not crtsh.get("checked") and "certspotter" in available_tools:
                try:
                    from scraper.osint_engine import check_subdomains_emails
                    crtsh_data = check_subdomains_emails(domain)
                    patch["crtsh"] = crtsh_data
                except Exception as e:
                    log.debug(f"  Backfill crtsh error for {name}: {e}")

            firebase = b.get("firebase") or {}
            if isinstance(firebase, str):
                try: firebase = json.loads(firebase)
                except: firebase = {}
            if not firebase:
                try:
                    from scraper.osint_engine import check_firebase_exposure
                    session = cffi_requests.Session(impersonate="chrome120")
                    resp = session.get(f"https://{domain}", timeout=5, allow_redirects=True)
                    html = resp.text if resp.status_code == 200 else ""
                    firebase_data = check_firebase_exposure(domain, html)
                    if firebase_data.get("firebase_detected") or firebase_data.get("firebase_open"):
                        patch["firebase"] = firebase_data
                except Exception:
                    pass

            api_keys = b.get("api_keys") or {}
            if isinstance(api_keys, str):
                try: api_keys = json.loads(api_keys)
                except: api_keys = {}
            if not api_keys:
                try:
                    from scraper.osint_engine import extract_api_keys
                    session = cffi_requests.Session(impersonate="chrome120")
                    resp = session.get(f"https://{domain}", timeout=5, allow_redirects=True)
                    html = resp.text if resp.status_code == 200 else ""
                    api_data = extract_api_keys(html, domain)
                    if api_data.get("key_count", 0) > 0:
                        patch["api_keys"] = api_data
                except Exception:
                    pass

            if patch:
                try:
                    r = cffi_requests.patch(
                        f"{SUPABASE_URL}/rest/v1/businesses?id=eq.{biz_id}",
                        json=patch,
                        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"},
                        timeout=15
                    )
                    if r.status_code in (200, 204):
                        backfilled += 1
                        log.info(f"  [BACKFILL] {name} | updated {list(patch.keys())}")
                    time.sleep(1)
                except Exception as e:
                    log.debug(f"  Backfill patch error for {name}: {e}")

        log.info(f"Backfill complete: {backfilled}/{len(incomplete)} updated")
        self._total_backfilled += backfilled
        return backfilled
    def get_graph_data(self):
        now = time.time()
        with self._graph_cache_lock:
            if self._graph_cache is not None and (now - self._graph_cache_time) < GRAPH_CACHE_TTL:
                return self._graph_cache
        data = self._fetch_all_businesses_for_graph()
        with self._graph_cache_lock:
            self._graph_cache = data
            self._graph_cache_time = now
        return data

    def _fetch_all_businesses_for_graph(self):
        try:
            resp = cffi_requests.get(
                f"{SUPABASE_URL}/rest/v1/businesses?select=id,name,city,sector,tech_stack,health_score,ssl_grade,breach_count,vulnerabilities,open_ports,breach_names,security_warnings",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=10,
            )
            data = resp.json()
            if not isinstance(data, list):
                return []
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

    # ── Model State Cache ────────────────────────────────────────
    def get_model_state(self):
        now = time.time()
        if self._model_cache and (now - self._model_cache_time) < 300:
            return self._model_cache
        try:
            resp = cffi_requests.get(
                f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=5,
            )
            rows = resp.json()
            if rows:
                self._model_cache = rows[0].get("model_state", "")
                self._model_cache_time = now
                return self._model_cache
        except Exception:
            pass
        return self._model_cache or ""

    def _save_model_state(self, model_b64):
        if not model_b64:
            return
        self._model_cache = model_b64
        self._model_cache_time = time.time()
        try:
            cffi_requests.patch(
                f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
                json={"model_state": model_b64},
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=minimal"},
                timeout=5,
            )
        except Exception:
            pass

    # ── Upsert ──────────────────────────────────────────────────
    def upsert_business(self, biz, target):
        from scraper.osint_engine import validate_consistency
        biz = validate_consistency(biz)

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
            "address": biz.get("address", ""),
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
            "requires_review": biz.get("requires_review", False),
            "review_flags": json.dumps(biz.get("review_flags", [])),
        }
        with self._rate_limiters["supabase"]:
            resp = cffi_requests.post(
                f"{SUPABASE_URL}/rest/v1/businesses",
                json=data,
                headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
                timeout=10,
            )
        return resp.status_code < 400

    def _save_snapshot(self, biz_id, biz):
        try:
            with self._rate_limiters["supabase"]:
                cffi_requests.post(
                    f"{SUPABASE_URL}/rest/v1/snapshots",
                    json={
                        "business_id": biz_id,
                        "rating": biz.get("rating"),
                        "review_count": biz.get("review_count"),
            "health_score": int(biz.get("health_score", 50)),
                        "sentiment_score": 1.0 if biz.get("sentiment") == "positive" else -1.0 if biz.get("sentiment") == "negative" else 0.0,
                    },
                    headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=minimal"},
                    timeout=5,
                )
        except Exception:
            pass

    def _get_snapshots(self, biz_id):
        try:
            with self._rate_limiters["supabase"]:
                resp = cffi_requests.get(
                    f"{SUPABASE_URL}/rest/v1/snapshots?business_id=eq.{biz_id}&order=scan_date.desc&limit=10",
                    headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                    timeout=5,
                )
            return resp.json()
        except Exception:
            return []

    # ── Enrichment (per business) ───────────────────────────────
    def enrich_business(self, biz):
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
                with self._rate_limiters["internetdb"]:
                    osint = analyze_domain(domain, biz.get("rating", 0), biz.get("review_count", 0))
                biz["health_score"] = osint["health_score"]
                biz["ssl_grade"] = osint["ssl_grade"]
                biz["tech_stack"] = osint["tech_stack"]
                biz["vulnerabilities"] = osint.get("vulnerabilities", [])
                biz["open_ports"] = osint.get("open_ports", [])
                biz["security_warnings"] = osint.get("security_warnings", [])
                biz["ssl_deep"] = osint.get("ssl_deep", {})
                biz["security_headers"] = osint.get("security_headers", {})
                biz["abuseipdb"] = osint.get("abuseipdb", {})
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

        try:
            from scraper.crisis_predictor import predict_crisis
            model_b64 = self.get_model_state()
            snapshots = []
            if biz.get("id"):
                snapshots = self._get_snapshots(biz["id"])
            all_biz = self.get_graph_data()
            crisis = predict_crisis(biz, all_businesses=all_biz, snapshots=snapshots, model_state_b64=model_b64)
            biz["crisis_probability"] = crisis.get("crisis_probability", 0)
            biz["crisis_risk_level"] = crisis.get("risk_level", "UNKNOWN")
            biz["crisis_recommendations"] = crisis.get("recommendations", [])
            biz["cvss_severity"] = crisis.get("cvss", {}).get("severity", "NONE")
            biz["cvss_max"] = crisis.get("cvss", {}).get("cvss_max", 0)
            new_model_b64 = crisis.get("model_state_b64")
            if new_model_b64:
                self._save_model_state(new_model_b64)
        except Exception as e:
            log.debug(f"  Crisis prediction skipped: {e}")

        return biz

    # ── Parallel Enrich + Save ──────────────────────────────────
    def _enrich_and_save_one(self, biz, target):
        if not biz.get("website") and not biz.get("email"):
            return None, "skip"

        name = biz.get("name", "?")[:40]
        t0 = time.time()
        try:
            if self._is_duplicate(biz, target):
                print(f"  [SKIP] {name} — duplicate (website/phone already in DB)")
                return None, "skip"

            result = self.enrich_business(biz)
            self.upsert_business(result, target)
            elapsed = time.time() - t0

            try:
                with self._rate_limiters["supabase"]:
                    resp = cffi_requests.get(
                        f"{SUPABASE_URL}/rest/v1/businesses?select=id&name=eq.{result['name']}&city=eq.{target['city']}&sector=eq.{target['sector']}&limit=1",
                        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                        timeout=5,
                    )
                rows = resp.json()
                if rows:
                    self._save_snapshot(rows[0]["id"], result)
            except Exception:
                pass

            temp = result.get("lead_temperature", "COLD")
            print(f"  [{temp}] {name} ({elapsed:.1f}s)")
            if result.get("email"):
                print(f"    Email: {result['email']}")
            print(f"    Health: {result.get('health_score', 0)} | SSL: {result.get('ssl_grade', '?')}")
            print(f"    Crisis: {result.get('crisis_risk_level', '?')} ({result.get('crisis_probability', 0) * 100:.1f}%)")
            return result, "ok"
        except Exception as e:
            log.error(f"  Enrich failed for {name}: {e}")
            return None, "error"

    # ── Run Once (Parallel) ─────────────────────────────────────
    def run_once(self):
        from scraper.finder import search_businesses

        self.check_tools_health()

        # Step 1: Backfill incomplete data first
        backfilled = self.backfill_incomplete()

        t0 = time.time()
        targets = get_targets()
        state = load_state()
        idx = (state["current_index"] + 1) % len(targets)
        target = targets[idx]
        city, sector = target["city"], target["sector"]

        with self._lock:
            self._current_target = f"{city}/{sector}"
            self._current_run = idx + 1

        state["current_index"] = idx
        save_state(state)

        print()
        print(f"{'='*60}")
        print(f"  RUN #{idx + 1}/{len(targets)}  |  {city} / {sector}")
        print(f"{'='*60}")

        businesses = search_businesses(city, sector, 5)
        if not businesses:
            print(f"  [!] No businesses found. Skipping.")
            return

        enriched = 0
        skipped = 0
        errors = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._enrich_and_save_one, biz, target): biz
                for biz in businesses
            }
            for future in as_completed(futures):
                result, status = future.result()
                if status == "skip":
                    skipped += 1
                elif status == "ok":
                    enriched += 1
                    with self._lock:
                        self._last_db_write = time.time()
                        self._total_businesses += 1
                        self._total_emails += 1
                elif status == "error":
                    errors += 1

        elapsed = time.time() - t0
        print(f"  Done: {enriched} enriched, {skipped} skipped, {errors} errors in {elapsed:.1f}s")

        with self._lock:
            self._total_runs += 1
            self._errors += errors

        state = load_state()
        state["total_runs"] = state.get("total_runs", 0) + 1
        state["total_businesses"] = state.get("total_businesses", 0) + enriched
        state["total_emails"] = state.get("total_emails", 0) + enriched
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        save_state(state)

        return enriched

    # ── Diagnostics ─────────────────────────────────────────────
    def run_diagnostics(self):
        diag = {"time": datetime.now(timezone.utc).isoformat(), "checks": []}

        # 1. DNS check
        try:
            dns.resolver.resolve("supabase.co", "A")
            diag["checks"].append({"name": "DNS", "status": "OK"})
        except Exception as e:
            diag["checks"].append({"name": "DNS", "status": "FAIL", "error": str(e)})
            self._fix_dns()

        # 2. Supabase connectivity
        try:
            resp = cffi_requests.get(
                f"{SUPABASE_URL}/rest/v1/businesses?select=id&limit=1",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=5,
            )
            if resp.status_code == 200:
                diag["checks"].append({"name": "Supabase", "status": "OK"})
            else:
                diag["checks"].append({"name": "Supabase", "status": "FAIL", "code": resp.status_code})
        except Exception as e:
            diag["checks"].append({"name": "Supabase", "status": "FAIL", "error": str(e)})

        # 3. OpenRouter API
        or_key = os.environ.get("OPENROUTER_API_KEY", "")
        if or_key:
            try:
                resp = cffi_requests.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {or_key}"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    diag["checks"].append({"name": "OpenRouter", "status": "OK"})
                else:
                    diag["checks"].append({"name": "OpenRouter", "status": "FAIL", "code": resp.status_code})
            except Exception as e:
                diag["checks"].append({"name": "OpenRouter", "status": "FAIL", "error": str(e)})
        else:
            diag["checks"].append({"name": "OpenRouter", "status": "SKIP", "reason": "no key"})

        # 4. DB row count
        try:
            resp = cffi_requests.get(
                f"{SUPABASE_URL}/rest/v1/businesses?select=id",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=5,
            )
            count = len(resp.json())
            diag["db_count"] = count
        except Exception:
            count = -1
            diag["db_count"] = -1

        # 5. Targets file
        try:
            targets = get_targets()
            diag["targets_count"] = len(targets)
        except Exception as e:
            diag["targets_count"] = 0
            diag["checks"].append({"name": "Targets", "status": "FAIL", "error": str(e)})

        with self._lock:
            self._diagnostics.append(diag)
            if len(self._diagnostics) > 20:
                self._diagnostics = self._diagnostics[-20:]

        return diag

    def _is_duplicate(self, biz, target):
        website = (biz.get("website") or "").strip().rstrip("/").replace("www.", "").lower()
        phone = biz.get("phone") or ""
        import re as _re
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

        query = "|".join(checks)
        try:
            resp = cffi_requests.get(
                f"{SUPABASE_URL}/rest/v1/businesses?select=id&{query}&limit=1",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=5,
            )
            rows = resp.json()
            if isinstance(rows, list) and len(rows) > 0:
                return True
        except Exception:
            pass
        return False

    def _fix_dns(self):
        try:
            dns.resolver.default_resolver.nameservers = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
            log.info("DNS reset to Google + Cloudflare")
        except Exception:
            pass

    # ── Main Loop ───────────────────────────────────────────────
    def start(self):
        print()
        print("  ========================================")
        print("  Crisora Engine v2 — SELF-HEALING")
        print("  Zero-sleep + Watchdog + Parallel")
        print("  Press Ctrl+C to stop")
        print("  ========================================")
        print()

        self._running = True

        watchdog = threading.Thread(target=self._watchdog_loop, daemon=True)
        watchdog.start()

        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                print("\n  Stopped by user.")
                break
            except Exception as e:
                log.error(f"Run failed: {e}")
                with self._lock:
                    self._errors += 1

            # Minimal delay between runs (1 second, not 30)
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n  Stopped by user.")
                break

    def _watchdog_loop(self):
        log.info(f"Watchdog started (interval={WATCHDOG_INTERVAL}s, stall={STALL_TIMEOUT}s)")
        while self._running:
            time.sleep(WATCHDOG_INTERVAL)

            try:
                self._check_stall()
                self.run_diagnostics()
            except Exception as e:
                log.error(f"Watchdog error: {e}")

    def _check_stall(self):
        now = time.time()
        with self._lock:
            last_write = self._last_db_write
            stall_seconds = now - last_write

        if stall_seconds > STALL_TIMEOUT:
            with self._lock:
                self._stall_count += 1

            log.warning(f"STALL DETECTED: {stall_seconds:.0f}s since last DB write (stall #{self._stall_count})")
            diag = self.run_diagnostics()

            failed_checks = [c for c in diag.get("checks", []) if c["status"] == "FAIL"]
            if failed_checks:
                log.error(f"Diagnostics failures: {[c['name'] for c in failed_checks]}")
                self._try_restart()
            else:
                log.info("All diagnostics passed. Stall may be due to search returning 0 results.")

    def _try_restart(self):
        log.info("Attempting self-heal: resetting DNS + clearing graph cache")
        self._fix_dns()
        with self._graph_cache_lock:
            self._graph_cache = None
            self._graph_cache_time = 0
        with self._lock:
            self._last_db_write = time.time()
            self._stall_count = 0


# ── Module-level convenience ────────────────────────────────────
_daemon_instance = None

def _get_daemon():
    global _daemon_instance
    if _daemon_instance is None:
        _daemon_instance = CrisoraDaemon()
    return _daemon_instance

def run_once():
    return _get_daemon().run_once()

def get_status():
    return _get_daemon().get_status()

INTERVAL_SECONDS = 1  # minimal delay between runs

if __name__ == "__main__":
    _get_daemon().start()
