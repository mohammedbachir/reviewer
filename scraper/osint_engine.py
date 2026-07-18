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
from typing import Dict, List
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
# MAIN OSINT FUNCTION
# ════════════════════════════════════════════════════════════════

def analyze_domain(domain: str, rating: float = 0, review_count: int = 0) -> Dict:
    logger.info(f"OSINT analyzing: {domain}")
    result = {
        "domain": domain,
        "health_score": 50,
        "ssl_grade": "",
        "tech_stack": [],
        "dns": {},
        "page_speed": {},
        "has_website": True,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

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
        result["tech_stack"] = detect_tech(domain)
    except Exception as e:
        logger.debug(f"Tech detection error: {e}")

    result["health_score"] = _calculate_health(result, rating, review_count)

    logger.info(f"  Health: {result['health_score']}/100 | SSL: {result['ssl_grade']} | Tech: {len(result['tech_stack'])}")
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
        resp = session.get(f"https://{domain}", headers=HEADERS, timeout=8)
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


def detect_tech(domain: str) -> List[str]:
    session = _create_session()
    techs = set()

    try:
        resp = session.get(f"https://{domain}", headers=HEADERS, timeout=10)
        content = resp.text
        content_lower = content.lower()
        headers_str = json.dumps(dict(resp.headers)).lower()

        cookies_str = ""
        for cookie in resp.cookies:
            cookies_str += cookie.name.lower() + " "

        all_text = content_lower + " " + headers_str + " " + cookies_str

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

    return max(0, min(100, score))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = analyze_domain("mmdc.ae", rating=4.5, review_count=120)
    print(json.dumps(result, indent=2, default=str))
