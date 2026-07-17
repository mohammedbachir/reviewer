"""
Pipeline #5: Alert Engine
Detects critical changes and generates alerts.
Integrates: temporal.alerts, temporal.severity, temporal.decay
"""

import os
import sys
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import duckdb


class AlertEngine:
    """Detects critical business changes and generates alerts."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "data.duckdb")
        self.alerts: List[Dict] = []
        self.stats = {
            "total_alerts": 0,
            "critical": 0,
            "warning": 0,
            "info": 0,
        }

    def check_business(self, business: Dict) -> List[Dict]:
        """Check a business for alert conditions."""
        alerts = []

        # Alert: Rating drop
        rating = business.get("rating", 0)
        if rating > 0 and rating < 3.0:
            alerts.append({
                "level": "critical",
                "type": "low_rating",
                "business": business.get("name", "unknown"),
                "message": f"Rating critically low: {rating}/5",
                "timestamp": datetime.now().isoformat(),
            })

        # Alert: Many unanswered reviews
        unanswered = business.get("unanswered_reviews", 0)
        if unanswered >= 50:
            alerts.append({
                "level": "critical",
                "type": "review_fatigue",
                "business": business.get("name", "unknown"),
                "message": f"{unanswered} unanswered reviews — prime target",
                "timestamp": datetime.now().isoformat(),
            })
        elif unanswered >= 20:
            alerts.append({
                "level": "warning",
                "type": "review_fatigue",
                "business": business.get("name", "unknown"),
                "message": f"{unanswered} unanswered reviews",
                "timestamp": datetime.now().isoformat(),
            })

        # Alert: Low health score
        health = business.get("health_score", 50)
        if health < 30:
            alerts.append({
                "level": "critical",
                "type": "low_health",
                "business": business.get("name", "unknown"),
                "message": f"Health score critically low: {health}/100",
                "timestamp": datetime.now().isoformat(),
            })
        elif health < 50:
            alerts.append({
                "level": "warning",
                "type": "declining_health",
                "business": business.get("name", "unknown"),
                "message": f"Health score declining: {health}/100",
                "timestamp": datetime.now().isoformat(),
            })

        # Alert: No website (opportunity)
        if not business.get("website"):
            alerts.append({
                "level": "info",
                "type": "no_website",
                "business": business.get("name", "unknown"),
                "message": "No website — potential website service lead",
                "timestamp": datetime.now().isoformat(),
            })

        # Alert: High priority target
        if business.get("target_priority") == "high":
            alerts.append({
                "level": "info",
                "type": "high_priority",
                "business": business.get("name", "unknown"),
                "message": f"High priority target ({business.get('review_count', 0)} reviews, {business.get('unanswered_reviews', 0)} unanswered)",
                "timestamp": datetime.now().isoformat(),
            })

        self.alerts.extend(alerts)
        for a in alerts:
            self.stats[a["level"]] = self.stats.get(a["level"], 0) + 1
        self.stats["total_alerts"] = len(self.alerts)

        return alerts

    def check_batch(self, businesses: List[Dict]) -> List[Dict]:
        """Check multiple businesses for alerts."""
        all_alerts = []
        for biz in businesses:
            alerts = self.check_business(biz)
            all_alerts.extend(alerts)
        return all_alerts

    def get_alerts(self, level: str = None) -> List[Dict]:
        """Get alerts, optionally filtered by level."""
        if level:
            return [a for a in self.alerts if a["level"] == level]
        return self.alerts.copy()

    def get_critical_alerts(self) -> List[Dict]:
        """Get only critical alerts."""
        return self.get_alerts("critical")

    def get_stats(self) -> Dict:
        """Get alert statistics."""
        return self.stats.copy()

    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts = []
        self.stats = {"total_alerts": 0, "critical": 0, "warning": 0, "info": 0}


if __name__ == "__main__":
    engine = AlertEngine(":memory:")

    # Test with sample businesses
    test_businesses = [
        {"name": "Fresh Cuts", "rating": 2.1, "unanswered_reviews": 80, "health_score": 20, "target_priority": "high", "website": ""},
        {"name": "Bloom Beauty", "rating": 4.0, "unanswered_reviews": 25, "health_score": 45, "target_priority": "medium", "website": "https://bloom.com"},
        {"name": "Al Noor", "rating": 4.8, "unanswered_reviews": 5, "health_score": 92, "target_priority": "low", "website": "https://alnoor.com"},
    ]

    alerts = engine.check_batch(test_businesses)
    print(f"[Test] Generated {len(alerts)} alerts:")
    for a in alerts:
        print(f"  [{a['level'].upper()}] {a['business']}: {a['message']}")

    stats = engine.get_stats()
    print(f"\n[Test] Stats: {stats}")
