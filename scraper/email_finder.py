"""
FindLeads — Email Finder
Discovers business emails from websites, crt.sh, PGP keyservers.
Inspired by MailAccess and theHarvester.
"""

import re
import json
import logging
from typing import Optional, List, Set
from urllib.parse import urljoin, urlparse

from curl_cffi import requests as cffi_requests

logger = logging.getLogger("email_finder")

# ════════════════════════════════════════════════════════════════
# EMAIL VALIDATION
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _create_session():
    return cffi_requests.Session(impersonate="chrome120")


# ════════════════════════════════════════════════════════════════
# EMAIL DISCOVERY
# ════════════════════════════════════════════════════════════════

def find_email_from_website(website_url: str) -> Optional[str]:
    """
    Find the best email from a business website.
    Returns the highest-confidence email found.
    """
    if not website_url:
        return None

    domain = _extract_domain(website_url)
    if not domain or domain in SKIP_DOMAINS:
        return None

    session = _create_session()
    all_emails: Set[str] = set()

    # Source 1: Website crawl (most important)
    try:
        website_emails = _crawl_website(session, website_url, domain)
        all_emails.update(website_emails)
        logger.info(f"  Website: found {len(website_emails)} emails")
    except Exception as e:
        logger.debug(f"  Website crawl error: {e}")

    # Source 2: Common paths
    try:
        path_emails = _check_common_paths(session, website_url, domain)
        all_emails.update(path_emails)
        logger.info(f"  Paths: found {len(path_emails)} emails")
    except Exception as e:
        logger.debug(f"  Common paths error: {e}")

    # Source 3: crt.sh (Certificate Transparency)
    try:
        ct_emails = _check_crt_sh(session, domain)
        all_emails.update(ct_emails)
        logger.info(f"  crt.sh: found {len(ct_emails)} emails")
    except Exception as e:
        logger.debug(f"  crt.sh error: {e}")

    # Source 4: PGP keyservers
    try:
        pgp_emails = _check_pgp_keyserver(session, domain)
        all_emails.update(pgp_emails)
        logger.info(f"  PGP: found {len(pgp_emails)} emails")
    except Exception as e:
        logger.debug(f"  PGP error: {e}")

    # Filter and rank
    filtered = _filter_emails(all_emails, domain)
    best = _rank_emails(filtered)

    if best:
        logger.info(f"  Best email: {best}")
    else:
        logger.info(f"  No email found for {domain}")

    return best


def find_all_emails(website_url: str) -> List[str]:
    """Find all emails from a business website (unranked)."""
    if not website_url:
        return []

    domain = _extract_domain(website_url)
    if not domain or domain in SKIP_DOMAINS:
        return []

    session = _create_session()
    all_emails: Set[str] = set()

    try:
        all_emails.update(_crawl_website(session, website_url, domain))
    except Exception:
        pass
    try:
        all_emails.update(_check_common_paths(session, website_url, domain))
    except Exception:
        pass
    try:
        all_emails.update(_check_crt_sh(session, domain))
    except Exception:
        pass
    try:
        all_emails.update(_check_pgp_keyserver(session, domain))
    except Exception:
        pass

    return sorted(_filter_emails(all_emails, domain))


# ════════════════════════════════════════════════════════════════
# SOURCE 1: WEBSITE CRAWL
# ════════════════════════════════════════════════════════════════

def _crawl_website(session, url: str, target_domain: str, max_pages: int = 3) -> Set[str]:
    """Crawl website pages looking for emails."""
    emails = set()
    visited = set()
    to_visit = [url]

    while to_visit and len(visited) < max_pages:
        page_url = to_visit.pop(0)
        if page_url in visited:
            continue
        visited.add(page_url)

        try:
            resp = session.get(page_url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue

            content = resp.text
            found = EMAIL_REGEX.findall(content)
            for email in found:
                email = email.lower().strip()
                email_domain = email.split("@")[1]
                if email_domain == target_domain:
                    emails.add(email)

            # Find links to crawl (same domain only)
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
# SOURCE 2: COMMON PATHS
# ════════════════════════════════════════════════════════════════

COMMON_PATHS = [
    "/contact", "/contact-us",
    "/about", "/about-us",
    "/.well-known/security.txt",
]

def _check_common_paths(session, base_url: str, target_domain: str) -> Set[str]:
    """Check common paths for emails."""
    emails = set()
    base = base_url.rstrip("/")

    for path in COMMON_PATHS:
        url = base + path
        try:
            resp = session.get(url, headers=HEADERS, timeout=8)
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
# SOURCE 3: CERTIFICATE TRANSPARENCY (crt.sh)
# ════════════════════════════════════════════════════════════════

def _check_crt_sh(session, domain: str) -> Set[str]:
    """Query crt.sh for certificate-registered emails."""
    emails = set()
    url = f"https://crt.sh/?q=%25.{domain}&output=json"

    try:
        resp = session.get(url, headers={"User-Agent": "FindLeads/1.0"}, timeout=8)
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
# SOURCE 4: PGP KEYSERVERS
# ════════════════════════════════════════════════════════════════

def _check_pgp_keyserver(session, domain: str) -> Set[str]:
    """Search PGP keyservers for emails matching domain."""
    emails = set()
    url = f"https://keys.openpgp.org/search?q={domain}"

    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            found = EMAIL_REGEX.findall(resp.text)
            for email in found:
                email = email.lower().strip()
                if email.split("@")[1] == domain:
                    emails.add(email)
    except Exception:
        pass

    return emails


# ════════════════════════════════════════════════════════════════
# FILTERING & RANKING
# ════════════════════════════════════════════════════════════════

def _filter_emails(emails: Set[str], target_domain: str) -> Set[str]:
    """Filter out disposable, role-based, and irrelevant emails."""
    filtered = set()
    for email in emails:
        parts = email.split("@")
        if len(parts) != 2:
            continue
        local, domain = parts
        # Must be on target domain
        if domain != target_domain:
            continue
        # Skip disposable
        if domain in DISPOSABLE_DOMAINS:
            continue
        # Skip role accounts (but keep them as fallback)
        if local.split("+")[0] in ROLE_PREFIXES:
            continue
        # Skip system emails
        if any(x in local for x in ["noreply", "no-reply", "donotreply", "mailer-daemon"]):
            continue
        filtered.add(email)
    return filtered


def _rank_emails(emails: Set[str]) -> Optional[str]:
    """Pick the best email from filtered set."""
    if not emails:
        return None

    # Priority order for common business patterns
    priority = [
        "contact", "info", "hello", "office", "admin",
        "sales", "team", "support", "help",
    ]

    email_list = list(emails)

    # First: look for priority keywords
    for keyword in priority:
        for email in email_list:
            local = email.split("+")[0].split("@")[0]
            if local == keyword:
                return email

    # Second: prefer shorter, simpler emails
    email_list.sort(key=lambda e: len(e.split("@")[0]))
    return email_list[0]


def _extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.split(":")[0]  # Remove port
        domain = domain.lstrip("www.")
        return domain.lower()
    except Exception:
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    email = find_email_from_website("https://www.mmdc.ae")
    print(f"Best email: {email}")
    all_emails = find_all_emails("https://www.mmdc.ae")
    print(f"All emails: {all_emails}")
