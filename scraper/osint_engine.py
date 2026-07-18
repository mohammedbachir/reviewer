"""
FindLeads — Lightweight OSINT Engine
WHOIS, DNS, SSL, tech detection, page speed.
All via HTTP/DNS — no heavy dependencies.
"""

import json
import ssl
import socket
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.parse import urlparse

from curl_cffi import requests as cffi_requests

logger = logging.getLogger("osint")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _create_session():
    return cffi_requests.Session(impersonate="chrome120")


# ════════════════════════════════════════════════════════════════
# MAIN OSINT FUNCTION
# ════════════════════════════════════════════════════════════════

def analyze_domain(domain: str, rating: float = 0, review_count: int = 0) -> Dict:
    """
    Full OSINT analysis for a domain.
    Returns dict with health_score, tech_stack, ssl_grade, dns_info, etc.
    """
    logger.info(f"OSINT analyzing: {domain}")
    result = {
        "domain": domain,
        "health_score": 50,
        "ssl_grade": "",
        "tech_stack": [],
        "dns": {},
        "whois": {},
        "page_speed": {},
        "has_website": True,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. SSL Certificate
    try:
        ssl_info = check_ssl(domain)
        result["ssl_grade"] = ssl_info.get("grade", "")
        result["ssl_expiry"] = ssl_info.get("expiry", "")
        result["ssl_issuer"] = ssl_info.get("issuer", "")
    except Exception as e:
        logger.debug(f"SSL error: {e}")

    # 2. DNS Records
    try:
        result["dns"] = check_dns(domain)
    except Exception as e:
        logger.debug(f"DNS error: {e}")

    # 3. Page Speed (basic)
    try:
        result["page_speed"] = check_page_speed(domain)
    except Exception as e:
        logger.debug(f"Page speed error: {e}")

    # 4. Tech Stack Detection
    try:
        result["tech_stack"] = detect_tech(domain)
    except Exception as e:
        logger.debug(f"Tech detection error: {e}")

    # 5. Calculate health score
    result["health_score"] = _calculate_health(result, rating, review_count)

    logger.info(f"  Health: {result['health_score']}/100 | SSL: {result['ssl_grade']} | Tech: {len(result['tech_stack'])}")
    return result


# ════════════════════════════════════════════════════════════════
# SSL CERTIFICATE
# ════════════════════════════════════════════════════════════════

def check_ssl(domain: str) -> Dict:
    """Check SSL certificate info and grade."""
    result = {"grade": "F", "expiry": "", "issuer": "", "days_left": 0}

    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

        # Get expiry
        not_after = cert.get("notAfter", "")
        if not_after:
            expiry_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            days_left = (expiry_dt - datetime.utcnow()).days
            result["expiry"] = not_after
            result["days_left"] = days_left

        # Get issuer
        issuer = cert.get("issuer", [])
        for rdn in issuer:
            for attr in rdn:
                if attr[0] == "organizationName":
                    result["issuer"] = attr[1]
                    break

        # Grade
        if days_left > 365:
            result["grade"] = "A"
        elif days_left > 180:
            result["grade"] = "B"
        elif days_left > 30:
            result["grade"] = "C"
        elif days_left > 0:
            result["grade"] = "D"
        else:
            result["grade"] = "F"

    except Exception:
        result["grade"] = "F"

    return result


# ════════════════════════════════════════════════════════════════
# DNS RECORDS
# ════════════════════════════════════════════════════════════════

def check_dns(domain: str) -> Dict:
    """Basic DNS lookup via HTTP (Google DNS)."""
    result = {"a": [], "mx": [], "txt": [], "ns": []}

    session = _create_session()
    base = "https://dns.google/resolve"

    for rtype in ["A", "MX", "TXT", "NS"]:
        try:
            resp = session.get(base, params={"name": domain, "type": rtype}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for ans in data.get("Answer", []):
                    if ans.get("type") == {"A": 1, "MX": 15, "TXT": 16, "NS": 2}.get(rtype):
                        value = ans.get("data", "")
                        if rtype == "MX":
                            value = value.split(" ")[-1] if " " in value else value
                        result[rtype.lower()].append(value)
        except Exception:
            continue

    return result


# ════════════════════════════════════════════════════════════════
# PAGE SPEED (basic)
# ════════════════════════════════════════════════════════════════

def check_page_speed(domain: str) -> Dict:
    """Check basic page speed metrics."""
    result = {"load_time_ms": 0, "status_code": 0, "grade": "C"}

    session = _create_session()
    start = time.time()
    try:
        resp = session.get(f"https://{domain}", headers=HEADERS, timeout=10)
        elapsed = int((time.time() - start) * 1000)
        result["load_time_ms"] = elapsed
        result["status_code"] = resp.status_code

        if elapsed < 1000:
            result["grade"] = "A"
        elif elapsed < 2000:
            result["grade"] = "B"
        elif elapsed < 3000:
            result["grade"] = "C"
        else:
            result["grade"] = "D"
    except Exception:
        result["load_time_ms"] = 9999
        result["grade"] = "F"

    return result


# ════════════════════════════════════════════════════════════════
# TECH STACK DETECTION
# ════════════════════════════════════════════════════════════════

TECH_SIGNATURES = {
    "WordPress": ["wp-content", "wp-includes", "wordpress"],
    "Shopify": ["shopify", "cdn.shopify.com"],
    "Wix": ["wix.com", "wixstatic.com"],
    "Squarespace": ["squarespace.com", "sqsp"],
    "React": ["react", "_next", "nextjs"],
    "Vue.js": ["vue", "vuejs"],
    "Angular": ["ng-app", "angular"],
    "Bootstrap": ["bootstrap"],
    "Tailwind": ["tailwind"],
    "jQuery": ["jquery"],
    "Google Analytics": ["google-analytics.com", "gtag", "googletagmanager"],
    "Google Tag Manager": ["googletagmanager.com", "gtm.js"],
    "Facebook Pixel": ["facebook.net/en_US/fbevents", "fbq("],
    "Cloudflare": ["cloudflare", "cf-ray"],
    "AWS": ["amazonaws.com", "cloudfront.net"],
    "Vercel": ["vercel", "_vercel"],
    "Netlify": ["netlify"],
    "PHP": [".php", "x-powered-by: PHP"],
    "Python": ["python", "wsgi", "django", "flask"],
    "Node.js": ["node.js", "express"],
    "Laravel": ["laravel", "csrf-token"],
    "Drupal": ["drupal"],
    "Joomla": ["joomla"],
    "Ghost": ["ghost-"],
    "Webflow": ["webflow"],
}


def detect_tech(domain: str) -> list:
    """Detect technologies from page HTML."""
    session = _create_session()
    techs = []

    try:
        resp = session.get(f"https://{domain}", headers=HEADERS, timeout=10)
        content = resp.text.lower()
        headers_str = str(resp.headers).lower()

        all_text = content + " " + headers_str

        for tech, signatures in TECH_SIGNATURES.items():
            for sig in signatures:
                if sig.lower() in all_text:
                    techs.append(tech)
                    break
    except Exception:
        pass

    return sorted(set(techs))


# ════════════════════════════════════════════════════════════════
# HEALTH SCORE CALCULATION
# ════════════════════════════════════════════════════════════════

def _calculate_health(osint: Dict, rating: float, review_count: int) -> int:
    """Calculate 0-100 health score from OSINT data."""
    score = 50  # baseline

    # SSL (0-15 points)
    ssl_grades = {"A": 15, "B": 10, "C": 5, "D": 0, "F": -5}
    score += ssl_grades.get(osint.get("ssl_grade", "F"), 0)

    # Page speed (0-15 points)
    speed_grades = {"A": 15, "B": 10, "C": 5, "D": 0, "F": -5}
    score += speed_grades.get(osint.get("page_speed", {}).get("grade", "F"), 0)

    # Tech stack (0-10 points — having modern tech is good)
    techs = osint.get("tech_stack", [])
    if len(techs) >= 5:
        score += 10
    elif len(techs) >= 3:
        score += 7
    elif len(techs) >= 1:
        score += 3

    # DNS (0-10 points)
    dns = osint.get("dns", {})
    if dns.get("mx"):
        score += 5
    if dns.get("txt"):
        # Check for SPF/DMARC
        for txt in dns["txt"]:
            if "spf" in txt.lower():
                score += 3
            if "dmarc" in txt.lower():
                score += 2

    # Google rating (0-10 points)
    if rating >= 4.5:
        score += 10
    elif rating >= 4.0:
        score += 7
    elif rating >= 3.5:
        score += 4
    elif rating < 2.0:
        score -= 5

    # Review count (0-10 points)
    if review_count >= 200:
        score += 10
    elif review_count >= 100:
        score += 7
    elif review_count >= 50:
        score += 4
    elif review_count >= 10:
        score += 2

    return max(0, min(100, score))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = analyze_domain("mmdc.ae", rating=4.5, review_count=120)
    print(json.dumps(result, indent=2, default=str))
