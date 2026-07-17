"""
Pipeline #6: Report Generator
Generates CSV and text reports after each scan run.
"""

import csv
import json
import os
from datetime import datetime
from typing import Dict, List


class ReportGenerator:
    """Generates reports from pipeline results."""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_csv(self, businesses: List[Dict], filename: str = None) -> str:
        """Generate CSV report from business data."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"findleads_report_{timestamp}.csv"

        filepath = os.path.join(self.output_dir, filename)

        headers = [
            "Name", "City", "Sector", "Rating", "Reviews", "Phone", "Website",
            "Address", "Priority", "Response Rate", "Unanswered", "Health Score",
        ]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for biz in businesses:
                writer.writerow([
                    biz.get("name", ""),
                    biz.get("city", ""),
                    biz.get("sector", ""),
                    biz.get("rating", 0),
                    biz.get("review_count", 0),
                    biz.get("phone", ""),
                    biz.get("website", ""),
                    biz.get("address", ""),
                    biz.get("target_priority", ""),
                    biz.get("response_rate", 0),
                    biz.get("unanswered_reviews", 0),
                    biz.get("health_score", 50),
                ])

        return filepath

    def generate_text_report(self, businesses: List[Dict], alerts: List[Dict] = None,
                             stats: Dict = None, filename: str = None) -> str:
        """Generate text summary report."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"findleads_summary_{timestamp}.txt"

        filepath = os.path.join(self.output_dir, filename)

        lines = []
        lines.append("=" * 60)
        lines.append("  FindLeads — Scan Report")
        lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)
        lines.append("")

        # Stats summary
        if stats:
            lines.append("--- Scan Statistics ---")
            lines.append(f"  Businesses found: {stats.get('businesses_found', len(businesses))}")
            lines.append(f"  OSINT scanned: {stats.get('osint_scanned', 0)}")
            lines.append(f"  Emails found: {stats.get('emails_found', 0)}")
            lines.append(f"  Duration: {stats.get('duration', 0):.1f}s")
            lines.append("")

        # Priority breakdown
        high = [b for b in businesses if b.get("target_priority") == "high"]
        medium = [b for b in businesses if b.get("target_priority") == "medium"]
        low = [b for b in businesses if b.get("target_priority") == "low"]

        lines.append("--- Priority Breakdown ---")
        lines.append(f"  HIGH priority:   {len(high)} businesses")
        lines.append(f"  MEDIUM priority: {len(medium)} businesses")
        lines.append(f"  LOW priority:    {len(low)} businesses")
        lines.append("")

        # Top targets
        lines.append("--- Top Targets ---")
        sorted_biz = sorted(businesses, key=lambda x: x.get("unanswered_reviews", 0), reverse=True)
        for i, biz in enumerate(sorted_biz[:10]):
            lines.append(f"  {i + 1}. {biz.get('name', '?')} ({biz.get('city', '?')})")
            lines.append(f"     Rating: {biz.get('rating', 0)}/5 | Reviews: {biz.get('review_count', 0)} | Unanswered: {biz.get('unanswered_reviews', 0)}")
            if biz.get("website"):
                lines.append(f"     Website: {biz['website']}")
            lines.append("")

        # Alerts
        if alerts:
            lines.append("--- Alerts ---")
            critical = [a for a in alerts if a["level"] == "critical"]
            warning = [a for a in alerts if a["level"] == "warning"]
            info = [a for a in alerts if a["level"] == "info"]
            lines.append(f"  Critical: {len(critical)}")
            lines.append(f"  Warning:  {len(warning)}")
            lines.append(f"  Info:     {len(info)}")
            for a in critical[:5]:
                lines.append(f"  [CRITICAL] {a['business']}: {a['message']}")
            lines.append("")

        lines.append("=" * 60)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return filepath

    def generate_json(self, businesses: List[Dict], filename: str = None) -> str:
        """Generate JSON report."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"findleads_data_{timestamp}.json"

        filepath = os.path.join(self.output_dir, filename)

        report = {
            "generated_at": datetime.now().isoformat(),
            "total_businesses": len(businesses),
            "businesses": businesses,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        return filepath

    def get_report_files(self) -> List[str]:
        """List all report files."""
        if not os.path.exists(self.output_dir):
            return []
        return [f for f in os.listdir(self.output_dir) if f.endswith(('.csv', '.txt', '.json'))]


if __name__ == "__main__":
    rg = ReportGenerator()

    test_biz = [
        {"name": "Fresh Cuts", "city": "Dubai", "sector": "barbershops", "rating": 2.1, "review_count": 80, "target_priority": "high", "unanswered_reviews": 75, "health_score": 20, "website": "", "phone": "+971501234567", "address": "Dubai Marina"},
        {"name": "Bloom Beauty", "city": "Dubai", "sector": "beauty salons", "rating": 4.0, "review_count": 25, "target_priority": "medium", "unanswered_reviews": 22, "health_score": 45, "website": "https://bloom.com", "phone": "", "address": "JBR"},
    ]

    csv_path = rg.generate_csv(test_biz)
    print(f"[Test] CSV: {csv_path}")

    txt_path = rg.generate_text_report(test_biz, stats={"businesses_found": 2, "duration": 45.2})
    print(f"[Test] TXT: {txt_path}")

    json_path = rg.generate_json(test_biz)
    print(f"[Test] JSON: {json_path}")
