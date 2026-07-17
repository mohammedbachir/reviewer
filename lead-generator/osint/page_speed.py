"""
#62 Page Speed Analysis
Analyze website loading speed using Playwright performance metrics.
"""

import asyncio
import os
import urllib.request
import json
from datetime import datetime
from typing import Dict


class PageSpeedAnalyzer:
    """Analyzes website loading speed and performance."""

    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.stats = {"total_analyzed": 0, "errors": 0}

    def analyze(self, url: str) -> Dict:
        """Analyze page speed using Playwright."""
        async def _analyze():
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                try:
                    start_time = asyncio.get_event_loop().time()
                    response = await page.goto(url, wait_until="load", timeout=30000)
                    load_time = asyncio.get_event_loop().time() - start_time

                    # Get performance metrics
                    metrics = await page.evaluate("""() => {
                        const perf = performance;
                        const nav = perf.getEntriesByType('navigation')[0];
                        return {
                            domContentLoaded: nav ? nav.domContentLoadedEventEnd - nav.startTime : 0,
                            loadComplete: nav ? nav.loadEventEnd - nav.startTime : 0,
                            ttfb: nav ? nav.responseStart - nav.startTime : 0,
                            domInteractive: nav ? nav.domInteractive - nav.startTime : 0,
                            transferSize: nav ? nav.transferSize : 0,
                        };
                    }""")

                    status_code = response.status if response else 0

                    # Grade
                    if load_time < 2:
                        grade = "A"
                    elif load_time < 4:
                        grade = "B"
                    elif load_time < 7:
                        grade = "C"
                    else:
                        grade = "D"

                    result = {
                        "url": url,
                        "load_time_seconds": round(load_time, 2),
                        "status_code": status_code,
                        "grade": grade,
                        "dom_content_loaded": round(metrics.get("domContentLoaded", 0) / 1000, 2),
                        "ttfb": round(metrics.get("ttfb", 0) / 1000, 2),
                        "transfer_size_kb": round(metrics.get("transferSize", 0) / 1024, 1),
                        "timestamp": datetime.now().isoformat(),
                    }

                except Exception as e:
                    result = {"url": url, "error": str(e), "grade": "F"}
                finally:
                    await browser.close()

            return result

        try:
            result = asyncio.run(_analyze())
            self.results[url] = result
            if "error" not in result:
                self.stats["total_analyzed"] += 1
            else:
                self.stats["errors"] += 1
            return result
        except Exception as e:
            self.stats["errors"] += 1
            return {"url": url, "error": str(e), "grade": "F"}

    def get_stats(self) -> Dict:
        """Get analysis statistics."""
        return self.stats.copy()

    def get_slowest(self) -> list:
        """Get websites sorted by load time (slowest first)."""
        valid = [r for r in self.results.values() if "load_time_seconds" in r]
        return sorted(valid, key=lambda x: x["load_time_seconds"], reverse=True)


if __name__ == "__main__":
    analyzer = PageSpeedAnalyzer()
    print("[Test] PageSpeedAnalyzer initialized")
    print(f"[Test] Stats: {analyzer.get_stats()}")
