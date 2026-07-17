"""
#18 Data Sync
Synchronizes data from the existing FindLeads pipeline into the Knowledge Graph.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(__file__))


class DataSync:
    """Synchronizes FindLeads pipeline data into the Knowledge Graph."""

    def __init__(self, db):
        self.db = db
        from nodes import NodeManager
        from edges import EdgeManager
        self.nodes = NodeManager(db)
        self.edges = EdgeManager(db)

    def sync_osint_result(self, business_name: str, osint_data: Dict) -> Dict:
        """Sync OSINT scan results into the knowledge graph."""
        business = self.nodes.upsert_business(
            name=business_name,
            city=osint_data.get("city", "Unknown"),
            sector=osint_data.get("sector", "Unknown"),
            properties={
                "rating": osint_data.get("rating", 0),
                "review_count": osint_data.get("review_count", 0),
                "last_scan": datetime.now().isoformat(),
            },
        )

        techs = osint_data.get("technologies", [])
        for tech in techs:
            tech_node = self.nodes.create_node(
                "tech",
                tech,
                {"detected_at": datetime.now().isoformat()},
            )
            self.edges.connect_business_tech(business["id"], tech_node["id"])

        emails = osint_data.get("emails", [])
        for email in emails:
            email_node = self.nodes.create_node(
                "email",
                email,
                {"valid": True, "discovered_at": datetime.now().isoformat()},
            )
            self.edges.connect_business_email(business["id"], email_node["id"])

        health = osint_data.get("health_score", {})
        if health:
            self.nodes.update_node(business["id"], {
                "health_score": health.get("score", 0),
                "health_status": health.get("status", "unknown"),
                "opportunity_level": health.get("opportunity", "unknown"),
            })

        return business

    def sync_sentiment(self, business_id: str, sentiment_data: Dict) -> Dict:
        """Sync sentiment analysis results."""
        self.nodes.update_node(business_id, {
            "sentiment_avg": sentiment_data.get("average", 0),
            "sentiment_negative_pct": sentiment_data.get("negative_percentage", 0),
            "sentiment_positive_pct": sentiment_data.get("positive_percentage", 0),
            "total_reviews_analyzed": sentiment_data.get("total_reviews", 0),
        })
        return {"status": "synced", "business_id": business_id}

    def sync_tech_stack(self, business_id: str, tech_stack: Dict) -> Dict:
        """Sync technology detection results."""
        detected = tech_stack.get("detected", [])
        for tech in detected:
            tech_node = self.nodes.create_node(
                "tech",
                tech["name"],
                {"version": tech.get("version", ""), "category": tech.get("category", "")},
            )
            self.edges.connect_business_tech(business_id, tech_node["id"])

        return {"status": "synced", "technologies": len(detected)}

    def sync_whois(self, business_id: str, whois_data: Dict) -> Dict:
        """Sync WHOIS lookup results."""
        self.nodes.update_node(business_id, {
            "domain": whois_data.get("domain", ""),
            "registrar": whois_data.get("registrar", ""),
            "creation_date": whois_data.get("creation_date", ""),
            "expiry_date": whois_data.get("expiry_date", ""),
            "days_until_expiry": whois_data.get("days_until_expiry", 0),
        })
        return {"status": "synced", "business_id": business_id}

    def sync_ssl(self, business_id: str, ssl_data: Dict) -> Dict:
        """Sync SSL intelligence results."""
        self.nodes.update_node(business_id, {
            "ssl_grade": ssl_data.get("grade", ""),
            "ssl_issuer": ssl_data.get("issuer", ""),
            "ssl_valid": ssl_data.get("is_valid", False),
        })
        return {"status": "synced", "business_id": business_id}

    def sync_batch(self, businesses: List[Dict]) -> Dict:
        """Sync multiple businesses at once."""
        results = {"synced": 0, "errors": 0, "details": []}

        for biz in businesses:
            try:
                self.sync_osint_result(biz["name"], biz)
                results["synced"] += 1
                results["details"].append({"name": biz["name"], "status": "ok"})
            except Exception as e:
                results["errors"] += 1
                results["details"].append({"name": biz.get("name", "unknown"), "status": "error", "error": str(e)})

        return results


if __name__ == "__main__":
    from database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        sync = DataSync(db)

        osint_result = {
            "city": "Dubai",
            "sector": "beauty salons",
            "rating": 4.2,
            "review_count": 120,
            "technologies": ["WordPress", "WooCommerce", "jQuery"],
            "emails": ["info@bloom.ae", "ahmed@bloom.ae"],
            "health_score": {"score": 65, "status": "healthy", "opportunity": "high"},
        }

        business = sync.sync_osint_result("Bloom Beauty Studio", osint_result)
        print(f"Synced: {business['name']}")
        print(f"DB Stats: {db.stats()}")
