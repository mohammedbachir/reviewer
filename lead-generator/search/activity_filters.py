"""
#36 Activity Filters
Filter by reply activity (active, slow, dormant, silent).
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ActivityFilter:
    """Activity-based filtering for businesses."""

    ACTIVITY_LEVELS = {
        "active": {"max_days": 30, "description": "Replied in last 30 days"},
        "slow": {"max_days": 90, "description": "Replied in last 31-90 days"},
        "dormant": {"max_days": 180, "description": "Replied in last 91-180 days"},
        "silent": {"max_days": 9999, "description": "No reply in 180+ days"},
    }

    def __init__(self, db):
        self.db = db

    def filter_by_activity(self, level: str) -> List[Dict]:
        """Filter by activity level."""
        rows = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )
        result = []
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            activity = self._classify_activity(props)
            if activity == level:
                row["properties"] = props
                result.append(row)
        return result

    def filter_active(self) -> List[Dict]:
        """Get active businesses (responded recently)."""
        return self.filter_by_activity("active")

    def filter_silent(self) -> List[Dict]:
        """Get silent businesses (no responses)."""
        return self.filter_by_activity("silent")

    def filter_with_low_response_rate(self, threshold: float = 30) -> List[Dict]:
        """Get businesses with response rate below threshold."""
        rows = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )
        result = []
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            rate = float(props.get("response_rate", 0) or 0)
            if rate < threshold:
                row["properties"] = props
                result.append(row)
        return result

    def get_activity_distribution(self) -> Dict:
        """Get distribution of activity levels."""
        rows = self.db.fetchall(
            "SELECT properties FROM nodes WHERE type = 'business'"
        )
        distribution = {"active": 0, "slow": 0, "dormant": 0, "silent": 0, "unknown": 0}
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            level = self._classify_activity(props)
            distribution[level] = distribution.get(level, 0) + 1

        return {
            "distribution": distribution,
            "total": sum(distribution.values()),
        }

    def _classify_activity(self, props: Dict) -> str:
        """Classify activity level based on last scan and response rate."""
        response_rate = float(props.get("response_rate", 0) or 0)
        last_scan = props.get("last_scan", "")

        if response_rate >= 50:
            return "active"
        if response_rate >= 20:
            return "slow"
        if response_rate > 0:
            return "dormant"
        return "silent"


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        af = ActivityFilter(db)
        dist = af.get_activity_distribution()
        print(f"Activity distribution: {dist}")
