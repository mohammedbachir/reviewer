"""
#26 Trend Analysis
Analyzes trends across businesses and sectors over time.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict


class TrendAnalyzer:
    """Analyzes trends across businesses, sectors, and cities."""

    def __init__(self, db):
        self.db = db

    def sector_trend(self, sector: str) -> Dict:
        """Analyze health trend for a specific sector."""
        nodes = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )

        sector_businesses = []
        for node in nodes:
            props = json.loads(node.get("properties", "{}"))
            if props.get("sector", "").lower() == sector.lower():
                sector_businesses.append(node)

        if not sector_businesses:
            return {"sector": sector, "trend": "no_data", "business_count": 0}

        scores = []
        for biz in sector_businesses:
            props = json.loads(biz.get("properties", "{}"))
            score = props.get("health_score", 0)
            if score:
                scores.append(score)

        if not scores:
            return {"sector": sector, "trend": "no_data", "business_count": len(sector_businesses)}

        avg_score = sum(scores) / len(scores)
        declining = sum(1 for s in scores if s < 50)
        healthy = sum(1 for s in scores if s >= 70)

        if declining > len(scores) * 0.5:
            trend = "declining"
        elif healthy > len(scores) * 0.5:
            trend = "healthy"
        else:
            trend = "mixed"

        return {
            "sector": sector,
            "trend": trend,
            "business_count": len(sector_businesses),
            "avg_health_score": round(avg_score, 1),
            "healthy_count": healthy,
            "declining_count": declining,
            "min_score": min(scores),
            "max_score": max(scores),
        }

    def city_trend(self, city: str) -> Dict:
        """Analyze health trend for a specific city."""
        nodes = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )

        city_businesses = []
        for node in nodes:
            props = json.loads(node.get("properties", "{}"))
            if props.get("city", "").lower() == city.lower():
                city_businesses.append(node)

        if not city_businesses:
            return {"city": city, "trend": "no_data", "business_count": 0}

        scores = []
        sectors = defaultdict(list)
        for biz in city_businesses:
            props = json.loads(biz.get("properties", "{}"))
            score = props.get("health_score", 0)
            sector = props.get("sector", "unknown")
            if score:
                scores.append(score)
                sectors[sector].append(score)

        avg_score = sum(scores) / len(scores) if scores else 0
        sector_avgs = {}
        for sec, sc in sectors.items():
            sector_avgs[sec] = round(sum(sc) / len(sc), 1)

        declining = sum(1 for s in scores if s < 50)
        if declining > len(scores) * 0.5:
            trend = "declining"
        elif avg_score >= 70:
            trend = "healthy"
        else:
            trend = "mixed"

        return {
            "city": city,
            "trend": trend,
            "business_count": len(city_businesses),
            "avg_health_score": round(avg_score, 1),
            "sector_averages": sector_avgs,
            "declining_count": declining,
        }

    def global_trend(self) -> Dict:
        """Analyze overall trend across all businesses."""
        nodes = self.db.fetchall(
            "SELECT properties FROM nodes WHERE type = 'business'",
        )

        scores = []
        sectors = defaultdict(list)
        cities = defaultdict(list)

        for node in nodes:
            props = json.loads(node.get("properties", "{}"))
            score = props.get("health_score", 0)
            sector = props.get("sector", "unknown")
            city = props.get("city", "unknown")
            if score:
                scores.append(score)
                sectors[sector].append(score)
                cities[city].append(score)

        if not scores:
            return {"trend": "no_data", "total_businesses": 0}

        avg_score = sum(scores) / len(scores)
        declining = sum(1 for s in scores if s < 50)
        healthy = sum(1 for s in scores if s >= 70)
        critical = sum(1 for s in scores if s <= 30)

        sector_avgs = {}
        for sec, sc in sectors.items():
            sector_avgs[sec] = {
                "avg": round(sum(sc) / len(sc), 1),
                "count": len(sc),
            }

        city_avgs = {}
        for c, sc in cities.items():
            city_avgs[c] = {
                "avg": round(sum(sc) / len(sc), 1),
                "count": len(sc),
            }

        return {
            "trend": "declining" if declining > len(scores) * 0.4 else "healthy" if healthy > len(scores) * 0.4 else "mixed",
            "total_businesses": len(scores),
            "avg_health_score": round(avg_score, 1),
            "healthy_count": healthy,
            "declining_count": declining,
            "critical_count": critical,
            "sector_breakdown": sector_avgs,
            "city_breakdown": city_avgs,
        }

    def opportunity_sectors(self) -> List[Dict]:
        """Find sectors with most declining businesses (highest opportunity)."""
        nodes = self.db.fetchall(
            "SELECT properties FROM nodes WHERE type = 'business'",
        )

        sector_data = defaultdict(lambda: {"scores": [], "count": 0})
        for node in nodes:
            props = json.loads(node.get("properties", "{}"))
            sector = props.get("sector", "unknown")
            score = props.get("health_score", 0)
            sector_data[sector]["count"] += 1
            if score:
                sector_data[sector]["scores"].append(score)

        results = []
        for sector, data in sector_data.items():
            if not data["scores"]:
                continue
            avg = sum(data["scores"]) / len(data["scores"])
            declining = sum(1 for s in data["scores"] if s < 50)
            opportunity_pct = (declining / data["count"]) * 100

            results.append({
                "sector": sector,
                "avg_health": round(avg, 1),
                "total": data["count"],
                "declining": declining,
                "opportunity_pct": round(opportunity_pct, 1),
            })

        results.sort(key=lambda x: x["opportunity_pct"], reverse=True)
        return results


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        businesses = [
            ("b1", "Bloom", {"sector": "beauty", "city": "Dubai", "health_score": 72}),
            ("b2", "Glow", {"sector": "beauty", "city": "Abu Dhabi", "health_score": 45}),
            ("b3", "McGill", {"sector": "dental", "city": "Dubai", "health_score": 57}),
            ("b4", "Al Noor", {"sector": "dental", "city": "Sharjah", "health_score": 92}),
            ("b5", "Fresh Cuts", {"sector": "barbershops", "city": "Dubai", "health_score": 28}),
        ]
        for bid, name, props in businesses:
            db.execute(
                "INSERT INTO nodes (id, type, name, properties) VALUES (?, ?, ?, ?)",
                (bid, "business", name, json.dumps(props)),
            )

        ta = TrendAnalyzer(db)

        beauty = ta.sector_trend("beauty")
        print(f"Beauty trend: {beauty['trend']} (avg: {beauty['avg_health_score']})")

        dubai = ta.city_trend("Dubai")
        print(f"Dubai trend: {dubai['trend']} (avg: {dubai['avg_health_score']})")

        global_t = ta.global_trend()
        print(f"Global: {global_t['trend']} (avg: {global_t['avg_health_score']}, total: {global_t['total_businesses']})")

        opp = ta.opportunity_sectors()
        print(f"Opportunities: {[o['sector'] for o in opp]}")
