"""
#37 Search CLI
Interactive command line interface for searches.
"""

import sys
import os
import json
from typing import Dict

sys.path.insert(0, os.path.dirname(__file__))


class SearchCLI:
    """Interactive CLI for searching the knowledge graph."""

    def __init__(self, db):
        self.db = db

    def search_interactive(self) -> Dict:
        """Run interactive search."""
        from .filters import FilterEngine
        from .health_filters import HealthFilter
        from .activity_filters import ActivityFilter

        fe = FilterEngine(self.db)
        hf = HealthFilter(self.db)
        af = ActivityFilter(self.db)

        print("\n" + "=" * 50)
        print("  FindLeads Search")
        print("=" * 50)
        print("\n  Filter options:")
        print("  1. By country")
        print("  2. By city")
        print("  3. By sector")
        print("  4. By health status")
        print("  5. By activity level")
        print("  6. By name")
        print("  7. Combined search")
        print("  8. Statistics")
        print("  0. Exit")

        choice = input("\n  Choice: ").strip()

        filters = {}

        if choice == "1":
            from .geo_filters import GeoFilter
            gf = GeoFilter(self.db)
            countries = gf.get_all_countries()
            print("\n  Available countries:")
            for i, c in enumerate(countries):
                print(f"    {i + 1}. {c['country']} ({c['count']} businesses)")
            c = input("  Country name: ").strip()
            filters["country"] = c

        elif choice == "2":
            city = input("  City name: ").strip()
            filters["city"] = city

        elif choice == "3":
            from .sector_filters import SectorFilter
            sf = SectorFilter(self.db)
            sectors = sf.get_all_sectors()
            print("\n  Available sectors:")
            for i, s in enumerate(sectors):
                print(f"    {i + 1}. {s['sector']} ({s['count']} businesses)")
            s = input("  Sector name: ").strip()
            filters["sector"] = s

        elif choice == "4":
            print("\n  Health statuses: healthy, moderate, critical, dead")
            h = input("  Status: ").strip()
            filters["health_status"] = h

        elif choice == "5":
            print("\n  Activity levels: active, slow, dormant, silent")
            a = input("  Level: ").strip()
            filters["opportunity_level"] = a

        elif choice == "6":
            n = input("  Business name: ").strip()
            filters["name_contains"] = n

        elif choice == "7":
            print("\n  Combined search (press Enter to skip):")
            c = input("  Country: ").strip()
            if c:
                filters["country"] = c
            city = input("  City: ").strip()
            if city:
                filters["city"] = city
            s = input("  Sector: ").strip()
            if s:
                filters["sector"] = s
            min_h = input("  Min health (0-100): ").strip()
            if min_h:
                filters["min_health"] = float(min_h)
            max_h = input("  Max health (0-100): ").strip()
            if max_h:
                filters["max_health"] = float(max_h)

        elif choice == "8":
            stats = fe.get_statistics()
            print(f"\n  Total businesses: {stats['total_businesses']}")
            print(f"  By city: {stats['by_city']}")
            print(f"  By sector: {stats['by_sector']}")
            print(f"  By health: {stats['by_health_status']}")
            return stats

        elif choice == "0":
            return {"status": "exited"}

        else:
            print("  Invalid choice")
            return {"status": "invalid"}

        result = fe.search(filters)
        print(f"\n  Found {result['total']} businesses:")
        for biz in result["results"]:
            props = biz["properties"]
            print(f"    - {biz['name']} | Health: {props.get('health_score', '-')} | Rating: {props.get('rating', '-')} | {props.get('city', '')}")

        return result


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        cli = SearchCLI(db)
        print("Search CLI ready")
