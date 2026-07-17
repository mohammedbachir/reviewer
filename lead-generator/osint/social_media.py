"""
#64 Social Media Discovery
Find social media accounts from business website.
"""

import re
import os
from datetime import datetime
from typing import Dict, List


class SocialMediaDiscovery:
    """Discovers social media accounts from business websites."""

    SOCIAL_PATTERNS = {
        "facebook": [
            r'facebook\.com/([a-zA-Z0-9_.]+)',
            r'fb\.com/([a-zA-Z0-9_.]+)',
        ],
        "instagram": [
            r'instagram\.com/([a-zA-Z0-9_.]+)',
        ],
        "twitter": [
            r'twitter\.com/([a-zA-Z0-9_]+)',
            r'x\.com/([a-zA-Z0-9_]+)',
        ],
        "linkedin": [
            r'linkedin\.com/company/([a-zA-Z0-9_-]+)',
            r'linkedin\.com/in/([a-zA-Z0-9_-]+)',
        ],
        "youtube": [
            r'youtube\.com/@([a-zA-Z0-9_-]+)',
            r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        ],
        "tiktok": [
            r'tiktok\.com/@([a-zA-Z0-9_.]+)',
        ],
        "snapchat": [
            r'snapchat\.com/add/([a-zA-Z0-9_.]+)',
        ],
        "whatsapp": [
            r'wa\.me/([0-9]+)',
            r'whatsapp\.com/send\?phone=([0-9]+)',
        ],
    }

    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.stats = {"total_scanned": 0, "found": 0, "errors": 0}

    def discover(self, url: str) -> Dict:
        """Discover social media accounts from a website."""
        import requests
        from bs4 import BeautifulSoup

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers, timeout=15)
            html = response.text

            # Also check common social pages
            social_pages = ["/contact", "/about", "/links"]
            full_text = html
            for page in social_pages:
                try:
                    page_url = url.rstrip("/") + page
                    page_resp = requests.get(page_url, headers=headers, timeout=10)
                    full_text += page_resp.text
                except Exception:
                    pass

            accounts = {}
            for platform, patterns in self.SOCIAL_PATTERNS.items():
                for pattern in patterns:
                    matches = re.findall(pattern, full_text, re.IGNORECASE)
                    if matches:
                        accounts[platform] = list(set(matches))

            # Also check for social icons/links
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                for platform, patterns in self.SOCIAL_PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, href, re.IGNORECASE):
                            match = re.search(pattern, href, re.IGNORECASE)
                            if match and platform not in accounts:
                                accounts[platform] = [match.group(1)]

            result = {
                "url": url,
                "accounts": accounts,
                "platforms_found": list(accounts.keys()),
                "total_platforms": len(accounts),
                "timestamp": datetime.now().isoformat(),
            }

            self.results[url] = result
            self.stats["total_scanned"] += 1
            if accounts:
                self.stats["found"] += 1
            return result

        except Exception as e:
            self.stats["errors"] += 1
            return {"url": url, "error": str(e), "accounts": {}}

    def get_stats(self) -> Dict:
        """Get discovery statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    smd = SocialMediaDiscovery()
    print("[Test] SocialMediaDiscovery initialized")
    print(f"[Test] Platforms: {list(smd.SOCIAL_PATTERNS.keys())}")
    print(f"[Test] Stats: {smd.get_stats()}")
