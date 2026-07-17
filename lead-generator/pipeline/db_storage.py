"""
Pipeline #3: DB Storage
Stores scraped businesses + OSINT results into DuckDB.
Integrates: graph.database, graph.nodes, graph.edges, graph.sync
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import duckdb


class DBStorage:
    """Stores business data into DuckDB database."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "data.duckdb")
        self.is_memory = (self.db_path == ":memory:")
        self._conn = None
        self.stats = {
            "businesses_stored": 0,
            "nodes_created": 0,
            "edges_created": 0,
            "snapshots_taken": 0,
        }
        self._ensure_tables()

    def _get_conn(self):
        """Get a database connection (reuse for in-memory)."""
        if self.is_memory:
            if self._conn is None:
                self._conn = duckdb.connect(":memory:")
            return self._conn
        return duckdb.connect(self.db_path)

    def _close_conn(self, conn):
        """Close connection (only for file-based)."""
        if not self.is_memory:
            conn.close()

    def _ensure_tables(self):
        """Create required tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.execute("CREATE SEQUENCE IF NOT EXISTS node_id_seq START 1")
        except Exception:
            pass
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id INTEGER DEFAULT nextval('node_id_seq'),
                    name TEXT,
                    city TEXT,
                    sector TEXT,
                    country TEXT DEFAULT 'UAE',
                    rating REAL DEFAULT 0,
                    review_count INTEGER DEFAULT 0,
                    website TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    address TEXT DEFAULT '',
                    google_url TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    response_rate INTEGER DEFAULT 0,
                    unanswered_reviews INTEGER DEFAULT 0,
                    target_priority TEXT DEFAULT 'low',
                    health_score INTEGER DEFAULT 50,
                    osint_data TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                )
            """)
        except Exception:
            pass
        # Auto-migrate: add email column if missing
        try:
            cols = [r[1] for r in conn.execute("DESCRIBE businesses").fetchall()]
            if "email" not in cols:
                conn.execute("ALTER TABLE businesses ADD COLUMN email TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("""
                    id INTEGER DEFAULT nextval('node_id_seq'),
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
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER DEFAULT nextval('node_id_seq'),
                    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    city TEXT,
                    sector TEXT,
                    businesses_found INTEGER DEFAULT 0,
                    osint_scanned INTEGER DEFAULT 0,
                    emails_found INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    PRIMARY KEY (id)
                )
            """)
        except Exception:
            pass
        self._close_conn(conn)

    def store_business(self, business: Dict) -> int:
        """Store a single business. Returns the business ID."""
        conn = self._get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM businesses WHERE name = ? AND city = ?",
                [business.get("name", ""), business.get("city", "")]
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE businesses SET
                        rating = ?, review_count = ?, website = ?, email = ?, phone = ?,
                        address = ?, google_url = ?, category = ?,
                        response_rate = ?, unanswered_reviews = ?, target_priority = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, [
                    business.get("rating", 0),
                    business.get("review_count", 0),
                    business.get("website", ""),
                    business.get("email", ""),
                    business.get("phone", ""),
                    business.get("address", ""),
                    business.get("google_url", ""),
                    business.get("category", ""),
                    business.get("response_rate", 0),
                    business.get("unanswered_reviews", 0),
                    business.get("target_priority", "low"),
                    existing[0],
                ])
                self._close_conn(conn)
                return existing[0]
            else:
                result = conn.execute("""
                    INSERT INTO businesses (name, city, sector, country, rating, review_count,
                        website, email, phone, address, google_url, category,
                        response_rate, unanswered_reviews, target_priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                """, [
                    business.get("name", ""),
                    business.get("city", ""),
                    business.get("sector", ""),
                    business.get("country", "UAE"),
                    business.get("rating", 0),
                    business.get("review_count", 0),
                    business.get("website", ""),
                    business.get("email", ""),
                    business.get("phone", ""),
                    business.get("address", ""),
                    business.get("google_url", ""),
                    business.get("category", ""),
                    business.get("response_rate", 0),
                    business.get("unanswered_reviews", 0),
                    business.get("target_priority", "low"),
                ]).fetchone()
                self._close_conn(conn)
                self.stats["businesses_stored"] += 1
                return result[0] if result else 0
        except Exception as e:
            self._close_conn(conn)
            print(f"[DBStorage] Error storing {business.get('name', '?')}: {e}")
            return 0

    def store_osint(self, business_id: int, osint_data: Dict):
        """Store OSINT data for a business."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE businesses SET osint_data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [json.dumps(osint_data, default=str), business_id]
            )
        except Exception as e:
            print(f"[DBStorage] Error storing OSINT for {business_id}: {e}")
        finally:
            self._close_conn(conn)

    def update_health(self, business_id: int, health_score: int):
        """Update health score for a business."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE businesses SET health_score = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [health_score, business_id]
            )
        except Exception as e:
            print(f"[DBStorage] Error updating health for {business_id}: {e}")
        finally:
            self._close_conn(conn)

    def take_snapshot(self, business_id: int, business: Dict):
        """Take a temporal snapshot of a business."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO snapshots (business_id, rating, review_count, health_score, status)
                VALUES (?, ?, ?, ?, ?)
            """, [
                business_id,
                business.get("rating", 0),
                business.get("review_count", 0),
                business.get("health_score", 50),
                "active",
            ])
            self.stats["snapshots_taken"] += 1
        except Exception as e:
            print(f"[DBStorage] Error taking snapshot for {business_id}: {e}")
        finally:
            self._close_conn(conn)

    def start_run(self, city: str, sector: str) -> int:
        """Record the start of a scan run. Returns run ID."""
        conn = self._get_conn()
        try:
            result = conn.execute("""
                INSERT INTO scan_runs (city, sector, status)
                VALUES (?, ?, 'running')
                RETURNING id
            """, [city, sector]).fetchone()
            self._close_conn(conn)
            return result[0] if result else 0
        except Exception as e:
            self._close_conn(conn)
            print(f"[DBStorage] Error starting run: {e}")
            return 0

    def end_run(self, run_id: int, businesses_found: int, osint_scanned: int,
                emails_found: int, duration: float, status: str = "completed"):
        """Record the end of a scan run."""
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE scan_runs SET
                    businesses_found = ?, osint_scanned = ?, emails_found = ?,
                    duration_seconds = ?, status = ?
                WHERE id = ?
            """, [businesses_found, osint_scanned, emails_found, duration, status, run_id])
        except Exception as e:
            print(f"[DBStorage] Error ending run {run_id}: {e}")
        finally:
            self._close_conn(conn)

    def get_business_count(self) -> int:
        """Get total businesses in database."""
        conn = self._get_conn()
        try:
            result = conn.execute("SELECT COUNT(*) FROM businesses").fetchone()
            return result[0] if result else 0
        except Exception:
            return 0
        finally:
            self._close_conn(conn)

    def get_stats(self) -> Dict:
        """Get storage statistics."""
        conn = self._get_conn()
        try:
            biz_count = conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]
            snap_count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
            run_count = conn.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0]
            db_size = 0
            if not self.is_memory and os.path.exists(self.db_path):
                db_size = round(os.path.getsize(self.db_path) / 1024 / 1024, 2)
            return {
                "businesses": biz_count,
                "snapshots": snap_count,
                "scan_runs": run_count,
                "db_path": self.db_path,
                "db_size_mb": db_size,
            }
        except Exception as e:
            return {"error": str(e)}
        finally:
            self._close_conn(conn)


if __name__ == "__main__":
    storage = DBStorage(":memory:")
    print("[Test] DBStorage initialized (in-memory)")
    stats = storage.get_stats()
    print(f"[Test] Stats: {stats}")
