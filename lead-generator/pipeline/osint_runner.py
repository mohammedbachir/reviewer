"""
Pipeline #2: OSINT Runner
Runs deep OSINT analysis on scraped businesses.
Integrates: tech_detector, whois, dns, sentiment, financial_health, hidden_emails, domain_history, ssl
"""

import sys
import os
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from osint.engine import DeepOSINTEngine


class OSINTRunner:
    """Runs deep OSINT on businesses found by the scraper."""

    def __init__(self):
        self.engine = DeepOSINTEngine()
        self.results: Dict[str, Dict] = {}
        self.stats = {
            "total_scanned": 0,
            "successful": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None,
        }

    def scan_business(self, business: Dict) -> Dict:
        """Run deep OSINT on a single business."""
        website = business.get("website", "")
        name = business.get("name", "unknown")

        if not website:
            return {"status": "no_website", "business": name}

        try:
            osint_result = self.engine.scan(website)
            self.results[name] = osint_result
            self.stats["successful"] += 1
            return {"status": "success", "business": name, "osint": osint_result}
        except Exception as e:
            self.stats["failed"] += 1
            return {"status": "error", "business": name, "error": str(e)}

    def scan_batch(self, businesses: List[Dict]) -> List[Dict]:
        """Run OSINT on a batch of businesses."""
        self.stats["start_time"] = datetime.now().isoformat()
        self.stats["total_scanned"] = len(businesses)
        results = []

        for i, biz in enumerate(businesses):
            print(f"[OSINTRunner] [{i + 1}/{len(businesses)}] Scanning: {biz.get('name', 'unknown')}")
            result = self.scan_business(biz)
            results.append(result)

        self.stats["end_time"] = datetime.now().isoformat()
        print(f"[OSINTRunner] Done: {self.stats['successful']} success, {self.stats['failed']} failed")
        return results

    def get_results(self) -> Dict:
        """Get all OSINT results."""
        return self.results.copy()

    def get_stats(self) -> Dict:
        """Get OSINT statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    runner = OSINTRunner()
    print("[Test] OSINTRunner initialized")
    print(f"[Test] Engine: {runner.engine}")
    print("[Test] Ready for OSINT scanning")
