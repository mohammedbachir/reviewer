"""
#60 IP Rotation Tracking
Track which IPs were used, avoid repeating.
"""

import json
import os
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional


class IPTracker:
    """Tracks IP addresses used during scraping."""

    def __init__(self, tracker_path: str = None):
        self.tracker_path = tracker_path or os.path.join(os.path.dirname(__file__), "..", "ip_history.json")
        self.history: List[Dict] = []
        self.current_ip: Optional[str] = None
        self._load()

    def _load(self):
        """Load IP history from file."""
        if os.path.exists(self.tracker_path):
            with open(self.tracker_path, "r") as f:
                self.history = json.load(f)

    def _save(self):
        """Save IP history to file."""
        os.makedirs(os.path.dirname(self.tracker_path) or ".", exist_ok=True)
        with open(self.tracker_path, "w") as f:
            json.dump(self.history, f, indent=2)

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

    def record_ip(self, ip: str = None, source: str = "direct"):
        """Record an IP address usage."""
        if ip is None:
            ip = self.get_current_ip()
        if not ip:
            return

        entry = {
            "ip": ip,
            "source": source,
            "timestamp": datetime.now().isoformat(),
        }
        self.history.append(entry)
        self.current_ip = ip
        self._save()

    def was_used(self, ip: str) -> bool:
        """Check if an IP was already used."""
        return any(h["ip"] == ip for h in self.history)

    def get_unique_ips(self) -> List[str]:
        """Get list of unique IPs used."""
        return list(set(h["ip"] for h in self.history))

    def get_usage_count(self, ip: str) -> int:
        """Get how many times an IP was used."""
        return sum(1 for h in self.history if h["ip"] == ip)

    def get_stats(self) -> Dict:
        """Get IP tracking statistics."""
        unique_ips = self.get_unique_ips()
        sources = {}
        for h in self.history:
            src = h.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        return {
            "total_records": len(self.history),
            "unique_ips": len(unique_ips),
            "current_ip": self.current_ip,
            "sources": sources,
        }

    def clear_history(self):
        """Clear IP history."""
        self.history = []
        self._save()


if __name__ == "__main__":
    tracker = IPTracker()
    tracker.record_ip("192.168.1.1", "github_actions")
    tracker.record_ip("10.0.0.1", "oracle_cloud")
    tracker.record_ip("172.16.0.1", "local")

    print(f"Stats: {tracker.get_stats()}")
    print(f"Unique IPs: {tracker.get_unique_ips()}")
    print(f"Used 192.168.1.1: {tracker.was_used('192.168.1.1')}")
    print(f"Used 99.99.99.99: {tracker.was_used('99.99.99.99')}")
