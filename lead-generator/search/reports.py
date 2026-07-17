"""
#38 Search Reports
Generate filtered PDF/CSV reports with statistics.
"""

import json
import csv
import os
from datetime import datetime
from typing import Dict, List, Optional


class SearchReporter:
    """Generates reports from search results."""

    def __init__(self, db):
        self.db = db

    def generate_csv_report(self, businesses: List[Dict], filepath: str, title: str = "FindLeads Report") -> Dict:
        """Generate CSV report from a list of businesses."""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        headers = ["Name", "City", "Sector", "Country", "Rating", "Reviews", "Health Score",
                    "Health Status", "Sentiment", "Negative %", "SSL Grade", "Emails",
                    "Opportunity", "Response Rate"]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([title])
            writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
            writer.writerow([f"Total: {len(businesses)} businesses"])
            writer.writerow([])
            writer.writerow(headers)

            for biz in businesses:
                props = biz.get("properties", {})
                emails = props.get("emails", [])
                if isinstance(emails, str):
                    try:
                        emails = json.loads(emails)
                    except (json.JSONDecodeError, TypeError):
                        emails = [emails] if emails else []

                writer.writerow([
                    biz.get("name", ""),
                    props.get("city", ""),
                    props.get("sector", ""),
                    props.get("country", ""),
                    props.get("rating", ""),
                    props.get("review_count", ""),
                    props.get("health_score", ""),
                    props.get("health_status", ""),
                    props.get("sentiment_avg", ""),
                    props.get("negative_pct", ""),
                    props.get("ssl_grade", ""),
                    ", ".join(emails) if emails else "",
                    props.get("opportunity_level", ""),
                    props.get("response_rate", ""),
                ])

        return {
            "status": "generated",
            "filepath": filepath,
            "businesses": len(businesses),
            "size_bytes": os.path.getsize(filepath),
        }

    def generate_summary_report(self, businesses: List[Dict]) -> Dict:
        """Generate summary statistics from a list of businesses."""
        if not businesses:
            return {"total": 0, "message": "No businesses to summarize"}

        total = len(businesses)
        cities = {}
        sectors = {}
        health_scores = []
        ratings = []
        opportunities = {"urgent": 0, "high": 0, "medium": 0, "low": 0}
        statuses = {"healthy": 0, "moderate": 0, "critical": 0}

        for biz in businesses:
            props = biz.get("properties", {})
            city = props.get("city", "Unknown")
            sector = props.get("sector", "Unknown")
            cities[city] = cities.get(city, 0) + 1
            sectors[sector] = sectors.get(sector, 0) + 1

            score = props.get("health_score", 0)
            if score:
                health_scores.append(float(score))
                if score >= 70:
                    statuses["healthy"] += 1
                elif score >= 40:
                    statuses["moderate"] += 1
                else:
                    statuses["critical"] += 1

            rating = props.get("rating", 0)
            if rating:
                ratings.append(float(rating))

            opp = props.get("opportunity_level", "low")
            opportunities[opp] = opportunities.get(opp, 0) + 1

        return {
            "total": total,
            "cities": cities,
            "sectors": sectors,
            "avg_health": round(sum(health_scores) / len(health_scores), 1) if health_scores else 0,
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
            "health_distribution": statuses,
            "opportunity_distribution": opportunities,
            "top_city": max(cities.items(), key=lambda x: x[1])[0] if cities else "N/A",
            "top_sector": max(sectors.items(), key=lambda x: x[1])[0] if sectors else "N/A",
        }

    def generate_text_report(self, businesses: List[Dict], title: str = "FindLeads Search Report") -> str:
        """Generate a text-based report."""
        summary = self.generate_summary_report(businesses)

        lines = []
        lines.append("=" * 60)
        lines.append(f"  {title}")
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"  Total Businesses: {summary['total']}")
        lines.append(f"  Average Health: {summary['avg_health']}/100")
        lines.append(f"  Average Rating: {summary['avg_rating']}/5.0")
        lines.append("")
        lines.append("  Health Distribution:")
        for status, count in summary.get("health_distribution", {}).items():
            lines.append(f"    {status}: {count}")
        lines.append("")
        lines.append("  Opportunity Distribution:")
        for opp, count in summary.get("opportunity_distribution", {}).items():
            lines.append(f"    {opp}: {count}")
        lines.append("")
        lines.append("  By City:")
        for city, count in summary.get("cities", {}).items():
            lines.append(f"    {city}: {count}")
        lines.append("")
        lines.append("  By Sector:")
        for sector, count in summary.get("sectors", {}).items():
            lines.append(f"    {sector}: {count}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("  Business Details:")
        lines.append("-" * 60)

        for biz in businesses[:20]:
            props = biz.get("properties", {})
            lines.append(f"  {biz.get('name', 'Unknown')}")
            lines.append(f"    City: {props.get('city', '-')} | Sector: {props.get('sector', '-')}")
            lines.append(f"    Health: {props.get('health_score', '-')} | Rating: {props.get('rating', '-')} | Opportunity: {props.get('opportunity_level', '-')}")
            lines.append("")

        if len(businesses) > 20:
            lines.append(f"  ... and {len(businesses) - 20} more businesses")

        lines.append("=" * 60)
        return "\n".join(lines)


if __name__ == "__main__":
    from graph.database import GraphDatabase

    with GraphDatabase(":memory:") as db:
        reporter = SearchReporter(db)
        report = reporter.generate_summary_report([])
        print(f"Report: {report}")
