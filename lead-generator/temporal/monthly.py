"""
#24 Monthly Health Tracking
Tracks business health score over time (monthly averages).
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class MonthlyTracker:
    """Tracks business health scores on a monthly basis."""

    def __init__(self, db):
        self.db = db

    def record_monthly_health(self, business_id: str, health_data: Dict) -> Dict:
        """Record health data for the current month."""
        now = datetime.now()
        month_key = f"{now.year}-{now.month:02d}"

        existing = self.db.fetchone(
            "SELECT id FROM taxonomy WHERE country = ? AND city = ? AND sector = ?",
            (month_key, business_id, "health"),
        )

        props_json = json.dumps(health_data, ensure_ascii=False)

        if existing:
            self.db.execute(
                "UPDATE taxonomy SET avg_health_score = ? WHERE id = ?",
                (health_data.get("health_score", 0), existing["id"]),
            )
        else:
            self.db.execute(
                """INSERT INTO taxonomy (country, city, sector, avg_health_score, last_scan, business_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (month_key, business_id, "health", health_data.get("health_score", 0),
                 now.strftime("%Y-%m-%d"), 1),
            )

        return {"business_id": business_id, "month": month_key, "health_score": health_data.get("health_score", 0)}

    def get_health_history(self, business_id: str) -> List[Dict]:
        """Get all monthly health snapshots for a business."""
        snapshots = self.db.fetchall(
            """SELECT data, scan_date FROM snapshots WHERE node_id = ? ORDER BY scan_date ASC""",
            (business_id,),
        )

        monthly = {}
        for snap in snapshots:
            data = json.loads(snap.get("data", "{}"))
            scan_date = str(snap.get("scan_date", ""))
            if scan_date:
                month_key = scan_date[:7]
                health = data.get("health_score", 0)
                if health:
                    if month_key not in monthly:
                        monthly[month_key] = []
                    monthly[month_key].append(health)

        history = []
        for month, scores in sorted(monthly.items()):
            avg_score = sum(scores) / len(scores)
            history.append({
                "month": month,
                "avg_health_score": round(avg_score, 1),
                "scans": len(scores),
                "min_score": min(scores),
                "max_score": max(scores),
            })

        return history

    def get_monthly_comparison(self, business_id: str) -> Optional[Dict]:
        """Compare current month vs previous month."""
        history = self.get_health_history(business_id)
        if len(history) < 2:
            return None

        current = history[-1]
        previous = history[-2]
        diff = current["avg_health_score"] - previous["avg_health_score"]

        return {
            "business_id": business_id,
            "current_month": current["month"],
            "current_score": current["avg_health_score"],
            "previous_month": previous["month"],
            "previous_score": previous["avg_health_score"],
            "diff": round(diff, 1),
            "trend": "improving" if diff > 0 else "declining" if diff < 0 else "stable",
        }

    def get_sector_health(self, sector: str) -> Dict:
        """Get average health score for all businesses in a sector."""
        nodes = self.db.fetchall(
            """SELECT properties FROM nodes WHERE type = 'business'""",
        )

        sector_scores = []
        for node in nodes:
            props = json.loads(node.get("properties", "{}"))
            if props.get("sector", "").lower() == sector.lower():
                score = props.get("health_score", 0)
                if score:
                    sector_scores.append(score)

        if not sector_scores:
            return {"sector": sector, "avg_score": 0, "business_count": 0}

        return {
            "sector": sector,
            "avg_score": round(sum(sector_scores) / len(sector_scores), 1),
            "business_count": len(sector_scores),
            "min_score": min(sector_scores),
            "max_score": max(sector_scores),
        }

    def get_worst_performers(self, top_n: int = 10) -> List[Dict]:
        """Get businesses with lowest health scores."""
        nodes = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )

        businesses = []
        for node in nodes:
            props = json.loads(node.get("properties", "{}"))
            score = props.get("health_score", 0)
            if score:
                businesses.append({
                    "id": node["id"],
                    "name": node["name"],
                    "health_score": score,
                    "city": props.get("city", ""),
                    "sector": props.get("sector", ""),
                    "status": props.get("health_status", "unknown"),
                })

        businesses.sort(key=lambda x: x["health_score"])
        return businesses[:top_n]

    def get_best_performers(self, top_n: int = 10) -> List[Dict]:
        """Get businesses with highest health scores."""
        nodes = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )

        businesses = []
        for node in nodes:
            props = json.loads(node.get("properties", "{}"))
            score = props.get("health_score", 0)
            if score:
                businesses.append({
                    "id": node["id"],
                    "name": node["name"],
                    "health_score": score,
                    "city": props.get("city", ""),
                    "sector": props.get("sector", ""),
                    "status": props.get("health_status", "unknown"),
                })

        businesses.sort(key=lambda x: x["health_score"], reverse=True)
        return businesses[:top_n]


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        db.execute(
            "INSERT INTO nodes (id, type, name, properties) VALUES (?, ?, ?, ?)",
            ("biz1", "business", "Bloom", json.dumps({"sector": "beauty", "city": "Dubai", "health_score": 72})),
        )
        db.execute(
            "INSERT INTO nodes (id, type, name, properties) VALUES (?, ?, ?, ?)",
            ("biz2", "business", "Glow", json.dumps({"sector": "beauty", "city": "Abu Dhabi", "health_score": 45})),
        )
        db.execute(
            "INSERT INTO snapshots (node_id, scan_date, data) VALUES (?, ?, ?)",
            ("biz1", "2026-06-01", json.dumps({"health_score": 80})),
        )
        db.execute(
            "INSERT INTO snapshots (node_id, scan_date, data) VALUES (?, ?, ?)",
            ("biz1", "2026-07-01", json.dumps({"health_score": 72})),
        )

        mt = MonthlyTracker(db)
        history = mt.get_health_history("biz1")
        print(f"Bloom history: {history}")

        comparison = mt.get_monthly_comparison("biz1")
        print(f"Comparison: {comparison}")

        sector = mt.get_sector_health("beauty")
        print(f"Beauty sector: {sector}")

        worst = mt.get_worst_performers(3)
        print(f"Worst: {[w['name'] for w in worst]}")
