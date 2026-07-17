"""
#23 Change Severity Scoring
Classifies changes as low/medium/high/critical based on impact.
"""

from typing import Dict, List


class SeverityScorer:
    """Assigns severity scores to detected changes."""

    SEVERITY_WEIGHTS = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
        "info": 0,
    }

    def __init__(self, db=None):
        self.db = db

    def score_changes(self, changes: List[Dict]) -> List[Dict]:
        """Add severity scores to a list of changes."""
        scored = []
        for change in changes:
            scored_change = dict(change)
            scored_change["severity"] = self._determine_severity(change)
            scored_change["severity_score"] = self.SEVERITY_WEIGHTS.get(scored_change["severity"], 0)
            scored.append(scored_change)
        return scored

    def _determine_severity(self, change: Dict) -> str:
        """Determine severity based on change type and magnitude."""
        change_type = change.get("type", "")
        direction = change.get("direction", "")
        diff = abs(float(change.get("diff", "0") or "0"))

        if change_type == "first_scan":
            return "info"
        if change_type == "no_change":
            return "info"

        if change_type == "domain_expiring":
            return "critical"

        if change_type == "rating_change":
            if diff >= 0.5:
                return "high"
            if diff >= 0.2:
                return "medium"
            return "low"

        if change_type == "health_change":
            if diff >= 20:
                return "critical"
            if diff >= 10:
                return "high"
            if diff >= 5:
                return "medium"
            return "low"

        if change_type == "sentiment_change":
            if diff >= 0.5:
                return "high"
            if diff >= 0.3:
                return "medium"
            return "low"

        if change_type == "review_count_change":
            if direction == "decreased":
                return "high"
            if diff >= 20:
                return "medium"
            return "low"

        if change_type in ("tech_added", "tech_removed"):
            return "medium"

        if change_type in ("email_added", "email_removed"):
            return "low"

        if change_type == "ssl_change":
            return "medium"

        if change_type == "activity_change":
            if direction == "decreased":
                return "high"
            return "low"

        return "low"

    def overall_severity(self, changes: List[Dict]) -> Dict:
        """Calculate overall severity for a set of changes."""
        if not changes:
            return {"level": "info", "score": 0, "message": "No changes"}

        total_score = 0
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        for change in changes:
            sev = change.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            total_score += self.SEVERITY_WEIGHTS.get(sev, 0)

        if severity_counts["critical"] > 0:
            level = "critical"
            message = f"{severity_counts['critical']} critical changes detected"
        elif severity_counts["high"] >= 2:
            level = "critical"
            message = f"{severity_counts['high']} high-severity changes"
        elif severity_counts["high"] > 0:
            level = "high"
            message = f"{severity_counts['high']} high-severity changes"
        elif severity_counts["medium"] > 0:
            level = "medium"
            message = f"{severity_counts['medium']} medium changes"
        elif severity_counts["low"] > 0:
            level = "low"
            message = f"{severity_counts['low']} minor changes"
        else:
            level = "info"
            message = "No significant changes"

        return {
            "level": level,
            "score": total_score,
            "counts": severity_counts,
            "message": message,
        }

    def prioritize_changes(self, changes: List[Dict]) -> List[Dict]:
        """Sort changes by severity (highest first)."""
        scored = self.score_changes(changes)
        return sorted(scored, key=lambda x: x.get("severity_score", 0), reverse=True)


if __name__ == "__main__":
    ss = SeverityScorer()

    changes = [
        {"type": "rating_change", "old_value": "4.5", "new_value": "3.8", "diff": "0.7"},
        {"type": "health_change", "old_value": "80", "new_value": "45", "diff": "35"},
        {"type": "tech_removed", "old_value": "jQuery", "new_value": ""},
        {"type": "domain_expiring", "old_value": "60", "new_value": "5", "diff": "55"},
    ]

    scored = ss.score_changes(changes)
    for s in scored:
        print(f"  {s['type']}: {s['severity']} (score: {s['severity_score']})")

    overall = ss.overall_severity(scored)
    print(f"\nOverall: {overall['level']} — {overall['message']}")
    print(f"Counts: {overall['counts']}")
