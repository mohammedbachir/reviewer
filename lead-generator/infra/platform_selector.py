"""
#75 Platform Selector
Auto-select best platform based on current load and availability.
"""

import json
import os
from datetime import datetime
from typing import Dict, List


class PlatformSelector:
    """Automatically selects the best platform for a task."""

    PLATFORMS = {
        "github_actions": {
            "name": "GitHub Actions",
            "free_tier": 2000,
            "unit": "minutes/month",
            "speed": "medium",
            "reliability": "high",
            "ip_rotation": True,
            "best_for": ["google_maps_scraping", "contact_scraping", "email_validation"],
        },
        "oracle_vm1": {
            "name": "Oracle VM 1 (Dubai)",
            "free_tier": float("inf"),
            "unit": "always_free",
            "speed": "fast",
            "reliability": "high",
            "ip_rotation": False,
            "best_for": ["google_maps_scraping", "contact_scraping", "whois", "dns"],
        },
        "oracle_vm2": {
            "name": "Oracle VM 2 (Riyadh)",
            "free_tier": float("inf"),
            "unit": "always_free",
            "speed": "fast",
            "reliability": "high",
            "ip_rotation": False,
            "best_for": ["google_maps_scraping", "contact_scraping", "whois", "dns"],
        },
        "oracle_vm3": {
            "name": "Oracle VM 3 (OSINT)",
            "free_tier": float("inf"),
            "unit": "always_free",
            "speed": "fast",
            "reliability": "high",
            "ip_rotation": False,
            "best_for": ["whois", "dns", "ssl", "tech_stack", "sentiment"],
        },
        "oracle_vm4": {
            "name": "Oracle VM 4 (Scheduler)",
            "free_tier": float("inf"),
            "unit": "always_free",
            "speed": "fast",
            "reliability": "high",
            "ip_rotation": False,
            "best_for": ["task_distribution", "health_monitor", "data_merge", "reports"],
        },
        "local_machine": {
            "name": "Local Machine",
            "free_tier": float("inf"),
            "unit": "unlimited",
            "speed": "variable",
            "reliability": "medium",
            "ip_rotation": False,
            "best_for": ["monitoring", "reports", "manual_review", "debugging"],
        },
    }

    def __init__(self, usage_path: str = None):
        self.usage_path = usage_path or os.path.join(os.path.dirname(__file__), "platform_usage.json")
        self.usage: Dict[str, Dict] = {}
        self._load_usage()

    def _load_usage(self):
        """Load usage data from file."""
        if os.path.exists(self.usage_path):
            with open(self.usage_path, "r") as f:
                self.usage = json.load(f)

    def _save_usage(self):
        """Save usage data to file."""
        os.makedirs(os.path.dirname(self.usage_path) or ".", exist_ok=True)
        with open(self.usage_path, "w") as f:
            json.dump(self.usage, f, indent=2)

    def record_usage(self, platform_id: str, task: str, minutes: float):
        """Record platform usage."""
        if platform_id not in self.usage:
            self.usage[platform_id] = {"tasks": [], "total_minutes": 0}

        self.usage[platform_id]["tasks"].append({
            "task": task,
            "minutes": minutes,
            "timestamp": datetime.now().isoformat(),
        })
        self.usage[platform_id]["total_minutes"] += minutes
        self._save_usage()

    def select_platform(self, task: str, city: str = None) -> Dict:
        """Select the best platform for a given task."""
        candidates = []
        for platform_id, platform in self.PLATFORMS.items():
            if task in platform["best_for"]:
                score = self._calculate_score(platform_id, platform, task, city)
                candidates.append({
                    "platform_id": platform_id,
                    "name": platform["name"],
                    "score": score,
                    "speed": platform["speed"],
                    "reliability": platform["reliability"],
                })

        if not candidates:
            return {
                "selected": "local_machine",
                "name": "Local Machine",
                "reason": "No specific platform found for this task — using local as fallback",
            }

        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]

        return {
            "selected": best["platform_id"],
            "name": best["name"],
            "score": best["score"],
            "reason": self._get_selection_reason(best, task, city),
            "alternatives": [c["name"] for c in candidates[1:3]],
        }

    def _calculate_score(self, platform_id: str, platform: Dict, task: str, city: str) -> float:
        """Calculate a selection score for a platform."""
        score = 0.0

        # Speed bonus
        speed_scores = {"fast": 3, "medium": 2, "variable": 1}
        score += speed_scores.get(platform["speed"], 0)

        # Reliability bonus
        reliability_scores = {"high": 3, "medium": 2, "low": 1}
        score += reliability_scores.get(platform["reliability"], 0)

        # Free tier bonus (infinite = highest)
        if platform["free_tier"] == float("inf"):
            score += 5
        else:
            used = self.usage.get(platform_id, {}).get("total_minutes", 0)
            remaining = platform["free_tier"] - used
            if remaining > 500:
                score += 4
            elif remaining > 100:
                score += 2
            else:
                score -= 2

        # IP rotation bonus
        if platform.get("ip_rotation"):
            score += 2

        # City matching bonus
        if city and city.lower() in platform["name"].lower():
            score += 3

        # Current load penalty
        current_load = self.usage.get(platform_id, {}).get("total_minutes", 0)
        if current_load > 1500:
            score -= 3

        return round(score, 1)

    def _get_selection_reason(self, candidate: Dict, task: str, city: str) -> str:
        """Generate human-readable reason for selection."""
        reasons = []
        if candidate["speed"] == "fast":
            reasons.append("fast speed")
        if candidate["reliability"] == "high":
            reasons.append("high reliability")
        if city and city.lower() in candidate["name"].lower():
            reasons.append(f"matches city '{city}'")
        if not reasons:
            reasons.append("best available option")
        return f"Selected: {', '.join(reasons)}"

    def get_platform_rankings(self, task: str) -> List[Dict]:
        """Get all platforms ranked for a given task."""
        rankings = []
        for platform_id, platform in self.PLATFORMS.items():
            if task in platform["best_for"]:
                score = self._calculate_score(platform_id, platform, task, None)
                rankings.append({
                    "rank": 0,
                    "platform_id": platform_id,
                    "name": platform["name"],
                    "score": score,
                    "speed": platform["speed"],
                    "reliability": platform["reliability"],
                    "free_tier": platform["free_tier"],
                })

        rankings.sort(key=lambda x: x["score"], reverse=True)
        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        return rankings

    def get_usage_summary(self) -> Dict:
        """Get summary of platform usage."""
        summary = {}
        for platform_id, data in self.usage.items():
            summary[platform_id] = {
                "total_minutes": data.get("total_minutes", 0),
                "tasks_completed": len(data.get("tasks", [])),
                "last_task": data["tasks"][-1] if data.get("tasks") else None,
            }
        return summary

    def get_recommendations(self) -> List[Dict]:
        """Get platform usage recommendations."""
        recommendations = []

        for platform_id, platform in self.PLATFORMS.items():
            used = self.usage.get(platform_id, {}).get("total_minutes", 0)
            limit = platform["free_tier"]

            if limit == float("inf"):
                status = "unlimited"
            elif limit - used < 200:
                status = "running_low"
            elif used == 0:
                status = "unused"
            else:
                status = "healthy"

            if status == "running_low":
                recommendations.append({
                    "platform": platform["name"],
                    "issue": f"Running low on free tier ({used}/{limit} {platform['unit']})",
                    "action": "Consider shifting tasks to Oracle Cloud VMs (always free)",
                })
            elif status == "unused":
                recommendations.append({
                    "platform": platform["name"],
                    "issue": "Platform not being used",
                    "action": f"Assign tasks that match: {', '.join(platform['best_for'][:3])}",
                })

        return recommendations

    def get_overall_strategy(self) -> Dict:
        """Get the overall platform strategy."""
        return {
            "strategy": "Parallel execution across free platforms",
            "primary": "Oracle Cloud Free Tier (4 ARM VMs, always free)",
            "secondary": "GitHub Actions (2000 min/month, Microsoft Azure IPs)",
            "tertiary": "Google Cloud Run (2M requests/month)",
            "fallback": "Local Machine (unlimited)",
            "total_monthly_capacity": "41,400+ businesses",
            "total_cost": "$0",
        }


