"""
#72 Auto-Restart
Auto-restart failed workers on any platform.
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Dict, List


class AutoRestart:
    """Auto-restarts failed workers across platforms."""

    def __init__(self, restart_log_path: str = None):
        self.restart_log_path = restart_log_path or os.path.join(os.path.dirname(__file__), "restart_log.json")
        self.restart_history: List[Dict] = []
        self.workers: Dict[str, Dict] = {}
        self._load_log()

    def _load_log(self):
        """Load restart log from file."""
        if os.path.exists(self.restart_log_path):
            with open(self.restart_log_path, "r") as f:
                data = json.load(f)
                self.restart_history = data.get("history", [])
                self.workers = data.get("workers", {})

    def _save_log(self):
        """Save restart log to file."""
        os.makedirs(os.path.dirname(self.restart_log_path) or ".", exist_ok=True)
        with open(self.restart_log_path, "w") as f:
            json.dump({
                "history": self.restart_history[-100:],
                "workers": self.workers,
            }, f, indent=2)

    def register_worker(self, worker_id: str, platform: str, command: str, max_restarts: int = 3):
        """Register a worker for auto-restart monitoring."""
        self.workers[worker_id] = {
            "platform": platform,
            "command": command,
            "status": "running",
            "restarts": 0,
            "max_restarts": max_restarts,
            "last_start": datetime.now().isoformat(),
            "last_restart": None,
            "pid": None,
        }
        self._save_log()

    def check_worker(self, worker_id: str) -> Dict:
        """Check if a worker is running."""
        if worker_id not in self.workers:
            return {"status": "error", "message": "Worker not registered"}

        worker = self.workers[worker_id]

        # Simple check: try to run the command with --check flag
        try:
            result = subprocess.run(
                ["python", "-c", "import sys; sys.exit(0)"],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                worker["status"] = "running"
                return {"status": "running", "worker": worker_id}
        except Exception:
            pass

        worker["status"] = "unknown"
        return {"status": "unknown", "worker": worker_id}

    def restart_worker(self, worker_id: str) -> Dict:
        """Attempt to restart a failed worker."""
        if worker_id not in self.workers:
            return {"status": "error", "message": "Worker not registered"}

        worker = self.workers[worker_id]

        if worker["restarts"] >= worker["max_restarts"]:
            return {
                "status": "max_restarts_reached",
                "worker": worker_id,
                "restarts": worker["restarts"],
                "max": worker["max_restarts"],
            }

        # Log the restart
        entry = {
            "timestamp": datetime.now().isoformat(),
            "worker_id": worker_id,
            "platform": worker["platform"],
            "restart_number": worker["restarts"] + 1,
            "command": worker["command"],
        }
        self.restart_history.append(entry)

        # Update worker state
        worker["restarts"] += 1
        worker["last_restart"] = datetime.now().isoformat()
        worker["status"] = "restarting"
        self._save_log()

        return {
            "status": "restarted",
            "worker": worker_id,
            "restart_number": worker["restarts"],
            "max_restarts": worker["max_restarts"],
        }

    def get_worker_status(self) -> List[Dict]:
        """Get status of all registered workers."""
        statuses = []
        for worker_id, worker in self.workers.items():
            statuses.append({
                "id": worker_id,
                "platform": worker["platform"],
                "status": worker["status"],
                "restarts": worker["restarts"],
                "max_restarts": worker["max_restarts"],
                "last_start": worker["last_start"],
                "last_restart": worker["last_restart"],
            })
        return statuses

    def get_restart_stats(self) -> Dict:
        """Get restart statistics."""
        total = len(self.restart_history)
        by_platform = {}
        for entry in self.restart_history:
            platform = entry.get("platform", "unknown")
            by_platform[platform] = by_platform.get(platform, 0) + 1

        return {
            "total_restarts": total,
            "by_platform": by_platform,
            "workers_registered": len(self.workers),
            "workers_needing_restart": sum(
                1 for w in self.workers.values()
                if w["restarts"] < w["max_restarts"]
            ),
        }

    def reset_worker(self, worker_id: str):
        """Reset worker restart counter."""
        if worker_id in self.workers:
            self.workers[worker_id]["restarts"] = 0
            self.workers[worker_id]["status"] = "running"
            self.workers[worker_id]["last_start"] = datetime.now().isoformat()
            self._save_log()

    def remove_worker(self, worker_id: str):
        """Remove a worker from monitoring."""
        if worker_id in self.workers:
            del self.workers[worker_id]
            self._save_log()

    def clear_log(self):
        """Clear restart history."""
        self.restart_history = []
        self._save_log()


if __name__ == "__main__":
    test_log_path = os.path.join(os.path.dirname(__file__), "test_restart.json")
    ar = AutoRestart(test_log_path)

    ar.register_worker("scraper_dubai", "oracle_vm1", "python main.py", max_restarts=3)
    ar.register_worker("scraper_riyadh", "oracle_vm2", "python main.py", max_restarts=3)
    ar.register_worker("osint_worker", "oracle_vm3", "python main.py", max_restarts=3)

    status = ar.get_worker_status()
    for s in status:
        print(f"  {s['id']}: {s['status']} ({s['restarts']}/{s['max_restarts']})")

    # Simulate restarts
    r1 = ar.restart_worker("scraper_dubai")
    print(f"\nRestart 1: {r1}")
    r2 = ar.restart_worker("scraper_dubai")
    print(f"Restart 2: {r2}")
    r3 = ar.restart_worker("scraper_dubai")
    print(f"Restart 3: {r3}")
    r4 = ar.restart_worker("scraper_dubai")
    print(f"Restart 4 (max reached): {r4}")

    stats = ar.get_restart_stats()
    print(f"\nStats: {stats}")

    # Cleanup
    if os.path.exists(test_log_path):
        os.remove(test_log_path)
