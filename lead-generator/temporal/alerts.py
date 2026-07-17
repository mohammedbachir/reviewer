"""
#25 Alert Generation
Auto-generates alerts for critical changes.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional


class AlertGenerator:
    """Generates alerts for critical business changes."""

    ALERT_RULES = {
        "rating_drop": {"threshold": 0.3, "severity": "high", "message": "Rating dropped by {diff}"},
        "health_decline": {"threshold": 10, "severity": "high", "message": "Health score dropped by {diff} points"},
        "domain_expiring": {"threshold": 30, "severity": "critical", "message": "Domain expires in {days} days"},
        "sentiment_drop": {"threshold": 0.3, "severity": "medium", "message": "Sentiment declined by {diff}"},
        "review_decrease": {"threshold": 5, "severity": "high", "message": "Review count decreased by {count}"},
        "no_replies": {"threshold": 90, "severity": "high", "message": "No replies for {days} days"},
        "critical_health": {"threshold": 30, "severity": "critical", "message": "Health score is critically low ({score}/100)"},
        "ssl_expired": {"severity": "critical", "message": "SSL certificate has expired or is invalid"},
    }

    def __init__(self, db):
        self.db = db

    def generate_alerts(self, business_id: str, changes: List[Dict]) -> List[Dict]:
        """Generate alerts based on detected changes."""
        alerts = []
        node = self._get_business(business_id)
        if not node:
            return alerts

        props = node.get("properties", {})

        for change in changes:
            alerts.extend(self._check_rating_alert(change, props))
            alerts.extend(self._check_health_alert(change, props))
            alerts.extend(self._check_domain_alert(change, props))
            alerts.extend(self._check_sentiment_alert(change, props))
            alerts.extend(self._check_review_alert(change, props))

        alerts.extend(self._check_static_alerts(props))

        for alert in alerts:
            alert["business_id"] = business_id
            alert["business_name"] = node.get("name", "")
            alert["generated_at"] = datetime.now().isoformat()

        seen = set()
        unique_alerts = []
        for alert in alerts:
            key = (alert.get("alert_type"), alert.get("message"))
            if key not in seen:
                seen.add(key)
                unique_alerts.append(alert)

        return unique_alerts

    def _get_business(self, business_id: str) -> Dict:
        """Get business node data."""
        row = self.db.fetchone(
            "SELECT name, properties FROM nodes WHERE id = ?",
            (business_id,),
        )
        if row:
            row["properties"] = json.loads(row.get("properties", "{}"))
        return row or {}

    def _check_rating_alert(self, change: Dict, props: Dict) -> List[Dict]:
        """Check for rating-related alerts."""
        if change.get("type") != "rating_change":
            return []

        diff = abs(float(change.get("diff", "0") or "0"))
        rule = self.ALERT_RULES["rating_drop"]

        if diff >= rule["threshold"]:
            return [{
                "alert_type": "rating_drop",
                "severity": rule["severity"],
                "message": rule["message"].format(diff=round(diff, 2)),
                "old_value": change.get("old_value", ""),
                "new_value": change.get("new_value", ""),
            }]
        return []

    def _check_health_alert(self, change: Dict, props: Dict) -> List[Dict]:
        """Check for health-related alerts."""
        if change.get("type") != "health_change":
            return []

        diff = abs(float(change.get("diff", "0") or "0"))
        rule = self.ALERT_RULES["health_decline"]

        if diff >= rule["threshold"]:
            return [{
                "alert_type": "health_decline",
                "severity": rule["severity"],
                "message": rule["message"].format(diff=round(diff, 1)),
                "old_value": change.get("old_value", ""),
                "new_value": change.get("new_value", ""),
            }]
        return []

    def _check_domain_alert(self, change: Dict, props: Dict) -> List[Dict]:
        """Check for domain expiry alerts."""
        if change.get("type") == "domain_expiring":
            days = int(change.get("new_value", "0") or "0")
            rule = self.ALERT_RULES["domain_expiring"]
            return [{
                "alert_type": "domain_expiring",
                "severity": rule["severity"],
                "message": rule["message"].format(days=days),
                "old_value": change.get("old_value", ""),
                "new_value": change.get("new_value", ""),
            }]

        days = int(props.get("days_until_expiry", 0) or 0)
        if 0 < days <= 30:
            rule = self.ALERT_RULES["domain_expiring"]
            return [{
                "alert_type": "domain_expiring",
                "severity": rule["severity"],
                "message": rule["message"].format(days=days),
                "old_value": "-", "new_value": str(days),
            }]
        return []

    def _check_sentiment_alert(self, change: Dict, props: Dict) -> List[Dict]:
        """Check for sentiment-related alerts."""
        if change.get("type") != "sentiment_change":
            return []

        diff = abs(float(change.get("diff", "0") or "0"))
        rule = self.ALERT_RULES["sentiment_drop"]

        if diff >= rule["threshold"]:
            return [{
                "alert_type": "sentiment_drop",
                "severity": rule["severity"],
                "message": rule["message"].format(diff=round(diff, 2)),
                "old_value": change.get("old_value", ""),
                "new_value": change.get("new_value", ""),
            }]
        return []

    def _check_review_alert(self, change: Dict, props: Dict) -> List[Dict]:
        """Check for review count alerts."""
        if change.get("type") != "review_count_change":
            return []

        diff = abs(int(change.get("diff", "0") or "0"))
        rule = self.ALERT_RULES["review_decrease"]

        if change.get("direction") == "decreased" and diff >= rule["threshold"]:
            return [{
                "alert_type": "review_decrease",
                "severity": rule["severity"],
                "message": rule["message"].format(count=diff),
                "old_value": change.get("old_value", ""),
                "new_value": change.get("new_value", ""),
            }]
        return []

    def _check_static_alerts(self, props: Dict) -> List[Dict]:
        """Check for static condition alerts (not change-based)."""
        alerts = []

        health = float(props.get("health_score", 0) or 0)
        if 0 < health <= 30:
            rule = self.ALERT_RULES["critical_health"]
            alerts.append({
                "alert_type": "critical_health",
                "severity": rule["severity"],
                "message": rule["message"].format(score=round(health)),
                "old_value": "-", "new_value": str(round(health)),
            })

        ssl_valid = props.get("ssl_valid", True)
        if ssl_valid is False:
            rule = self.ALERT_RULES["ssl_expired"]
            alerts.append({
                "alert_type": "ssl_expired",
                "severity": rule["severity"],
                "message": rule["message"],
                "old_value": "-", "new_value": "invalid",
            })

        return alerts

    def get_all_alerts(self, business_id: Optional[str] = None) -> List[Dict]:
        """Get all generated alerts."""
        if business_id:
            return self.db.fetchall(
                "SELECT * FROM changes WHERE node_id = ? AND severity IN ('high', 'critical') ORDER BY scan_date DESC",
                (business_id,),
            )
        return self.db.fetchall(
            "SELECT * FROM changes WHERE severity IN ('high', 'critical') ORDER BY scan_date DESC",
        )

    def alert_summary(self) -> Dict:
        """Get summary of all alerts by severity."""
        rows = self.db.fetchall(
            "SELECT severity, COUNT(*) as cnt FROM changes WHERE severity IN ('high', 'critical') GROUP BY severity"
        )
        summary = {row["severity"]: row["cnt"] for row in rows}
        summary["total"] = sum(summary.values())
        return summary


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        db.execute(
            "INSERT INTO nodes (id, type, name, properties) VALUES (?, ?, ?, ?)",
            ("biz1", "business", "Bloom", json.dumps({"health_score": 25, "days_until_expiry": 15, "ssl_valid": True})),
        )

        ag = AlertGenerator(db)
        changes = [
            {"type": "rating_change", "old_value": "4.5", "new_value": "3.8", "diff": "0.7"},
            {"type": "health_change", "old_value": "80", "new_value": "25", "diff": "55"},
            {"type": "domain_expiring", "old_value": "60", "new_value": "15", "diff": "45"},
        ]

        alerts = ag.generate_alerts("biz1", changes)
        print(f"Alerts generated: {len(alerts)}")
        for a in alerts:
            print(f"  [{a['severity'].upper()}] {a['alert_type']}: {a['message']}")
