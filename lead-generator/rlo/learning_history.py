"""
#43 Learning History
Save all learning history to DuckDB for long-term analysis.
"""

import json
import os
from datetime import datetime
from typing import Dict, List


class LearningHistory:
    """Saves all learning data to DuckDB for long-term analysis."""

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
            conn.execute("CREATE SEQUENCE IF NOT EXISTS learning_history_id_seq")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_history (
                    id INTEGER DEFAULT nextval('learning_history_id_seq') PRIMARY KEY,
                    event_type TEXT,
                    event_data TEXT,
                    prompt_name TEXT,
                    business_name TEXT,
                    outcome TEXT,
                    metrics TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception:
            pass
        self._close_conn(conn)

    def record_event(self, event_type: str, event_data: Dict, prompt_name: str = None,
                     business_name: str = None, outcome: str = None):
        """Record a learning event."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO learning_history (event_type, event_data, prompt_name, business_name, outcome, metrics)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                event_type,
                json.dumps(event_data, default=str),
                prompt_name,
                business_name,
                outcome,
                json.dumps({}, default=str),
            ])
        finally:
            self._close_conn(conn)

    def get_history(self, event_type: str = None, limit: int = 100) -> List[Dict]:
        """Get learning history, optionally filtered by event type."""
        conn = self._get_conn()
        try:
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM learning_history WHERE event_type = ? ORDER BY created_at DESC LIMIT ?",
                    [event_type, limit]
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM learning_history ORDER BY created_at DESC LIMIT ?",
                    [limit]
                ).fetchall()
            return [
                {"id": r[0], "type": r[1], "data": r[2], "prompt": r[3],
                 "business": r[4], "outcome": r[5], "date": str(r[7])}
                for r in rows
            ]
        finally:
            self._close_conn(conn)

    def get_stats(self) -> Dict:
        """Get learning statistics."""
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM learning_history").fetchone()[0]
            types = conn.execute(
                "SELECT event_type, COUNT(*) FROM learning_history GROUP BY event_type"
            ).fetchall()
            return {
                "total_events": total,
                "by_type": {r[0]: r[1] for r in types},
            }
        finally:
            self._close_conn(conn)

    def get_prompt_performance(self, prompt_name: str) -> Dict:
        """Get performance data for a specific prompt."""
        conn = self._get_conn()
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM learning_history WHERE prompt_name = ?", [prompt_name]
            ).fetchone()[0]
            positive = conn.execute(
                "SELECT COUNT(*) FROM learning_history WHERE prompt_name = ? AND outcome = 'positive'",
                [prompt_name]
            ).fetchone()[0]
            return {
                "prompt": prompt_name,
                "total_events": total,
                "positive_outcomes": positive,
                "success_rate": round(positive / total * 100, 1) if total > 0 else 0,
            }
        finally:
            self._close_conn(conn)
