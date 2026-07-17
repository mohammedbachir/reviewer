"""
Pipeline #1: Auto Scraper
Automated Google Maps scraping with stealth capabilities.
Uses finder.py + stealth modules for undetectable scraping.
"""

import asyncio
import random
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from finder import _scrape_async
from stealth.delays import RandomDelays
from stealth.user_agent import UserAgentRotator
from stealth.headers import HeaderRotator


class AutoScraper:
    """Automated Google Maps scraper with stealth."""

    def __init__(self):
        self.delays = RandomDelays(min_delay=5, max_delay=15)
        self.ua_rotator = UserAgentRotator()
        self.header_rotator = HeaderRotator()
        self.results: List[Dict] = []
        self.stats = {
            "total_scraped": 0,
            "cities_scraped": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }

    def scrape_city(self, city: str, business_type: str, limit: int = 50) -> List[Dict]:
        """Scrape businesses from a single city."""
        print(f"[AutoScraper] Scraping {business_type} in {city} (limit: {limit})")
        self.stats["start_time"] = datetime.now().isoformat()

        try:
            businesses = _scrape_async(f"{business_type} in {city}", limit)
            self.results.extend(businesses)
            self.stats["total_scraped"] += len(businesses)
            self.stats["cities_scraped"] += 1
            print(f"[AutoScraper] Found {len(businesses)} businesses in {city}")
            return businesses
        except Exception as e:
            self.stats["errors"] += 1
            print(f"[AutoScraper] Error scraping {city}: {e}")
            return []

    def scrape_multi_city(self, cities: List[str], business_type: str, limit_per_city: int = 50) -> List[Dict]:
        """Scrape multiple cities with delays between each."""
        all_businesses = []
        for i, city in enumerate(cities):
            print(f"\n[AutoScraper] City {i + 1}/{len(cities)}: {city}")
            businesses = self.scrape_city(city, business_type, limit_per_city)
            all_businesses.extend(businesses)

            if i < len(cities) - 1:
                delay = self.delays.wait_sync()
                print(f"[AutoScraper] Waiting {delay:.1f}s before next city...")

        self.stats["end_time"] = datetime.now().isoformat()
        return all_businesses

    def get_stats(self) -> Dict:
        """Get scraping statistics."""
        return self.stats.copy()

    def get_results(self) -> List[Dict]:
        """Get all scraped results."""
        return self.results.copy()

    def clear_results(self):
        """Clear stored results."""
        self.results = []


if __name__ == "__main__":
    scraper = AutoScraper()
    print("[Test] AutoScraper initialized")
    print(f"[Test] UA pool: {scraper.ua_rotator.get_stats()['total_ua_pool']}")
    print(f"[Test] Delays: {scraper.delays.get_stats()['config']}")
    print("[Test] Ready for scraping")
