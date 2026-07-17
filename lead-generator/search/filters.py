"""
#30 Filter Engine
Multi-criteria filtering combining all filter types.
"""

import json
from typing import Dict, List, Optional, Any


class FilterEngine:
    """Combines all filter types into a single query."""

    def __init__(self, db):
        self.db = db

    def search(self, filters: Optional[Dict] = None, limit: int = 50, offset: int = 0) -> Dict:
        """Execute a multi-criteria search."""
        if not filters:
            filters = {}

        query = "SELECT id, name, properties FROM nodes WHERE type = 'business'"
        params = []

        if filters.get("country"):
            query += " AND json_extract_string(properties, '$.country') = ?"
            params.append(filters["country"])

        if filters.get("city"):
            query += " AND json_extract_string(properties, '$.city') = ?"
            params.append(filters["city"])

        if filters.get("sector"):
            query += " AND json_extract_string(properties, '$.sector') = ?"
            params.append(filters["sector"])

        if filters.get("min_health") is not None:
            query += " AND CAST(JSON_EXTRACT(properties, '$.health_score') AS DOUBLE) >= ?"
            params.append(filters["min_health"])

        if filters.get("max_health") is not None:
            query += " AND CAST(JSON_EXTRACT(properties, '$.health_score') AS DOUBLE) <= ?"
            params.append(filters["max_health"])

        if filters.get("min_rating") is not None:
            query += " AND CAST(JSON_EXTRACT(properties, '$.rating') AS DOUBLE) >= ?"
            params.append(filters["min_rating"])

        if filters.get("max_rating") is not None:
            query += " AND CAST(JSON_EXTRACT(properties, '$.rating') AS DOUBLE) <= ?"
            params.append(filters["max_rating"])

        if filters.get("health_status"):
            query += " AND json_extract_string(properties, '$.health_status') = ?"
            params.append(filters["health_status"])

        if filters.get("opportunity_level"):
            query += " AND json_extract_string(properties, '$.opportunity_level') = ?"
            params.append(filters["opportunity_level"])

        if filters.get("name_contains"):
            query += " AND name ILIKE ?"
            params.append(f"%{filters['name_contains']}%")

        count_query = query.replace("SELECT id, name, properties", "SELECT COUNT(*) as cnt")
        count_result = self.db.fetchone(count_query, tuple(params))
        total = count_result["cnt"] if count_result else 0

        query += " ORDER BY name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.db.fetchall(query, tuple(params))
        for row in rows:
            row["properties"] = json.loads(row.get("properties", "{}"))

        return {
            "results": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        }

    def search_by_name(self, name: str) -> List[Dict]:
        """Search businesses by name."""
        rows = self.db.fetchall(
            "SELECT id, name, properties FROM nodes WHERE type = 'business' AND name ILIKE ?",
            (f"%{name}%",),
        )
        for row in rows:
            row["properties"] = json.loads(row.get("properties", "{}"))
        return rows

    def get_statistics(self) -> Dict:
        """Get overall statistics."""
        total = self.db.fetchone("SELECT COUNT(*) as cnt FROM nodes WHERE type = 'business'")
        by_city = self.db.fetchall(
            """SELECT json_extract_string(properties, '$.city') as city, COUNT(*) as cnt 
               FROM nodes WHERE type = 'business' GROUP BY city"""
        )
        by_sector = self.db.fetchall(
            """SELECT json_extract_string(properties, '$.sector') as sector, COUNT(*) as cnt 
               FROM nodes WHERE type = 'business' GROUP BY sector"""
        )
        by_health = self.db.fetchall(
            """SELECT 
                CASE 
                    WHEN CAST(JSON_EXTRACT(properties, '$.health_score') AS DOUBLE) >= 70 THEN 'healthy'
                    WHEN CAST(JSON_EXTRACT(properties, '$.health_score') AS DOUBLE) >= 40 THEN 'moderate'
                    ELSE 'critical'
                END as status,
                COUNT(*) as cnt
               FROM nodes WHERE type = 'business' GROUP BY status"""
        )

        return {
            "total_businesses": total["cnt"] if total else 0,
            "by_city": {row["city"]: row["cnt"] for row in by_city if row["city"]},
            "by_sector": {row["sector"]: row["cnt"] for row in by_sector if row["sector"]},
            "by_health_status": {row["status"]: row["cnt"] for row in by_health if row["status"]},
        }


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        fe = FilterEngine(db)
        result = fe.search()
        print(f"Search: {result['total']} businesses")
        stats = fe.get_statistics()
        print(f"Stats: {stats}")
