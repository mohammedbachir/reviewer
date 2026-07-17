"""
#34 Sector Filters
Filter by sector (beauty salons, dental clinics, restaurants, hotels, etc.)
"""

import json
from typing import Dict, List, Optional


class SectorFilter:
    """Sector-based filtering for businesses."""

    def __init__(self, db):
        self.db = db

    def filter_by_sector(self, sector: str) -> List[Dict]:
        """Get all businesses in a sector."""
        rows = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )
        result = []
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            if props.get("sector", "").lower() == sector.lower():
                row["properties"] = props
                result.append(row)
        return result

    def filter_by_sectors(self, sectors: List[str]) -> List[Dict]:
        """Get businesses in any of the specified sectors."""
        rows = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )
        result = []
        sectors_lower = [s.lower() for s in sectors]
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            if props.get("sector", "").lower() in sectors_lower:
                row["properties"] = props
                result.append(row)
        return result

    def get_all_sectors(self) -> List[Dict]:
        """Get all sectors with business counts."""
        rows = self.db.fetchall(
            "SELECT properties FROM nodes WHERE type = 'business'"
        )
        counts = {}
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            sector = props.get("sector", "Unknown")
            counts[sector] = counts.get(sector, 0) + 1
        return [{"sector": s, "count": n} for s, n in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

    def get_sector_stats(self, sector: str) -> Dict:
        """Get statistics for a specific sector."""
        businesses = self.filter_by_sector(sector)
        if not businesses:
            return {"sector": sector, "total": 0}

        cities = {}
        health_scores = []
        ratings = []
        for biz in businesses:
            props = biz["properties"]
            city = props.get("city", "unknown")
            cities[city] = cities.get(city, 0) + 1
            score = props.get("health_score", 0)
            if score:
                health_scores.append(score)
            rating = props.get("rating", 0)
            if rating:
                ratings.append(rating)

        return {
            "sector": sector,
            "total": len(businesses),
            "cities": cities,
            "avg_health": round(sum(health_scores) / len(health_scores), 1) if health_scores else 0,
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
            "declining": sum(1 for h in health_scores if h < 50),
        }

    def get_sector_comparison(self) -> List[Dict]:
        """Compare all sectors."""
        sectors = self.get_all_sectors()
        comparison = []
        for s in sectors:
            stats = self.get_sector_stats(s["sector"])
            comparison.append(stats)
        comparison.sort(key=lambda x: x.get("avg_health", 0))
        return comparison


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        sf = SectorFilter(db)
        sectors = sf.get_all_sectors()
        print(f"Sectors: {sectors}")
        comparison = sf.get_sector_comparison()
        print(f"Sector comparison: {len(comparison)} sectors")
