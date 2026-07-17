"""
#61 Website Screenshot
Screenshot business website using Playwright (for mockups).
"""

import os
from datetime import datetime
from typing import Dict


class WebsiteScreenshot:
    """Takes screenshots of business websites."""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "..", "screenshots")
        os.makedirs(self.output_dir, exist_ok=True)
        self.stats = {"total_screenshots": 0, "errors": 0}

    def take_screenshot(self, url: str, business_name: str = None, width: int = 1920, height: int = 1080) -> Dict:
        """Take a screenshot of a website."""
        import asyncio
        from playwright.async_api import async_playwright

        if business_name is None:
            business_name = url.replace("https://", "").replace("http://", "").replace("/", "_")[:50]

        filename = f"{business_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.output_dir, filename)

        async def _screenshot():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(viewport={"width": width, "height": height})
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=filepath, full_page=False)
                except Exception as e:
                    print(f"[Screenshot] Error: {e}")
                    await browser.close()
                    return None
                await browser.close()
            return filepath

        try:
            result = asyncio.run(_screenshot())
            if result:
                self.stats["total_screenshots"] += 1
                return {"status": "success", "filepath": filepath, "url": url}
        except Exception as e:
            self.stats["errors"] += 1
            return {"status": "error", "error": str(e)}

        return {"status": "error", "error": "unknown"}

    def get_stats(self) -> Dict:
        """Get screenshot statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    ss = WebsiteScreenshot()
    print(f"[Test] Output dir: {ss.output_dir}")
    print(f"[Test] Stats: {ss.get_stats()}")
    print("[Test] Ready to take screenshots")
