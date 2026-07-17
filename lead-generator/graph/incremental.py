"""
#19 Incremental Updates
Tracks changes between scans and maintains data freshness.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class IncrementalUpdater:
    """Tracks changes between scans and maintains data freshness."""

    def __init__(self, db):
        self.db = db
        from nodes import NodeManager
        self.nodes = NodeManager(db)

    def create_snapshot(self, business_id: str, data: Dict) -> Dict:
        """Create a snapshot of business data at a point in time."""
        scan_date = datetime.now().date().isoformat()
        data_json = json.dumps(data, ensure_ascii=False)

        self.db.execute(
            "INSERT INTO snapshots (node_id, scan_date, data) VALUES (?, ?, ?)",
            (business_id, scan_date, data_json),
        )

        return {"business_id": business_id, "scan_date": scan_date, "status": "saved"}

    def detect_changes(self, business_id: str, new_data: Dict) -> List[Dict]:
        """Compare new scan data with the last snapshot and detect changes."""
        last_snapshot = self.db.fetchone(
            "SELECT * FROM snapshots WHERE node_id = ? ORDER BY scan_date DESC LIMIT 1",
            (business_id,),
        )

        if not last_snapshot:
            return [{"type": "first_scan", "severity": "info", "message": "First scan - no previous data"}]

        old_data = json.loads(last_snapshot.get("data", "{}"))
        changes = []

        if old_data.get("rating") and new_data.get("rating"):
            old_r = float(old_data["rating"])
            new_r = float(new_data["rating"])
            diff = new_r - old_r
            if abs(diff) >= 0.1:
                severity = "high" if abs(diff) >= 0.5 else "medium"
                changes.append({
                    "type": "rating_change",
                    "old_value": str(old_r),
                    "new_value": str(new_r),
                    "diff": str(round(diff, 2)),
                    "severity": severity,
                })

        old_health = old_data.get("health_score", 0)
        new_health = new_data.get("health_score", 0)
        if old_health and new_health:
            diff = new_health - old_health
            if abs(diff) >= 5:
                severity = "high" if abs(diff) >= 15 else "medium"
                changes.append({
                    "type": "health_change",
                    "old_value": str(old_health),
                    "new_value": str(new_health),
                    "diff": str(diff),
                    "severity": severity,
                })

        old_techs = set(old_data.get("technologies", []))
        new_techs = set(new_data.get("technologies", []))
        added_techs = new_techs - old_techs
        removed_techs = old_techs - new_techs

        if added_techs:
            changes.append({
                "type": "tech_added",
                "old_value": "",
                "new_value": ", ".join(added_techs),
                "severity": "low",
            })

        if removed_techs:
            changes.append({
                "type": "tech_removed",
                "old_value": ", ".join(removed_techs),
                "new_value": "",
                "severity": "medium",
            })

        old_sentiment = old_data.get("sentiment_avg", 0)
        new_sentiment = new_data.get("sentiment_avg", 0)
        if old_sentiment and new_sentiment:
            diff = new_sentiment - old_sentiment
            if abs(diff) >= 0.2:
                changes.append({
                    "type": "sentiment_change",
                    "old_value": str(round(old_sentiment, 2)),
                    "new_value": str(round(new_sentiment, 2)),
                    "diff": str(round(diff, 2)),
                    "severity": "medium",
                })

        return changes if changes else [{"type": "no_change", "severity": "info", "message": "No significant changes detected"}]

    def record_changes(self, business_id: str, scan_date: str, changes: List[Dict]):
        """Record detected changes in the changes table."""
        for change in changes:
            if change.get("type") == "no_change":
                continue
            self.db.execute(
                "INSERT INTO changes (node_id, scan_date, change_type, old_value, new_value, severity) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    business_id,
                    scan_date,
                    change.get("type", ""),
                    change.get("old_value", ""),
                    change.get("new_value", ""),
                    change.get("severity", "low"),
                ),
            )

    def get_all_changes(self, business_id: Optional[str] = None, days: int = 30) -> List[Dict]:
        """Get recent changes for a business or all businesses."""
        since = (datetime.now() - timedelta(days=days)).date().isoformat()

        if business_id:
            return self.db.fetchall(
                "SELECT * FROM changes WHERE node_id = ? AND scan_date >= ? ORDER BY scan_date DESC",
                (business_id, since),
            )

        return self.db.fetchall(
            "SELECT * FROM changes WHERE scan_date >= ? ORDER BY scan_date DESC",
            (since,),
        )

    def get_snapshots(self, business_id: str) -> List[Dict]:
        """Get all snapshots for a business."""
        rows = self.db.fetchall(
            "SELECT * FROM snapshots WHERE node_id = ? ORDER BY scan_date DESC",
            (business_id,),
        )
        for row in rows:
            row["data"] = json.loads(row.get("data", "{}"))
        return rows

    def health_trend(self, business_id: str) -> List[Dict]:
        """Get health score trend over time."""
        snapshots = self.get_snapshots(business_id)
        trend = []
        for snap in snapshots:
            health_score = snap["data"].get("health_score", 0)
            if health_score:
                trend.append({"date": snap["scan_date"], "health_score": health_score})
        return sorted(trend, key=lambda x: x["date"])

    def detect_decay(self, business_id: str, threshold_days: int = 90) -> Optional[Dict]:
        """Detect if a business has stopped being active."""
        last_scan = self.db.fetchone(
            "SELECT MAX(scan_date) as last_scan FROM snapshots WHERE node_id = ?",
            (business_id,),
        )

        if not last_scan or not last_scan.get("last_scan"):
            return None

        last_scan_date = datetime.strptime(str(last_scan["last_scan"]), "%Y-%m-%d")
        days_inactive = (datetime.now() - last_scan_date).days

        if days_inactive >= threshold_days:
            return {
                "business_id": business_id,
                "days_inactive": days_inactive,
                "last_scan": str(last_scan["last_scan"]),
                "severity": "high" if days_inactive >= 180 else "medium",
            }

        return None


if __name__ == "__main__":
    from database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        updater = IncrementalUpdater(db)

        b = db.execute(
            "INSERT INTO nodes (id, type, name, properties) VALUES (?, ?, ?, ?)",
            ("biz_test", "business", "Test Business", json.dumps({"city": "Dubai", "sector": "beauty"})),
        )

        old_data = {"rating": 4.0, "health_score": 70, "technologies": ["WordPress", "jQuery"], "sentiment_avg": 3.5}
        updater.create_snapshot("biz_test", old_data)

        new_data = {"rating": 3.5, "health_score": 55, "technologies": ["WordPress"], "sentiment_avg": 2.8}
        changes = updater.detect_changes("biz_test", new_data)

        print(f"Changes detected: {len(changes)}")
        for change in changes:
            print(f"  - {change['type']}: {change.get('old_value', '')} -> {change.get('new_value', '')} ({change['severity']})")

        updater.record_changes("biz_test", datetime.now().date().isoformat(), changes)
        recent = updater.get_all_changes("biz_test")
        print(f"Changes recorded: {len(recent)}")
