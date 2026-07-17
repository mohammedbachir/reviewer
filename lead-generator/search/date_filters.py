"""
#32 Date Range Filters
Filter by specific month, last month, last 3 months, custom range.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class DateFilter:
    """Date-based filtering for business data."""

    def __init__(self, db):
        self.db = db

    def filter_by_month(self, year: int, month: int) -> List[Dict]:
        """Filter snapshots by specific month."""
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        rows = self.db.fetchall(
            """SELECT DISTINCT n.id, n.name, n.properties 
               FROM nodes n 
               JOIN snapshots s ON n.id = s.node_id 
               WHERE n.type = 'business' AND s.scan_date >= ? AND s.scan_date < ?""",
            (start_date, end_date),
        )
        for row in rows:
            row["properties"] = __import__("json").loads(row.get("properties", "{}"))
        return rows

    def filter_last_days(self, days: int) -> List[Dict]:
        """Filter businesses scanned in the last N days."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self.db.fetchall(
            """SELECT DISTINCT n.id, n.name, n.properties 
               FROM nodes n 
               JOIN snapshots s ON n.id = s.node_id 
               WHERE n.type = 'business' AND s.scan_date >= ?""",
            (since,),
        )
        for row in rows:
            row["properties"] = __import__("json").loads(row.get("properties", "{}"))
        return rows

    def filter_custom_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Filter by custom date range."""
        rows = self.db.fetchall(
            """SELECT DISTINCT n.id, n.name, n.properties 
               FROM nodes n 
               JOIN snapshots s ON n.id = s.node_id 
               WHERE n.type = 'business' AND s.scan_date >= ? AND s.scan_date <= ?""",
            (start_date, end_date),
        )
        for row in rows:
            row["properties"] = __import__("json").loads(row.get("properties", "{}"))
        return rows

    def filter_never_scanned(self) -> List[Dict]:
        """Find businesses that have never been scanned."""
        rows = self.db.fetchall(
            """SELECT id, name, properties FROM nodes n 
               WHERE type = 'business' 
               AND NOT EXISTS (SELECT 1 FROM snapshots s WHERE s.node_id = n.id)"""
        )
        for row in rows:
            row["properties"] = __import__("json").loads(row.get("properties", "{}"))
        return rows

    def filter_stale(self, days: int = 30) -> List[Dict]:
        """Find businesses not scanned in the last N days."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self.db.fetchall(
            """SELECT n.id, n.name, n.properties FROM nodes n 
               WHERE type = 'business' 
               AND NOT EXISTS (
                   SELECT 1 FROM snapshots s 
                   WHERE s.node_id = n.id AND s.scan_date >= ?
               )"""
            , (since,),
        )
        for row in rows:
            row["properties"] = __import__("json").loads(row.get("properties", "{}"))
        return rows

    def get_scan_summary(self) -> Dict:
        """Get summary of when businesses were last scanned."""
        rows = self.db.fetchall(
            """SELECT n.id, n.name, 
                      MAX(s.scan_date) as last_scan
               FROM nodes n 
               LEFT JOIN snapshots s ON n.id = s.node_id
               WHERE n.type = 'business'
               GROUP BY n.id, n.name"""
        )
        for row in rows:
            if hasattr(row.get("last_scan"), "isoformat"):
                row["last_scan"] = row["last_scan"].isoformat()
        return {"businesses": rows, "total": len(rows)}


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        df = DateFilter(db)
        summary = df.get_scan_summary()
        print(f"Scan summary: {summary}")
