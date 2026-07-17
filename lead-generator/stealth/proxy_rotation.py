"""
#55 Free Proxy Rotation
Rotate free IP per request using proxy lists.
"""

import json
import random
import urllib.request
from typing import Dict, List, Optional


class ProxyRotator:
    """Rotates free proxy servers."""

    FREE_PROXY_URLS = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
    ]

    def __init__(self):
        self.proxies: List[str] = []
        self.used_proxies: List[str] = []
        self.current_proxy: Optional[str] = None
        self.proxy_count = 0

    def fetch_proxies(self) -> List[str]:
        """Fetch free proxy list from online sources."""
        all_proxies = []
        for url in self.FREE_PROXY_URLS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                response = urllib.request.urlopen(req, timeout=10)
                data = response.read().decode("utf-8")
                proxies = [line.strip() for line in data.split("\n") if line.strip()]
                all_proxies.extend(proxies[:50])
            except Exception:
                continue

        self.proxies = list(set(all_proxies))
        random.shuffle(self.proxies)
        return self.proxies

    def get_next(self) -> Optional[str]:
        """Get the next proxy from the pool."""
        if not self.proxies:
            self.fetch_proxies()
        if not self.proxies:
            return None

        proxy = self.proxies.pop(0)
        self.used_proxies.append(proxy)
        self.current_proxy = proxy
        self.proxy_count += 1
        return proxy

    def get_random(self) -> Optional[str]:
        """Get a random proxy."""
        if not self.proxies:
            self.fetch_proxies()
        if not self.proxies:
            return None

        proxy = random.choice(self.proxies)
        self.used_proxies.append(proxy)
        self.current_proxy = proxy
        self.proxy_count += 1
        return proxy

    def mark_bad(self, proxy: str):
        """Mark a proxy as bad (remove from pool)."""
        if proxy in self.proxies:
            self.proxies.remove(proxy)

    def reset(self):
        """Reset proxy pool and fetch fresh proxies."""
        self.proxies = []
        self.used_proxies = []
        self.current_proxy = None
        self.fetch_proxies()

    def get_stats(self) -> Dict:
        """Get proxy rotation stats."""
        return {
            "pool_size": len(self.proxies),
            "used_count": len(self.used_proxies),
            "total_rotations": self.proxy_count,
            "current_proxy": self.current_proxy,
        }


if __name__ == "__main__":
    pr = ProxyRotator()
    print("Proxy rotator initialized")
    print(f"Stats: {pr.get_stats()}")
    print("Proxy fetching will work when run with network access")
