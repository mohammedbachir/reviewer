"""
#70 IP Pool Manager
Manage IP addresses from all platforms (Microsoft, Oracle, Google, Local) - avoid repeats.
"""

import json
import os
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional


class IPPool:
    """Manages IP addresses from multiple platforms."""

    def __init__(self, pool_path: str = None):
        self.pool_path = pool_path or os.path.join(os.path.dirname(__file__), "ip_pool.json")
        self.platforms: Dict[str, List[Dict]] = {}
        self.current_ip: Optional[str] = None
        self._load_pool()

    def _load_pool(self):
        """Load IP pool from file."""
        if os.path.exists(self.pool_path):
            with open(self.pool_path, "r") as f:
                data = json.load(f)
                self.platforms = data.get("platforms", {})
                self.current_ip = data.get("current_ip")

    def _save_pool(self):
        """Save IP pool to file."""
        os.makedirs(os.path.dirname(self.pool_path) or ".", exist_ok=True)
        with open(self.pool_path, "w") as f:
            json.dump({
                "platforms": self.platforms,
                "current_ip": self.current_ip,
                "last_updated": datetime.now().isoformat(),
            }, f, indent=2)

    def register_platform(self, platform_id: str, ip: str, source: str = "direct"):
        """Register an IP address for a platform."""
        if platform_id not in self.platforms:
            self.platforms[platform_id] = []

        entry = {
            "ip": ip,
            "source": source,
            "registered_at": datetime.now().isoformat(),
            "usage_count": 0,
            "last_used": None,
        }
        self.platforms[platform_id].append(entry)
        self._save_pool()

    def get_next_ip(self, platform_id: str) -> Optional[str]:
        """Get next available IP for a platform (round-robin)."""
        if platform_id not in self.platforms or not self.platforms[platform_id]:
            return None

        entries = self.platforms[platform_id]
        # Sort by usage count ascending
        entries.sort(key=lambda x: x["usage_count"])

        # Return least-used IP
        next_entry = entries[0]
        next_entry["usage_count"] += 1
        next_entry["last_used"] = datetime.now().isoformat()
        self.current_ip = next_entry["ip"]
        self._save_pool()
        return next_entry["ip"]

    def is_ip_used(self, ip: str) -> bool:
        """Check if an IP was already used by any platform."""
        for platform_entries in self.platforms.values():
            for entry in platform_entries:
                if entry["ip"] == ip:
                    return True
        return False

    def get_all_ips(self) -> Dict[str, List[str]]:
        """Get all IPs organized by platform."""
        result = {}
        for platform_id, entries in self.platforms.items():
            result[platform_id] = [e["ip"] for e in entries]
        return result

    def get_unique_ips(self) -> List[str]:
        """Get all unique IPs across all platforms."""
        all_ips = set()
        for entries in self.platforms.values():
            for entry in entries:
                all_ips.add(entry["ip"])
        return sorted(list(all_ips))

    def get_stats(self) -> Dict:
        """Get IP pool statistics."""
        total_ips = 0
        platform_stats = {}
        for platform_id, entries in self.platforms.items():
            total_ips += len(entries)
            avg_usage = sum(e["usage_count"] for e in entries) / len(entries) if entries else 0
            platform_stats[platform_id] = {
                "count": len(entries),
                "avg_usage": round(avg_usage, 1),
                "ips": [e["ip"] for e in entries],
            }

        return {
            "total_ips": total_ips,
            "unique_ips": len(self.get_unique_ips()),
            "platforms": platform_stats,
            "current_ip": self.current_ip,
        }

    def remove_platform(self, platform_id: str):
        """Remove a platform and all its IPs."""
        if platform_id in self.platforms:
            del self.platforms[platform_id]
            self._save_pool()

    def clear_pool(self):
        """Clear the entire IP pool."""
        self.platforms = {}
        self.current_ip = None
        self._save_pool()

    def get_current_ip(self) -> Optional[str]:
        """Get the current public IP address."""
        try:
            req = urllib.request.Request("https://api.ipify.org?format=json", headers={"User-Agent": "Mozilla/5.0"})
            response = urllib.request.urlopen(req, timeout=5)
            data = json.loads(response.read().decode())
            self.current_ip = data.get("ip")
            return self.current_ip
        except Exception:
            return None

    def get_platform_recommendations(self) -> Dict:
        """Get recommendations for which platform to use next."""
        platform_load = {}
        for platform_id, entries in self.platforms.items():
            total_usage = sum(e["usage_count"] for e in entries)
            platform_load[platform_id] = total_usage

        if not platform_load:
            return {"recommendation": "No platforms registered", "next_action": "Register platforms first"}

        # Find platform with lowest load
        min_platform = min(platform_load, key=platform_load.get)
        return {
            "recommendation": f"Use {min_platform}",
            "reason": f"Lowest load ({platform_load[min_platform]} total uses)",
            "platform_loads": platform_load,
        }


if __name__ == "__main__":
    test_pool_path = os.path.join(os.path.dirname(__file__), "test_ip_pool.json")
    pool = IPPool(test_pool_path)

    # Register test IPs
    pool.register_platform("github_actions", "13.64.0.1", "microsoft_azure")
    pool.register_platform("github_actions", "13.64.0.2", "microsoft_azure")
    pool.register_platform("oracle_vm1", "129.146.0.1", "oracle_cloud")
    pool.register_platform("oracle_vm2", "129.146.0.2", "oracle_cloud")
    pool.register_platform("local", "99.99.99.99", "local_isp")

    stats = pool.get_stats()
    print(f"Pool stats: {stats}")

    # Get next IPs
    for _ in range(5):
        ip = pool.get_next_ip("github_actions")
        print(f"  GitHub Actions next IP: {ip}")

    rec = pool.get_platform_recommendations()
    print(f"Recommendation: {rec}")

    # Cleanup
    if os.path.exists(test_pool_path):
        os.remove(test_pool_path)
