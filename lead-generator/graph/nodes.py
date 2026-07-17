"""
#15 Node Storage
Manages nodes in the knowledge graph: business, person, email, tech, review.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any


class NodeManager:
    """Manages node CRUD operations in the Knowledge Graph."""

    def __init__(self, db):
        self.db = db

    def create_node(
        self,
        node_type: str,
        name: str,
        properties: Optional[Dict] = None,
        node_id: Optional[str] = None,
    ) -> Dict:
        """Create a new node."""
        if node_id is None:
            node_id = f"{node_type}_{uuid.uuid4().hex[:12]}"

        now = datetime.now().isoformat()
        props_json = json.dumps(properties or {}, ensure_ascii=False)

        self.db.execute(
            """INSERT OR REPLACE INTO nodes (id, type, name, properties, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (node_id, node_type, name, props_json, now, now),
        )

        return {"id": node_id, "type": node_type, "name": name, "properties": properties or {}}

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get a node by ID."""
        row = self.db.fetchone("SELECT * FROM nodes WHERE id = ?", (node_id,))
        if row:
            row["properties"] = json.loads(row.get("properties", "{}"))
            return row
        return None

    def find_nodes(
        self,
        node_type: Optional[str] = None,
        name_contains: Optional[str] = None,
        property_key: Optional[str] = None,
        property_value: Optional[Any] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Find nodes with optional filters."""
        query = "SELECT * FROM nodes WHERE 1=1"
        params = []

        if node_type:
            query += " AND type = ?"
            params.append(node_type)

        if name_contains:
            query += " AND name ILIKE ?"
            params.append(f"%{name_contains}%")

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = self.db.fetchall(query, tuple(params))
        for row in rows:
            row["properties"] = json.loads(row.get("properties", "{}"))
        return rows

    def update_node(self, node_id: str, properties: Dict) -> bool:
        """Update node properties (merge with existing)."""
        existing = self.get_node(node_id)
        if not existing:
            return False

        merged = {**existing["properties"], **properties}
        props_json = json.dumps(merged, ensure_ascii=False)
        now = datetime.now().isoformat()

        self.db.execute(
            "UPDATE nodes SET properties = ?, updated_at = ? WHERE id = ?",
            (props_json, now, node_id),
        )
        return True

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges."""
        self.db.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (node_id, node_id))
        self.db.execute("DELETE FROM snapshots WHERE node_id = ?", (node_id,))
        self.db.execute("DELETE FROM changes WHERE node_id = ?", (node_id,))
        self.db.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        return True

    def upsert_business(
        self,
        name: str,
        city: str,
        sector: str,
        country: str = "UAE",
        properties: Optional[Dict] = None,
    ) -> Dict:
        """Insert or update a business node. Returns existing if found."""
        existing = self.db.fetchone(
            "SELECT id FROM nodes WHERE type = 'business' AND name = ?",
            (name,),
        )

        props = properties or {}
        props.update({"city": city, "sector": sector, "country": country})

        if existing:
            self.update_node(existing["id"], props)
            return self.get_node(existing["id"])
        else:
            return self.create_node("business", name, props, node_id=f"biz_{uuid.uuid5(uuid.NAMESPACE_URL, name).hex[:12]}")

    def count_by_type(self) -> Dict[str, int]:
        """Count nodes by type."""
        rows = self.db.fetchall("SELECT type, COUNT(*) as cnt FROM nodes GROUP BY type")
        return {row["type"]: row["cnt"] for row in rows}


if __name__ == "__main__":
    from database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        nm = NodeManager(db)

        b1 = nm.upsert_business("Bloom Beauty Studio", "Dubai", "beauty salons", rating=4.2, review_count=120)
        b2 = nm.upsert_business("McGill Dental Center", "Dubai", "dental clinics", rating=4.5, review_count=200)
        p1 = nm.create_node("person", "Ahmed Al-Maktoum", {"role": "owner", "email": "ahmed@bloom.ae"})
        t1 = nm.create_node("tech", "WordPress", {"version": "6.4"})

        print(f"Business 1: {b1['name']} ({b1['id']})")
        print(f"Business 2: {b2['name']} ({b2['id']})")
        print(f"Person: {p1['name']}")
        print(f"Tech: {t1['name']}")
        print(f"Counts: {nm.count_by_type()}")
