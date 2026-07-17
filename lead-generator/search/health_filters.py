"""
#35 Health Filters
Filter by health score (healthy, moderate, critical, dead).
"""

import json
from typing import Dict, List, Optional


class HealthFilter:
    """Health score-based filtering for businesses."""

    HEALTH_RANGES = {
        "healthy": (70, 100),
        "moderate": (40, 69),
        "critical": (20, 39),
        "dead": (0, 19),
    }

    def __init__(self, db):
        self.db = db

    def filter_by_status(self, status: str) -> List[Dict]:
        """Filter by health status."""
        min_h, max_h = self.HEALTH_RANGES.get(status, (0, 100))
        return self.filter_by_range(min_h, max_h)

    def filter_by_range(self, min_health: float, max_health: float) -> List[Dict]:
        """Filter by health score range."""
        rows = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )
        result = []
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            score = float(props.get("health_score", 0) or 0)
            if min_health <= score <= max_health:
                row["properties"] = props
                result.append(row)
        return result

    def filter_healthy(self) -> List[Dict]:
        """Get healthy businesses (health >= 70)."""
        return self.filter_by_status("healthy")

    def filter_declining(self) -> List[Dict]:
        """Get declining businesses (health 20-69)."""
        return self.filter_by_range(20, 69)

    def filter_critical(self) -> List[Dict]:
        """Get critical businesses (health < 40)."""
        return self.filter_by_range(0, 39)

    def get_health_distribution(self) -> Dict:
        """Get distribution of health scores."""
        rows = self.db.fetchall(
            "SELECT properties FROM nodes WHERE type = 'business'"
        )
        distribution = {"healthy": 0, "moderate": 0, "critical": 0, "dead": 0}
        scores = []
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            score = float(props.get("health_score", 0) or 0)
            if score:
                scores.append(score)
                if score >= 70:
                    distribution["healthy"] += 1
                elif score >= 40:
                    distribution["moderate"] += 1
                elif score >= 20:
                    distribution["critical"] += 1
                else:
                    distribution["dead"] += 1

        return {
            "distribution": distribution,
            "total": len(scores),
            "avg": round(sum(scores) / len(scores), 1) if scores else 0,
            "min": min(scores) if scores else 0,
            "max": max(scores) if scores else 0,
        }


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        hf = HealthFilter(db)
        dist = hf.get_health_distribution()
        print(f"Health distribution: {dist}")
