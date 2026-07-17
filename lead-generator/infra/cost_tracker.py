"""
#73 Cost Tracker
Track usage across all free tiers (GitHub minutes, Oracle CPU, Google requests).
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List


class CostTracker:
    """Tracks usage across all free tier platforms."""

    FREE_TIERS = {
        "github_actions": {
            "name": "GitHub Actions",
            "free_limit": 2000,
            "unit": "minutes/month",
            "cost_per_unit": 0,
        },
        "oracle_cloud": {
            "name": "Oracle Cloud Free Tier",
            "free_limit": float("inf"),
            "unit": "VM-hours/month",
            "cost_per_unit": 0,
            "note": "Always Free — no limit",
        },
        "google_cloud_run": {
            "name": "Google Cloud Run",
            "free_limit": 2000000,
            "unit": "requests/month",
            "cost_per_unit": 0,
        },
        "duckdb": {
            "name": "DuckDB",
            "free_limit": float("inf"),
            "unit": "queries",
            "cost_per_unit": 0,
            "note": "Open source — no limit",
        },
        "playwright": {
            "name": "Playwright",
            "free_limit": float("inf"),
            "unit": "browser sessions",
            "cost_per_unit": 0,
            "note": "Open source — no limit",
        },
    }

    def __init__(self, usage_path: str = None):
        self.usage_path = usage_path or os.path.join(os.path.dirname(__file__), "cost_usage.json")
        self.usage: Dict[str, List[Dict]] = {}
        self._load_usage()

    def _load_usage(self):
        """Load usage data from file."""
        if os.path.exists(self.usage_path):
            with open(self.usage_path, "r") as f:
                self.usage = json.load(f)

    def _save_usage(self):
        """Save usage data to file."""
        os.makedirs(os.path.dirname(self.usage_path) or ".", exist_ok=True)
        with open(self.usage_path, "w") as f:
            json.dump(self.usage, f, indent=2)

    def record_usage(self, platform: str, amount: float, details: str = ""):
        """Record usage for a platform."""
        if platform not in self.usage:
            self.usage[platform] = []

        entry = {
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "details": details,
        }
        self.usage[platform].append(entry)
        self._save_usage()

    def get_monthly_usage(self, month: str = None) -> Dict:
        """Get usage for a specific month (YYYY-MM format)."""
        if month is None:
            month = datetime.now().strftime("%Y-%m")

        monthly = {}
        for platform, entries in self.usage.items():
            month_entries = [e for e in entries if e["timestamp"][:7] == month]
            total = sum(e["amount"] for e in month_entries)
            monthly[platform] = {
                "total": total,
                "entries": len(month_entries),
            }
        return monthly

    def get_usage_vs_limit(self) -> List[Dict]:
        """Compare current usage against free tier limits."""
        current_month = datetime.now().strftime("%Y-%m")
        monthly = self.get_monthly_usage(current_month)

        results = []
        for platform_id, tier in self.FREE_TIERS.items():
            used = monthly.get(platform_id, {}).get("total", 0)
            limit = tier["free_limit"]

            if limit == float("inf"):
                usage_percent = 0
                status = "unlimited"
            else:
                usage_percent = round(used / limit * 100, 2) if limit > 0 else 0
                if usage_percent >= 90:
                    status = "critical"
                elif usage_percent >= 70:
                    status = "warning"
                else:
                    status = "ok"

            results.append({
                "platform": tier["name"],
                "used": used,
                "limit": limit if limit != float("inf") else "unlimited",
                "unit": tier["unit"],
                "usage_percent": usage_percent,
                "status": status,
                "cost": tier["cost_per_unit"] * used,
            })
        return results

    def get_total_cost(self, months: int = 1) -> Dict:
        """Calculate total cost for the given number of months."""
        total = 0
        breakdown = {}
        for platform_id, tier in self.FREE_TIERS.items():
            platform_cost = tier["cost_per_unit"] * months * 1000  # estimated 1000 units/month
            breakdown[tier["name"]] = platform_cost
            total += platform_cost

        return {
            "total_cost": total,
            "currency": "USD",
            "period_months": months,
            "breakdown": breakdown,
            "note": "All platforms are free — $0 total",
        }

    def get_efficiency_score(self) -> Dict:
        """Calculate how efficiently we're using free tiers."""
        current_month = datetime.now().strftime("%Y-%m")
        monthly = self.get_monthly_usage(current_month)

        scores = {}
        for platform_id, tier in self.FREE_TIERS.items():
            used = monthly.get(platform_id, {}).get("total", 0)
            limit = tier["free_limit"]

            if limit == float("inf"):
                score = 100
            elif limit > 0:
                score = min(100, round(used / limit * 100, 1))
            else:
                score = 0

            scores[tier["name"]] = {
                "efficiency_percent": score,
                "status": "maximized" if score >= 80 else "underused" if score < 30 else "optimal",
            }

        avg_score = sum(s["efficiency_percent"] for s in scores.values()) / len(scores) if scores else 0
        return {
            "platforms": scores,
            "overall_efficiency": round(avg_score, 1),
            "recommendation": self._get_recommendation(scores),
        }

    def _get_recommendation(self, scores: Dict) -> str:
        """Get recommendation based on usage scores."""
        underused = [name for name, s in scores.items() if s["status"] == "underused"]
        if underused:
            return f"Consider increasing usage on: {', '.join(underused)}"
        return "All platforms are being used optimally"

    def get_monthly_trend(self) -> List[Dict]:
        """Get usage trend for the last 6 months."""
        months = []
        for i in range(5, -1, -1):
            date = datetime.now() - timedelta(days=30 * i)
            month_str = date.strftime("%Y-%m")
            monthly = self.get_monthly_usage(month_str)
            total = sum(m.get("total", 0) for m in monthly.values())
            months.append({
                "month": month_str,
                "total_usage": total,
                "platforms": monthly,
            })
        return months

    def export_report(self, filepath: str) -> Dict:
        """Export usage report as JSON."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "current_month": datetime.now().strftime("%Y-%m"),
            "usage_vs_limit": self.get_usage_vs_limit(),
            "total_cost": self.get_total_cost(),
            "efficiency": self.get_efficiency_score(),
            "trend": self.get_monthly_trend(),
        }
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        return {"status": "exported", "filepath": filepath}


if __name__ == "__main__":
    test_usage_path = os.path.join(os.path.dirname(__file__), "test_cost.json")
    ct = CostTracker(test_usage_path)

    # Simulate usage
    ct.record_usage("github_actions", 15, "Scraping Dubai beauty salons")
    ct.record_usage("github_actions", 10, "Scraping Riyadh beauty salons")
    ct.record_usage("oracle_cloud", 1, "VM uptime")
    ct.record_usage("google_cloud_run", 500, "API requests")
    ct.record_usage("duckdb", 50, "Graph queries")
    ct.record_usage("playwright", 20, "Browser sessions")

    usage = ct.get_monthly_usage()
    print(f"Monthly usage: {usage}")

    vs_limit = ct.get_usage_vs_limit()
    print(f"\nUsage vs limits:")
    for item in vs_limit:
        print(f"  {item['platform']}: {item['used']} / {item['limit']} ({item['usage_percent']}%) [{item['status']}]")

    cost = ct.get_total_cost()
    print(f"\nTotal cost: ${cost['total_cost']}")

    efficiency = ct.get_efficiency_score()
    print(f"\nEfficiency: {efficiency['overall_efficiency']}%")
    print(f"Recommendation: {efficiency['recommendation']}")

    # Cleanup
    if os.path.exists(test_usage_path):
        os.remove(test_usage_path)
