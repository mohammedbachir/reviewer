"""
#41 Prompt Scoring
Track which email prompts worked and which failed.
"""

import json
import os
from datetime import datetime
from typing import Dict, List


class PromptScorer:
    """Scores email prompts based on response rates."""

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
            conn.execute("""
                CREATE SEQUENCE IF NOT EXISTS prompt_scores_id_seq
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_scores (
                    id INTEGER DEFAULT nextval('prompt_scores_id_seq') PRIMARY KEY,
                    prompt_name TEXT UNIQUE,
                    total_sent INTEGER DEFAULT 0,
                    positive_replies INTEGER DEFAULT 0,
                    negative_replies INTEGER DEFAULT 0,
                    neutral_replies INTEGER DEFAULT 0,
                    response_rate REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception:
            pass
        self._close_conn(conn)

    def record_sent(self, prompt_name: str):
        """Record that a prompt was sent."""
        conn = self._get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM prompt_scores WHERE prompt_name = ?", [prompt_name]
            ).fetchone()
            if existing:
                conn.execute("""
                    UPDATE prompt_scores SET total_sent = total_sent + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE prompt_name = ?
                """, [prompt_name])
            else:
                conn.execute("""
                    INSERT INTO prompt_scores (prompt_name, total_sent) VALUES (?, 1)
                """, [prompt_name])
        finally:
            self._close_conn(conn)

    def record_reply(self, prompt_name: str, classification: str):
        """Record a reply classification for a prompt."""
        conn = self._get_conn()
        try:
            col = f"{classification}_replies"
            if col not in ("positive_replies", "negative_replies", "neutral_replies"):
                return
            conn.execute(f"""
                UPDATE prompt_scores SET {col} = {col} + 1, updated_at = CURRENT_TIMESTAMP
                WHERE prompt_name = ?
            """, [prompt_name])
            conn.execute("""
                UPDATE prompt_scores SET
                    response_rate = CASE WHEN total_sent > 0
                        THEN (positive_replies * 100.0 / total_sent) ELSE 0 END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE prompt_name = ?
            """, [prompt_name])
        finally:
            self._close_conn(conn)

    def get_score(self, prompt_name: str) -> Dict:
        """Get score for a specific prompt."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM prompt_scores WHERE prompt_name = ?", [prompt_name]
            ).fetchone()
            if row:
                return {
                    "name": row[1], "total_sent": row[2], "positive": row[3],
                    "negative": row[4], "neutral": row[5], "response_rate": row[6],
                }
        finally:
            self._close_conn(conn)
        return {"name": prompt_name, "total_sent": 0, "response_rate": 0}

    def get_all_scores(self) -> List[Dict]:
        """Get scores for all prompts."""
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM prompt_scores ORDER BY response_rate DESC").fetchall()
            return [
                {"name": r[1], "total_sent": r[2], "positive": r[3],
                 "negative": r[4], "neutral": r[5], "response_rate": r[6]}
                for r in rows
            ]
        finally:
            self._close_conn(conn)

    def get_best_prompt(self) -> Dict:
        scores = self.get_all_scores()
        return scores[0] if scores else {"name": "none", "response_rate": 0}

    def get_worst_prompt(self) -> Dict:
        scores = self.get_all_scores()
        return scores[-1] if scores else {"name": "none", "response_rate": 0}
