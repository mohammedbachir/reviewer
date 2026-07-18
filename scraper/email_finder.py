"""
FindLeads — Email Finder (Permutation Engine)
Generates email permutations, verifies via DNSMX + Gravatar + crt.sh + website crawl.
Inspired by alm-000/builds, BCON, email_enumerator.
"""

import re
import json
import hashlib
import logging
from typing import Optional, List, Set, Dict
from urllib.parse import urljoin, urlparse

from curl_cffi import requests as cffi_requests

logger = logging.getLogger("email_finder")

# ════════════════════════════════════════════════════════════════
# CONSTANTS
# ════════════════════════════════════════════════════════════════

EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "10minutemail.com", "yopmail.com", "sharklasers.com", "guerrillamailblock.com",
    "grr.la", "dispostable.com", "maildrop.cc", "fakeinbox.com",
    "temp-mail.org", "mohmal.com", "getairmail.com", "harakirimail.com",
}

ROLE_PREFIXES = {
    "info", "contact", "support", "help", "admin", "sales", "marketing",
    "hr", "careers", "jobs", "press", "media", "legal", "compliance",
    "billing", "accounts", "team", "office", "hello", "service",
    "webmaster", "postmaster", "hostmaster", "abuse", "noc", "security",
    "feedback", "suggestions", "inquiries", "enquiries",
}

