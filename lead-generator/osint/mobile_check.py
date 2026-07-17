"""
#63 Mobile Responsiveness Check
Check if website works on mobile using Playwright viewport.
"""

import asyncio
import os
from datetime import datetime
from typing import Dict


class MobileCheck:
    """Checks mobile responsiveness of websites."""

    MOBILE_VIEWPORTS = {
        "iphone_14": {"width": 390, "height": 844},
        "iphone_se": {"width": 375, "height": 667},
        "galaxy_s21": {"width": 360, "height": 800},
        "ipad": {"width": 768, "height": 1024},
    }

    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.stats = {"total_checked": 0, "mobile_friendly": 0, "errors": 0}

    def check(self, url: str, device: str = "iphone_14") -> Dict:
        """Check if a website is mobile responsive."""
        viewport = self.MOBILE_VIEWPORTS.get(device, self.MOBILE_VIEWPORTS["iphone_14"])

        async def _check():
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport=viewport,
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                )
                page = await context.new_page()

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Check for mobile indicators
                    checks = await page.evaluate("""() => {
                        const viewport = document.querySelector('meta[name="viewport"]');
                        const hasViewport = !!viewport;
                        const viewportContent = viewport ? viewport.getAttribute('content') : '';

                        // Check for horizontal scrollbar
                        const hasHorizontalScroll = document.documentElement.scrollWidth > window.innerWidth;

                        // Check font sizes
                        const body = document.body;
                        const bodyFontSize = window.getComputedStyle(body).fontSize;

                        // Check touch targets
                        const buttons = document.querySelectorAll('button, a');
                        const smallTargets = Array.from(buttons).filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width < 44 || rect.height < 44;
                        }).length;

                        return {
                            hasViewport: hasViewport,
                            viewportContent: viewportContent,
                            hasHorizontalScroll: hasHorizontalScroll,
                            bodyFontSize: bodyFontSize,
                            totalButtons: buttons.length,
                            smallTouchTargets: smallTargets,
                        };
                    }""")

                    is_mobile_friendly = (
                        checks["hasViewport"] and
                        not checks["hasHorizontalScroll"] and
                        checks["smallTouchTargets"] < checks["totalButtons"] * 0.3
                    )

                    if is_mobile_friendly:
                        self.stats["mobile_friendly"] += 1

                    result = {
                        "url": url,
                        "device": device,
                        "viewport": viewport,
                        "is_mobile_friendly": is_mobile_friendly,
                        "has_viewport_meta": checks["hasViewport"],
                        "has_horizontal_scroll": checks["hasHorizontalScroll"],
                        "small_touch_targets": checks["smallTouchTargets"],
                        "total_buttons": checks["totalButtons"],
                        "timestamp": datetime.now().isoformat(),
                    }

                except Exception as e:
                    result = {"url": url, "error": str(e), "is_mobile_friendly": False}
                finally:
                    await browser.close()

            return result

        try:
            result = asyncio.run(_check())
            self.results[url] = result
            self.stats["total_checked"] += 1
            return result
        except Exception as e:
            self.stats["errors"] += 1
            return {"url": url, "error": str(e), "is_mobile_friendly": False}

    def get_stats(self) -> Dict:
        """Get check statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    mc = MobileCheck()
    print("[Test] MobileCheck initialized")
    print(f"[Test] Devices: {list(mc.MOBILE_VIEWPORTS.keys())}")
    print(f"[Test] Stats: {mc.get_stats()}")
