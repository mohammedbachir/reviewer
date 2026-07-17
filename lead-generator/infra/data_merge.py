"""
#74 Data Merge Engine
Merge data from multiple sources into single DuckDB (handle duplicates, conflicts).
"""

import os
import json
import duckdb
from datetime import datetime
from typing import Dict, List, Optional


class DataMerger:
    """Merges data from multiple sources into a single DuckDB database."""

    def __init__(self, primary_db: str = None):
        self.primary_db = primary_db or os.path.join(os.path.dirname(__file__), "..", "data.duckdb")
        self.merge_log_path = os.path.join(os.path.dirname(self.primary_db), "merge_log.json")
        self.merge_history: List[Dict] = []
        self._load_log()

    def _load_log(self):
        """Load merge log from file."""
        if os.path.exists(self.merge_log_path):
            with open(self.merge_log_path, "r") as f:
                self.merge_history = json.load(f)

    def _save_log(self):
        """Save merge log to file."""
        os.makedirs(os.path.dirname(self.merge_log_path) or ".", exist_ok=True)
        with open(self.merge_log_path, "w") as f:
            json.dump(self.merge_history[-100:], f, indent=2)

    def merge_databases(self, source_db: str, strategy: str = "upsert") -> Dict:
        """Merge a source DuckDB into the primary database."""
        if not os.path.exists(source_db):
            return {"status": "error", "message": "Source database not found"}

        if not os.path.exists(self.primary_db):
            # Create primary database with schema
            conn = duckdb.connect(self.primary_db)
            self._ensure_schema(conn)
            conn.close()

        try:
            source_conn = duckdb.connect(source_db, read_only=True)
            primary_conn = duckdb.connect(self.primary_db)

            # Ensure schema exists
            self._ensure_schema(primary_conn)

            results = {"nodes_merged": 0, "edges_merged": 0, "duplicates_skipped": 0}

            # Merge nodes
            try:
                nodes = source_conn.execute("SELECT * FROM nodes").fetchall()
                columns = [desc[0] for desc in source_conn.description]
                for row in nodes:
                    row_dict = dict(zip(columns, row))
                    node_id = row_dict.get("node_id") or row_dict.get("id")

                    # Check for existing node
                    existing = primary_conn.execute(
                        "SELECT id FROM nodes WHERE node_id = ? OR id = ?",
                        [node_id, node_id]
                    ).fetchone()

                    if existing and strategy == "skip":
                        results["duplicates_skipped"] += 1
                    elif existing and strategy == "upsert":
                        # Update existing
                        primary_conn.execute(
                            "UPDATE nodes SET properties = ?, updated_at = CURRENT_TIMESTAMP WHERE node_id = ? OR id = ?",
                            [json.dumps(row_dict.get("properties", {})), node_id, node_id]
                        )
                        results["nodes_merged"] += 1
                    else:
                        # Insert new
                        primary_conn.execute(
                            "INSERT INTO nodes (node_id, node_type, properties, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                            [node_id, row_dict.get("node_type", "unknown"), json.dumps(row_dict.get("properties", {}))]
                        )
                        results["nodes_merged"] += 1
            except Exception:
                pass

            # Merge edges
            try:
                edges = source_conn.execute("SELECT * FROM edges").fetchall()
                columns = [desc[0] for desc in source_conn.description]
                for row in edges:
                    row_dict = dict(zip(columns, row))
                    source_node = row_dict.get("source_node_id")
                    target_node = row_dict.get("target_node_id")

                    # Check for existing edge
                    existing = primary_conn.execute(
                        "SELECT id FROM edges WHERE source_node_id = ? AND target_node_id = ? AND edge_type = ?",
                        [source_node, target_node, row_dict.get("edge_type")]
                    ).fetchone()

                    if existing and strategy == "skip":
                        results["duplicates_skipped"] += 1
                    elif existing and strategy == "upsert":
                        primary_conn.execute(
                            "UPDATE edges SET properties = ?, updated_at = CURRENT_TIMESTAMP WHERE source_node_id = ? AND target_node_id = ? AND edge_type = ?",
                            [json.dumps(row_dict.get("properties", {})), source_node, target_node, row_dict.get("edge_type")]
                        )
                        results["edges_merged"] += 1
                    else:
                        primary_conn.execute(
                            "INSERT INTO edges (source_node_id, target_node_id, edge_type, properties, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                            [source_node, target_node, row_dict.get("edge_type"), json.dumps(row_dict.get("properties", {}))]
                        )
                        results["edges_merged"] += 1
            except Exception:
                pass

            source_conn.close()
            primary_conn.close()

            # Log the merge
            entry = {
                "timestamp": datetime.now().isoformat(),
                "source": source_db,
                "strategy": strategy,
                "results": results,
            }
            self.merge_history.append(entry)
            self._save_log()

            results["status"] = "success"
            return results

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _ensure_schema(self, conn):
        """Ensure required tables exist in the database."""
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY,
                    node_id TEXT UNIQUE,
                    node_type TEXT,
                    properties TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception:
            pass
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY,
                    source_node_id TEXT,
                    target_node_id TEXT,
                    edge_type TEXT,
                    properties TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception:
            pass

    def merge_csv(self, csv_path: str, table_name: str = "businesses") -> Dict:
        """Merge a CSV file into the primary database."""
        if not os.path.exists(csv_path):
            return {"status": "error", "message": "CSV file not found"}

        try:
            conn = duckdb.connect(self.primary_db)
            result = conn.execute(f"""
                INSERT OR IGNORE INTO {table_name}
                SELECT * FROM read_csv_auto('{csv_path}')
            """).fetchall()
            conn.close()
            return {"status": "success", "rows_affected": len(result)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_merge_history(self) -> List[Dict]:
        """Get merge operation history."""
        return self.merge_history

    def get_merge_stats(self) -> Dict:
        """Get merge statistics."""
        total = len(self.merge_history)
        strategies = {}
        for entry in self.merge_history:
            s = entry.get("strategy", "unknown")
            strategies[s] = strategies.get(s, 0) + 1

        total_nodes = sum(e.get("results", {}).get("nodes_merged", 0) for e in self.merge_history)
        total_edges = sum(e.get("results", {}).get("edges_merged", 0) for e in self.merge_history)
        total_skipped = sum(e.get("results", {}).get("duplicates_skipped", 0) for e in self.merge_history)

        return {
            "total_merges": total,
            "strategies_used": strategies,
            "total_nodes_merged": total_nodes,
            "total_edges_merged": total_edges,
            "total_duplicates_skipped": total_skipped,
        }


if __name__ == "__main__":
    merger = DataMerger(":memory:")

    # Test merge stats
    stats = merger.get_merge_stats()
    print(f"Initial stats: {stats}")

    history = merger.get_merge_history()
    print(f"Merge history: {len(history)} entries")

    print("DataMerger initialized successfully")
