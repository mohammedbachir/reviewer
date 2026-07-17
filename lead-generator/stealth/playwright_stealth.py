"""
#49 Playwright Stealth
Configures Playwright to remove bot traces.
"""

import json
import os
from typing import Dict, Optional


STEALTH_JS = """
// Override navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// Override navigator.plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Override navigator.languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en', 'ar'],
});

// Override chrome runtime
window.chrome = { runtime: {} };

// Override permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);

// Override WebGL vendor and renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.apply(this, arguments);
};
"""


class StealthManager:
    """Manages Playwright stealth configurations."""

    def __init__(self):
        self.stealth_script = STEALTH_JS
        self.config = {
            "headless": True,
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
            "timezone_id": "Asia/Dubai",
            "color_scheme": "light",
            "has_touch": False,
            "is_mobile": False,
            "java_script_enabled": True,
            "bypass_csp": True,
            "ignore_https_errors": True,
        }

    def get_browser_args(self) -> list:
        """Get browser launch arguments for stealth."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080",
            "--start-maximized",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-web-security",
            "--allow-running-insecure-content",
        ]

    def get_context_options(self) -> Dict:
        """Get browser context options."""
        return {
            "viewport": self.config["viewport"],
            "user_agent": self._get_default_ua(),
            "locale": self.config["locale"],
            "timezone_id": self.config["timezone_id"],
            "color_scheme": self.config["color_scheme"],
            "has_touch": self.config["has_touch"],
            "is_mobile": self.config["is_mobile"],
            "java_script_enabled": self.config["java_script_enabled"],
            "bypass_csp": self.config["bypass_csp"],
            "ignore_https_errors": self.config["ignore_https_errors"],
        }

    async def apply_stealth(self, page):
        """Apply stealth scripts to a page."""
        await page.add_init_script(self.stealth_script)
        return page

    def get_stealth_report(self) -> Dict:
        """Generate stealth readiness report."""
        return {
            "stealth_script_lines": len(self.stealth_script.split("\n")),
            "browser_args": len(self.get_browser_args()),
            "config": self.config,
            "status": "ready",
        }

    def _get_default_ua(self) -> str:
        """Get a default user agent."""
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def save_config(self, filepath: str):
        """Save stealth config to file."""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.config, f, indent=2)

    def load_config(self, filepath: str):
        """Load stealth config from file."""
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                self.config.update(json.load(f))


if __name__ == "__main__":
    sm = StealthManager()
    report = sm.get_stealth_report()
    print(f"Stealth report: {report}")
    print(f"Browser args: {sm.get_browser_args()[:3]}...")
