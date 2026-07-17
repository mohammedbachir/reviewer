"""
#31 Query Builder
Builds DuckDB SQL queries from filter criteria.
"""

from typing import Dict, List, Optional, Tuple


class QueryBuilder:
    """Builds SQL queries dynamically from filter criteria."""

    def __init__(self):
        self.base_query = "SELECT id, name, properties FROM nodes WHERE type = 'business'"
        self.count_base = "SELECT COUNT(*) as cnt FROM nodes WHERE type = 'business'"
        self.conditions = []
        self.params = []

    def reset(self):
        """Reset the query builder."""
        self.conditions = []
        self.params = []
        return self

    def where_country(self, country: str) -> "QueryBuilder":
        """Filter by country."""
        self.conditions.append("JSON_EXTRACT(properties, '$.country') = ?")
        self.params.append(country)
        return self

    def where_city(self, city: str) -> "QueryBuilder":
        """Filter by city."""
        self.conditions.append("JSON_EXTRACT(properties, '$.city') = ?")
        self.params.append(city)
        return self

    def where_sector(self, sector: str) -> "QueryBuilder":
        """Filter by sector."""
        self.conditions.append("JSON_EXTRACT(properties, '$.sector') = ?")
        self.params.append(sector)
        return self

    def where_health_min(self, min_val: float) -> "QueryBuilder":
        """Filter by minimum health score."""
        self.conditions.append("CAST(JSON_EXTRACT(properties, '$.health_score') AS DOUBLE) >= ?")
        self.params.append(min_val)
        return self

    def where_health_max(self, max_val: float) -> "QueryBuilder":
        """Filter by maximum health score."""
        self.conditions.append("CAST(JSON_EXTRACT(properties, '$.health_score') AS DOUBLE) <= ?")
        self.params.append(max_val)
        return self

    def where_rating_min(self, min_val: float) -> "QueryBuilder":
        """Filter by minimum rating."""
        self.conditions.append("CAST(JSON_EXTRACT(properties, '$.rating') AS DOUBLE) >= ?")
        self.params.append(min_val)
        return self

    def where_rating_max(self, max_val: float) -> "QueryBuilder":
        """Filter by maximum rating."""
        self.conditions.append("CAST(JSON_EXTRACT(properties, '$.rating') AS DOUBLE) <= ?")
        self.params.append(max_val)
        return self

    def where_health_status(self, status: str) -> "QueryBuilder":
        """Filter by health status."""
        self.conditions.append("JSON_EXTRACT(properties, '$.health_status') = ?")
        self.params.append(status)
        return self

    def where_opportunity(self, level: str) -> "QueryBuilder":
        """Filter by opportunity level."""
        self.conditions.append("JSON_EXTRACT(properties, '$.opportunity_level') = ?")
        self.params.append(level)
        return self

    def where_name_contains(self, name: str) -> "QueryBuilder":
        """Filter by name substring."""
        self.conditions.append("name ILIKE ?")
        self.params.append(f"%{name}%")
        return self

    def where_has_email(self) -> "QueryBuilder":
        """Filter businesses that have at least one email."""
        self.conditions.append("JSON_EXTRACT_LENGTH(properties, '$.emails') > 0")
        return self

    def build(self) -> Tuple[str, tuple]:
        """Build the final SQL query."""
        query = self.base_query
        if self.conditions:
            query += " AND " + " AND ".join(self.conditions)
        query += " ORDER BY name"
        return query, tuple(self.params)

    def build_count(self) -> Tuple[str, tuple]:
        """Build count query."""
        query = self.count_base
        if self.conditions:
            query += " AND " + " AND ".join(self.conditions)
        return query, tuple(self.params)

    def build_with_limit(self, limit: int, offset: int = 0) -> Tuple[str, tuple]:
        """Build query with limit and offset."""
        query, params = self.build()
        query += " LIMIT ? OFFSET ?"
        return query, tuple(list(params) + [limit, offset])


if __name__ == "__main__":
    qb = QueryBuilder()
    query, params = qb.where_city("Dubai").where_sector("beauty salons").where_health_max(50).build()
    print(f"Query: {query}")
    print(f"Params: {params}")

    count_query, count_params = qb.build_count()
    print(f"Count: {count_query}")

    qb.reset()
    q2, p2 = qb.where_health_status("critical").where_rating_max(3.0).build_with_limit(10)
    print(f"Critical: {q2}")
    print(f"Params: {p2}")
