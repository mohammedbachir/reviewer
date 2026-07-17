"""
#54 Random Headers
Change Accept-Language, Referer, etc. per request.
"""

import random
from typing import Dict, List


class HeaderRotator:
    """Rotates HTTP headers to avoid fingerprinting."""

    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "ar-AE,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        "en-US,en;q=0.9,ar;q=0.8",
        "en-CA,en;q=0.9,fr;q=0.8",
    ]

    REFERERS = [
        "https://www.google.com/",
        "https://www.google.ae/",
        "https://www.google.sa/",
        "https://www.bing.com/",
        "https://search.yahoo.com/",
    ]

    ACCEPT_HEADERS = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    ]

    def __init__(self):
        self.header_count = 0

    def get_random_headers(self) -> Dict:
        """Get a complete set of random headers."""
        self.header_count += 1
        return {
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Referer": random.choice(self.REFERERS),
            "Accept": random.choice(self.ACCEPT_HEADERS),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    def get_search_headers(self, query: str) -> Dict:
        """Get headers for a Google search request."""
        headers = self.get_random_headers()
        headers["Referer"] = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return headers

    def get_business_headers(self) -> Dict:
        """Get headers for a business page visit."""
        headers = self.get_random_headers()
        headers["Sec-Fetch-Site"] = "none"
        headers["Cache-Control"] = "no-cache"
        return headers

    def get_stats(self) -> Dict:
        """Get header rotation stats."""
        return {
            "header_rotations": self.header_count,
            "accept_languages": len(self.ACCEPT_LANGUAGES),
            "referers": len(self.REFERERS),
        }


if __name__ == "__main__":
    hr = HeaderRotator()
    for i in range(3):
        h = hr.get_random_headers()
        print(f"  {i + 1}. Accept-Language: {h['Accept-Language']}")
        print(f"     Referer: {h['Referer']}")
    print(f"Stats: {hr.get_stats()}")
