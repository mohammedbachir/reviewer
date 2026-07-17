"""
#20 Export & Backup
Exports the knowledge graph to JSON, CSV, and DuckDB backup formats.
"""

import json
import csv
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any


class GraphExporter:
    """Exports the knowledge graph to various formats."""

    def __init__(self, db):
        self.db = db

    def export_json(self, filepath: str) -> Dict:
        """Export entire graph to JSON format."""
        nodes = self.db.fetchall("SELECT id, type, name, properties FROM nodes")
        for node in nodes:
            node["properties"] = json.loads(node.get("properties", "{}"))

        edges = self.db.fetchall("SELECT id, source_id, target_id, type, properties, confidence FROM edges")
        for edge in edges:
            edge["properties"] = json.loads(edge.get("properties", "{}"))

        snapshots = self.db.fetchall("SELECT id, node_id, scan_date, data FROM snapshots")
        for snap in snapshots:
            snap["data"] = json.loads(snap.get("data", "{}"))
            if hasattr(snap.get("scan_date"), "isoformat"):
                snap["scan_date"] = snap["scan_date"].isoformat()

        changes = self.db.fetchall("SELECT * FROM changes")
        for ch in changes:
            if hasattr(ch.get("scan_date"), "isoformat"):
                ch["scan_date"] = ch["scan_date"].isoformat()

        export_data = {
            "export_date": datetime.now().isoformat(),
            "stats": {
                "nodes": len(nodes),
                "edges": len(edges),
                "snapshots": len(snapshots),
                "changes": len(changes),
            },
            "nodes": nodes,
            "edges": edges,
            "snapshots": snapshots,
            "changes": changes,
        }

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        return {"status": "exported", "filepath": filepath, "size_bytes": os.path.getsize(filepath)}

    def export_nodes_csv(self, filepath: str) -> Dict:
        """Export nodes to CSV."""
        nodes = self.db.fetchall("SELECT id, type, name, properties, created_at, updated_at FROM nodes")
        for node in nodes:
            node["properties"] = json.dumps(json.loads(node.get("properties", "{}")), ensure_ascii=False)

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "type", "name", "properties", "created_at", "updated_at"])
            writer.writeheader()
            writer.writerows(nodes)

        return {"status": "exported", "filepath": filepath, "rows": len(nodes)}

    def export_edges_csv(self, filepath: str) -> Dict:
        """Export edges to CSV."""
        edges = self.db.fetchall("SELECT * FROM edges")
        for edge in edges:
            edge["properties"] = json.dumps(json.loads(edge.get("properties", "{}")), ensure_ascii=False)

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "source_id", "target_id", "type", "properties", "confidence", "created_at"])
            writer.writeheader()
            writer.writerows(edges)

        return {"status": "exported", "filepath": filepath, "rows": len(edges)}

    def export_changes_csv(self, filepath: str) -> Dict:
        """Export changes to CSV."""
        changes = self.db.fetchall("SELECT * FROM changes ORDER BY scan_date DESC")

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "node_id", "scan_date", "change_type", "old_value", "new_value", "severity"])
            writer.writeheader()
            writer.writerows(changes)

        return {"status": "exported", "filepath": filepath, "rows": len(changes)}

    def backup_duckdb(self, backup_dir: str) -> Dict:
        """Create a backup of the DuckDB database file."""
        db_path = self.db.db_path
        if not os.path.exists(db_path):
            return {"status": "error", "message": "Database file not found"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"findleads_backup_{timestamp}.duckdb"
        backup_path = os.path.join(backup_dir, backup_name)

        os.makedirs(backup_dir, exist_ok=True)

        try:
            self.db.conn.execute(f"BACKUP DATABASE TO '{backup_path}'")
        except Exception:
            self.db.conn.close()
            shutil.copy2(db_path, backup_path)
            self.db._connect()
            self.db._init_schema()

        return {
            "status": "backed_up",
            "filepath": backup_path,
            "size_bytes": os.path.getsize(backup_path) if os.path.exists(backup_path) else 0,
            "timestamp": timestamp,
        }

    def restore_duckdb(self, backup_path: str) -> Dict:
        """Restore database from a backup file."""
        if not os.path.exists(backup_path):
            return {"status": "error", "message": "Backup file not found"}

        target_path = self.db.db_path
        self.db.close()

        shutil.copy2(backup_path, target_path)

        return {"status": "restored", "source": backup_path, "target": target_path}

    def export_networkx_json(self, filepath: str) -> Dict:
        """Export NetworkX-compatible JSON (for visualization tools)."""
        nodes = self.db.fetchall("SELECT id, type, name, properties FROM nodes")
        edges = self.db.fetchall("SELECT source_id, target_id, type, confidence FROM edges")

        graph_json = {
            "directed": True,
            "multigraph": False,
            "graph": {"name": "FindLeads Knowledge Graph"},
            "nodes": [
                {"id": n["id"], "label": n["name"], "type": n["type"], **json.loads(n.get("properties", "{}"))}
                for n in nodes
            ],
            "links": [
                {"source": e["source_id"], "target": e["target_id"], "type": e["type"], "weight": e.get("confidence", 1.0)}
                for e in edges
            ],
        }

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(graph_json, f, ensure_ascii=False, indent=2)

        return {"status": "exported", "filepath": filepath, "nodes": len(nodes), "links": len(edges)}


if __name__ == "__main__":
    from database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        db.execute("""
            INSERT INTO nodes (id, type, name, properties) VALUES
            ('biz1', 'business', 'Bloom Beauty', '{"city": "Dubai", "sector": "beauty salons", "rating": 4.2}'),
            ('tech1', 'tech', 'WordPress', '{"version": "6.4"}')
        """)
        db.execute("""
            INSERT INTO edges (id, source_id, target_id, type, properties, confidence) VALUES
            ('e1', 'biz1', 'tech1', 'uses', '{"relationship": "technology"}', 1.0)
        """)

        exporter = GraphExporter(db)
        result = exporter.export_json("test_export.json")
        print(f"Export: {result}")

        csv_result = exporter.export_nodes_csv("test_nodes.csv")
        print(f"CSV Export: {csv_result}")

        net_result = exporter.export_networkx_json("test_networkx.json")
        print(f"NetworkX Export: {net_result}")

        backup_result = exporter.backup_duckdb("test_backups")
        print(f"Backup: {backup_result}")