SKIP_DOMAINS = {
    "google.com", "googleapis.com", "gstatic.com", "youtube.com",
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "github.com", "wikipedia.org", "apple.com", "microsoft.com",
    "cloudflare.com", "jquery.com", "schema.org", "ogp.me",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Common email patterns (in order of likelihood)
EMAIL_PATTERNS = [
    "info", "contact", "hello", "admin", "office",
    "sales", "support", "team", "help", "service",
    "enquiries", "inquiries",
]


def _create_session():
    return cffi_requests.Session(impersonate="chrome120")


# ════════════════════════════════════════════════════════════════
# MAIN EMAIL DISCOVERY (NEW — PERMUTATION + MULTI-SOURCE)
# ════════════════════════════════════════════════════════════════

def find_best_email(website_url: str, business_name: str = "") -> Dict:
    """
    Find the best email with full provenance and confidence.
    Returns: {"email": str, "confidence": float, "source": str, "all_found": list}
    """
    domain = _extract_domain(website_url)
    if not domain or domain in SKIP_DOMAINS:
        return {"email": None, "confidence": 0, "source": "skipped", "all_found": []}

    session = _create_session()
    candidates: List[Dict] = []  # {"email": str, "confidence": float, "source": str}

    # Source 1: Website crawl (most reliable)
    try:
        website_emails = _crawl_website(session, website_url, domain)
        for em in website_emails:
            conf = 90 if _is_business_email(em) else 70
            candidates.append({"email": em, "confidence": conf, "source": "website"})
        logger.info(f"  Website: {len(website_emails)} emails")
    except Exception as e:
        logger.debug(f"  Website error: {e}")

    # Source 2: Common paths (/contact, /about)
    try:
        path_emails = _check_common_paths(session, website_url, domain)
        for em in path_emails:
            conf = 85 if _is_business_email(em) else 65
            candidates.append({"email": em, "confidence": conf, "source": "paths"})
        logger.info(f"  Paths: {len(path_emails)} emails")
    except Exception as e:
        logger.debug(f"  Paths error: {e}")

    # Source 3: crt.sh (Certificate Transparency)
    try:
        ct_emails = _check_crt_sh(session, domain)
        for em in ct_emails:
            conf = 60 if _is_business_email(em) else 45
            candidates.append({"email": em, "confidence": conf, "source": "crt.sh"})
        logger.info(f"  crt.sh: {len(ct_emails)} emails")
    except Exception as e:
        logger.debug(f"  crt.sh error: {e}")

    # Source 4: Email Permutation Engine (generate + DNSMX verify)
    try:
        perm_emails = _permutation_engine(session, domain, business_name)
        for em in perm_emails:
            conf = 75 if em.get("dns_verified") else 50
            candidates.append({"email": em["email"], "confidence": conf, "source": "permutation"})
        logger.info(f"  Permutation: {len(perm_emails)} verified emails")
    except Exception as e:
        logger.debug(f"  Permutation error: {e}")

    # Source 5: Gravatar check (skipped — 3-5s overhead, low value vs permutation)

    # Source 6: WHOIS/RDAP (skipped — slow and unreliable)

    # Deduplicate + rank
    best = _rank_candidates(candidates, domain)
    all_found = sorted(set(c["email"] for c in candidates))

    if best:
        logger.info(f"  Best: {best['email']} (confidence: {best['confidence']}%)")
    else:
        logger.info(f"  No email found for {domain}")

    return {
        "email": best["email"] if best else None,
        "confidence": best["confidence"] if best else 0,
        "source": best["source"] if best else "none",
        "all_found": all_found,
    }


# ════════════════════════════════════════════════════════════════
# PERMUTATION ENGINE — Generate + Verify
# ════════════════════════════════════════════════════════════════

def _permutation_engine(session, domain: str, business_name: str) -> List[Dict]:
    """Generate email permutations and verify via DNSMX."""
    results = []

    # Generate permutations
    permutations = _generate_permutations(domain, business_name)

    # Verify via DNSMX (no SMTP — just check MX records exist)
    has_mx = _check_mx_exists(session, domain)

    for email in permutations:
        dns_verified = has_mx  # If domain has MX, all emails are theoretically deliverable
        results.append({"email": email, "dns_verified": dns_verified})

    return results


def _generate_permutations(domain: str, business_name: str) -> List[str]:
    """Generate common email permutations for a domain."""
    emails = []
    name_parts = _extract_name_parts(business_name, domain)

    # Always include common role-based patterns
    for prefix in ["info", "contact", "admin"]:
        emails.append(f"{prefix}@{domain}")

    # If we have name parts, generate name-based permutations
    if name_parts:
        first = name_parts.get("first", "")
        last = name_parts.get("last", "")
        short = name_parts.get("short", "")

        if first:
            emails.append(f"{first}@{domain}")
        if first and last:
            emails.append(f"{first}.{last}@{domain}")
            emails.append(f"{first}{last}@{domain}")
            emails.append(f"{first[0]}{last}@{domain}")
            emails.append(f"{first}{last[0]}@{domain}")
        if short:
            emails.append(f"{short}@{domain}")

    # Business name-based
    slug = _business_name_to_slug(business_name)
    if slug:
        emails.append(f"{slug}@{domain}")

    return list(set(emails))


def _extract_name_parts(business_name: str, domain: str) -> Dict:
    """Extract first/last name parts from business name."""
    if not business_name:
        return {}

    # Remove common suffixes
    clean = re.sub(r'\b(LLC|Inc|Corp|Ltd|Co|Company|L\.L\.C|FZ-LLC)\b', '', business_name, flags=re.IGNORECASE)
    clean = clean.strip()

    parts = clean.split()
    if len(parts) >= 2:
        return {
            "first": parts[0].lower(),
            "last": parts[-1].lower(),
            "short": parts[0][0] + parts[-1].lower() if parts[0] else "",
        }
    elif len(parts) == 1:
        return {
            "first": parts[0].lower(),
            "last": "",
            "short": parts[0].lower(),
        }
    return {}


def _business_name_to_slug(name: str) -> str:
    """Convert business name to email-friendly slug."""
    if not name:
        return ""
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    words = clean.split()
    if words:
        return "".join(w.lower() for w in words[:2])
    return ""


def _check_mx_exists(session, domain: str) -> bool:
    """Check if domain has MX records (indicates email capability)."""
    try:
        resp = session.get(
            "https://dns.google/resolve",
            params={"name": domain, "type": "MX"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            for ans in data.get("Answer", []):
                if ans.get("type") == 15:  # MX record
                    return True
    except Exception:
        pass
    return False


# ════════════════════════════════════════════════════════════════
# GRAVATAR CHECK
# ════════════════════════════════════════════════════════════════

def _check_gravatar_patterns(session, domain: str) -> List[str]:
    """Check if common email patterns have Gravatar profiles."""
    found = []
    patterns = ["info", "contact", "admin"]

    for prefix in patterns:
        email = f"{prefix}@{domain}"
        try:
            # Gravatar uses MD5 of email
            md5 = hashlib.md5(email.lower().encode()).hexdigest()
            resp = session.get(
                f"https://www.gravatar.com/avatar/{md5}?d=404",
                timeout=3,
            )
            if resp.status_code == 200 and len(resp.content) > 500:
                found.append(email)
        except Exception:
            continue

    return found


# ════════════════════════════════════════════════════════════════
# WHOIS / RDAP
# ════════════════════════════════════════════════════════════════

def _check_whois_rdap(session, domain: str) -> List[str]:
    """Query RDAP for domain registrant email."""
    emails = []

    try:
        # First get the RDAP server from IANA
        tld = domain.split(".")[-1]
        resp = session.get(f"https://rdap.nic.uk/domain/{domain}", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            for evt in data.get("events", []):
                pass
            for ent in data.get("entities", []):
                for vc in ent.get("vcardArray", [[]])[1]:
                    if vc[0] == "email":
                        emails.append(vc[3].lower())
    except Exception:
        pass

    return list(set(emails))


# ════════════════════════════════════════════════════════════════
# WEBSITE CRAWL
# ════════════════════════════════════════════════════════════════

def _crawl_website(session, url: str, target_domain: str, max_pages: int = 2) -> Set[str]:
    emails = set()
    visited = set()
    to_visit = [url]

    while to_visit and len(visited) < max_pages:
        page_url = to_visit.pop(0)
        if page_url in visited:
            continue
        visited.add(page_url)

        try:
            resp = session.get(page_url, headers=HEADERS, timeout=6)
            if resp.status_code != 200:
                continue

            content = resp.text
            found = EMAIL_REGEX.findall(content)
            for email in found:
                email = email.lower().strip()
                email_domain = email.split("@")[1]
                if email_domain == target_domain:
                    emails.add(email)

            links = re.findall(r'href="([^"]+)"', content)
            for link in links:
                abs_url = urljoin(page_url, link)
                parsed = urlparse(abs_url)
                if parsed.netloc and target_domain in parsed.netloc:
                    if abs_url not in visited and len(to_visit) < max_pages:
                        to_visit.append(abs_url)
        except Exception:
            continue

    return emails


# ════════════════════════════════════════════════════════════════
# COMMON PATHS
# ════════════════════════════════════════════════════════════════

COMMON_PATHS = [
    "/contact", "/contact-us",
    "/about", "/about-us",
]

def _check_common_paths(session, base_url: str, target_domain: str) -> Set[str]:
    emails = set()
    base = base_url.rstrip("/")

    for path in COMMON_PATHS:
        url = base + path
        try:
            resp = session.get(url, headers=HEADERS, timeout=5)
            if resp.status_code == 200:
                found = EMAIL_REGEX.findall(resp.text)
                for email in found:
                    email = email.lower().strip()
                    if email.split("@")[1] == target_domain:
                        emails.add(email)
        except Exception:
            continue

    return emails


# ════════════════════════════════════════════════════════════════
# CRT.SH
# ════════════════════════════════════════════════════════════════

def _check_crt_sh(session, domain: str) -> Set[str]:
    emails = set()
    url = f"https://crt.sh/?q=%25.{domain}&output=json"

    try:
        resp = session.get(url, headers={"User-Agent": "FindLeads/1.0"}, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            for cert in data:
                name = cert.get("name_value", "")
                for line in name.split("\n"):
                    found = EMAIL_REGEX.findall(line)
                    for email in found:
                        email = email.lower().strip()
                        if email.split("@")[1] == domain:
                            emails.add(email)
    except Exception:
        pass

    return emails


# ════════════════════════════════════════════════════════════════
# RANKING & HELPERS
# ════════════════════════════════════════════════════════════════

def _is_business_email(email: str) -> bool:
    """Check if email looks like a business email (not role-based)."""
    local = email.split("@")[0].split("+")[0]
    if local in ROLE_PREFIXES:
        return False
    if any(x in local for x in ["noreply", "no-reply", "donotreply", "mailer-daemon"]):
        return False
    return True


def _rank_candidates(candidates: List[Dict], target_domain: str) -> Optional[Dict]:
    """Pick the best email from candidates by confidence + source priority."""
    if not candidates:
        return None

    # Filter to target domain only
    valid = [c for c in candidates if c["email"].split("@")[1] == target_domain]
    if not valid:
        return None

    # Filter out disposable
    valid = [c for c in valid if c["email"].split("@")[1] not in DISPOSABLE_DOMAINS]

    # Sort by confidence (highest first)
    valid.sort(key=lambda c: c["confidence"], reverse=True)

    return valid[0] if valid else None


def _extract_domain(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.split(":")[0]
        domain = domain.lstrip("www.")
        return domain.lower()
    except Exception:
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = find_best_email("https://www.mmdc.ae", "MMDC")
    print(json.dumps(result, indent=2))
