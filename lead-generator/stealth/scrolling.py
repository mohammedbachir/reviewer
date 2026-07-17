"""
#51 Random Scrolling
Slow scrolling like a human reading content.
"""

import asyncio
import random
from typing import Dict


class HumanScroller:
    """Simulates human scrolling behavior."""

    def __init__(self):
        self.scroll_count = 0
        self.total_scrolled = 0

    async def scroll_down(self, page, distance: int = 0, pauses: int = 0):
        """Scroll down like a human reading."""
        if distance == 0:
            distance = random.randint(100, 400)
        if pauses == 0:
            pauses = random.randint(2, 5)

        for _ in range(pauses):
            chunk = distance // pauses
            await page.mouse.wheel(0, chunk)
            self.scroll_count += 1
            self.total_scrolled += chunk
            await asyncio.sleep(random.uniform(0.5, 2.0))

    async def scroll_up(self, page, distance: int = 0):
        """Scroll up to re-read something."""
        if distance == 0:
            distance = random.randint(50, 200)
        await page.mouse.wheel(0, -distance)
        self.scroll_count += 1
        self.total_scrolled += distance
        await asyncio.sleep(random.uniform(0.3, 1.0))

    async def scroll_to_bottom(self, page, max_scrolls: int = 10):
        """Scroll to bottom of page gradually."""
        for _ in range(max_scrolls):
            distance = random.randint(200, 500)
            await self.scroll_down(page, distance=distance, pauses=random.randint(1, 3))

            at_bottom = await page.evaluate(
                "(window.innerHeight + window.scrollY) >= document.body.scrollHeight - 50"
            )
            if at_bottom:
                break

            await asyncio.sleep(random.uniform(1.0, 3.0))

    async def scroll_like_reading(self, page, scroll_count: int = 5):
        """Scroll slowly like reading content."""
        for i in range(scroll_count):
            distance = random.randint(100, 300)
            await self.scroll_down(page, distance=distance, pauses=random.randint(3, 6))
            await asyncio.sleep(random.uniform(2.0, 5.0))

            if random.random() < 0.2:
                await self.scroll_up(page, random.randint(50, 150))
                await asyncio.sleep(random.uniform(1.0, 2.0))

    def get_stats(self) -> Dict:
        """Get scrolling statistics."""
        return {
            "scroll_count": self.scroll_count,
            "total_scrolled_px": self.total_scrolled,
        }


if __name__ == "__main__":
    hs = HumanScroller()
    stats = hs.get_stats()
    print(f"Scroller stats: {stats}")
    print("Human scroller ready (needs async page for live test)")
