"""
#17 Graph Queries
NetworkX-based graph traversal and analysis.
Finds shortest paths, connected components, and clusters.
"""

import networkx as nx
import json
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, Counter


class GraphQueries:
    """Graph traversal and analysis using NetworkX."""

    def __init__(self, db):
        self.db = db
        self.nx_graph = nx.MultiDiGraph()
        self._build_graph()

    def _build_graph(self):
        """Load all nodes and edges into NetworkX graph."""
        self.nx_graph.clear()

        nodes = self.db.fetchall("SELECT id, type, name, properties FROM nodes")
        for node in nodes:
            props = json.loads(node.get("properties", "{}"))
            self.nx_graph.add_node(
                node["id"],
                type=node["type"],
                name=node["name"],
                properties=props,
            )

        edges = self.db.fetchall("SELECT id, source_id, target_id, type, properties, confidence FROM edges")
        for edge in edges:
            props = json.loads(edge.get("properties", "{}"))
            self.nx_graph.add_edge(
                edge["source_id"],
                edge["target_id"],
                key=edge["id"],
                type=edge["type"],
                properties=props,
                confidence=edge.get("confidence", 1.0),
            )

    def refresh(self):
        """Rebuild the NetworkX graph from DuckDB."""
        self._build_graph()

    def shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find shortest path between two nodes."""
        try:
            path = nx.shortest_path(self.nx_graph, source=source, target=target)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def all_paths(self, source: str, target: str, cutoff: int = 4) -> List[List[str]]:
        """Find all paths up to cutoff length."""
        try:
            paths = list(nx.all_simple_paths(self.nx_graph, source=source, target=target, cutoff=cutoff))
            return paths
        except nx.NodeNotFound:
            return []

    def connected_components(self) -> List[Set[str]]:
        """Find connected components (ignoring edge direction)."""
        undirected = self.nx_graph.to_undirected()
        return list(nx.connected_components(undirected))

    def strongly_connected(self) -> List[Set[str]]:
        """Find strongly connected components."""
        return list(nx.strongly_connected_components(self.nx_graph))

    def degree_centrality(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """Find most connected nodes (potential 'god nodes')."""
        centrality = nx.degree_centrality(self.nx_graph)
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:top_n]

    def betweenness_centrality(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """Find bridge nodes that connect different clusters."""
        try:
            centrality = nx.betweenness_centrality(self.nx_graph)
            sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
            return sorted_nodes[:top_n]
        except Exception:
            return []

    def detect_communities(self) -> List[Set[str]]:
        """Detect communities using greedy modularity."""
        undirected = self.nx_graph.to_undirected()
        try:
            from networkx.algorithms.community import greedy_modularity_communities
            communities = greedy_modularity_communities(undirected)
            return [c for c in communities]
        except Exception:
            return []

    def find_node_neighbors(self, node_id: str, direction: str = "both") -> Dict[str, List]:
        """Get neighbors of a node."""
        neighbors = {"in": [], "out": []}

        if direction in ("in", "both"):
            for pred in self.nx_graph.predecessors(node_id):
                neighbors["in"].append(pred)

        if direction in ("out", "both"):
            for succ in self.nx_graph.successors(node_id):
                neighbors["out"].append(succ)

        return neighbors

    def get_node_importance(self, node_id: str) -> Dict:
        """Calculate importance metrics for a node."""
        if node_id not in self.nx_graph:
            return {"error": "Node not found"}

        degree = self.nx_graph.in_degree(node_id) + self.nx_graph.out_degree(node_id)

        try:
            closeness = nx.closeness_centrality(self.nx_graph, node_id)
        except Exception:
            closeness = 0.0

        return {
            "node_id": node_id,
            "degree": degree,
            "closeness_centrality": closeness,
        }

    def find_similar_businesses(self, node_id: str, max_results: int = 5) -> List[Dict]:
        """Find businesses connected to similar tech/people."""
        if node_id not in self.nx_graph:
            return []

        my_neighbors = set()
        for neighbor in self.nx_graph.neighbors(node_id):
            for inner_neighbor in self.nx_graph.neighbors(neighbor):
                if inner_neighbor != node_id:
                    my_neighbors.add((neighbor, inner_neighbor))

        similarity_scores = defaultdict(int)
        for neighbor_id, shared_node in my_neighbors:
            similarity_scores[neighbor_id] += 1

        sorted_similar = sorted(similarity_scores.items(), key=lambda x: x[1], reverse=True)[:max_results]

        results = []
        for node_id, score in sorted_similar:
            node_data = self.nx_graph.nodes.get(node_id, {})
            results.append({
                "node_id": node_id,
                "name": node_data.get("name", ""),
                "type": node_data.get("type", ""),
                "similarity_score": score,
            })

        return results

    def graph_stats(self) -> Dict:
        """Get NetworkX graph statistics."""
        return {
            "nodes": self.nx_graph.number_of_nodes(),
            "edges": self.nx_graph.number_of_edges(),
            "density": round(nx.density(self.nx_graph), 6) if self.nx_graph.number_of_nodes() > 0 else 0,
            "connected_components": len(self.connected_components()),
            "avg_degree": round(sum(dict(self.nx_graph.degree()).values()) / max(self.nx_graph.number_of_nodes(), 1), 2),
        }


if __name__ == "__main__":
    from database import GraphDatabase
    from nodes import NodeManager
    from edges import EdgeManager

    with GraphDatabase(":memory:") as db:
        nm = NodeManager(db)
        em = EdgeManager(db)

        b1 = nm.upsert_business("Bloom Beauty", "Dubai", "beauty salons")
        b2 = nm.upsert_business("Glow Beauty", "Dubai", "beauty salons")
        t1 = nm.create_node("tech", "WordPress", {"version": "6.4"})
        p1 = nm.create_node("person", "Ahmed", {"role": "owner"})

        em.connect_business_tech(b1["id"], t1["id"])
        em.connect_business_tech(b2["id"], t1["id"])
        em.connect_business_owner(b1["id"], p1["id"])

        gq = GraphQueries(db)
        print(f"Graph: {gq.graph_stats()}")
        print(f"Path Bloom->Glow: {gq.shortest_path(b1['id'], b2['id'])}")
        print(f"Components: {gq.connected_components()}")
        print(f"Communities: {gq.detect_communities()}")
