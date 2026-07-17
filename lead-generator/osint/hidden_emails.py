"""
#11 Hidden Emails Discovery
Searches for hidden emails in website files: CSS, JS, PDFs, sitemap, robots.txt.
"""

import re
import requests
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
}

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

JUNK_PATTERNS = [
    "sentry.io", "example.com", "test.com", "noreply", "no-reply",
    "wixpress.com", "sentry-next.wixpress.com", "sentry.io",
    "schema.org", "w3.org", "googleusercontent.com", "gstatic.com",
    "wordpress.org", "wordpress.com", "gravatar.com",
    "facebook.com", "twitter.com", "instagram.com",
    "protection@cloudflare", "abuse@",
]


def find_hidden_emails(url: str, max_pages: int = 10, timeout: int = 10) -> Dict:
    """
    Search for hidden emails across a website.
    
    Returns:
        Dict with found emails and their sources
    """
    result = {
        "url": url,
        "emails": [],
        "emails_by_source": {},
        "total_found": 0,
        "valid_emails": [],
    }

    if not url.startswith("http"):
        url = "https://" + url

    session = requests.Session()
    session.headers.update(HEADERS)

    found_emails: Set[str] = set()
    sources_checked: List[str] = []

    pages_to_check = _get_pages_to_check(url)

    for page_url in pages_to_check[:max_pages]:
        try:
            response = session.get(page_url, timeout=timeout, allow_redirects=True)
            if response.status_code != 200:
                continue

            sources_checked.append(page_url)
            emails = EMAIL_REGEX.findall(response.text)
            cleaned = _clean_emails(emails)

            for email in cleaned:
                if email not in found_emails:
                    found_emails.add(email)
                    source = _identify_source(page_url)
                    if source not in result["emails_by_source"]:
                        result["emails_by_source"][source] = []
                    result["emails_by_source"][source].append(email)

        except Exception:
            continue

    try:
        robots_url = url.rstrip("/") + "/robots.txt"
        response = session.get(robots_url, timeout=timeout)
        if response.status_code == 200:
            emails = EMAIL_REGEX.findall(response.text)
            cleaned = _clean_emails(emails)
            for email in cleaned:
                if email not in found_emails:
                    found_emails.add(email)
                    if "robots.txt" not in result["emails_by_source"]:
                        result["emails_by_source"]["robots.txt"] = []
                    result["emails_by_source"]["robots.txt"].append(email)
    except Exception:
        pass

    try:
        sitemap_url = url.rstrip("/") + "/sitemap.xml"
        response = session.get(sitemap_url, timeout=timeout)
        if response.status_code == 200:
            emails = EMAIL_REGEX.findall(response.text)
            cleaned = _clean_emails(emails)
            for email in cleaned:
                if email not in found_emails:
                    found_emails.add(email)
                    if "sitemap.xml" not in result["emails_by_source"]:
                        result["emails_by_source"]["sitemap.xml"] = []
                    result["emails_by_source"]["sitemap.xml"].append(email)
    except Exception:
        pass

    result["emails"] = list(found_emails)
    result["total_found"] = len(found_emails)
    result["valid_emails"] = [e for e in found_emails if _is_valid_email(e)]

    return result


def _get_pages_to_check(url: str) -> List[str]:
    """Generate list of pages to check for hidden emails."""
    pages = [
        url,
        url.rstrip("/") + "/about",
        url.rstrip("/") + "/about-us",
        url.rstrip("/") + "/contact",
        url.rstrip("/") + "/contact-us",
        url.rstrip("/") + "/team",
        url.rstrip("/") + "/our-team",
        url.rstrip("/") + "/staff",
    ]

    css_js_pages = [
        url.rstrip("/") + "/style.css",
        url.rstrip("/") + "/styles.css",
        url.rstrip("/") + "/main.css",
        url.rstrip("/") + "/app.js",
        url.rstrip("/") + "/main.js",
    ]

    return pages + css_js_pages


def _clean_emails(emails: List[str]) -> List[str]:
    """Clean and filter emails."""
    cleaned = set()
    for email in emails:
        email = email.lower().strip().rstrip(".")
        if len(email) > 50 or len(email) < 5:
            continue
        if not re.match(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", email):
            continue
        is_junk = any(pattern in email for pattern in JUNK_PATTERNS)
        if not is_junk:
            cleaned.add(email)
    return list(cleaned)


def _identify_source(url: str) -> str:
    """Identify the source type from URL."""
    path = urlparse(url).path
    if "robots.txt" in path:
        return "robots.txt"
    if "sitemap" in path:
        return "sitemap.xml"
    if ".css" in path:
        return "CSS files"
    if ".js" in path:
        return "JS files"
    if any(x in path for x in ["/about", "/team", "/staff"]):
        return "Team/About pages"
    if any(x in path for x in ["/contact"]):
        return "Contact pages"
    return "Main pages"


def _is_valid_email(email: str) -> bool:
    """Basic email validation."""
    if not re.match(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", email):
        return False
    domain = email.split("@")[1]
    if domain in ["example.com", "test.com", "localhost"]:
        return False
    return True


if __name__ == "__main__":
    test_urls = ["mmdc.ae", "bloombeautystudio.ae"]
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Hidden Emails: {url}")
        print("=" * 60)
        result = find_hidden_emails(url)
        print(f"  Total found: {result['total_found']}")
        print(f"  Valid emails: {result['valid_emails']}")
        print(f"  By source: {result['emails_by_source']}")
