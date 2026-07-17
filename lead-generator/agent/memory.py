"""
#48 Conversation Memory
Remember previous conversations using DuckDB.
"""

import json
import os
from datetime import datetime
from typing import Dict, List


class ConversationMemory:
    """Stores and retrieves conversation history from DuckDB."""

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
            conn.execute("CREATE SEQUENCE IF NOT EXISTS conversations_id_seq")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER DEFAULT nextval('conversations_id_seq') PRIMARY KEY,
                    business_name TEXT,
                    contact_email TEXT,
                    role TEXT,
                    message TEXT,
                    sentiment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception:
            pass
        self._close_conn(conn)

    def add_message(self, business_name: str, contact_email: str, role: str,
                    message: str, sentiment: str = "neutral"):
        """Add a message to conversation history."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO conversations (business_name, contact_email, role, message, sentiment)
                VALUES (?, ?, ?, ?, ?)
            """, [business_name, contact_email, role, message, sentiment])
        finally:
            self._close_conn(conn)

    def get_conversation(self, business_name: str) -> List[Dict]:
        """Get full conversation history for a business."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT role, message, sentiment, created_at
                FROM conversations
                WHERE business_name = ?
                ORDER BY created_at ASC
            """, [business_name]).fetchall()
            return [{"role": r[0], "message": r[1], "sentiment": r[2], "date": str(r[3])} for r in rows]
        finally:
            self._close_conn(conn)

    def get_last_message(self, business_name: str) -> Dict:
        """Get the last message in a conversation."""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT role, message, sentiment, created_at
                FROM conversations
                WHERE business_name = ?
                ORDER BY created_at DESC LIMIT 1
            """, [business_name]).fetchone()
            if row:
                return {"role": row[0], "message": row[1], "sentiment": row[2], "date": str(row[3])}
            return {}
        finally:
            self._close_conn(conn)

    def get_stats(self) -> Dict:
        """Get conversation statistics."""
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            businesses = conn.execute(
                "SELECT COUNT(DISTINCT business_name) FROM conversations"
            ).fetchone()[0]
            return {"total_messages": total, "unique_businesses": businesses}
        finally:
            self._close_conn(conn)
