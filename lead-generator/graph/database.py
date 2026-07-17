"""
#14 Graph Database Setup
DuckDB-based knowledge graph with JSON columns for flexible properties.
Single file storage: data.duckdb
"""

import os
import json
import duckdb
from datetime import datetime
from typing import Optional, Dict, List, Any


DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data.duckdb")


class GraphDatabase:
    """
    DuckDB-based Knowledge Graph database.
    
    Schema:
        - nodes: id, type, name, properties (JSON), created_at, updated_at
        - edges: id, source_id, target_id, type, properties (JSON), confidence, created_at
        - snapshots: id, node_id, scan_date, data (JSON)
        - changes: id, node_id, scan_date, change_type, old_value, new_value, severity
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.conn = None
        self._connect()
        self._init_schema()

    def _connect(self):
        """Establish connection to DuckDB."""
        self.conn = duckdb.connect(self.db_path)

    def _init_schema(self):
        """Create all tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                type TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                confidence REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES nodes(id),
                FOREIGN KEY (target_id) REFERENCES nodes(id)
            )
        """)

        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS snapshot_id_seq START 1
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER DEFAULT nextval('snapshot_id_seq') PRIMARY KEY,
                node_id TEXT NOT NULL,
                scan_date DATE NOT NULL,
                data TEXT DEFAULT '{}',
                FOREIGN KEY (node_id) REFERENCES nodes(id)
            )
        """)

        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS change_id_seq START 1
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS changes (
                id INTEGER DEFAULT nextval('change_id_seq') PRIMARY KEY,
                node_id TEXT NOT NULL,
                scan_date DATE NOT NULL,
                change_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                severity TEXT DEFAULT 'low',
                FOREIGN KEY (node_id) REFERENCES nodes(id)
            )
        """)

        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS taxonomy_id_seq START 1
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS taxonomy (
                id INTEGER DEFAULT nextval('taxonomy_id_seq') PRIMARY KEY,
                country TEXT NOT NULL,
                city TEXT NOT NULL,
                sector TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                last_scan DATE,
                business_count INTEGER DEFAULT 0,
                avg_health_score REAL DEFAULT 0
            )
        """)

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_node ON snapshots(node_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_changes_node ON changes(node_id)")

    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute a query and return results."""
        if params:
            return self.conn.execute(query, params)
        return self.conn.execute(query)

    def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """Execute query and return all rows as list of dicts."""
        result = self.execute(query, params)
        columns = [desc[0] for desc in result.description] if result.description else []
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict]:
        """Execute query and return single row as dict."""
        result = self.execute(query, params)
        columns = [desc[0] for desc in result.description] if result.description else []
        row = result.fetchone()
        if row:
            return dict(zip(columns, row))
        return None

    def table_count(self, table: str) -> int:
        """Get row count for a table."""
        result = self.execute(f"SELECT COUNT(*) FROM {table}")
        return result.fetchone()[0]

    def stats(self) -> Dict:
        """Get database statistics."""
        return {
            "db_path": self.db_path,
            "db_size_mb": round(os.path.getsize(self.db_path) / 1024 / 1024, 2) if os.path.exists(self.db_path) else 0,
            "nodes": self.table_count("nodes"),
            "edges": self.table_count("edges"),
            "snapshots": self.table_count("snapshots"),
            "changes": self.table_count("changes"),
            "taxonomy_entries": self.table_count("taxonomy"),
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    with GraphDatabase(":memory:") as db:
        print("Graph Database initialized (in-memory)")
        print(f"Schema: nodes, edges, snapshots, changes, taxonomy")
        
        db.execute("""
            INSERT INTO nodes (id, type, name, properties) VALUES
            ('bloom-beauty', 'business', 'Bloom Beauty Studio', '{"city": "Dubai", "sector": "beauty salons", "rating": 4.2}')
        """)
        
        stats = db.stats()
        print(f"Stats: {stats}")
        print("Database test PASSED")
