"""
#53 Random User-Agent
Change User-Agent per request to avoid fingerprinting.
"""

import random
from typing import Dict, List


USER_AGENTS = {
    "chrome_windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ],
    "chrome_mac": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ],
    "firefox_windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    ],
    "safari_mac": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ],
    "edge_windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ],
}


class UserAgentRotator:
    """Rotates User-Agent strings to avoid detection."""

    def __init__(self):
        self.all_ua = []
        for category, agents in USER_AGENTS.items():
            for ua in agents:
                self.all_ua.append({"user_agent": ua, "category": category})
        self.used_history: List[str] = []
        self.rotation_count = 0

    def get_random(self) -> str:
        """Get a random User-Agent."""
        entry = random.choice(self.all_ua)
        self.used_history.append(entry["user_agent"])
        self.rotation_count += 1
        return entry["user_agent"]

    def get_by_category(self, category: str) -> str:
        """Get a User-Agent from a specific category."""
        agents = USER_AGENTS.get(category, [])
        if not agents:
            return self.get_random()
        ua = random.choice(agents)
        self.used_history.append(ua)
        self.rotation_count += 1
        return ua

    def get_desktop_ua(self) -> str:
        """Get a desktop User-Agent."""
        categories = ["chrome_windows", "chrome_mac", "firefox_windows", "safari_mac", "edge_windows"]
        return self.get_by_category(random.choice(categories))

    def get_mobile_ua(self) -> str:
        """Get a mobile User-Agent."""
        mobile_uas = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        ]
        ua = random.choice(mobile_uas)
        self.used_history.append(ua)
        self.rotation_count += 1
        return ua

    def get_stats(self) -> Dict:
        """Get rotation statistics."""
        unique = len(set(self.used_history))
        return {
            "total_ua_pool": len(self.all_ua),
            "rotations": self.rotation_count,
            "unique_used": unique,
        }


if __name__ == "__main__":
    uar = UserAgentRotator()
    print(f"Pool size: {uar.get_stats()['total_ua_pool']}")
    for i in range(5):
        ua = uar.get_random()
        print(f"  {i + 1}. {ua[:80]}...")
    print(f"Stats: {uar.get_stats()}")
