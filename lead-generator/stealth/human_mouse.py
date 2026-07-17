"""
#50 Human Mouse Movement
Natural random mouse movement simulation using Playwright.
"""

import asyncio
import random
import math
from typing import List, Tuple, Dict


class HumanMouse:
    """Simulates natural human mouse movements."""

    def __init__(self):
        self.move_history: List[Tuple[int, int]] = []

    async def move_to(self, page, x: int, y: int, steps: int = 0):
        """Move mouse to target with human-like bezier curve."""
        if steps == 0:
            steps = random.randint(10, 25)

        start_x = random.randint(100, 500)
        start_y = random.randint(100, 400)

        ctrl_x = (start_x + x) / 2 + random.randint(-100, 100)
        ctrl_y = (start_y + y) / 2 + random.randint(-100, 100)

        for i in range(steps + 1):
            t = i / steps
            px = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * x
            py = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * y

            px += random.uniform(-2, 2)
            py += random.uniform(-2, 2)

            await page.mouse.move(px, py)
            await asyncio.sleep(random.uniform(0.005, 0.025))

        self.move_history.append((x, y))

    async def random_explore(self, page, duration: float = 3.0):
        """Randomly move mouse around the page for a duration."""
        import time
        start = time.time()
        while time.time() - start < duration:
            x = random.randint(50, 1800)
            y = random.randint(50, 900)
            await self.move_to(page, x, y, steps=random.randint(5, 15))
            await asyncio.sleep(random.uniform(0.3, 1.5))

    async def hover_element(self, page, selector: str):
        """Hover over an element with natural movement."""
        try:
            element = await page.query_selector(selector)
            if element:
                box = await element.bounding_box()
                if box:
                    target_x = box["x"] + box["width"] / 2 + random.randint(-10, 10)
                    target_y = box["y"] + box["height"] / 2 + random.randint(-5, 5)
                    await self.move_to(page, int(target_x), int(target_y))
                    await asyncio.sleep(random.uniform(0.2, 0.8))
        except Exception:
            pass

    def get_movement_stats(self) -> Dict:
        """Get statistics about mouse movements."""
        if not self.move_history:
            return {"total_moves": 0}

        distances = []
        for i in range(1, len(self.move_history)):
            x1, y1 = self.move_history[i - 1]
            x2, y2 = self.move_history[i]
            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            distances.append(dist)

        return {
            "total_moves": len(self.move_history),
            "avg_distance": round(sum(distances) / len(distances), 1) if distances else 0,
            "max_distance": round(max(distances), 1) if distances else 0,
        }


if __name__ == "__main__":
    hm = HumanMouse()
    stats = hm.get_movement_stats()
    print(f"Mouse stats: {stats}")
    print("Human mouse movement ready (needs async page for live test)")
