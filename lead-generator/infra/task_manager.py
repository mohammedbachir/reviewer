"""
#69 Task Distribution Manager
Distribute scraping tasks across platforms (which platform does what).
"""

import json
import os
from datetime import datetime
from typing import Dict, List


class TaskDistributor:
    """Distributes tasks across multiple platforms."""

    PLATFORMS = {
        "github_actions": {
            "name": "GitHub Actions",
            "free_tier": "2000 min/month",
            "capabilities": ["google_maps_scraping", "contact_scraping", "email_validation"],
            "speed": "medium",
            "cost_per_hour": 0,
            "max_concurrent": 1,
        },
        "oracle_vm1": {
            "name": "Oracle VM 1 (Dubai)",
            "free_tier": "Always Free",
            "capabilities": ["google_maps_scraping", "contact_scraping", "osint", "whois"],
            "speed": "fast",
            "cost_per_hour": 0,
            "max_concurrent": 2,
        },
        "oracle_vm2": {
            "name": "Oracle VM 2 (Riyadh)",
            "free_tier": "Always Free",
            "capabilities": ["google_maps_scraping", "contact_scraping", "osint", "whois"],
            "speed": "fast",
            "cost_per_hour": 0,
            "max_concurrent": 2,
        },
        "oracle_vm3": {
            "name": "Oracle VM 3 (OSINT)",
            "free_tier": "Always Free",
            "capabilities": ["whois", "dns", "ssl", "tech_stack", "sentiment"],
            "speed": "fast",
            "cost_per_hour": 0,
            "max_concurrent": 4,
        },
        "oracle_vm4": {
            "name": "Oracle VM 4 (Scheduler)",
            "free_tier": "Always Free",
            "capabilities": ["task_distribution", "health_monitor", "data_merge", "reports"],
            "speed": "fast",
            "cost_per_hour": 0,
            "max_concurrent": 1,
        },
        "local_machine": {
            "name": "Local Machine",
            "free_tier": "Unlimited",
            "capabilities": ["monitoring", "reports", "manual_review", "debugging"],
            "speed": "variable",
            "cost_per_hour": 0,
            "max_concurrent": 1,
        },
    }

    TASK_TYPES = {
        "google_maps_scraping": {"priority": 1, "estimated_minutes": 10, "output": "businesses"},
        "contact_scraping": {"priority": 2, "estimated_minutes": 5, "output": "emails"},
        "email_validation": {"priority": 3, "estimated_minutes": 2, "output": "validated_emails"},
        "whois": {"priority": 4, "estimated_minutes": 1, "output": "domain_info"},
        "dns": {"priority": 5, "estimated_minutes": 1, "output": "dns_records"},
        "ssl": {"priority": 6, "estimated_minutes": 1, "output": "ssl_info"},
        "tech_stack": {"priority": 7, "estimated_minutes": 2, "output": "tech_info"},
        "sentiment": {"priority": 8, "estimated_minutes": 3, "output": "sentiment_scores"},
        "task_distribution": {"priority": 9, "estimated_minutes": 1, "output": "task_assignments"},
        "health_monitor": {"priority": 10, "estimated_minutes": 1, "output": "health_status"},
        "data_merge": {"priority": 11, "estimated_minutes": 5, "output": "merged_data"},
        "reports": {"priority": 12, "estimated_minutes": 3, "output": "reports"},
    }

    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "task_config.json")
        self.assignments: List[Dict] = []

    def get_platforms(self) -> Dict:
        """Get all available platforms."""
        return self.PLATFORMS.copy()

    def get_task_types(self) -> Dict:
        """Get all task types."""
        return self.TASK_TYPES.copy()

    def assign_tasks(self, city: str = "dubai", sector: str = "beauty salons") -> List[Dict]:
        """Assign tasks to platforms based on capabilities."""
        assignments = []

        # Scraping tasks
        assignments.append({
            "task": "google_maps_scraping",
            "platform": "oracle_vm1",
            "city": city,
            "sector": sector,
            "estimated_minutes": 10,
            "priority": 1,
        })
        assignments.append({
            "task": "google_maps_scraping",
            "platform": "oracle_vm2",
            "city": "riyadh",
            "sector": sector,
            "estimated_minutes": 10,
            "priority": 1,
        })

        # Contact scraping
        assignments.append({
            "task": "contact_scraping",
            "platform": "github_actions",
            "city": city,
            "sector": sector,
            "estimated_minutes": 5,
            "priority": 2,
        })

        # OSINT tasks
        for task_name in ["whois", "dns", "ssl", "tech_stack", "sentiment"]:
            assignments.append({
                "task": task_name,
                "platform": "oracle_vm3",
                "city": "all",
                "sector": sector,
                "estimated_minutes": self.TASK_TYPES[task_name]["estimated_minutes"],
                "priority": self.TASK_TYPES[task_name]["priority"],
            })

        # Scheduler
        assignments.append({
            "task": "data_merge",
            "platform": "oracle_vm4",
            "city": "all",
            "sector": sector,
            "estimated_minutes": 5,
            "priority": 11,
        })

        self.assignments = assignments
        return assignments

    def get_platform_summary(self) -> Dict:
        """Get summary of platform utilization."""
        summary = {}
        for platform_id, platform in self.PLATFORMS.items():
            tasks_for_platform = [a for a in self.assignments if a["platform"] == platform_id]
            total_minutes = sum(a["estimated_minutes"] for a in tasks_for_platform)
            summary[platform_id] = {
                "name": platform["name"],
                "tasks_assigned": len(tasks_for_platform),
                "total_minutes": total_minutes,
                "utilization": f"{round(total_minutes / 60 * 100, 1)}%",
            }
        return summary

    def estimate_daily_capacity(self) -> Dict:
        """Estimate daily data collection capacity across all platforms.

        Note: Platforms run IN PARALLEL, not serially.
        - GitHub Actions: ~67 min/day (2000 min/month)
        - 4 Oracle VMs: 24/7 with multi-core parallelism
        """
        github_minutes = 2000 / 30  # ~66.7 min/day
        # Each Oracle VM can run 4 concurrent tasks (4 ARM cores each)
        # Effective parallel minutes per VM per day = 24h * 60min * 4 cores
        oracle_parallel_minutes = 24 * 60 * 4 * 4  # 4 VMs * 4 cores
        total_effective_minutes = github_minutes + oracle_parallel_minutes
        # Average ~4 min per business when running in parallel across all cores
        avg_minutes_per_business = 4.2
        businesses_per_day = int(total_effective_minutes / avg_minutes_per_business)
        return {
            "github_actions_minutes_per_day": round(github_minutes, 1),
            "oracle_vm_minutes_per_day": oracle_parallel_minutes,
            "total_minutes_per_day": round(total_effective_minutes, 1),
            "avg_minutes_per_business": avg_minutes_per_business,
            "estimated_businesses_per_day": businesses_per_day,
            "estimated_businesses_per_month": businesses_per_day * 30,
        }

    def save_assignments(self):
        """Save task assignments to file."""
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump({
                "assignments": self.assignments,
                "timestamp": datetime.now().isoformat(),
            }, f, indent=2)

    def load_assignments(self) -> List[Dict]:
        """Load task assignments from file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                data = json.load(f)
                self.assignments = data.get("assignments", [])
                return self.assignments
        return []


if __name__ == "__main__":
    td = TaskDistributor()
    assignments = td.assign_tasks("dubai", "beauty salons")
    print(f"Assigned {len(assignments)} tasks")
    for a in assignments:
        print(f"  {a['task']} -> {a['platform']} ({a['estimated_minutes']} min)")

    summary = td.get_platform_summary()
    print(f"\nPlatform summary:")
    for pid, s in summary.items():
        print(f"  {s['name']}: {s['tasks_assigned']} tasks, {s['total_minutes']} min ({s['utilization']})")

    capacity = td.estimate_daily_capacity()
    print(f"\nDaily capacity: {capacity['estimated_businesses_per_day']} businesses")
    print(f"Monthly capacity: {capacity['estimated_businesses_per_month']} businesses")
