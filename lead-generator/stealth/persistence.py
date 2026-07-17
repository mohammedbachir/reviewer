"""
#58 DuckDB Persistence
Save data to single compressed DuckDB file.
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Optional


class DuckDBPersistence:
    """Manages DuckDB file persistence and compression."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "data.duckdb")
        self.backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")

    def get_db_info(self) -> Dict:
        """Get information about the database file."""
        if not os.path.exists(self.db_path):
            return {"exists": False, "path": self.db_path}

        stat = os.stat(self.db_path)
        return {
            "exists": True,
            "path": self.db_path,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    def backup(self, label: str = None) -> Dict:
        """Create a timestamped backup of the database."""
        if not os.path.exists(self.db_path):
            return {"status": "error", "message": "Database not found"}

        os.makedirs(self.backup_dir, exist_ok=True)

        if label is None:
            label = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_name = f"findleads_{label}.duckdb"
        backup_path = os.path.join(self.backup_dir, backup_name)

        shutil.copy2(self.db_path, backup_path)

        return {
            "status": "backed_up",
            "filepath": backup_path,
            "size_bytes": os.path.getsize(backup_path),
            "label": label,
        }

    def restore(self, backup_path: str) -> Dict:
        """Restore database from a backup."""
        if not os.path.exists(backup_path):
            return {"status": "error", "message": "Backup not found"}

        shutil.copy2(backup_path, self.db_path)
        return {"status": "restored", "source": backup_path, "target": self.db_path}

    def list_backups(self) -> list:
        """List all available backups."""
        if not os.path.exists(self.backup_dir):
            return []

        backups = []
        for f in sorted(os.listdir(self.backup_dir)):
            if f.endswith(".duckdb"):
                path = os.path.join(self.backup_dir, f)
                stat = os.stat(path)
                backups.append({
                    "filename": f,
                    "path": path,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                })
        return backups

    def cleanup_old_backups(self, keep_last: int = 10):
        """Remove old backups, keeping only the last N."""
        backups = self.list_backups()
        if len(backups) <= keep_last:
            return {"removed": 0}

        to_remove = backups[:-keep_last]
        for b in to_remove:
            os.remove(b["path"])

        return {"removed": len(to_remove)}

    def export_json(self, nodes: list, filepath: str) -> Dict:
        """Export graph data to JSON for external storage."""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"nodes": nodes, "export_date": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
        return {"status": "exported", "filepath": filepath, "nodes": len(nodes)}


if __name__ == "__main__":
    persistence = DuckDBPersistence(":memory:")
    info = persistence.get_db_info()
    print(f"DB info: {info}")
    backups = persistence.list_backups()
    print(f"Backups: {len(backups)}")
