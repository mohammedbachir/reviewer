"""
#16 Edge Storage
Manages relationships between nodes: owns, uses, employs, has_email, etc.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any


class EdgeManager:
    """Manages edge CRUD operations in the Knowledge Graph."""

    def __init__(self, db):
        self.db = db

    def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict] = None,
        confidence: float = 1.0,
        edge_id: Optional[str] = None,
    ) -> Dict:
        """Create a new edge between two nodes."""
        if edge_id is None:
            edge_id = f"edge_{uuid.uuid4().hex[:12]}"

        now = datetime.now().isoformat()
        props_json = json.dumps(properties or {}, ensure_ascii=False)

        self.db.execute(
            """INSERT OR REPLACE INTO edges (id, source_id, target_id, type, properties, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (edge_id, source_id, target_id, edge_type, props_json, confidence, now),
        )

        return {
            "id": edge_id,
            "source_id": source_id,
            "target_id": target_id,
            "type": edge_type,
            "properties": properties or {},
            "confidence": confidence,
        }

    def get_edge(self, edge_id: str) -> Optional[Dict]:
        """Get an edge by ID."""
        row = self.db.fetchone("SELECT * FROM edges WHERE id = ?", (edge_id,))
        if row:
            row["properties"] = json.loads(row.get("properties", "{}"))
            return row
        return None

    def find_edges(
        self,
        edge_type: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Find edges with optional filters."""
        query = "SELECT * FROM edges WHERE 1=1"
        params = []

        if edge_type:
            query += " AND type = ?"
            params.append(edge_type)

        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)

        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.db.fetchall(query, tuple(params))
        for row in rows:
            row["properties"] = json.loads(row.get("properties", "{}"))
        return rows

    def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge."""
        self.db.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
        return True

    def connect_business_owner(self, business_id: str, person_id: str, confidence: float = 0.8) -> Dict:
        """Create an 'owns' edge between business and person."""
        return self.create_edge(
            business_id,
            person_id,
            "owns",
            {"relationship": "owner"},
            confidence,
        )

    def connect_business_tech(self, business_id: str, tech_id: str, confidence: float = 1.0) -> Dict:
        """Create a 'uses' edge between business and technology."""
        return self.create_edge(
            business_id,
            tech_id,
            "uses",
            {"relationship": "technology"},
            confidence,
        )

    def connect_business_email(self, business_id: str, email_id: str, confidence: float = 0.9) -> Dict:
        """Create a 'has_email' edge between business and email."""
        return self.create_edge(
            business_id,
            email_id,
            "has_email",
            {"relationship": "contact_email"},
            confidence,
        )

    def get_business_neighbors(self, business_id: str, edge_type: Optional[str] = None) -> Dict:
        """Get all neighbors of a business node."""
        query = """
            SELECT e.type as edge_type, n.id, n.type as node_type, n.name, n.properties
            FROM edges e
            JOIN nodes n ON (
                (e.target_id = ? AND n.id = e.source_id)
                OR (e.source_id = ? AND n.id = e.target_id)
            )
            WHERE e.source_id = ? OR e.target_id = ?
        """
        params = (business_id, business_id, business_id, business_id)

        if edge_type:
            query += " AND e.type = ?"
            params = params + (edge_type,)

        rows = self.db.fetchall(query, params)
        result = {"owners": [], "technologies": [], "emails": []}
        for row in rows:
            row["properties"] = json.loads(row.get("properties", "{}"))
            node_type = row["node_type"]
            if node_type == "person":
                result["owners"].append(row)
            elif node_type == "tech":
                result["technologies"].append(row)
            elif node_type == "email":
                result["emails"].append(row)

        return result

    def count_by_type(self) -> Dict[str, int]:
        """Count edges by type."""
        rows = self.db.fetchall("SELECT type, COUNT(*) as cnt FROM edges GROUP BY type")
        return {row["type"]: row["cnt"] for row in rows}


if __name__ == "__main__":
    from database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        from nodes import NodeManager

        nm = NodeManager(db)
        em = EdgeManager(db)

        b1 = nm.upsert_business("Bloom Beauty Studio", "Dubai", "beauty salons")
        p1 = nm.create_node("person", "Ahmed", {"role": "owner"})
        t1 = nm.create_node("tech", "WordPress", {"version": "6.4"})
        e1 = nm.create_node("email", "ahmed@bloom.ae", {"valid": True})

        em.connect_business_owner(b1["id"], p1["id"], 0.9)
        em.connect_business_tech(b1["id"], t1["id"], 1.0)
        em.connect_business_email(b1["id"], e1["id"], 0.85)

        neighbors = em.get_business_neighbors(b1["id"])
        print(f"Bloom owners: {neighbors['owners']}")
        print(f"Bloom tech: {neighbors['technologies']}")
        print(f"Bloom emails: {neighbors['emails']}")
        print(f"Edge counts: {em.count_by_type()}")