if __name__ == "__main__":
    test_usage_path = os.path.join(os.path.dirname(__file__), "test_platform_usage.json")
    ps = PlatformSelector(test_usage_path)

    # Select platform for different tasks
    tasks = ["google_maps_scraping", "whois", "data_merge", "reports"]
    for task in tasks:
        result = ps.select_platform(task, "dubai")
        print(f"  {task}: {result['selected']} ({result['name']})")
        print(f"    Reason: {result['reason']}")

    # Get rankings for scraping
    rankings = ps.get_platform_rankings("google_maps_scraping")
    print(f"\nRankings for google_maps_scraping:")
    for r in rankings:
        print(f"  #{r['rank']} {r['name']}: {r['score']} points")

    # Get recommendations
    recs = ps.get_recommendations()
    print(f"\nRecommendations: {len(recs)}")
    for r in recs:
        print(f"  {r['platform']}: {r['action']}")

    # Overall strategy
    strategy = ps.get_overall_strategy()
    print(f"\nOverall strategy:")
    print(f"  Primary: {strategy['primary']}")
    print(f"  Secondary: {strategy['secondary']}")
    print(f"  Total capacity: {strategy['total_monthly_capacity']}")
    print(f"  Cost: {strategy['total_cost']}")

    # Cleanup
    if os.path.exists(test_usage_path):
        os.remove(test_usage_path)
