"""
#6 Tech Stack Detection
Detects technologies used by a website: CMS, frameworks, CDNs, analytics, hosting.
Uses HTTP headers, meta tags, script sources, and HTML patterns.
"""

import re
import requests
from typing import Dict, List, Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TECH_SIGNATURES = {
    "WordPress": {
        "headers": ["x-powered-by:.*wordpress"],
        "html": ["wp-content/", "wp-includes/", 'name="generator" content="WordPress'],
        "cookies": ["wordpress_"],
    },
    "Shopify": {
        "headers": ["x-shopify-stage"],
        "html": ["cdn.shopify.com", "Shopify.theme", "shopify-section"],
        "cookies": ["_shopify_"],
    },
    "WooCommerce": {
        "html": ["woocommerce", "wc-", "wp-content/plugins/woocommerce"],
    },
    "Squarespace": {
        "html": ["squarespace.com", "sqsp-console", "static.squarespace.com"],
    },
    "Wix": {
        "html": ["wix.com", "wixstatic.com", "wix-html.com"],
    },
    "Webflow": {
        "html": ["webflow.com", "wf-cdn", "wf-cdn2"],
    },
    "React": {
        "html": ["react", "reactroot", "__NEXT_DATA__", "_reactRoot"],
        "scripts": ["react\\.min\\.js", "react-dom"],
    },
    "Next.js": {
        "html": ["__NEXT_DATA__", "_next/static"],
        "scripts": ["_next/"],
    },
    "Vue.js": {
        "html": ["vue\\.js", "vue\\.min\\.js", "data-v-"],
        "scripts": ["vue\\.min\\.js", "vue\\.runtime"],
    },
    "Angular": {
        "html": ["ng-version", "ng-app", "angular\\.js", "angular\\.min\\.js"],
    },
    "Bootstrap": {
        "html": ["bootstrap\\.min\\.css", "bootstrap\\.min\\.js", "bootstrap/"],
    },
    "Tailwind CSS": {
        "html": ["tailwindcss", "tailwind\\.min\\.css"],
    },
    "jQuery": {
        "scripts": ["jquery\\.min\\.js", "jquery-[0-9]", "jquery\\.js"],
    },
    "Google Analytics": {
        "html": ["google-analytics.com/analytics", "gtag(", "googletagmanager.com"],
    },
    "Google Tag Manager": {
        "html": ["googletagmanager.com/gtm.js", "gtm.js"],
    },
    "Facebook Pixel": {
        "html": ["connect.facebook.net", "fbq(", "facebook.com/tr"],
    },
    "Cloudflare": {
        "headers": ["cf-ray", "cf-cache-status", "server:.*cloudflare"],
    },
    "Nginx": {
        "headers": ["server:.*nginx"],
    },
    "Apache": {
        "headers": ["server:.*apache"],
    },
    "LiteSpeed": {
        "headers": ["server:.*litespeed"],
    },
    "IIS": {
        "headers": ["server:.*microsoft-iis", "x-powered-by:.*asp\\.net"],
    },
    "PHP": {
        "headers": ["x-powered-by:.*php"],
    },
    "ASP.NET": {
        "headers": ["x-powered-by:.*asp\\.net", "x-aspnet-version"],
    },
    "Mailchimp": {
        "html": ["mailchimp", "list-manage.com", "mc\\.us"],
    },
    "HubSpot": {
        "html": ["hubspot.com", "hs-script", "hs-"],
    },
    "Stripe": {
        "html": ["stripe\\.com", "Stripe("],
    },
    "PayPal": {
        "html": ["paypal\\.com", "paypalobjects\\.com"],
    },
}


