"""
#22 Change Detection
Compares current vs previous snapshot and detects all types of changes.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any


class ChangeDetector:
    """Detects changes between consecutive snapshots."""

    def __init__(self, db):
        self.db = db

    def detect_all_changes(self, business_id: str) -> List[Dict]:
        """Compare latest vs previous snapshot and return all changes."""
        latest = self._get_snapshot(business_id, "latest")
        previous = self._get_snapshot(business_id, "previous")

        if not latest:
            return []
        if not previous:
            return [{"type": "first_scan", "field": "all", "severity": "info",
                     "message": "First scan — no previous data to compare"}]

        old = previous["data"]
        new = latest["data"]
        changes = []

        changes.extend(self._compare_rating(old, new))
        changes.extend(self._compare_review_count(old, new))
        changes.extend(self._compare_health_score(old, new))
        changes.extend(self._compare_sentiment(old, new))
        changes.extend(self._compare_technologies(old, new))
        changes.extend(self._compare_emails(old, new))
        changes.extend(self._compare_ssl(old, new))
        changes.extend(self._compare_domain_expiry(old, new))
        changes.extend(self._compare_activity(old, new))

        return changes if changes else [{
            "type": "no_change", "field": "all", "severity": "info",
            "old_value": "-", "new_value": "-",
            "message": "No significant changes detected",
        }]

    def _get_snapshot(self, business_id: str, which: str) -> Optional[Dict]:
        """Get latest or previous snapshot."""
        if which == "latest":
            row = self.db.fetchone(
                "SELECT * FROM snapshots WHERE node_id = ? ORDER BY scan_date DESC LIMIT 1",
                (business_id,),
            )
        else:
            row = self.db.fetchone(
                """SELECT * FROM snapshots WHERE node_id = ? 
                   AND scan_date < (SELECT MAX(scan_date) FROM snapshots WHERE node_id = ?)
                   ORDER BY scan_date DESC LIMIT 1""",
                (business_id, business_id),
            )
        if row:
            row["data"] = json.loads(row.get("data", "{}"))
            if hasattr(row.get("scan_date"), "isoformat"):
                row["scan_date"] = row["scan_date"].isoformat()
        return row

    def _compare_rating(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare rating changes."""
        old_r = float(old.get("rating", 0) or 0)
        new_r = float(new.get("rating", 0) or 0)
        if old_r == 0 and new_r == 0:
            return []
        diff = new_r - old_r
        if abs(diff) < 0.05:
            return []
        direction = "increased" if diff > 0 else "decreased"
        return [{
            "type": "rating_change", "field": "rating",
            "old_value": str(round(old_r, 2)), "new_value": str(round(new_r, 2)),
            "diff": str(round(diff, 2)), "direction": direction,
        }]

    def _compare_review_count(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare review count changes."""
        old_c = int(old.get("review_count", 0) or 0)
        new_c = int(new.get("review_count", 0) or 0)
        diff = new_c - old_c
        if diff == 0:
            return []
        direction = "increased" if diff > 0 else "decreased"
        return [{
            "type": "review_count_change", "field": "review_count",
            "old_value": str(old_c), "new_value": str(new_c),
            "diff": str(diff), "direction": direction,
        }]

    def _compare_health_score(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare health score changes."""
        old_h = float(old.get("health_score", 0) or 0)
        new_h = float(new.get("health_score", 0) or 0)
        if old_h == 0 and new_h == 0:
            return []
        diff = new_h - old_h
        if abs(diff) < 1:
            return []
        direction = "improved" if diff > 0 else "declined"
        return [{
            "type": "health_change", "field": "health_score",
            "old_value": str(round(old_h, 1)), "new_value": str(round(new_h, 1)),
            "diff": str(round(diff, 1)), "direction": direction,
        }]

    def _compare_sentiment(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare sentiment changes."""
        old_s = float(old.get("sentiment_avg", 0) or 0)
        new_s = float(new.get("sentiment_avg", 0) or 0)
        if old_s == 0 and new_s == 0:
            return []
        diff = new_s - old_s
        if abs(diff) < 0.1:
            return []
        direction = "improved" if diff > 0 else "declined"
        return [{
            "type": "sentiment_change", "field": "sentiment_avg",
            "old_value": str(round(old_s, 2)), "new_value": str(round(new_s, 2)),
            "diff": str(round(diff, 2)), "direction": direction,
        }]

    def _compare_technologies(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare technology stack changes."""
        old_techs = set(old.get("technologies", []))
        new_techs = set(new.get("technologies", []))
        added = new_techs - old_techs
        removed = old_techs - new_techs
        changes = []
        if added:
            changes.append({
                "type": "tech_added", "field": "technologies",
                "old_value": "", "new_value": ", ".join(sorted(added)),
                "diff": str(len(added)), "direction": "added",
            })
        if removed:
            changes.append({
                "type": "tech_removed", "field": "technologies",
                "old_value": ", ".join(sorted(removed)), "new_value": "",
                "diff": str(len(removed)), "direction": "removed",
            })
        return changes

    def _compare_emails(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare email changes."""
        old_emails = set(old.get("emails", []))
        new_emails = set(new.get("emails", []))
        added = new_emails - old_emails
        removed = old_emails - new_emails
        changes = []
        if added:
            changes.append({
                "type": "email_added", "field": "emails",
                "old_value": "", "new_value": ", ".join(sorted(added)),
                "diff": str(len(added)), "direction": "added",
            })
        if removed:
            changes.append({
                "type": "email_removed", "field": "emails",
                "old_value": ", ".join(sorted(removed)), "new_value": "",
                "diff": str(len(removed)), "direction": "removed",
            })
        return changes

    def _compare_ssl(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare SSL grade changes."""
        old_ssl = old.get("ssl_grade", "")
        new_ssl = new.get("ssl_grade", "")
        if not old_ssl or not new_ssl or old_ssl == new_ssl:
            return []
        return [{
            "type": "ssl_change", "field": "ssl_grade",
            "old_value": old_ssl, "new_value": new_ssl,
            "diff": f"{old_ssl} -> {new_ssl}", "direction": "changed",
        }]

    def _compare_domain_expiry(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare domain expiry changes."""
        old_exp = int(old.get("days_until_expiry", 0) or 0)
        new_exp = int(new.get("days_until_expiry", 0) or 0)
        if old_exp == 0 and new_exp == 0:
            return []
        if new_exp <= 30 and old_exp > 30:
            return [{
                "type": "domain_expiring", "field": "days_until_expiry",
                "old_value": str(old_exp), "new_value": str(new_exp),
                "diff": str(new_exp - old_exp), "direction": "critical",
            }]
        return []

    def _compare_activity(self, old: Dict, new: Dict) -> List[Dict]:
        """Compare activity level changes (response rate)."""
        old_resp = float(old.get("response_rate", 0) or 0)
        new_resp = float(new.get("response_rate", 0) or 0)
        diff = new_resp - old_resp
        if abs(diff) < 1:
            return []
        direction = "increased" if diff > 0 else "decreased"
        return [{
            "type": "activity_change", "field": "response_rate",
            "old_value": str(round(old_resp, 1)), "new_value": str(round(new_resp, 1)),
            "diff": str(round(diff, 1)), "direction": direction,
        }]

    def record_changes(self, business_id: str, scan_date: str, changes: List[Dict]):
        """Record detected changes in the changes table."""
        for change in changes:
            if change.get("type") in ("no_change", "first_scan"):
                continue
            self.db.execute(
                """INSERT INTO changes (node_id, scan_date, change_type, old_value, new_value, severity)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    business_id, scan_date,
                    change.get("type", ""),
                    change.get("old_value", ""),
                    change.get("new_value", ""),
                    change.get("severity", "low"),
                ),
            )

    def get_all_changes(self, business_id: Optional[str] = None, days: int = 30) -> List[Dict]:
        """Get recent changes for a business or all businesses."""
        since = (datetime.now().replace(hour=0, minute=0, second=0)).strftime("%Y-%m-%d")
        if business_id:
            return self.db.fetchall(
                "SELECT * FROM changes WHERE node_id = ? AND scan_date >= ? ORDER BY scan_date DESC",
                (business_id, since),
            )
        return self.db.fetchall(
            "SELECT * FROM changes WHERE scan_date >= ? ORDER BY scan_date DESC",
            (since,),
        )


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        db.execute(
            "INSERT INTO nodes (id, type, name, properties) VALUES (?, ?, ?, ?)",
            ("biz_test", "business", "Test Biz", json.dumps({})),
        )

        db.execute(
            "INSERT INTO snapshots (node_id, scan_date, data) VALUES (?, ?, ?)",
            ("biz_test", "2026-06-01", json.dumps({"rating": 4.5, "review_count": 100, "health_score": 80, "sentiment_avg": 4.0, "technologies": ["WordPress", "jQuery"]})),
        )
        db.execute(
            "INSERT INTO snapshots (node_id, scan_date, data) VALUES (?, ?, ?)",
            ("biz_test", "2026-07-01", json.dumps({"rating": 4.1, "review_count": 130, "health_score": 65, "sentiment_avg": 3.5, "technologies": ["WordPress"]})),
        )

        cd = ChangeDetector(db)
        changes = cd.detect_all_changes("biz_test")
        print(f"Changes detected: {len(changes)}")
        for c in changes:
            print(f"  {c['type']}: {c.get('old_value', '')} -> {c.get('new_value', '')}")
