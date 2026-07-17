"""
#59 External Backup
Automatic backup to Google Drive (15GB) + Dropbox (2GB) via rclone.
"""

import os
import subprocess
import json
from datetime import datetime
from typing import Dict, List


class ExternalBackup:
    """Manages external backup to cloud storage."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "data.duckdb")
        self.rclone_config = os.path.expanduser("~/.config/rclone/rclone.conf")

    def get_setup_instructions(self) -> Dict:
        """Get instructions for setting up rclone."""
        return {
            "steps": [
                "1. Install rclone: https://rclone.org/install/",
                "2. Run: rclone config",
                "3. Add Google Drive remote (name: gdrive)",
                "4. Add Dropbox remote (name: dropbox)",
                "5. Test: rclone ls gdrive:findleads/",
            ],
            "google_drive_free": "15 GB",
            "dropbox_free": "2 GB",
            "command_backup_gdrive": f"rclone copy {self.db_path} gdrive:findleads/ --progress",
            "command_backup_dropbox": f"rclone copy {self.db_path} dropbox:findleads/ --progress",
            "command_restore_gdrive": f"rclone copy gdrive:findleads/data.duckdb {os.path.dirname(self.db_path)}/ --progress",
        }

    def backup_to_gdrive(self) -> Dict:
        """Backup database to Google Drive."""
        try:
            cmd = ["rclone", "copy", self.db_path, "gdrive:findleads/", "--progress"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return {"status": "success", "destination": "Google Drive", "timestamp": datetime.now().isoformat()}
            return {"status": "error", "message": result.stderr}
        except FileNotFoundError:
            return {"status": "error", "message": "rclone not installed"}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Backup timed out"}

    def backup_to_dropbox(self) -> Dict:
        """Backup database to Dropbox."""
        try:
            cmd = ["rclone", "copy", self.db_path, "dropbox:findleads/", "--progress"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return {"status": "success", "destination": "Dropbox", "timestamp": datetime.now().isoformat()}
            return {"status": "error", "message": result.stderr}
        except FileNotFoundError:
            return {"status": "error", "message": "rclone not installed"}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Backup timed out"}

    def backup_all(self) -> List[Dict]:
        """Backup to all configured remote storage."""
        results = []
        results.append(self.backup_to_gdrive())
        results.append(self.backup_to_dropbox())
        return results

    def is_rclone_installed(self) -> bool:
        """Check if rclone is installed."""
        try:
            result = subprocess.run(["rclone", "version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


if __name__ == "__main__":
    eb = ExternalBackup()
    installed = eb.is_rclone_installed()
    print(f"rclone installed: {installed}")
    instructions = eb.get_setup_instructions()
    print(f"Setup steps: {len(instructions['steps'])}")
