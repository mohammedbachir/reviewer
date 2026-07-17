"""
#33 Geographic Filters
Filter by country, city, or all cities in a country.
"""

import json
from typing import Dict, List, Optional


class GeoFilter:
    """Geographic filtering for businesses."""

    def __init__(self, db):
        self.db = db

    def filter_by_country(self, country: str) -> List[Dict]:
        """Get all businesses in a country."""
        rows = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )
        result = []
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            if props.get("country", "").lower() == country.lower():
                row["properties"] = props
                result.append(row)
        return result

    def filter_by_city(self, city: str) -> List[Dict]:
        """Get all businesses in a city."""
        rows = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )
        result = []
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            if props.get("city", "").lower() == city.lower():
                row["properties"] = props
                result.append(row)
        return result

    def filter_by_country_and_city(self, country: str, city: str) -> List[Dict]:
        """Get all businesses in a specific country+city."""
        rows = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business'",
        )
        result = []
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            if (props.get("country", "").lower() == country.lower() and
                    props.get("city", "").lower() == city.lower()):
                row["properties"] = props
                result.append(row)
        return result

    def get_all_countries(self) -> List[Dict]:
        """Get all countries with business counts."""
        rows = self.db.fetchall(
            "SELECT properties FROM nodes WHERE type = 'business'"
        )
        counts = {}
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            country = props.get("country", "Unknown")
            counts[country] = counts.get(country, 0) + 1
        return [{"country": c, "count": n} for c, n in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

    def get_all_cities(self, country: Optional[str] = None) -> List[Dict]:
        """Get all cities with business counts."""
        rows = self.db.fetchall(
            "SELECT properties FROM nodes WHERE type = 'business'"
        )
        counts = {}
        for row in rows:
            props = json.loads(row.get("properties", "{}"))
            city = props.get("city", "Unknown")
            cty = props.get("country", "Unknown")
            if country and cty.lower() != country.lower():
                continue
            counts[city] = counts.get(city, 0) + 1
        return [{"city": c, "count": n} for c, n in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

    def get_city_stats(self, city: str) -> Dict:
        """Get statistics for a specific city."""
        businesses = self.filter_by_city(city)
        if not businesses:
            return {"city": city, "total": 0}

        sectors = {}
        health_scores = []
        ratings = []
        for biz in businesses:
            props = biz["properties"]
            sector = props.get("sector", "unknown")
            sectors[sector] = sectors.get(sector, 0) + 1
            score = props.get("health_score", 0)
            if score:
                health_scores.append(score)
            rating = props.get("rating", 0)
            if rating:
                ratings.append(rating)

        return {
            "city": city,
            "total": len(businesses),
            "sectors": sectors,
            "avg_health": round(sum(health_scores) / len(health_scores), 1) if health_scores else 0,
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
        }


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        gf = GeoFilter(db)
        countries = gf.get_all_countries()
        print(f"Countries: {countries}")
        stats = gf.get_city_stats("Dubai")
        print(f"Dubai stats: {stats}")
