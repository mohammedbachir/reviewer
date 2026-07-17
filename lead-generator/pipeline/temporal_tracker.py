"""
Pipeline #4: Temporal Snapshot
Creates snapshots after every scan run for historical tracking.
Integrates: temporal.snapshots, temporal.changes, temporal.severity
"""

import os
import sys
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import duckdb


class TemporalTracker:
    """Tracks business changes over time via snapshots."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "data.duckdb")
        self.is_memory = (self.db_path == ":memory:")
        self._conn = None
        self.stats = {
            "snapshots_created": 0,
            "changes_detected": 0,
            "critical_changes": 0,
        }

    def _get_conn(self):
        """Get a database connection (reuse for in-memory)."""
        if self.is_memory:
            if self._conn is None:
                self._conn = duckdb.connect(":memory:")
                self._ensure_tables(self._conn)
            return self._conn
        conn = duckdb.connect(self.db_path)
        self._ensure_tables(conn)
        return conn

    def _ensure_tables(self, conn):
        """Create snapshots table if it doesn't exist."""
        try:
            conn.execute("CREATE SEQUENCE IF NOT EXISTS temporal_snap_id_seq START 1")
        except Exception:
            pass
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER DEFAULT nextval('temporal_snap_id_seq'),
                    business_id INTEGER,
                    scan_date DATE DEFAULT CURRENT_DATE,
                    rating REAL,
                    review_count INTEGER,
                    health_score INTEGER,
                    sentiment_score REAL DEFAULT 0,
                    replied_to_reviews INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                )
            """)
        except Exception:
            pass

    def _close_conn(self, conn):
        """Close connection (only for file-based)."""
        if not self.is_memory:
            conn.close()

    def take_all_snapshots(self, businesses: List[Dict]) -> int:
        """Take snapshots for all businesses after a scan run."""
        conn = self._get_conn()
        count = 0
        for biz in businesses:
            try:
                result = conn.execute(
                    "SELECT id FROM businesses WHERE name = ? AND city = ?",
                    [biz.get("name", ""), biz.get("city", "")]
                ).fetchone()

                if result:
                    business_id = result[0]
                    conn.execute("""
                        INSERT INTO snapshots (business_id, rating, review_count, health_score, status)
                        VALUES (?, ?, ?, ?, ?)
                    """, [
                        business_id,
                        biz.get("rating", 0),
                        biz.get("review_count", 0),
                        biz.get("health_score", 50),
                        "active",
                    ])
                    count += 1
            except Exception as e:
                print(f"[TemporalTracker] Snapshot error: {e}")

        self._close_conn(conn)
        self.stats["snapshots_created"] = count
        return count

    def detect_changes(self, business_id: int) -> List[Dict]:
        """Detect changes between latest and previous snapshot."""
        conn = self._get_conn()
        changes = []

        try:
            snapshots = conn.execute("""
                SELECT rating, review_count, health_score, scan_date
                FROM snapshots
                WHERE business_id = ?
                ORDER BY scan_date DESC
                LIMIT 2
            """, [business_id]).fetchall()

            if len(snapshots) < 2:
                self._close_conn(conn)
                return changes

            latest = snapshots[0]
            previous = snapshots[1]

            if latest[0] != previous[0]:
                changes.append({
                    "type": "rating_change",
                    "old": previous[0],
                    "new": latest[0],
                    "direction": "increased" if latest[0] > previous[0] else "decreased",
                })

            if latest[1] != previous[1]:
                changes.append({
                    "type": "review_count_change",
                    "old": previous[1],
                    "new": latest[1],
                    "direction": "increased" if latest[1] > previous[1] else "decreased",
                })

            if latest[2] != previous[2]:
                changes.append({
                    "type": "health_change",
                    "old": previous[2],
                    "new": latest[2],
                    "direction": "improved" if latest[2] > previous[2] else "declined",
                })

            self.stats["changes_detected"] += len(changes)
        except Exception as e:
            print(f"[TemporalTracker] Change detection error: {e}")
        finally:
            self._close_conn(conn)

        return changes

    def get_business_history(self, business_id: int) -> List[Dict]:
        """Get full snapshot history for a business."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT rating, review_count, health_score, scan_date, status
                FROM snapshots
                WHERE business_id = ?
                ORDER BY scan_date ASC
            """, [business_id]).fetchall()

            self._close_conn(conn)
            return [
                {"rating": r[0], "review_count": r[1], "health_score": r[2],
                 "date": str(r[3]), "status": r[4]}
                for r in rows
            ]
        except Exception:
            self._close_conn(conn)
            return []

    def get_stats(self) -> Dict:
        """Get temporal tracking statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    tracker = TemporalTracker(":memory:")
    print("[Test] TemporalTracker initialized")
    print("[Test] Ready for temporal tracking")
