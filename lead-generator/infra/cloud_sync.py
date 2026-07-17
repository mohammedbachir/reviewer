"""
#68 Cloud Sync Engine
Sync data.duckdb across all platforms (GitHub Artifacts, Oracle, Google Drive).
"""

import os
import json
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional


class CloudSync:
    """Syncs DuckDB database across multiple cloud platforms."""

    def __init__(self, db_path: str = None, project_root: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "data.duckdb")
        self.project_root = project_root or os.path.dirname(__file__)
        self.sync_log_path = os.path.join(os.path.dirname(self.db_path), "sync_log.json")
        self.sync_history: List[Dict] = []
        self._load_sync_log()

    def _load_sync_log(self):
        """Load sync history from file."""
        if os.path.exists(self.sync_log_path):
            with open(self.sync_log_path, "r") as f:
                self.sync_history = json.load(f)

    def _save_sync_log(self):
        """Save sync history to file."""
        os.makedirs(os.path.dirname(self.sync_log_path) or ".", exist_ok=True)
        with open(self.sync_log_path, "w") as f:
            json.dump(self.sync_history, f, indent=2)

    def _record_sync(self, source: str, destination: str, status: str, size_bytes: int = 0):
        """Record a sync operation."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "destination": destination,
            "status": status,
            "size_bytes": size_bytes,
        }
        self.sync_history.append(entry)
        self._save_sync_log()

    def get_platforms(self) -> List[Dict]:
        """Get all configured sync platforms."""
        return [
            {
                "name": "GitHub Artifacts",
                "type": "artifacts",
                "free_limit": "500 MB per artifact, 90 days retention",
                "method": "actions/upload-artifact",
                "cost": 0,
            },
            {
                "name": "Google Drive",
                "type": "rclone",
                "free_limit": "15 GB",
                "method": "rclone copy gdrive:findleads/",
                "cost": 0,
            },
            {
                "name": "Dropbox",
                "type": "rclone",
                "free_limit": "2 GB",
                "method": "rclone copy dropbox:findleads/",
                "cost": 0,
            },
            {
                "name": "Local Backup",
                "type": "filesystem",
                "free_limit": "Unlimited",
                "method": "shutil.copy2",
                "cost": 0,
            },
        ]

    def sync_to_local_backup(self, backup_dir: str = None) -> Dict:
        """Sync database to local backup directory."""
        if backup_dir is None:
            backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")

        if not os.path.exists(self.db_path):
            self._record_sync("local", backup_dir, "error_no_source")
            return {"status": "error", "message": "Database not found"}

        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(backup_dir, f"data_{timestamp}.duckdb")

        shutil.copy2(self.db_path, dest)
        size = os.path.getsize(dest)
        self._record_sync("local", dest, "success", size)
        return {"status": "success", "destination": dest, "size_bytes": size}

    def sync_to_gdrive(self) -> Dict:
        """Sync database to Google Drive via rclone."""
        try:
            cmd = ["rclone", "copy", self.db_path, "gdrive:findleads/data.duckdb", "--progress"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                self._record_sync("local", "gdrive", "success", size)
                return {"status": "success", "platform": "Google Drive"}
            self._record_sync("local", "gdrive", "error", 0)
            return {"status": "error", "message": result.stderr}
        except FileNotFoundError:
            return {"status": "error", "message": "rclone not installed"}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Sync timed out"}

    def sync_to_dropbox(self) -> Dict:
        """Sync database to Dropbox via rclone."""
        try:
            cmd = ["rclone", "copy", self.db_path, "dropbox:findleads/data.duckdb", "--progress"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                self._record_sync("local", "dropbox", "success", size)
                return {"status": "success", "platform": "Dropbox"}
            self._record_sync("local", "dropbox", "error", 0)
            return {"status": "error", "message": result.stderr}
        except FileNotFoundError:
            return {"status": "error", "message": "rclone not installed"}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Sync timed out"}

    def sync_all(self) -> List[Dict]:
        """Sync to all configured platforms."""
        results = []
        results.append(self.sync_to_local_backup())
        results.append(self.sync_to_gdrive())
        results.append(self.sync_to_dropbox())
        return results

    def get_sync_history(self) -> List[Dict]:
        """Get sync operation history."""
        return self.sync_history[-50:]

    def get_sync_stats(self) -> Dict:
        """Get sync statistics."""
        total = len(self.sync_history)
        successes = sum(1 for s in self.sync_history if s["status"] == "success")
        failures = total - successes
        platforms = {}
        for s in self.sync_history:
            dest = s.get("destination", "unknown")
            if dest not in platforms:
                platforms[dest] = {"success": 0, "error": 0}
            if s["status"] == "success":
                platforms[dest]["success"] += 1
            else:
                platforms[dest]["error"] += 1
        return {
            "total_syncs": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
            "by_platform": platforms,
        }

    def clear_sync_history(self):
        """Clear sync history."""
        self.sync_history = []
        self._save_sync_log()


if __name__ == "__main__":
    cs = CloudSync()
    platforms = cs.get_platforms()
    print(f"Platforms: {len(platforms)}")
    for p in platforms:
        print(f"  {p['name']}: {p['free_limit']} (${p['cost']})")
    stats = cs.get_sync_stats()
    print(f"Sync stats: {stats}")