def detect_tech_stack(url: str, timeout: int = 15) -> Dict:
    """
    Detect technologies used by a website.
    
    Returns:
        Dict with detected technologies organized by category
    """
    result = {
        "url": url,
        "cms": [],
        "frameworks": [],
        "analytics": [],
        "hosting": [],
        "payment": [],
        "marketing": [],
        "languages": [],
        "ssl": False,
        "mobile_friendly": False,
        "response_time_ms": 0,
        "status_code": 0,
        "detected": [],
    }

    if not url.startswith("http"):
        url = "https://" + url

    try:
        import time
        start = time.time()
        response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        elapsed_ms = int((time.time() - start) * 1000)

        result["response_time_ms"] = elapsed_ms
        result["status_code"] = response.status_code
        result["ssl"] = url.startswith("https://")

        html = response.text.lower()
        headers_str = str(response.headers).lower()

        for tech_name, signatures in TECH_SIGNATURES.items():
            detected = False

            for header_pattern in signatures.get("headers", []):
                if re.search(header_pattern, headers_str):
                    detected = True
                    break

            if not detected:
                for html_pattern in signatures.get("html", []):
                    if re.search(html_pattern, html):
                        detected = True
                        break

            if not detected:
                for script_pattern in signatures.get("scripts", []):
                    if re.search(script_pattern, html):
                        detected = True
                        break

            if not detected:
                for cookie_pattern in signatures.get("cookies", []):
                    for cookie_name in response.cookies:
                        if cookie_pattern in cookie_name.lower():
                            detected = True
                            break
                    if detected:
                        break

            if detected:
                result["detected"].append(tech_name)
                category = _categorize_tech(tech_name)
                if category:
                    result[category].append(tech_name)

        viewport_pattern = r'<meta[^>]*name=["\']viewport["\']'
        if re.search(viewport_pattern, html):
            result["mobile_friendly"] = True

        lang_patterns = {
            "PHP": ["<\\?php", "x-powered-by.*php"],
            "Python": ["wsgi", "django", "flask"],
            "Ruby": ["ruby", "rack", "passenger"],
            "Node.js": ["x-powered-by.*express", "x-powered-by.*node"],
        }
        for lang, patterns in lang_patterns.items():
            for pattern in patterns:
                if re.search(pattern, headers_str + html):
                    if lang not in result["languages"]:
                        result["languages"].append(lang)
                    break

    except requests.exceptions.SSLError:
        result["ssl"] = False
    except requests.exceptions.ConnectionError:
        result["status_code"] = -1
    except requests.exceptions.Timeout:
        result["status_code"] = -2
    except Exception:
        result["status_code"] = -3

    return result


def _categorize_tech(tech_name: str) -> Optional[str]:
    """Categorize a technology into a category."""
    categories = {
        "cms": ["WordPress", "Shopify", "Squarespace", "Wix", "Webflow"],
        "frameworks": ["React", "Next.js", "Vue.js", "Angular", "Bootstrap", "Tailwind CSS", "jQuery"],
        "analytics": ["Google Analytics", "Google Tag Manager", "Facebook Pixel"],
        "hosting": ["Cloudflare", "Nginx", "Apache", "LiteSpeed", "IIS"],
        "payment": ["Stripe", "PayPal"],
        "marketing": ["Mailchimp", "HubSpot"],
    }
    for category, techs in categories.items():
        if tech_name in techs:
            return category
    return None


if __name__ == "__main__":
    test_urls = [
        "https://bloombeautystudio.ae",
        "https://mmdc.ae",
    ]
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Tech Stack: {url}")
        print("=" * 60)
        result = detect_tech_stack(url)
        print(f"  Status: {result['status_code']}")
        print(f"  SSL: {result['ssl']}")
        print(f"  Mobile: {result['mobile_friendly']}")
        print(f"  Response: {result['response_time_ms']}ms")
        print(f"  Detected: {result['detected']}")
        print(f"  CMS: {result['cms']}")
        print(f"  Frameworks: {result['frameworks']}")
        print(f"  Analytics: {result['analytics']}")
        print(f"  Hosting: {result['hosting']}")
