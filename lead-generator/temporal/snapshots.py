"""
#21 Snapshot System
Takes a snapshot of business state at a point in time.
Stores: rating, review_count, health_score, sentiment, technologies, emails, etc.
"""

import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any


class SnapshotSystem:
    """Takes and retrieves business state snapshots."""

    def __init__(self, db):
        self.db = db

    def take_snapshot(self, business_id: str, data: Dict) -> Dict:
        """Take a snapshot of business state."""
        scan_date = date.today().isoformat()
        data_json = json.dumps(data, ensure_ascii=False)

        existing = self.db.fetchone(
            "SELECT id FROM snapshots WHERE node_id = ? AND scan_date = ?",
            (business_id, scan_date),
        )

        if existing:
            self.db.execute(
                "UPDATE snapshots SET data = ? WHERE id = ?",
                (data_json, existing["id"]),
            )
            snapshot_id = existing["id"]
        else:
            result = self.db.execute(
                "INSERT INTO snapshots (node_id, scan_date, data) VALUES (?, ?, ?)",
                (business_id, scan_date, data_json),
            )
            snapshot_id = self.db.fetchone(
                "SELECT id FROM snapshots WHERE node_id = ? AND scan_date = ?",
                (business_id, scan_date),
            )["id"]

        return {
            "snapshot_id": snapshot_id,
            "business_id": business_id,
            "scan_date": scan_date,
            "fields": list(data.keys()),
        }

    def take_snapshot_full(self, business_id: str) -> Dict:
        """Take a complete snapshot from node properties."""
        node = self.db.fetchone(
            "SELECT properties FROM nodes WHERE id = ?",
            (business_id,),
        )
        if not node:
            return {"error": "Business not found"}

        props = json.loads(node.get("properties", "{}"))
        return self.take_snapshot(business_id, props)

    def get_latest(self, business_id: str) -> Optional[Dict]:
        """Get the most recent snapshot for a business."""
        row = self.db.fetchone(
            "SELECT * FROM snapshots WHERE node_id = ? ORDER BY scan_date DESC LIMIT 1",
            (business_id,),
        )
        if row:
            row["data"] = json.loads(row.get("data", "{}"))
            if hasattr(row.get("scan_date"), "isoformat"):
                row["scan_date"] = row["scan_date"].isoformat()
        return row

    def get_previous(self, business_id: str) -> Optional[Dict]:
        """Get the second most recent snapshot (before the latest)."""
        row = self.db.fetchone(
            """SELECT * FROM snapshots WHERE node_id = ? 
               AND scan_date < (SELECT MAX(scan_date) FROM snapshots WHERE node_id = ?)
               ORDER BY scan_date DESC LIMIT 1""",
            (business_id, business_id),
        )
        if row:
            row["data"] = json.loads(row.get("data", "{}"))
            if hasattr(row.get("scan_date"), "isoformat"):
                row["scan_date"] = row["scan_date"].isoformat()
        return row

    def get_all_snapshots(self, business_id: str) -> List[Dict]:
        """Get all snapshots for a business, sorted by date."""
        rows = self.db.fetchall(
            "SELECT * FROM snapshots WHERE node_id = ? ORDER BY scan_date ASC",
            (business_id,),
        )
        for row in rows:
            row["data"] = json.loads(row.get("data", "{}"))
            if hasattr(row.get("scan_date"), "isoformat"):
                row["scan_date"] = row["scan_date"].isoformat()
        return rows

    def get_snapshots_in_range(self, business_id: str, start_date: str, end_date: str) -> List[Dict]:
        """Get snapshots within a date range."""
        rows = self.db.fetchall(
            "SELECT * FROM snapshots WHERE node_id = ? AND scan_date >= ? AND scan_date <= ? ORDER BY scan_date ASC",
            (business_id, start_date, end_date),
        )
        for row in rows:
            row["data"] = json.loads(row.get("data", "{}"))
            if hasattr(row.get("scan_date"), "isoformat"):
                row["scan_date"] = row["scan_date"].isoformat()
        return rows

    def snapshot_count(self, business_id: Optional[str] = None) -> int:
        """Count snapshots for a business or total."""
        if business_id:
            row = self.db.fetchone(
                "SELECT COUNT(*) as cnt FROM snapshots WHERE node_id = ?",
                (business_id,),
            )
        else:
            row = self.db.fetchone("SELECT COUNT(*) as cnt FROM snapshots")
        return row["cnt"] if row else 0

    def days_between_snapshots(self, business_id: str) -> List[Dict]:
        """Calculate days between consecutive snapshots."""
        snapshots = self.get_all_snapshots(business_id)
        if len(snapshots) < 2:
            return []

        gaps = []
        for i in range(1, len(snapshots)):
            prev_date = datetime.strptime(snapshots[i - 1]["scan_date"], "%Y-%m-%d")
            curr_date = datetime.strptime(snapshots[i]["scan_date"], "%Y-%m-%d")
            days_diff = (curr_date - prev_date).days

            gaps.append({
                "from_date": snapshots[i - 1]["scan_date"],
                "to_date": snapshots[i]["scan_date"],
                "days": days_diff,
            })

        return gaps


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        db.execute(
            "INSERT INTO nodes (id, type, name, properties) VALUES (?, ?, ?, ?)",
            ("biz_test", "business", "Test Biz", json.dumps({"rating": 4.0, "review_count": 100, "health_score": 75})),
        )

        ss = SnapshotSystem(db)
        s1 = ss.take_snapshot("biz_test", {"rating": 4.0, "review_count": 100, "health_score": 75})
        print(f"Snapshot 1: {s1}")

        latest = ss.get_latest("biz_test")
        print(f"Latest: {latest}")

        count = ss.snapshot_count("biz_test")
        print(f"Count: {count}")
