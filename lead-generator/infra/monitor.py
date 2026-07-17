"""
#71 Health Monitor
Monitor all platforms status (is GitHub Actions running? Are Oracle VMs healthy?)
"""

import json
import os
import urllib.request
from datetime import datetime
from typing import Dict, List


class HealthMonitor:
    """Monitors health status of all platforms."""

    def __init__(self, status_path: str = None):
        self.status_path = status_path or os.path.join(os.path.dirname(__file__), "platform_status.json")
        self.platforms: Dict[str, Dict] = {}
        self._load_status()

    def _load_status(self):
        """Load platform status from file."""
        if os.path.exists(self.status_path):
            with open(self.status_path, "r") as f:
                self.platforms = json.load(f)

    def _save_status(self):
        """Save platform status to file."""
        os.makedirs(os.path.dirname(self.status_path) or ".", exist_ok=True)
        with open(self.status_path, "w") as f:
            json.dump(self.platforms, f, indent=2)

    def register_platform(self, platform_id: str, name: str, check_url: str = None):
        """Register a platform for monitoring."""
        self.platforms[platform_id] = {
            "name": name,
            "check_url": check_url,
            "status": "unknown",
            "last_check": None,
            "last_success": None,
            "failures": 0,
            "uptime_percent": 100.0,
            "response_time_ms": None,
        }
        self._save_status()

    def check_platform(self, platform_id: str) -> Dict:
        """Check health of a specific platform."""
        if platform_id not in self.platforms:
            return {"status": "error", "message": "Platform not registered"}

        platform = self.platforms[platform_id]
        check_url = platform.get("check_url")

        if check_url:
            try:
                start = datetime.now()
                req = urllib.request.Request(check_url, headers={"User-Agent": "FindLeads/1.0"})
                response = urllib.request.urlopen(req, timeout=10)
                elapsed = (datetime.now() - start).total_seconds() * 1000

                if response.status == 200:
                    platform["status"] = "healthy"
                    platform["last_check"] = datetime.now().isoformat()
                    platform["last_success"] = datetime.now().isoformat()
                    platform["failures"] = 0
                    platform["response_time_ms"] = round(elapsed, 1)
                else:
                    platform["status"] = "degraded"
                    platform["last_check"] = datetime.now().isoformat()
                    platform["failures"] += 1
            except Exception as e:
                platform["status"] = "down"
                platform["last_check"] = datetime.now().isoformat()
                platform["failures"] += 1
                platform["response_time_ms"] = None
        else:
            # No URL to check — mark as reachable (manual check required)
            platform["status"] = "assumed_healthy"
            platform["last_check"] = datetime.now().isoformat()

        self._save_status()
        return platform.copy()

    def check_all(self) -> Dict:
        """Check health of all registered platforms."""
        results = {}
        for platform_id in self.platforms:
            results[platform_id] = self.check_platform(platform_id)
        return results

    def get_overall_health(self) -> Dict:
        """Get overall health summary."""
        total = len(self.platforms)
        healthy = sum(1 for p in self.platforms.values() if p["status"] == "healthy")
        degraded = sum(1 for p in self.platforms.values() if p["status"] == "degraded")
        down = sum(1 for p in self.platforms.values() if p["status"] == "down")
        unknown = total - healthy - degraded - down

        health_score = round(healthy / total * 100, 1) if total > 0 else 0

        return {
            "total_platforms": total,
            "healthy": healthy,
            "degraded": degraded,
            "down": down,
            "unknown": unknown,
            "health_score": health_score,
            "overall_status": "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "critical",
        }

    def get_platform_details(self) -> List[Dict]:
        """Get detailed status of each platform."""
        details = []
        for platform_id, platform in self.platforms.items():
            details.append({
                "id": platform_id,
                "name": platform["name"],
                "status": platform["status"],
                "last_check": platform["last_check"],
                "failures": platform["failures"],
                "response_time_ms": platform["response_time_ms"],
            })
        return details

    def get_alerts(self) -> List[Dict]:
        """Get alerts for unhealthy platforms."""
        alerts = []
        for platform_id, platform in self.platforms.items():
            if platform["status"] == "down":
                alerts.append({
                    "level": "critical",
                    "platform": platform["name"],
                    "message": f"{platform['name']} is DOWN",
                    "failures": platform["failures"],
                })
            elif platform["status"] == "degraded":
                alerts.append({
                    "level": "warning",
                    "platform": platform["name"],
                    "message": f"{platform['name']} is degraded",
                    "failures": platform["failures"],
                })
            elif platform["failures"] >= 3:
                alerts.append({
                    "level": "warning",
                    "platform": platform["name"],
                    "message": f"{platform['name']} has {platform['failures']} consecutive failures",
                })
        return alerts

    def reset_failures(self, platform_id: str):
        """Reset failure count for a platform."""
        if platform_id in self.platforms:
            self.platforms[platform_id]["failures"] = 0
            self.platforms[platform_id]["status"] = "healthy"
            self._save_status()


if __name__ == "__main__":
    test_status_path = os.path.join(os.path.dirname(__file__), "test_status.json")
    monitor = HealthMonitor(test_status_path)

    monitor.register_platform("github_actions", "GitHub Actions")
    monitor.register_platform("oracle_vm1", "Oracle VM 1 (Dubai)")
    monitor.register_platform("oracle_vm2", "Oracle VM 2 (Riyadh)")
    monitor.register_platform("oracle_vm3", "Oracle VM 3 (OSINT)")
    monitor.register_platform("oracle_vm4", "Oracle VM 4 (Scheduler)")
    monitor.register_platform("local", "Local Machine")

    # Check all
    results = monitor.check_all()
    for pid, r in results.items():
        print(f"  {r['name']}: {r['status']}")

    overall = monitor.get_overall_health()
    print(f"\nOverall health: {overall}")

    alerts = monitor.get_alerts()
    print(f"Alerts: {len(alerts)}")

    # Cleanup
    if os.path.exists(test_status_path):
        os.remove(test_status_path)
