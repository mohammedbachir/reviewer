"""
#27 Decay Detection
Detects businesses in decline — losing reviews, dropping rating, no activity.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class DecayDetector:
    """Detects businesses experiencing decay or decline."""

    DECAY_SIGNALS = {
        "rating_declining": {"weight": 0.25, "description": "Rating consistently dropping"},
        "health_declining": {"weight": 0.25, "description": "Health score declining"},
        "low_review_count": {"weight": 0.15, "description": "Very few reviews"},
        "negative_sentiment": {"weight": 0.20, "description": "Negative review sentiment"},
        "no_recent_activity": {"weight": 0.15, "description": "No recent review activity"},
    }

    def __init__(self, db):
        self.db = db

    def detect_decay(self, business_id: str) -> Dict:
        """Detect if a business is in decay."""
        node = self._get_business(business_id)
        if not node:
            return {"error": "Business not found"}

        props = node.get("properties", {})
        signals = {}
        total_score = 0

        signals["rating_declining"] = self._check_rating_decay(props)
        signals["health_declining"] = self._check_health_decay(props)
        signals["low_review_count"] = self._check_low_reviews(props)
        signals["negative_sentiment"] = self._check_negative_sentiment(props)
        signals["no_recent_activity"] = self._check_activity(props)

        for signal_name, signal_data in signals.items():
            weight = self.DECAY_SIGNALS[signal_name]["weight"]
            total_score += signal_data.get("score", 0) * weight

        decay_level = self._classify_decay(total_score)

        return {
            "business_id": business_id,
            "business_name": node.get("name", ""),
            "decay_score": round(total_score, 2),
            "decay_level": decay_level,
            "signals": signals,
            "recommendation": self._get_recommendation(decay_level, signals),
        }

    def _get_business(self, business_id: str) -> Dict:
        """Get business node data."""
        row = self.db.fetchone(
            "SELECT name, properties FROM nodes WHERE id = ?",
            (business_id,),
        )
        if row:
            row["properties"] = json.loads(row.get("properties", "{}"))
        return row or {}

    def _check_rating_decay(self, props: Dict) -> Dict:
        """Check if rating is declining."""
        rating = float(props.get("rating", 0) or 0)
        if rating == 0:
            return {"score": 0, "details": "No rating data"}

        if rating >= 4.0:
            score = 0
        elif rating >= 3.5:
            score = 0.3
        elif rating >= 3.0:
            score = 0.6
        else:
            score = 1.0

        return {"score": score, "rating": rating, "details": f"Rating: {rating}"}

    def _check_health_decay(self, props: Dict) -> Dict:
        """Check if health score is declining."""
        health = float(props.get("health_score", 0) or 0)
        if health == 0:
            return {"score": 0, "details": "No health data"}

        if health >= 70:
            score = 0
        elif health >= 50:
            score = 0.3
        elif health >= 30:
            score = 0.6
        else:
            score = 1.0

        return {"score": score, "health_score": health, "details": f"Health: {health}/100"}

    def _check_low_reviews(self, props: Dict) -> Dict:
        """Check if review count is very low."""
        review_count = int(props.get("review_count", 0) or 0)
        if review_count >= 100:
            score = 0
        elif review_count >= 50:
            score = 0.3
        elif review_count >= 20:
            score = 0.6
        else:
            score = 1.0

        return {"score": score, "review_count": review_count, "details": f"Reviews: {review_count}"}

    def _check_negative_sentiment(self, props: Dict) -> Dict:
        """Check if sentiment is negative."""
        negative_pct = float(props.get("sentiment_negative_pct", 0) or props.get("negative_pct", 0) or 0)
        if negative_pct <= 15:
            score = 0
        elif negative_pct <= 30:
            score = 0.3
        elif negative_pct <= 50:
            score = 0.6
        else:
            score = 1.0

        return {"score": score, "negative_pct": negative_pct, "details": f"Negative: {negative_pct}%"}

    def _check_activity(self, props: Dict) -> Dict:
        """Check recent activity level."""
        last_scan = props.get("last_scan", "")
        if not last_scan:
            return {"score": 0.5, "details": "No scan data"}

        try:
            scan_date = datetime.fromisoformat(last_scan)
            days_inactive = (datetime.now() - scan_date).days

            if days_inactive <= 30:
                score = 0
            elif days_inactive <= 60:
                score = 0.3
            elif days_inactive <= 90:
                score = 0.6
            else:
                score = 1.0

            return {"score": score, "days_inactive": days_inactive, "details": f"Inactive: {days_inactive} days"}
        except (ValueError, TypeError):
            return {"score": 0.5, "details": "Invalid scan date"}

    def _classify_decay(self, score: float) -> str:
        """Classify decay level based on score."""
        if score >= 0.7:
            return "severe"
        if score >= 0.5:
            return "moderate"
        if score >= 0.3:
            return "mild"
        return "healthy"

    def _get_recommendation(self, level: str, signals: Dict) -> str:
        """Get recommendation based on decay level."""
        if level == "severe":
            return "Critical: Business is in severe decline. Immediate outreach recommended. Highlight review management solution."
        if level == "moderate":
            return "Warning: Business showing moderate decay. Outreach recommended within 2 weeks. Focus on health improvement."
        if level == "mild":
            return "Watch: Minor decay signals. Monitor for 30 days before outreach."
        return "Healthy: Business is stable. Low priority for outreach."

    def detect_all_decaying(self, threshold: float = 0.3) -> List[Dict]:
        """Find all businesses with decay score above threshold."""
        nodes = self.db.fetchall(
            "SELECT id FROM nodes WHERE type = 'business'",
        )

        decaying = []
        for node in nodes:
            result = self.detect_decay(node["id"])
            if result.get("decay_score", 0) >= threshold:
                decaying.append(result)

        decaying.sort(key=lambda x: x.get("decay_score", 0), reverse=True)
        return decaying


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        businesses = [
            ("b1", "Bloom", {"rating": 3.8, "health_score": 45, "review_count": 80, "negative_pct": 35, "last_scan": "2026-06-01"}),
            ("b2", "Al Noor", {"rating": 4.8, "health_score": 92, "review_count": 350, "negative_pct": 5, "last_scan": "2026-07-15"}),
            ("b3", "Fresh Cuts", {"rating": 2.5, "health_score": 20, "review_count": 15, "negative_pct": 60, "last_scan": "2026-03-01"}),
        ]
        for bid, name, props in businesses:
            db.execute(
                "INSERT INTO nodes (id, type, name, properties) VALUES (?, ?, ?, ?)",
                (bid, "business", name, json.dumps(props)),
            )

        dd = DecayDetector(db)

        for bid, name, _ in businesses:
            result = dd.detect_decay(bid)
            print(f"{name}: {result['decay_level']} (score: {result['decay_score']})")
            print(f"  Recommendation: {result['recommendation']}")
            for sig, data in result["signals"].items():
                print(f"    {sig}: {data['details']} (score: {data['score']})")
            print()
