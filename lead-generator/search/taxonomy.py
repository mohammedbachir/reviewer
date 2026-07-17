"""
#29 Taxonomy System
Country > City > Sector hierarchy for organizing businesses.
"""

import json
from typing import Dict, List, Optional


class TaxonomySystem:
    """Manages country/city/sector taxonomy."""

    DEFAULT_TAXONOMY = {
        "UAE": {
            "Dubai": ["beauty salons", "dental clinics", "barbershops", "restaurants", "hotels"],
            "Abu Dhabi": ["beauty salons", "dental clinics", "restaurants", "hotels"],
            "Sharjah": ["beauty salons", "dental clinics", "restaurants"],
            "Ajman": ["beauty salons", "dental clinics"],
            "Ras Al Khaimah": ["hotels", "restaurants"],
        },
        "Saudi Arabia": {
            "Riyadh": ["beauty salons", "dental clinics", "restaurants", "hotels"],
            "Jeddah": ["beauty salons", "dental clinics", "restaurants"],
            "Dammam": ["beauty salons", "dental clinics"],
        },
        "Bahrain": {
            "Manama": ["beauty salons", "dental clinics", "restaurants", "hotels"],
        },
        "Qatar": {
            "Doha": ["beauty salons", "dental clinics", "restaurants", "hotels"],
        },
        "Kuwait": {
            "Kuwait City": ["beauty salons", "dental clinics", "restaurants", "hotels"],
        },
        "Oman": {
            "Muscat": ["beauty salons", "dental clinics", "restaurants", "hotels"],
        },
    }

    def __init__(self, db):
        self.db = db

    def init_taxonomy(self) -> Dict:
        """Initialize default taxonomy."""
        count = 0
        for country, cities in self.DEFAULT_TAXONOMY.items():
            for city, sectors in cities.items():
                for sector in sectors:
                    existing = self.db.fetchone(
                        "SELECT id FROM taxonomy WHERE country = ? AND city = ? AND sector = ?",
                        (country, city, sector),
                    )
                    if not existing:
                        self.db.execute(
                            "INSERT INTO taxonomy (country, city, sector, is_active) VALUES (?, ?, ?, TRUE)",
                            (country, city, sector),
                        )
                        count += 1
        return {"initialized": count, "status": "ok"}

    def get_all_countries(self) -> List[str]:
        """Get all countries."""
        rows = self.db.fetchall("SELECT DISTINCT country FROM taxonomy WHERE is_active = TRUE ORDER BY country")
        return [row["country"] for row in rows]

    def get_cities(self, country: str) -> List[str]:
        """Get all cities in a country."""
        rows = self.db.fetchall(
            "SELECT DISTINCT city FROM taxonomy WHERE country = ? AND is_active = TRUE ORDER BY city",
            (country,),
        )
        return [row["city"] for row in rows]

    def get_sectors(self, country: Optional[str] = None, city: Optional[str] = None) -> List[str]:
        """Get sectors, optionally filtered by country/city."""
        query = "SELECT DISTINCT sector FROM taxonomy WHERE is_active = TRUE"
        params = []
        if country:
            query += " AND country = ?"
            params.append(country)
        if city:
            query += " AND city = ?"
            params.append(city)
        query += " ORDER BY sector"
        rows = self.db.fetchall(query, tuple(params))
        return [row["sector"] for row in rows]

    def get_tree(self) -> Dict:
        """Get full taxonomy tree."""
        tree = {}
        rows = self.db.fetchall(
            "SELECT country, city, sector FROM taxonomy WHERE is_active = TRUE ORDER BY country, city, sector"
        )
        for row in rows:
            country = row["country"]
            city = row["city"]
            sector = row["sector"]
            if country not in tree:
                tree[country] = {}
            if city not in tree[country]:
                tree[country][city] = []
            tree[country][city].append(sector)
        return tree

    def add_entry(self, country: str, city: str, sector: str) -> Dict:
        """Add a new taxonomy entry."""
        existing = self.db.fetchone(
            "SELECT id FROM taxonomy WHERE country = ? AND city = ? AND sector = ?",
            (country, city, sector),
        )
        if existing:
            self.db.execute("UPDATE taxonomy SET is_active = TRUE WHERE id = ?", (existing["id"],))
            return {"status": "updated", "country": country, "city": city, "sector": sector}

        self.db.execute(
            "INSERT INTO taxonomy (country, city, sector, is_active) VALUES (?, ?, ?, TRUE)",
            (country, city, sector),
        )
        return {"status": "created", "country": country, "city": city, "sector": sector}

    def deactivate_entry(self, country: str, city: str, sector: str) -> Dict:
        """Deactivate a taxonomy entry."""
        self.db.execute(
            "UPDATE taxonomy SET is_active = FALSE WHERE country = ? AND city = ? AND sector = ?",
            (country, city, sector),
        )
        return {"status": "deactivated"}

    def search_taxonomy(self, query: str) -> List[Dict]:
        """Search taxonomy by partial match."""
        rows = self.db.fetchall(
            "SELECT * FROM taxonomy WHERE (country ILIKE ? OR city ILIKE ? OR sector ILIKE ?) AND is_active = TRUE",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        )
        return rows


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        ts = TaxonomySystem(db)
        init = ts.init_taxonomy()
        print(f"Taxonomy init: {init}")

        countries = ts.get_all_countries()
        print(f"Countries: {countries}")

        dubai_sectors = ts.get_sectors(country="UAE", city="Dubai")
        print(f"Dubai sectors: {dubai_sectors}")

        tree = ts.get_tree()
        print(f"Tree: {len(tree)} countries")

        search = ts.search_taxonomy("beauty")
        print(f"Search 'beauty': {len(search)} results")
