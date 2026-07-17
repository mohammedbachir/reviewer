"""
#42 Automated Feedback Loop
Updates prompt weights automatically based on response data.
"""

import json
import os
from datetime import datetime
from typing import Dict, List


class FeedbackLoop:
    """Automatically adjusts prompt weights based on performance."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "data.duckdb")
        self.is_memory = (self.db_path == ":memory:")
        self._conn = None
        self._ensure_table()

    def _get_conn(self):
        if self.is_memory:
            if self._conn is None:
                import duckdb
                self._conn = duckdb.connect(":memory:")
            return self._conn
        import duckdb
        return duckdb.connect(self.db_path)

    def _close_conn(self, conn):
        if not self.is_memory:
            conn.close()

    def _ensure_table(self):
        conn = self._get_conn()
        try:
            conn.execute("CREATE SEQUENCE IF NOT EXISTS feedback_loop_id_seq")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_loop (
                    id INTEGER DEFAULT nextval('feedback_loop_id_seq') PRIMARY KEY,
                    prompt_name TEXT,
                    adjustment REAL DEFAULT 0,
                    reason TEXT,
                    old_weight REAL,
                    new_weight REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception:
            pass
        self._close_conn(conn)

    def calculate_adjustment(self, prompt_name: str) -> Dict:
        """Calculate weight adjustment based on response data."""
        conn = self._get_conn()
        try:
            try:
                row = conn.execute(
                    "SELECT total_sent, positive_replies, negative_replies, response_rate FROM prompt_scores WHERE prompt_name = ?",
                    [prompt_name]
                ).fetchone()
            except Exception:
                row = None
            if not row or row[0] == 0:
                return {"adjustment": 0, "reason": "no_data"}

            total_sent, positive, negative, response_rate = row

            if response_rate > 20:
                adjustment, reason = 0.1, "high_response_rate"
            elif response_rate > 10:
                adjustment, reason = 0.05, "moderate_response_rate"
            elif response_rate < 2 and total_sent >= 10:
                adjustment, reason = -0.1, "low_response_rate"
            elif negative > positive and total_sent >= 5:
                adjustment, reason = -0.05, "more_negative_than_positive"
            else:
                adjustment, reason = 0, "insufficient_data"

            return {"adjustment": adjustment, "reason": reason, "current_rate": response_rate}
        finally:
            self._close_conn(conn)

    def apply_adjustment(self, prompt_name: str) -> Dict:
        """Apply weight adjustment to a prompt."""
        calc = self.calculate_adjustment(prompt_name)
        if calc["adjustment"] == 0:
            return calc

        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT response_rate FROM prompt_scores WHERE prompt_name = ?", [prompt_name]
            ).fetchone()
            old_weight = row[0] if row else 1.0
            new_weight = max(0.1, old_weight + calc["adjustment"])

            conn.execute("""
                INSERT INTO feedback_loop (prompt_name, adjustment, reason, old_weight, new_weight)
                VALUES (?, ?, ?, ?, ?)
            """, [prompt_name, calc["adjustment"], calc["reason"], old_weight, new_weight])

            return {
                "prompt": prompt_name,
                "adjustment": calc["adjustment"],
                "old_weight": old_weight,
                "new_weight": new_weight,
                "reason": calc["reason"],
            }
        finally:
            self._close_conn(conn)

    def get_feedback_history(self) -> List[Dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT prompt_name, adjustment, reason, old_weight, new_weight, created_at FROM feedback_loop ORDER BY created_at DESC"
            ).fetchall()
            return [
                {"prompt": r[0], "adjustment": r[1], "reason": r[2],
                 "old_weight": r[3], "new_weight": r[4], "date": str(r[5])}
                for r in rows
            ]
        finally:
            self._close_conn(conn)
