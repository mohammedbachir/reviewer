"""
#28 Opportunity Scoring
Scores businesses by opportunity level based on changes + health + timing.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional


class OpportunityScorer:
    """Scores businesses by how good an opportunity they are for outreach."""

    OPPORTUNITY_WEIGHTS = {
        "health_score": 0.25,
        "decay_signals": 0.20,
        "review_opportunity": 0.15,
        "email_availability": 0.15,
        "timing_urgency": 0.15,
        "tech_freshness": 0.10,
    }

    def __init__(self, db):
        self.db = db

    def score_opportunity(self, business_id: str) -> Dict:
        """Calculate opportunity score for a business."""
        node = self._get_business(business_id)
        if not node:
            return {"error": "Business not found"}

        props = node.get("properties", {})
        scores = {}

        scores["health_score"] = self._score_health(props)
        scores["decay_signals"] = self._score_decay(props)
        scores["review_opportunity"] = self._score_review_opportunity(props)
        scores["email_availability"] = self._score_email_availability(props)
        scores["timing_urgency"] = self._score_timing(props)
        scores["tech_freshness"] = self._score_tech(props)

        total = 0
        for component, weight in self.OPPORTUNITY_WEIGHTS.items():
            total += scores[component].get("score", 0) * weight

        level = self._classify_opportunity(total)

        return {
            "business_id": business_id,
            "business_name": node.get("name", ""),
            "total_score": round(total, 2),
            "level": level,
            "components": scores,
            "pitch_angle": self._get_pitch_angle(level, scores, props),
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

    def _score_health(self, props: Dict) -> Dict:
        """Score based on health score (lower = better opportunity)."""
        health = float(props.get("health_score", 50) or 50)
        if health <= 20:
            score = 1.0
        elif health <= 40:
            score = 0.8
        elif health <= 60:
            score = 0.5
        elif health <= 80:
            score = 0.3
        else:
            score = 0.1

        return {"score": score, "value": health, "details": f"Health: {health}/100"}

    def _score_decay(self, props: Dict) -> Dict:
        """Score based on decay signals."""
        negative_pct = float(props.get("negative_pct", 0) or props.get("sentiment_negative_pct", 0) or 0)
        health = float(props.get("health_score", 50) or 50)

        decay = 0
        if negative_pct > 40:
            decay += 0.5
        elif negative_pct > 25:
            decay += 0.3
        if health < 40:
            decay += 0.5
        elif health < 60:
            decay += 0.2

        return {"score": min(decay, 1.0), "value": round(decay, 2), "details": f"Decay signals: {round(decay, 2)}"}

    def _score_review_opportunity(self, props: Dict) -> Dict:
        """Score based on review management opportunity."""
        review_count = int(props.get("review_count", 0) or 0)
        response_rate = float(props.get("response_rate", 0) or 0)
        negative_pct = float(props.get("negative_pct", 0) or props.get("sentiment_negative_pct", 0) or 0)

        score = 0
        if negative_pct > 30:
            score += 0.4
        if response_rate < 30:
            score += 0.3
        if review_count > 50:
            score += 0.3

        return {"score": min(score, 1.0), "value": round(score, 2),
                "details": f"Reviews: {review_count}, Response: {response_rate}%, Negative: {negative_pct}%"}

    def _score_email_availability(self, props: Dict) -> Dict:
        """Score based on email availability."""
        emails = props.get("emails", [])
        if isinstance(emails, str):
            emails = json.loads(emails) if emails.startswith("[") else [emails]

        if len(emails) >= 2:
            score = 1.0
        elif len(emails) == 1:
            score = 0.6
        else:
            score = 0.1

        return {"score": score, "value": len(emails), "details": f"Emails found: {len(emails)}"}

    def _score_timing(self, props: Dict) -> Dict:
        """Score based on timing urgency."""
        days_until_expiry = int(props.get("days_until_expiry", 999) or 999)
        last_scan = props.get("last_scan", "")

        score = 0
        if days_until_expiry <= 30:
            score += 0.5
        elif days_until_expiry <= 60:
            score += 0.3

        if last_scan:
            try:
                scan_date = datetime.fromisoformat(last_scan)
                days_inactive = (datetime.now() - scan_date).days
                if days_inactive > 60:
                    score += 0.5
                elif days_inactive > 30:
                    score += 0.2
            except (ValueError, TypeError):
                pass

        return {"score": min(score, 1.0), "value": round(score, 2),
                "details": f"Domain: {days_until_expiry}d, Last scan: {last_scan or 'unknown'}"}

    def _score_tech(self, props: Dict) -> Dict:
        """Score based on technology freshness."""
        techs = props.get("technologies", [])
        if isinstance(techs, str):
            techs = json.loads(techs) if techs.startswith("[") else [techs]

        old_techs = {"jQuery", "Squarespace", "Wix"}
        modern_techs = {"React", "Next.js", "Vue.js", "Node.js"}

        old_count = sum(1 for t in techs if t in old_techs)
        modern_count = sum(1 for t in techs if t in modern_techs)

        if old_count > modern_count:
            score = 0.8
        elif modern_count > old_count:
            score = 0.2
        else:
            score = 0.5

        return {"score": score, "techs": techs, "details": f"Old: {old_count}, Modern: {modern_count}"}

    def _classify_opportunity(self, score: float) -> str:
        """Classify opportunity level."""
        if score >= 0.7:
            return "urgent"
        if score >= 0.5:
            return "high"
        if score >= 0.3:
            return "medium"
        return "low"

    def _get_pitch_angle(self, level: str, scores: Dict, props: Dict) -> str:
        """Generate pitch angle based on scores."""
        if level == "urgent":
            return f"URGENT: {props.get('name', 'Business')} has critical health ({props.get('health_score', 0)}/100) and needs immediate review management help."
        if level == "high":
            return f"HIGH: {props.get('name', 'Business')} shows strong decay signals. Focus on review response improvement."
        if level == "medium":
            return f"MEDIUM: {props.get('name', 'Business')} has moderate opportunity. Emphasize proactive review management."
        return f"LOW: {props.get('name', 'Business')} is relatively healthy. Position as preventive measure."

    def rank_all_opportunities(self, top_n: int = 10) -> List[Dict]:
        """Rank all businesses by opportunity score."""
        nodes = self.db.fetchall(
            "SELECT id FROM nodes WHERE type = 'business'",
        )

        scored = []
        for node in nodes:
            result = self.score_opportunity(node["id"])
            if "error" not in result:
                scored.append(result)

        scored.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        return scored[:top_n]

    def sector_opportunity(self, sector: str) -> Dict:
        """Get average opportunity score for a sector."""
        nodes = self.db.fetchall(
            "SELECT id, properties FROM nodes WHERE type = 'business'",
        )

        sector_scores = []
        for node in nodes:
            props = json.loads(node.get("properties", "{}"))
            if props.get("sector", "").lower() == sector.lower():
                result = self.score_opportunity(node["id"])
                if "error" not in result:
                    sector_scores.append(result["total_score"])

        if not sector_scores:
            return {"sector": sector, "avg_score": 0, "count": 0}

        return {
            "sector": sector,
            "avg_score": round(sum(sector_scores) / len(sector_scores), 2),
            "count": len(sector_scores),
            "level": self._classify_opportunity(sum(sector_scores) / len(sector_scores)),
        }


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        businesses = [
            ("b1", "Bloom", {"rating": 3.8, "health_score": 45, "review_count": 80, "negative_pct": 35,
                             "emails": ["ahmed@bloom.ae", "info@bloom.ae"], "days_until_expiry": 180,
                             "last_scan": "2026-07-01", "technologies": ["Shopify", "Instagram Pixel"],
                             "response_rate": 20, "sector": "beauty"}),
            ("b2", "Al Noor", {"rating": 4.8, "health_score": 92, "review_count": 350, "negative_pct": 5,
                               "emails": ["info@alnoor.ae", "dr.hassan@alnoor.ae"], "days_until_expiry": 365,
                               "last_scan": "2026-07-15", "technologies": ["React", "Node.js"],
                               "response_rate": 85, "sector": "dental"}),
            ("b3", "Fresh Cuts", {"rating": 2.5, "health_score": 20, "review_count": 15, "negative_pct": 60,
                                  "emails": [], "days_until_expiry": 5,
                                  "last_scan": "2026-03-01", "technologies": ["Squarespace"],
                                  "response_rate": 0, "sector": "barbershops"}),
        ]
        for bid, name, props in businesses:
            db.execute(
                "INSERT INTO nodes (id, type, name, properties) VALUES (?, ?, ?, ?)",
                (bid, "business", name, json.dumps(props)),
            )

        os = OpportunityScorer(db)

        for bid, name, _ in businesses:
            result = os.score_opportunity(bid)
            print(f"{name}: {result['level']} (score: {result['total_score']})")
            print(f"  Pitch: {result['pitch_angle']}")
            for comp, data in result["components"].items():
                print(f"    {comp}: {data['details']} (score: {data['score']})")
            print()

        ranking = os.rank_all_opportunities(3)
        print("Ranking:")
        for i, r in enumerate(ranking):
            print(f"  {i + 1}. {r['business_name']}: {r['level']} ({r['total_score']})")
