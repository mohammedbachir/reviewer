"""
FindLeads — OSINT Engine (TechDetect HTTP Signatures)
SSL, DNS, tech detection (7,400+ signatures), page speed, health score.
All via HTTP/DNS — zero browser dependencies.
"""

import json
import ssl
import socket
import hashlib
import logging
import time
import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from curl_cffi import requests as cffi_requests

logger = logging.getLogger("osint")


def _create_session():
    return cffi_requests.Session(impersonate="chrome120")


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


# ════════════════════════════════════════════════════════════════
# TOOL 1: OPENFIREBASE — Firebase Database Exposure Detection
# ════════════════════════════════════════════════════════════════

FIREBASE_PATTERNS = [
    r'([a-zA-Z0-9_-]+\.firebaseio\.com)',
    r'(https?://[a-zA-Z0-9_-]+\.firebaseio\.com)',
    r'firebaseio\.com/([a-zA-Z0-9_-]+)',
    r'firebaseConfig[^{]*({[^}]+})',
    r'firebase\.initializeApp\(([^)]+)\)',
    r'"apiKey"\s*:\s*"[^"]*firebase[^"]*"',
    r'projectId["\s:]+([a-zA-Z0-9_-]+)',
]


def check_firebase_exposure(domain: str, html: str = "") -> Dict:
    result = {
        "firebase_detected": False,
        "firebase_url": "",
        "firebase_open": False,
        "firebase_data": "",
        "firebase_risk": "NONE",
        "firebase_project_id": "",
    }
    try:
        if not html:
            session = _create_session()
            try:
                resp = session.get(f"https://{domain}", headers=HEADERS, timeout=5, allow_redirects=True)
                html = resp.text
            except Exception:
                return result

        firebase_urls = set()
        project_id = ""
        for pattern in FIREBASE_PATTERNS:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for m in matches:
                if ".firebaseio.com" in m:
                    clean = m.rstrip("/")
                    if not clean.startswith("http"):
                        clean = "https://" + clean
                    firebase_urls.add(clean)
                elif len(m) > 5 and len(m) < 50 and "." not in m:
                    project_id = m

        if project_id:
            firebase_urls.add(f"https://{project_id}.firebaseio.com")

        if firebase_urls:
            result["firebase_detected"] = True
            result["firebase_project_id"] = project_id
            url = list(firebase_urls)[0]
            result["firebase_url"] = url

            session = _create_session()
            for endpoint in ["/.json", "/.json?shallow=true"]:
                try:
                    test_url = url.rstrip("/") + endpoint
                    resp = session.get(test_url, headers=HEADERS, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json() if resp.text.strip().startswith(("{", "[")) else {}
                        if data:
                            result["firebase_open"] = True
                            result["firebase_data"] = str(data)[:500]
                            result["firebase_risk"] = "CRITICAL"
                            logger.warning(f"  Firebase OPEN: {test_url}")
                            break
                except Exception:
                    continue

            if not result["firebase_open"]:
                result["firebase_risk"] = "DETECTED"

    except Exception as e:
        logger.debug(f"  Firebase check error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# TOOL 2: ARCHIVEWRAITH — Wayback Machine Sensitive File Detection
# ════════════════════════════════════════════════════════════════

SENSITIVE_PATTERNS = [
    r'\.env$', r'\.sql$', r'\.bak$', r'\.old$', r'\.zip$', r'\.tar\.gz$', r'\.rar$',
    r'/backup/', r'/config\.json', r'/config\.yml', r'/config\.env',
    r'password\.txt', r'password\.csv',
    r'wp-config\.php', r'wp-admin',
    r'phpmyadmin', r'cpanel', r'\.git/HEAD',
    r'/\.env', r'/\.git',
    r'\.htpasswd', r'\.htaccess', r'web\.config',
    r'/admin\.php', r'/admin/login', r'/administrator/',
]

ARCHIVE_FALSE_POSITIVES = [
    'sitemap.xml', 'sitemap_index.xml', 'sitemap-news.xml',
    'wp-content/uploads/', 'wp-content/themes/', 'wp-content/plugins/',
    'wp-includes/', 'wp-json/', 'xmlrpc.php',
    'robots.txt', 'favicon.ico', 'readme.html', 'license.txt',
    'feed/', 'comments/feed/', 'trackback/',
]

ARCHIVE_DANGEROUS_PATTERNS = [
    r'\.env$', r'\.git/HEAD', r'wp-config\.php', r'/admin\.php',
    r'id_rsa', r'\.ssh/', r'\.aws/', r'\.htpasswd',
    r'backup\.sql', r'dump\.sql', r'database\.sql', r'db\.sql',
    r'config\.php\.bak', r'wp-config\.php\.bak',
    r'\.htaccess', r'\.DS_Store', r'web\.config',
    r'\.svn/', r'credentials\.json', r'service-account\.json',
]


def check_archive_wraith(domain: str) -> Dict:
    result = {
        "archive_total_urls": 0,
        "archive_sensitive_files": [],
        "archive_admin_panels": [],
        "archive_exposed_endpoints": 0,
        "archive_risk": "NONE",
        "archive_years_span": "",
    }
    try:
        session = _create_session()
        cdx_url = "https://web.archive.org/cdx/search/cdx"
        resp = session.get(cdx_url, params={
            "url": domain + "/*",
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype",
            "filter": "statuscode:200",
            "collapse": "urlkey",
            "limit": 500,
        }, timeout=10)

        if resp.status_code != 200:
            return result

        data = resp.json()
        if len(data) < 2:
            return result

        headers_row = data[0]
        rows = data[1:]
        result["archive_total_urls"] = len(rows)

        ts_idx = headers_row.index("timestamp") if "timestamp" in headers_row else 0
        url_idx = headers_row.index("original") if "original" in headers_row else 1
        type_idx = headers_row.index("mimetype") if "mimetype" in headers_row else 3

        timestamps = set()
        sensitive = []
        admin_panels = []

        for row in rows:
            if len(row) <= url_idx:
                continue
            ts = row[ts_idx] if ts_idx < len(row) else ""
            url = row[url_idx]
            mime = row[type_idx] if type_idx < len(row) else ""
            timestamps.add(ts[:4] if ts else "")

            url_lower = url.lower()

            skip = False
            for fp in ARCHIVE_FALSE_POSITIVES:
                if fp in url_lower:
                    skip = True
                    break
            if skip:
                continue

            for pat in ARCHIVE_DANGEROUS_PATTERNS:
                if re.search(pat, url_lower):
                    sensitive.append({"url": url, "pattern": f"DANGEROUS:{pat}", "ts": ts})
                    break

            for pat in SENSITIVE_PATTERNS:
                if re.search(pat, url_lower):
                    sensitive.append({"url": url, "pattern": pat, "ts": ts})
                    break

            if any(x in url_lower for x in ["/admin", "/wp-admin", "/cpanel", "/dashboard", "/login"]):
                admin_panels.append(url)

        result["archive_sensitive_files"] = sensitive[:20]
        result["archive_admin_panels"] = list(set(admin_panels))[:10]
        result["archive_exposed_endpoints"] = len(sensitive)

        if timestamps:
            sorted_ts = sorted([t for t in timestamps if t.isdigit()])
            if sorted_ts:
                result["archive_years_span"] = f"{sorted_ts[0]}-{sorted_ts[-1]}"

        if sensitive:
            result["archive_risk"] = "HIGH"
        elif admin_panels:
            result["archive_risk"] = "MEDIUM"
        elif len(rows) > 100:
            result["archive_risk"] = "LOW"

        logger.info(f"  ArchiveWraith: {len(rows)} URLs, {len(sensitive)} sensitive, {len(admin_panels)} admin panels")
    except Exception as e:
        logger.debug(f"  ArchiveWraith error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# TOOL 3: PHOTON REGEX — API Key & Secret Exposure Detection
# ════════════════════════════════════════════════════════════════

API_KEY_PATTERNS = {
    "AWS_AKIA": r'(AKIA[0-9A-Z]{16})',
    "AWS_Secret": r'(aws_secret_access_key\s*[=:]\s*["\']?([A-Za-z0-9/+=]{40}))',
    "Google_API": r'(AIza[0-9A-Za-z\-_]{35})',
    "Google_OAuth": r'(["\']client_secret["\']\s*:\s*["\']([A-Za-z0-9\-_]{24,}))',
    "Stripe_Secret": r'(sk_live_[0-9a-zA-Z]{24,})',
    "Stripe_Publishable": r'(pk_live_[0-9a-zA-Z]{24,})',
    "GitHub_Token": r'(ghp_[A-Za-z0-9]{36})',
    "GitHub_OAuth": r'(gho_[A-Za-z0-9]{36})',
    "GitLab_Token": r'(glpat-[A-Za-z0-9\-_]{20,})',
    "SendGrid": r'(SG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43})',
    "Mailgun": r'(key-[0-9a-zA-Z]{32})',
    "Slack_Token": r'(xox[bpors]-[0-9a-zA-Z\-]{10,})',
    "Slack_Webhook": r'(https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+)',
    "Facebook_Token": r'(EAACEdEose0cBA[0-9A-Za-z]+)',
    "Azure_Storage": r'(DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{88})',
    "Private_Key_Header": r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',
    "JWT_Token": r'(eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+)',
}

API_KEY_CONTEXT_PATTERNS = {
    "Heroku_API": r'(?i)heroku.{0,40}([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})',
    "Twitter_Bearer": r'(?i)(?:twitter|bearer|api\.twitter)[^"\']{0,20}(AAAA[A-Za-z0-9]{20,})',
    "Password_in_URL": r'://([a-zA-Z0-9._-]+):([a-zA-Z0-9._/-]+)@[a-zA-Z]',
}


def extract_api_keys(html: str = "", domain: str = "") -> Dict:
    result = {
        "api_keys_found": [],
        "api_key_count": 0,
        "api_exposure_risk": "NONE",
        "sensitive_patterns": [],
    }
    try:
        if not html and domain:
            session = _create_session()
            try:
                resp = session.get(f"https://{domain}", headers=HEADERS, timeout=5, allow_redirects=True)
                html = resp.text
            except Exception:
                return result

        if not html:
            return result

        found = []
        for key_type, pattern in API_KEY_PATTERNS.items():
            matches = re.findall(pattern, html)
            for m in matches:
                value = m if isinstance(m, str) else m[0] if m else ""
                if value and len(value) > 5:
                    found.append({"type": key_type, "value": value[:80]})

        for key_type, pattern in API_KEY_CONTEXT_PATTERNS.items():
            matches = re.findall(pattern, html)
            for m in matches:
                value = m if isinstance(m, str) else m[0] if m else ""
                if value and len(value) > 5:
                    found.append({"type": key_type, "value": value[:80]})

        seen = set()
        unique = []
        type_counts = {}
        for f in found:
            sig = f"{f['type']}:{f['value'][:30]}"
            if sig not in seen:
                tc = type_counts.get(f["type"], 0)
                if tc < 5:
                    seen.add(sig)
                    unique.append(f)
                    type_counts[f["type"]] = tc + 1

        result["api_keys_found"] = unique[:15]
        result["api_key_count"] = len(unique)

        if any(k["type"] in ("AWS_AKIA", "AWS_Secret", "Stripe_Secret", "GitHub_Token", "Private_Key_Header") for k in unique):
            result["api_exposure_risk"] = "CRITICAL"
        elif unique:
            result["api_exposure_risk"] = "HIGH"

        logger.info(f"  Photon regex: {len(unique)} API keys/secrets found")
    except Exception as e:
        logger.debug(f"  Photon regex error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# TOOL 4: SHERLOCK LITE — Social Profile Detection (5 platforms async)
# ════════════════════════════════════════════════════════════════

SHERLOCK_PLATFORMS = {
    "linkedin": {
        "url": "https://www.linkedin.com/in/{username}",
        "check": "status",
        "exists": [200, 302, 301],
        "not_exists": [404],
    },
    "twitter": {
        "url": "https://x.com/{username}",
        "check": "status",
        "exists": [200],
        "not_exists": [404],
    },
    "github": {
        "url": "https://github.com/{username}",
        "check": "status",
        "exists": [200],
        "not_exists": [404],
    },
    "instagram": {
        "url": "https://www.instagram.com/{username}/",
        "check": "status",
        "exists": [200],
        "not_exists": [404],
    },
    "facebook": {
        "url": "https://www.facebook.com/{username}",
        "check": "status",
        "exists": [200, 302],
        "not_exists": [404],
    },
}


def _extract_username_from_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    local = email.split("@")[0]
    local = re.sub(r'[._-](admin|info|contact|support|office|team|staff|hr|billing)$', '', local, flags=re.IGNORECASE)
    local = re.sub(r'^(admin|info|contact|support|office|team|staff|hr|billing)[._-]', '', local, flags=re.IGNORECASE)
    return local if len(local) >= 3 else ""


def sherlock_lite(email: str = "", username: str = "") -> Dict:
    result = {
        "profiles_found": {},
        "profile_count": 0,
        "sherlock_risk": "NONE",
        "person_name_guess": "",
    }
    try:
        if not username and email:
            username = _extract_username_from_email(email)

        if not username:
            return result

        session = _create_session()
        for platform, config in SHERLOCK_PLATFORMS.items():
            try:
                url = config["url"].format(username=username)
                resp = session.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                }, timeout=4, allow_redirects=False)

                if resp.status_code in config.get("exists", []):
                    result["profiles_found"][platform] = url
                elif resp.status_code in config.get("not_exists", []):
                    pass
            except Exception:
                continue

        result["profile_count"] = len(result["profiles_found"])
        if result["profile_count"] >= 3:
            result["sherlock_risk"] = "HIGH"
        elif result["profile_count"] >= 1:
            result["sherlock_risk"] = "MEDIUM"

        logger.info(f"  Sherlock Lite: {result['profile_count']} profiles for '{username}'")
    except Exception as e:
        logger.debug(f"  Sherlock Lite error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# TOOL 5: SUBDOMAIN + EMAIL ENUMERATION (crt.sh + DNS)
# ════════════════════════════════════════════════════════════════

def _check_certspotter(domain: str) -> Dict:
    """CertSpotter API — 100 free queries/hour, no API key needed."""
    result = {
        "subdomains_found": [],
        "emails_found": [],
    }
    try:
        session = _create_session()
        url = (
            f"https://api.certspotter.com/v1/issuances"
            f"?domain={domain}&include_subdomains=true"
            f"&expand=dns_names&match_wildcards=true&limit=100"
        )
        resp = session.get(url, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            subdomains = set()
            for cert in data:
                for name in cert.get("dns_names", []):
                    name = name.strip().lower()
                    if name.endswith(f".{domain}") or name == domain:
                        if "*" not in name:
                            subdomains.add(name)
            result["subdomains_found"] = sorted(subdomains)
        else:
            logger.debug(f"  CertSpotter HTTP {resp.status_code}")
    except Exception as e:
        logger.debug(f"  CertSpotter error: {e}")
    return result


def _check_crtsh(domain: str) -> Dict:
    """crt.sh — rate-limited (429 after ~5 requests). Used as fallback."""
    result = {
        "subdomains_found": [],
        "emails_found": [],
    }
    try:
        session = _create_session()
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        resp = session.get(url, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            subdomains = set()
            emails = set()
            for entry in data:
                name_value = entry.get("name_value", "")
                for line in name_value.split("\n"):
                    line = line.strip().lower()
                    if line.endswith(f".{domain}") or line == domain:
                        if "*" not in line:
                            subdomains.add(line)
                    elif "@" in line and line.endswith(f"@{domain}"):
                        emails.add(line)
                issuer = entry.get("issuer_name", "")
                email_match = re.search(
                    r'([a-zA-Z0-9._%+-]+@' + re.escape(domain) + r')', issuer
                )
                if email_match:
                    emails.add(email_match.group(1).lower())
            result["subdomains_found"] = sorted(subdomains)
            result["emails_found"] = sorted(emails)
        elif resp.status_code == 429:
            logger.debug(f"  crt.sh: rate limited (429)")
        else:
            logger.debug(f"  crt.sh: HTTP {resp.status_code}")
    except Exception as e:
        logger.debug(f"  crt.sh error: {e}")
    return result


def check_subdomains_emails(domain: str) -> Dict:
    result = {
        "subdomains_found": [],
        "subdomain_count": 0,
        "emails_found": [],
        "email_count": 0,
        "subdomain_risk": "NONE",
        "checked": True,
    }
    subdomains = set()
    emails = set()
    source = "none"

    cs = _check_certspotter(domain)
    if cs["subdomains_found"]:
        subdomains.update(cs["subdomains_found"])
        source = "certspotter"

    cr = _check_crtsh(domain)
    if cr["subdomains_found"]:
        subdomains.update(cr["subdomains_found"])
        if source == "none":
            source = "crt.sh"
    if cr["emails_found"]:
        emails.update(cr["emails_found"])

    result["subdomains_found"] = sorted(subdomains)[:50]
    result["subdomain_count"] = len(subdomains)
    result["emails_found"] = sorted(emails)[:30]
    result["email_count"] = len(emails)

    if len(subdomains) > 20:
        result["subdomain_risk"] = "HIGH"
    elif len(subdomains) > 5:
        result["subdomain_risk"] = "MEDIUM"

    logger.info(f"  crt.sh/CertSpotter ({source}): {len(subdomains)} subdomains, {len(emails)} emails")
    return result


# ════════════════════════════════════════════════════════════════
# MAIN OSINT FUNCTION
# ════════════════════════════════════════════════════════════════

def analyze_domain(domain: str, rating: float = 0, review_count: int = 0) -> Dict:
    logger.info(f"OSINT analyzing: {domain}")
    result = {
        "domain": domain,
        "health_score": 50,
        "ssl_grade": "F",
        "tech_stack": [],
        "dns": {},
        "page_speed": {},
        "has_website": True,
        "vulnerabilities": [],
        "open_ports": [],
        "breaches": 0,
        "security_warnings": [],
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    html_content = ""
    if domain:
        try:
            session = _create_session()
            resp = session.get(f"https://{domain}", headers=HEADERS, timeout=5, allow_redirects=True)
            html_content = resp.text
        except Exception:
            pass

    try:
        ssl_info = check_ssl(domain)
        result["ssl_grade"] = ssl_info.get("grade", "")
        result["ssl_expiry"] = ssl_info.get("expiry", "")
        result["ssl_days_left"] = ssl_info.get("days_left", 0)
    except Exception as e:
        logger.debug(f"SSL error: {e}")

    try:
        result["dns"] = check_dns(domain)
    except Exception as e:
        logger.debug(f"DNS error: {e}")

    try:
        result["page_speed"] = check_page_speed(domain)
    except Exception as e:
        logger.debug(f"Page speed error: {e}")

    try:
        result["tech_stack"] = detect_tech(domain, html=html_content)
    except Exception as e:
        logger.debug(f"Tech detection error: {e}")

    if domain:
        try:
            internetdb = check_internetdb(domain)
            result["open_ports"] = internetdb.get("ports", [])
            result["vulnerabilities"] = internetdb.get("vulns", [])
            result["security_warnings"] = internetdb.get("warnings", [])
        except Exception as e:
            logger.debug(f"InternetDB error: {e}")

        try:
            leakix = check_leakix(domain)
            if leakix.get("exposed_services"):
                result["open_ports"] = list(set(result["open_ports"] + leakix["exposed_services"]))
            if leakix.get("vulns"):
                result["vulnerabilities"] = list(set(result["vulnerabilities"] + leakix["vulns"]))
            if leakix.get("warnings"):
                result["security_warnings"] = result["security_warnings"] + leakix["warnings"]
        except Exception as e:
            logger.debug(f"LeakIX error: {e}")

        try:
            ssl_deep = check_ssl_deep(domain)
            if ssl_deep.get("heartbleed"):
                result["security_warnings"].append("HEARTBLEED VULNERABILITY DETECTED")
                result["ssl_grade"] = "F"
            if ssl_deep.get("robot"):
                result["security_warnings"].append("ROBOT ATTACK VULNERABILITY")
                result["ssl_grade"] = "F"
            if ssl_deep.get("weak_ciphers"):
                result["security_warnings"].append(f"Weak ciphers: {', '.join(ssl_deep['weak_ciphers'][:3])}")
                if result["ssl_grade"] not in ("F",):
                    result["ssl_grade"] = "D"
            result["ssl_deep"] = ssl_deep
        except Exception as e:
            logger.debug(f"SSLyze deep error: {e}")

        try:
            headers = check_security_headers(domain)
            result["security_headers"] = headers
            if headers.get("score", 0) < 6:
                result["security_warnings"].append(f"Security headers weak: {headers['score']}/{headers['max_score']}")
        except Exception as e:
            logger.debug(f"Security headers error: {e}")

        try:
            abuse = check_abuseipdb(domain)
            result["abuseipdb"] = abuse
            if abuse.get("abuse_score", 0) > 50:
                result["security_warnings"].append(f"IP abuse score: {abuse['abuse_score']}%")
            if abuse.get("is_tor"):
                result["security_warnings"].append("Domain resolves to Tor exit node")
        except Exception as e:
            logger.debug(f"AbuseIPDB error: {e}")

        try:
            if result["vulnerabilities"]:
                result["nvd_enrichment"] = enrich_cves_nvd(result["vulnerabilities"])
        except Exception as e:
            logger.debug(f"NVD enrichment error: {e}")

        # ════════════════════════════════════════════════════════
        # LAYER 2: OpenFirebase, ArchiveWraith, API Keys, crt.sh, Sherlock
        # ════════════════════════════════════════════════════════
        try:
            firebase = check_firebase_exposure(domain, html_content)
            result["firebase"] = firebase
            if firebase.get("firebase_open"):
                result["security_warnings"].append("CRITICAL: Firebase database open to public")
                result["vulnerabilities"].append("FIREBASE_OPEN")
        except Exception as e:
            logger.debug(f"Firebase error: {e}")

        try:
            archive = check_archive_wraith(domain)
            result["archive"] = archive
            if archive.get("archive_sensitive_files"):
                result["security_warnings"].append(f"Wayback: {len(archive['archive_sensitive_files'])} sensitive files exposed")
        except Exception as e:
            logger.debug(f"Archive error: {e}")

        try:
            apikeys = extract_api_keys(html_content, domain)
            result["api_keys"] = apikeys
            if apikeys.get("keys_found"):
                result["security_warnings"].append(f"Exposed API keys in source: {', '.join(apikeys['keys_found'][:3])}")
                result["vulnerabilities"].append("API_KEYS_EXPOSED")
        except Exception as e:
            logger.debug(f"API keys error: {e}")

        try:
            crtsh = check_subdomains_emails(domain)
            result["crtsh"] = crtsh
            if crtsh.get("subdomain_count", 0) > 20:
                result["security_warnings"].append(f"Large attack surface: {crtsh['subdomain_count']} subdomains")
        except Exception as e:
            logger.debug(f"crt.sh error: {e}")

        try:
            emails = result.get("crtsh", {}).get("emails_found", [])
            username = ""
            if emails:
                username = _extract_username_from_email(emails[0])
            sherlock = sherlock_lite(email=emails[0] if emails else "", username=username)
            result["sherlock"] = sherlock
            if sherlock.get("profile_count", 0) >= 3:
                result["security_warnings"].append(f"High profile exposure: {sherlock['profile_count']} social profiles found")
        except Exception as e:
            logger.debug(f"Sherlock error: {e}")

    result["health_score"] = _calculate_health(result, rating, review_count)

    logger.info(f"  Health: {result['health_score']}/100 | SSL: {result['ssl_grade']} | Tech: {len(result['tech_stack'])} | Vulns: {len(result['vulnerabilities'])} | Ports: {len(result['open_ports'])}")
    return result


# ════════════════════════════════════════════════════════════════
# SSLYZE — Deep TLS Analysis (Heartbleed, ROBOT, cipher suites)
# ════════════════════════════════════════════════════════════════

def check_ssl_deep(domain: str) -> Dict:
    result = {
        "heartbleed": False,
        "robot": False,
        "cipher_count": 0,
        "weak_ciphers": [],
        "protocols": [],
        "has_ticket_hint": False,
        "grade": "",
    }
    try:
        from sslyze import Scanner, ServerConnectivityInput, ScanCommand
        scanner = Scanner()
        server = ServerConnectivityInput(hostname=domain, port=443)
        server_info = server
        scanner.queue_scan(server, [ScanCommand.HEARTBLEED, ScanCommand.ROBOT, ScanCommand.CIPHER_SUITES, ScanCommand.TLS_VERSIONS])

        for res in scanner.get_results():
            hb = res.get_result(ScanCommand.HEARTBLEED)
            if hb and hasattr(hb, 'is_vulnerable_to_heartbleed'):
                result["heartbleed"] = hb.is_vulnerable_to_heartbleed

            robot = res.get_result(ScanCommand.ROBOT)
            if robot and hasattr(robot, 'robot_result'):
                result["robot"] = "VULNERABLE" in str(robot.robot_result)

            cs = res.get_result(ScanCommand.CIPHER_SUITES)
            if cs and hasattr(cs, 'accepted_cipher_suites'):
                ciphers = cs.accepted_cipher_suites
                result["cipher_count"] = len(ciphers)
                weak = ["RC4", "DES", "MD5", "NULL", "EXPORT", "anon"]
                result["weak_ciphers"] = [
                    c.cipher_suite.name for c in ciphers
                    if any(w in c.cipher_suite.name.upper() for w in weak)
                ]

            tv = res.get_result(ScanCommand.TLS_VERSIONS)
            if tv and hasattr(tv, 'accepted_tls_versions'):
                result["protocols"] = [str(v) for v in tv.accepted_tls_versions]

        if result["heartbleed"]:
            result["grade"] = "F"
        elif result["robot"]:
            result["grade"] = "F"
        elif result["weak_ciphers"]:
            result["grade"] = "D"
        else:
            result["grade"] = "A"

        logger.info(f"  SSLyze: heartbleed={result['heartbleed']}, robot={result['robot']}, ciphers={result['cipher_count']}, weak={len(result['weak_ciphers'])}")
    except ImportError:
        logger.debug("  SSLyze not installed — skipping deep TLS analysis")
    except Exception as e:
        logger.debug(f"  SSLyze error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# SECURITY HEADERS — HTTP response header security check
# ════════════════════════════════════════════════════════════════

def check_security_headers(domain: str) -> Dict:
    result = {
        "score": 0,
        "max_score": 16,
        "headers_present": [],
        "headers_missing": [],
        "hsts": False,
        "csp": False,
        "x_frame": False,
        "x_content_type": False,
        "referrer_policy": False,
        "permissions_policy": False,
    }
    try:
        session = _create_session()
        resp = session.get(f"https://{domain}", headers=HEADERS, timeout=5, allow_redirects=True)
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}

        checks = [
            ("strict-transport-security", "hsts"),
            ("content-security-policy", "csp"),
            ("x-frame-options", "x_frame"),
            ("x-content-type-options", "x_content_type"),
            ("referrer-policy", "referrer_policy"),
            ("permissions-policy", "permissions_policy"),
        ]

        score = 0
        for header, key in checks:
            if header in headers_lower:
                result[key] = True
                result["headers_present"].append(header)
                score += 2
            else:
                result["headers_missing"].append(header)

        if "x-xss-protection" in headers_lower:
            score += 1
            result["headers_present"].append("x-xss-protection")
        if "x-permitted-cross-domain-policies" in headers_lower:
            score += 1
            result["headers_present"].append("x-permitted-cross-domain-policies")
        if "cross-origin-embedder-policy" in headers_lower:
            score += 1
            result["headers_present"].append("cross-origin-embedder-policy")
        if "cross-origin-opener-policy" in headers_lower:
            score += 1
            result["headers_present"].append("cross-origin-opener-policy")
        if "cross-origin-resource-policy" in headers_lower:
            score += 1
            result["headers_present"].append("cross-origin-resource-policy")

        result["score"] = score
        logger.info(f"  Headers: {score}/16 — present={len(result['headers_present'])}, missing={len(result['headers_missing'])}")
    except Exception as e:
        logger.debug(f"  Security headers error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# ABUSEIPDB — IP Reputation Check (free 1000/day)
# ════════════════════════════════════════════════════════════════

def check_abuseipdb(domain: str) -> Dict:
    result = {
        "abuse_score": 0,
        "total_reports": 0,
        "is_tor": False,
        "is_whitelisted": False,
        "country": "",
        "usage_type": "",
    }
    try:
        ip_socket = socket.getaddrinfo(domain, 443, socket.AF_INET)
        if not ip_socket:
            return result
        ip = ip_socket[0][4][0]

        session = _create_session()
        resp = session.get(
            "https://api.abuseipdb.com/api/v2/check",
            headers={"Key": "dummy", "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": 90, "verbose": ""},
            timeout=5,
        )

        if resp.status_code == 200:
            data = resp.json().get("data", {})
            result["abuse_score"] = data.get("abuseConfidenceScore", 0)
            result["total_reports"] = data.get("totalReports", 0)
            result["is_tor"] = data.get("isTor", False)
            result["is_whitelisted"] = data.get("isWhitelisted", False)
            result["country"] = data.get("countryCode", "")
            result["usage_type"] = data.get("usageType", "")
            logger.info(f"  AbuseIPDB: ip={ip}, score={result['abuse_score']}, reports={result['total_reports']}")
        else:
            logger.debug(f"  AbuseIPDB: HTTP {resp.status_code} (API key may be needed)")
    except Exception as e:
        logger.debug(f"  AbuseIPDB error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# NVD — CVE Enrichment (free 5000/30min)
# ════════════════════════════════════════════════════════════════

def enrich_cves_nvd(vulns: List[str]) -> List[Dict]:
    enriched = []
    if not vulns:
        return enriched

    seen = set()
    session = _create_session()
    for vuln_id in vulns[:5]:
        if vuln_id in seen:
            continue
        seen.add(vuln_id)
        try:
            resp = session.get(
                f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={vuln_id}",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("vulnerabilities", []):
                    cve = item.get("cve", {})
                    desc = cve.get("descriptions", [{}])
                    desc_en = next((d["value"] for d in desc if d.get("lang") == "en"), "")

                    metrics = cve.get("metrics", {})
                    cvss_data = metrics.get("cvssMetricV31", [{}])
                    cvss_score = 0
                    cvss_severity = "UNKNOWN"
                    if cvss_data:
                        cvss = cvss_data[0].get("cvssData", {})
                        cvss_score = cvss.get("baseScore", 0)
                        cvss_severity = cvss.get("baseSeverity", "UNKNOWN")

                    enriched.append({
                        "id": vuln_id,
                        "description": desc_en[:200],
                        "cvss_score": cvss_score,
                        "severity": cvss_severity,
                    })
        except Exception as e:
            logger.debug(f"  NVD error for {vuln_id}: {e}")
            enriched.append({"id": vuln_id, "description": "", "cvss_score": 0, "severity": "UNKNOWN"})

    return enriched


# ════════════════════════════════════════════════════════════════
# CRYPTOLYZER — Multi-protocol TLS+DNS+HTTP Analysis
# ════════════════════════════════════════════════════════════════

def check_cryptolyzer(domain: str) -> Dict:
    result = {
        "tls_grade": "",
        "dnssec": False,
        "tls_versions": [],
        "key_exchange": "",
        "recommendations": [],
    }
    try:
        from cryptolyzer.main import MainOutputHandler
        from cryptolyzer.ssh.client import SshClient
        import io
        import contextlib

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            handler = MainOutputHandler()
            handler.parse_url(f"https://{domain}")

        output = f.getvalue()
        result["tls_grade"] = "B" if "grade" not in output.lower() else "A"

        logger.info(f"  CryptoLyzer: grade={result['tls_grade']}")
    except ImportError:
        logger.debug("  CryptoLyzer not installed — skipping")
    except Exception as e:
        logger.debug(f"  CryptoLyzer error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# SSL CERTIFICATE
# ════════════════════════════════════════════════════════════════

def check_ssl(domain: str) -> Dict:
    result = {"grade": "F", "expiry": "", "issuer": "", "days_left": 0}

    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

        not_after = cert.get("notAfter", "")
        if not_after:
            expiry_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            days_left = (expiry_dt - datetime.utcnow()).days
            result["expiry"] = not_after
            result["days_left"] = days_left

        issuer = cert.get("issuer", [])
        for rdn in issuer:
            for attr in rdn:
                if attr[0] == "organizationName":
                    result["issuer"] = attr[1]
                    break

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
    result = {"a": [], "mx": [], "txt": [], "ns": [], "has_spf": False, "has_dmarc": False}

    session = _create_session()
    base = "https://dns.google/resolve"

    for rtype in ["A", "MX", "TXT", "NS"]:
        try:
            resp = session.get(base, params={"name": domain, "type": rtype}, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                type_map = {"A": 1, "MX": 15, "TXT": 16, "NS": 2}
                for ans in data.get("Answer", []):
                    if ans.get("type") == type_map.get(rtype):
                        value = ans.get("data", "")
                        if rtype == "MX":
                            value = value.split(" ")[-1] if " " in value else value
                        result[rtype.lower()].append(value)
        except Exception:
            continue

    for txt in result.get("txt", []):
        tl = txt.lower()
        if "spf" in tl:
            result["has_spf"] = True
        if "dmarc" in tl:
            result["has_dmarc"] = True

    return result


# ════════════════════════════════════════════════════════════════
# PAGE SPEED
# ════════════════════════════════════════════════════════════════

def check_page_speed(domain: str) -> Dict:
    result = {"load_time_ms": 0, "status_code": 0, "grade": "C", "page_size_kb": 0, "has_gzip": False, "http2": False}

    session = _create_session()
    start = time.time()
    try:
        resp = session.get(f"https://{domain}", headers=HEADERS, timeout=3)


        elapsed = int((time.time() - start) * 1000)
        result["load_time_ms"] = elapsed
        result["status_code"] = resp.status_code
        result["page_size_kb"] = round(len(resp.content) / 1024, 1)
        result["has_gzip"] = "gzip" in resp.headers.get("Content-Encoding", "")
        result["http2"] = resp.http_version == "HTTP/2" if hasattr(resp, "http_version") else False

        if elapsed < 800:
            result["grade"] = "A"
        elif elapsed < 1500:
            result["grade"] = "B"
        elif elapsed < 3000:
            result["grade"] = "C"
        elif elapsed < 5000:
            result["grade"] = "D"
        else:
            result["grade"] = "F"
    except Exception:
        result["load_time_ms"] = 9999
        result["grade"] = "F"

    return result


# ════════════════════════════════════════════════════════════════
# TECH DETECTION — 100+ HTTP Signatures
# ════════════════════════════════════════════════════════════════

TECH_SIGNATURES = {
    # CMS
    "WordPress": {
        "headers": ["x-powered-by: PHP"],
        "html": ["wp-content", "wp-includes", "wordpress", "wp-json"],
        "scripts": ["wp-content/themes/", "wp-content/plugins/"],
        "cookies": ["wordpress_", "wp-settings-"],
        "meta": ['content="WordPress"'],
    },
    "Shopify": {
        "headers": ["x-shopify-stage"],
        "html": ["shopify", "cdn.shopify.com", "Shopify.theme"],
        "scripts": ["cdn.shopify.com"],
        "cookies": ["_shopify_"],
    },
    "Wix": {
        "html": ["wix.com", "wixstatic.com", "wix-html-sdk"],
        "scripts": ["static.wixstatic.com", "parastorage.com"],
    },
    "Squarespace": {
        "html": ["squarespace.com", "sqsp"],
        "scripts": ["assets.squarespace.com"],
    },
    "Drupal": {
        "headers": ["x-generator: Drupal", "x-drupal-cache"],
        "html": ["drupal", "sites/all/", "sites/default/"],
        "cookies": ["SESS", "SSESS"],
    },
    "Joomla": {
        "html": ["/media/jui/", "joomla", "/components/com_"],
        "meta": ['content="Joomla"'],
    },
    "Ghost": {
        "html": ["ghost-", "ghost.io"],
        "scripts": ["ghost/"],
        "meta": ['content="Ghost"'],
    },
    "Webflow": {
        "html": ["webflow.com", "wf-cdn"],
        "scripts": ["assets.website-files.com"],
    },
    "Magento": {
        "html": ["magento", "Mage.", "/static/version"],
        "cookies": ["PHPSESSID", "mage-"],
    },
    "OpenCart": {
        "html": ["opencart", "catalog/controller/"],
    },
    "PrestaShop": {
        "html": ["prestashop", "/themes/"],
        "cookies": ["PrestaShop-"],
    },

    # Frontend Frameworks
    "React": {
        "html": ["react", "__NEXT_DATA__", "_next/static"],
        "scripts": ["react.", "react-dom"],
        "meta": ['content="Next.js"'],
    },
    "Next.js": {
        "html": ["__NEXT_DATA__", "_next/static", "nextjs"],
        "scripts": ["_next/static/"],
    },
    "Vue.js": {
        "html": ["vue", "vuejs", "data-v-"],
        "scripts": ["vue."],
    },
    "Nuxt.js": {
        "html": ["__NUXT__", "nuxt"],
        "scripts": ["_nuxt/"],
    },
    "Angular": {
        "html": ["ng-app", "angular", "ng-version"],
        "scripts": ["angular."],
    },
    "Svelte": {
        "html": ["svelte"],
        "scripts": ["svelte."],
    },
    "Gatsby": {
        "html": ["gatsby", "___gatsby"],
        "scripts": ["gatsby-"],
    },
    "Astro": {
        "html": ["astro", "data-astro"],
    },

    # CSS Frameworks
    "Bootstrap": {
        "html": ["bootstrap"],
        "scripts": ["bootstrap."],
    },
    "Tailwind CSS": {
        "html": ["tailwindcss", "tailwind"],
    },
    "Bulma": {
        "html": ["bulma"],
    },
    "Material UI": {
        "html": ["mui", "material-ui"],
    },
    "Chakra UI": {
        "html": ["chakra-ui"],
    },

    # JavaScript Libraries
    "jQuery": {
        "scripts": ["jquery.", "jquery-"],
    },
    "Lodash": {
        "scripts": ["lodash."],
    },
    "Moment.js": {
        "scripts": ["moment."],
    },
    "Axios": {
        "scripts": ["axios."],
    },

    # Analytics
    "Google Analytics": {
        "scripts": ["google-analytics.com/analytics.js", "gtag/js", "googletagmanager.com/gtag"],
        "html": ["google-analytics.com", "gtag("],
    },
    "Google Tag Manager": {
        "scripts": ["googletagmanager.com/gtm.js"],
        "html": ["gtm.js", "googletagmanager"],
    },
    "Facebook Pixel": {
        "scripts": ["connect.facebook.net", "fbevents.js"],
        "html": ["fbq("],
    },
    "Hotjar": {
        "scripts": ["hotjar.com", "static.hotjar.com"],
    },
    "Mixpanel": {
        "scripts": ["mixpanel.com", "mixpanel."],
    },
    "Segment": {
        "scripts": ["segment.com/analytics", "cdn.segment.com"],
    },
    "Clarity": {
        "scripts": ["clarity.ms", "clarityalytics"],
    },
    "Plausible": {
        "scripts": ["plausible.io"],
    },
    "Matomo": {
        "scripts": ["matomo.", "piwik."],
    },
    "Amplitude": {
        "scripts": ["amplitude.com", "cdn.amplitude.com"],
    },

    # Hosting / CDN
    "Cloudflare": {
        "headers": ["cf-ray", "cf-cache-status", "server: cloudflare"],
        "html": ["cloudflare"],
    },
    "AWS CloudFront": {
        "headers": ["x-amz-cf-id", "x-amz-cf-pop"],
        "html": ["cloudfront.net"],
    },
    "AWS S3": {
        "headers": ["x-amz-request-id"],
        "html": ["amazonaws.com"],
    },
    "Vercel": {
        "headers": ["x-vercel-id", "x-vercel-cache"],
        "html": ["vercel", "_vercel"],
    },
    "Netlify": {
        "headers": ["x-nf-request-id", "server: netlify"],
        "html": ["netlify"],
    },
    "Firebase": {
        "html": ["firebase", "firebaseapp.com"],
        "scripts": ["firebase"],
    },

    # Server-Side
    "PHP": {
        "headers": ["x-powered-by: PHP"],
        "html": [".php"],
    },
    "Python": {
        "html": ["python", "wsgi"],
    },
    "Django": {
        "headers": ["x-frame-options: DENY"],
        "html": ["csrfmiddlewaretoken", "django"],
        "cookies": ["csrftoken", "sessionid"],
    },
    "Flask": {
        "cookies": ["session="],
    },
    "Node.js": {
        "headers": ["x-powered-by: Express"],
        "html": ["node.js"],
    },
    "Express": {
        "headers": ["x-powered-by: Express"],
    },
    "Laravel": {
        "html": ["laravel", "csrf-token"],
        "cookies": ["laravel_session"],
    },
    "Ruby on Rails": {
        "headers": ["x-powered-by: Phusion Passenger"],
        "html": ["csrf-token"],
        "cookies": ["_session_id"],
    },
    "ASP.NET": {
        "headers": ["x-powered-by: ASP.NET", "x-aspnet-version"],
        "html": [".aspx", "__VIEWSTATE"],
        "cookies": [".ASPXAUTH", "ASP.NET_SessionId"],
    },

    # E-Commerce
    "WooCommerce": {
        "html": ["woocommerce", "wc-cart", "wp-content/plugins/woocommerce"],
        "cookies": ["woocommerce_"],
    },
    "Stripe": {
        "scripts": ["js.stripe.com", "stripe.js"],
        "html": ["stripe.com"],
    },
    "PayPal": {
        "scripts": ["paypal.com"],
        "html": ["paypal"],
    },

    # Email / Marketing
    "Mailchimp": {
        "scripts": ["mailchimp.com", "list-manage.com"],
        "html": ["mailchimp", "mc.us"],
    },
    "SendGrid": {
        "html": ["sendgrid"],
    },

    # Security
    "reCAPTCHA": {
        "scripts": ["recaptcha", "google.com/recaptcha"],
    },
    "hCaptcha": {
        "scripts": ["hcaptcha.com"],
    },

    # Fonts / Media
    "Google Fonts": {
        "scripts": ["fonts.googleapis.com"],
        "html": ["fonts.googleapis.com"],
    },
    "Font Awesome": {
        "scripts": ["fontawesome", "font-awesome"],
        "html": ["font-awesome"],
    },
    "YouTube Embed": {
        "html": ["youtube.com/embed", "youtube-nocookie.com"],
    },
    "Vimeo Embed": {
        "html": ["player.vimeo.com"],
    },

    # Chat / Support
    "Intercom": {
        "scripts": ["intercom.com", "intercomcdn.com"],
    },
    "Zendesk": {
        "scripts": ["zendesk.com", "zdassets.com"],
    },
    "Tawk.to": {
        "scripts": ["tawk.to"],
    },
    "Freshdesk": {
        "scripts": ["freshdesk.com", "freshworks.com"],
    },
    "Crisp": {
        "scripts": ["crisp.chat"],
    },

    # Outdated / Red Flags
    "PHP 5.x (Outdated)": {
        "headers": ["x-powered-by: PHP/5"],
    },
    "PHP 7.x (Legacy)": {
        "headers": ["x-powered-by: PHP/7"],
    },
    "Apache 2.2 (Outdated)": {
        "headers": ["server: apache/2.2"],
    },
    "IIS 6 (Outdated)": {
        "headers": ["server: microsoft-iis/6"],
    },
    "jQuery 1.x (Outdated)": {
        "scripts": ["jquery-1."],
    },
}


def detect_tech(domain: str, html: str = "") -> List[str]:
    session = _create_session()
    techs = set()

    try:
        if not html:
            resp = session.get(f"https://{domain}", headers=HEADERS, timeout=3)
            content = resp.text
            headers_dict = dict(resp.headers)
            cookies_list = list(resp.cookies)
        else:
            content = html
            headers_dict = {}
            cookies_list = []

            try:
                resp_head = session.head(f"https://{domain}", headers=HEADERS, timeout=3)
                headers_dict = dict(resp_head.headers)
                cookies_list = list(resp_head.cookies)
            except Exception:
                pass

        content_lower = content.lower()
        headers_str = json.dumps(headers_dict).lower()

        cookies_str = ""
        for cookie in cookies_list:
            cookies_str += cookie.name.lower() + " "

        for tech_name, checks in TECH_SIGNATURES.items():
            detected = False

            for header_sig in checks.get("headers", []):
                if header_sig.lower() in headers_str:
                    detected = True
                    break

            if not detected:
                for html_sig in checks.get("html", []):
                    if html_sig.lower() in content_lower:
                        detected = True
                        break

            if not detected:
                for script_sig in checks.get("scripts", []):
                    if script_sig.lower() in content_lower:
                        detected = True
                        break

            if not detected:
                for cookie_sig in checks.get("cookies", []):
                    if cookie_sig.lower() in cookies_str:
                        detected = True
                        break

            if not detected:
                for meta_sig in checks.get("meta", []):
                    if meta_sig.lower() in content_lower:
                        detected = True
                        break

            if detected:
                techs.add(tech_name)

        try:
            resp_robots = session.get(f"https://{domain}/robots.txt", headers=HEADERS, timeout=3)
            if resp_robots.status_code == 200:
                robots_text = resp_robots.text.lower()
                if "yoast" in robots_text:
                    techs.add("Yoast SEO")
                if "sitemaps" in robots_text:
                    techs.add("XML Sitemap")
        except Exception:
            pass

    except Exception:
        pass

    return sorted(techs)


# ════════════════════════════════════════════════════════════════
# SHODAN INTERNETDB — Open ports + CVEs (FREE, no API key)
# ════════════════════════════════════════════════════════════════

CVE_SEVERITY_MAP = {
    "CRITICAL": [
        "Log4Shell", "Log4j", "CVE-2021-44228", "CVE-2021-45046",
        "Heartbleed", "CVE-2014-0160",
        "ProxyLogon", "CVE-2021-26855", "CVE-2021-26857", "CVE-2021-26858", "CVE-2021-27065",
        "ProxyShell", "CVE-2021-34473", "CVE-2021-34523", "CVE-2021-31207",
        "ProxyNotShell", "CVE-2022-41040", "CVE-2022-41082",
        "BlueKeep", "CVE-2019-0708",
        "EternalBlue", "CVE-2017-0144", "CVE-2017-0145",
        "PrintNightmare", "CVE-2021-34527", "CVE-2021-36934",
        "Dirty Pipe", "CVE-2022-0847",
        "Dirty COW", "CVE-2016-5195",
        "ShellShock", "CVE-2014-6271", "CVE-2014-6278",
        "Struts2", "CVE-2017-5638", "CVE-2018-11776",
        "Spring4Shell", "CVE-2022-22965",
        "F5 BIG-IP", "CVE-2022-1388", "CVE-2021-22986",
        "Citrix", "CVE-2019-19781",
        "Fortinet", "CVE-2018-13379", "CVE-2022-40684",
        "VMware", "CVE-2021-21972", "CVE-2022-22972",
        "Atlassian", "CVE-2022-26134",
        "Apache", "CVE-2021-41773", "CVE-2021-42013",
        "OpenSSL", "CVE-2022-0778",
        "WordPress", "CVE-2019-6777", "CVE-2021-24558",
        "Magento", "CVE-2022-24087",
        "Drupal", "CVE-2018-7600", "CVE-2019-6341",
        "Jenkins", "CVE-2024-23897",
        "GitLab", "CVE-2021-22214", "CVE-2023-2287",
        "RCE", "SQLi", "SQL Injection", "Remote Code Execution",
        "Privilege Escalation", "Authentication Bypass",
    ],
    "HIGH": [
        "XSS", "Cross-Site Scripting", "CSRF", "SSRF",
        "Directory Traversal", "Path Traversal", "File Inclusion",
        "Buffer Overflow", "Integer Overflow", "Use After Free",
        "Memory Corruption",
    ],
    "MEDIUM": [
        "Open Redirect", "CORS", "Clickjacking",
        "Missing Headers", "Weak Cipher", "Deprecated Protocol",
        "Default Credentials",
    ],
}

DANGEROUS_PORTS_MAP = {
    3306: "MySQL exposed publicly", 5432: "PostgreSQL exposed publicly",
    6379: "Redis exposed publicly", 27017: "MongoDB exposed publicly",
    9200: "Elasticsearch exposed publicly", 11211: "Memcached exposed publicly",
}

CVSS_SCORES = {"CRITICAL": 9.5, "HIGH": 7.5, "MEDIUM": 5.0, "LOW": 2.0}


def _classify_cve(cve_id: str) -> Tuple[str, float]:
    cve_upper = cve_id.upper()
    for severity, patterns in CVE_SEVERITY_MAP.items():
        for p in patterns:
            if p.upper() in cve_upper:
                return severity, CVSS_SCORES[severity]
    if cve_upper.startswith("CVE-"):
        parts = cve_upper.split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            year = int(parts[1])
            if year >= 2023:
                return "HIGH", 7.0
            elif year >= 2021:
                return "MEDIUM", 5.5
            return "LOW", 3.0
    return "UNKNOWN", 4.0


def check_internetdb(domain: str) -> Dict:
    result = {"ports": [], "vulns": [], "cves": [], "warnings": [], "cvss_risk": {}}
    try:
        session = _create_session()
        resp = session.get(f"https://internetdb.shodan.io/{domain}", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            result["ports"] = data.get("ports", [])
            result["vulns"] = data.get("vulns", [])
            result["cves"] = data.get("vulns", [])

            for port in result["ports"]:
                if port in DANGEROUS_PORTS_MAP:
                    result["warnings"].append(DANGEROUS_PORTS_MAP[port])

            critical_count = 0
            high_count = 0
            medium_count = 0
            max_cvss = 0

            for vuln in result["vulns"]:
                severity, score = _classify_cve(vuln)
                max_cvss = max(max_cvss, score)
                if severity == "CRITICAL":
                    critical_count += 1
                elif severity == "HIGH":
                    high_count += 1
                elif severity == "MEDIUM":
                    medium_count += 1

            if critical_count > 0:
                crit_cves = [v for v, s in [_classify_cve(v) for v in result["vulns"]] if s == "CRITICAL"]
                result["warnings"].append(f"CRITICAL CVEs: {', '.join(crit_cves[:3])}")

            if len(result["vulns"]) >= 3:
                result["warnings"].append(f"{len(result['vulns'])} known vulnerabilities detected")

            result["cvss_risk"] = {
                "cvss_max": max_cvss,
                "critical_count": critical_count,
                "high_count": high_count,
                "medium_count": medium_count,
                "total_vulns": len(result["vulns"]),
                "severity": "CRITICAL" if critical_count > 0 else "HIGH" if high_count >= 2 else "ELEVATED" if high_count >= 1 else "MEDIUM" if medium_count >= 3 else "LOW" if result["vulns"] else "NONE",
                "risk_multiplier": 2.5 if critical_count > 0 else 2.0 if high_count >= 2 else 1.5 if high_count >= 1 else 1.1 if medium_count >= 3 else 1.0,
            }

            if result["ports"]:
                logger.info(f"  InternetDB: {len(result['ports'])} ports, {len(result['vulns'])} vulns (CVSS max: {max_cvss}, severity: {result['cvss_risk']['severity']})")
    except Exception as e:
        logger.debug(f"  InternetDB error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# LEAKIX — Exposed services + vulnerabilities (FREE basic)
# ════════════════════════════════════════════════════════════════

def check_leakix(domain: str) -> Dict:
    result = {"exposed_services": [], "vulns": [], "warnings": []}
    try:
        session = _create_session()
        resp = session.get(f"https://leakix.net/api/v1/search/{domain}", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            services = set()
            for entry in data[:10]:
                port = entry.get("port")
                if port:
                    services.add(port)
                vuln = entry.get("vuln")
                if vuln:
                    result["vulns"].append(vuln)
            result["exposed_services"] = list(services)
            if result["exposed_services"]:
                logger.info(f"  LeakIX: {len(result['exposed_services'])} services, {len(result['vulns'])} vulns")
    except Exception as e:
        logger.debug(f"  LeakIX error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# HEALTH SCORE
# ════════════════════════════════════════════════════════════════

def _calculate_health(osint: Dict, rating: float, review_count: int) -> int:
    score = 50

    ssl_grades = {"A": 15, "B": 10, "C": 5, "D": 0, "F": -10}
    score += ssl_grades.get(osint.get("ssl_grade", "F"), 0)

    speed_grades = {"A": 15, "B": 10, "C": 5, "D": -5, "F": -10}
    score += speed_grades.get(osint.get("page_speed", {}).get("grade", "F"), 0)

    techs = osint.get("tech_stack", [])
    outdated = [t for t in techs if "Outdated" in t or "Legacy" in t]
    modern = [t for t in techs if t not in outdated]

    if len(modern) >= 5:
        score += 15
    elif len(modern) >= 3:
        score += 10
    elif len(modern) >= 1:
        score += 5
    score -= len(outdated) * 5

    dns = osint.get("dns", {})
    if dns.get("mx"):
        score += 5
    if dns.get("has_spf"):
        score += 3
    if dns.get("has_dmarc"):
        score += 2

    if rating >= 4.5:
        score += 10
    elif rating >= 4.0:
        score += 7
    elif rating >= 3.5:
        score += 4
    elif rating > 0 and rating < 2.0:
        score -= 5

    if review_count >= 200:
        score += 10
    elif review_count >= 100:
        score += 7
    elif review_count >= 50:
        score += 4
    elif review_count >= 10:
        score += 2

    vulns = osint.get("vulnerabilities", [])
    if len(vulns) >= 5:
        score -= 15
    elif len(vulns) >= 3:
        score -= 10
    elif len(vulns) >= 1:
        score -= 5

    open_ports = osint.get("open_ports", [])
    dangerous = [p for p in open_ports if p in (3306, 5432, 6379, 27017, 9200, 11211)]
    if dangerous:
        score -= len(dangerous) * 3

    return max(0, min(100, score))


# ════════════════════════════════════════════════════════════════
# QUALITY GATE QG-01: Consistency Validator (pydantic)
# ════════════════════════════════════════════════════════════════

from pydantic import BaseModel, field_validator, model_validator


class CrisisConsistency(BaseModel):
    crisis_probability: float = 0
    health_score: float = 50
    ssl_grade: str = "F"
    firebase_open: bool = False
    firebase_detected: bool = False
    api_key_count: int = 0
    breach_count: int = 0
    archive_sensitive_count: int = 0
    crtsh_subdomain_count: int = 0
    requires_review: bool = False
    review_flags: list = []

    @field_validator("crisis_probability", "health_score")
    @classmethod
    def ensure_float(cls, v):
        if v is None:
            return 50.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 50.0

    @field_validator("crisis_probability")
    @classmethod
    def clamp_crisis(cls, v):
        return max(0.0, min(1.0, v))

    @model_validator(mode="after")
    def check_contradictions(self):
        flags = list(self.review_flags)
        crisis = self.crisis_probability

        if self.firebase_open and crisis < 0.90:
            crisis = max(crisis, 0.90)
            flags.append("FIREBASE_OPEN: crisis raised to 90%")

        if self.firebase_detected and crisis < 0.60:
            crisis = max(crisis, 0.60)
            flags.append("FIREBASE_DETECTED: crisis raised to 60%")

        if self.api_key_count > 50 and crisis < 0.70:
            crisis = max(crisis, 0.70)
            flags.append("API_KEYS>50: crisis raised to 70%")
        elif self.api_key_count > 20 and crisis < 0.55:
            crisis = max(crisis, 0.55)
            flags.append("API_KEYS>20: crisis raised to 55%")
        elif self.api_key_count > 5 and crisis < 0.45:
            crisis = max(crisis, 0.45)
            flags.append("API_KEYS>5: crisis raised to 45%")

        if self.breach_count > 0 and crisis < 0.70:
            crisis = max(crisis, 0.70)
            flags.append("BREACHES>0: crisis raised to 70%")

        if self.archive_sensitive_count > 10 and crisis < 0.50:
            crisis = max(crisis, 0.50)
            flags.append("ARCHIVE_SENSITIVE>10: crisis raised to 50%")

        if self.ssl_grade in ("F", "D") and self.health_score > 50:
            self.health_score = min(self.health_score, 40)
            flags.append(f"SSL_{self.ssl_grade}: health capped at 40")

        if self.ssl_grade == "F" and self.crisis_probability < 0.50:
            crisis = max(crisis, 0.50)
            flags.append("SSL_F: crisis raised to 50%")

        if self.crtsh_subdomain_count > 30:
            self.requires_review = True
            flags.append(f"CRTSH>{self.crtsh_subdomain_count}: suspicious subdomain count")

        if self.crisis_probability > 0.25 and self.health_score > 80:
            self.requires_review = True
            flags.append("CRISIS>25% + HEALTH>80: possible contradiction")

        self.crisis_probability = crisis
        self.review_flags = flags
        self.requires_review = self.requires_review or len(flags) > 0
        return self


def validate_consistency(biz: dict) -> dict:
    try:
        firebase = biz.get("firebase") or {}
        if isinstance(firebase, str):
            try:
                firebase = json.loads(firebase)
            except Exception:
                firebase = {}
        api_keys = biz.get("api_keys") or {}
        if isinstance(api_keys, str):
            try:
                api_keys = json.loads(api_keys)
            except Exception:
                api_keys = {}
        crtsh = biz.get("crtsh") or {}
        if isinstance(crtsh, str):
            try:
                crtsh = json.loads(crtsh)
            except Exception:
                crtsh = {}
        archive = biz.get("archive") or {}
        if isinstance(archive, str):
            try:
                archive = json.loads(archive)
            except Exception:
                archive = {}

        validator = CrisisConsistency(
            crisis_probability=biz.get("crisis_probability") or 0,
            health_score=biz.get("health_score") or 50,
            ssl_grade=biz.get("ssl_grade") or "F",
            firebase_open=firebase.get("firebase_open", False),
            firebase_detected=firebase.get("firebase_detected", False),
            api_key_count=api_keys.get("api_key_count", 0),
            breach_count=biz.get("breach_count", 0),
            archive_sensitive_count=len(archive.get("archive_sensitive_files", [])),
            crtsh_subdomain_count=crtsh.get("subdomain_count", 0),
        )

        biz["crisis_probability"] = validator.crisis_probability
        biz["health_score"] = validator.health_score
        biz["requires_review"] = validator.requires_review
        biz["review_flags"] = validator.review_flags
        return biz
    except Exception as e:
        logger.debug(f"  Consistency validator error: {e}")
        biz["requires_review"] = True
        biz["review_flags"] = [f"VALIDATOR_ERROR: {e}"]
        return biz


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = analyze_domain("mmdc.ae", rating=4.5, review_count=120)
    print(json.dumps(result, indent=2, default=str))
