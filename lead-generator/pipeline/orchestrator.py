"""
Pipeline #7: Main Orchestrator — REAL INTEGRATION
Ties everything together with REAL Playwright scraping, REAL OSINT, REAL DuckDB storage.
No mock data. Production-ready.
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from finder import find_businesses
from analyzer import analyze_response_rate
from contact import find_email_from_website
from osint.engine import DeepOSINTEngine
from pipeline.db_storage import DBStorage
from pipeline.temporal_tracker import TemporalTracker
from pipeline.alert_engine import AlertEngine
from pipeline.report_generator import ReportGenerator


class PipelineOrchestrator:
    """Main orchestrator that runs the REAL FindLeads pipeline."""

    def __init__(self, db_path: str = None):
        self.storage = DBStorage(db_path)
        self.tracker = TemporalTracker(db_path)
        self.alert_engine = AlertEngine(db_path)
        self.report_gen = ReportGenerator()
        self.osint_engine = DeepOSINTEngine()
        self.run_stats = {
            "start_time": None,
            "end_time": None,
            "city": "",
            "sector": "",
            "businesses_found": 0,
            "emails_found": 0,
            "osint_scanned": 0,
            "alerts_generated": 0,
            "duration_seconds": 0,
        }

    def run(self, city: str, sector: str, limit: int = 50,
            enable_osint: bool = True, enable_alerts: bool = True,
            enable_reports: bool = True) -> Dict:
        """Run the full pipeline with REAL data."""
        self.run_stats["start_time"] = datetime.now().isoformat()
        self.run_stats["city"] = city
        self.run_stats["sector"] = sector
        start_time = time.time()

        print("=" * 60)
        print(f"  FindLeads Pipeline — {sector} in {city}")
        print("=" * 60)

        # Step 1: Record run start
        print("\n[Step 1/7] Recording run...")
        run_id = self.storage.start_run(city, sector)
        print(f"  Run ID: {run_id}")

        # Step 2: Scrape Google Maps (REAL Playwright)
        print("\n[Step 2/7] Scraping Google Maps...")
        businesses = find_businesses(city, sector, limit)
        self.run_stats["businesses_found"] = len(businesses)
        print(f"  Found: {len(businesses)} businesses")

        if not businesses:
            print("  No businesses found. Exiting.")
            self.storage.end_run(run_id, 0, 0, 0, 0, "no_results")
            return self.run_stats

        # Step 3: Analyze reviews (REAL analysis)
        print("\n[Step 3/7] Analyzing reviews...")
        for biz in businesses:
            analyze_response_rate(biz)
        high_priority = sum(1 for b in businesses if b.get("target_priority") == "high")
        print(f"  Analyzed: {len(businesses)} businesses — {high_priority} high priority")

        # Step 4: Find emails (REAL website scraping)
        print("\n[Step 4/7] Finding emails...")
        emails_found = 0
        for biz in businesses:
            website = biz.get("website", "")
            if website:
                try:
                    email = find_email_from_website(website)
                    biz["email"] = email or ""
                    if email:
                        emails_found += 1
                except Exception:
                    biz["email"] = ""
            else:
                biz["email"] = ""
        self.run_stats["emails_found"] = emails_found
        print(f"  Found: {emails_found} emails")

        # Step 5: Store in DuckDB
        print("\n[Step 5/7] Storing in DuckDB...")
        for biz in businesses:
            biz["city"] = city
            biz["sector"] = sector
            business_id = self.storage.store_business(biz)
            biz["id"] = business_id
            if business_id:
                self.tracker.take_all_snapshots([biz])
        db_stats = self.storage.get_stats()
        print(f"  Total businesses in DB: {db_stats.get('businesses', '?')}")
        print(f"  Total snapshots: {db_stats.get('snapshots', '?')}")

        # Step 6: Run Deep OSINT (REAL website analysis)
        if enable_osint:
            print("\n[Step 6/7] Running Deep OSINT...")
            osint_count = 0
            for biz in businesses:
                website = biz.get("website", "")
                if not website:
                    continue

                domain = website.replace("https://", "").replace("http://", "").split("/")[0]
                print(f"  [{osint_count + 1}/{len(businesses)}] Scanning: {domain}")

                try:
                    osint_result = self.osint_engine.analyze(
                        domain=domain,
                        rating=biz.get("rating", 0),
                        review_count=biz.get("review_count", 0),
                        response_rate=biz.get("response_rate", 0),
                    )
                    biz["osint_data"] = osint_result
                    biz["tech_stack"] = osint_result.get("tech", {}).get("detected", [])
                    biz["health_score"] = osint_result.get("health", {}).get("health_score", 50)
                    biz["ssl_grade"] = osint_result.get("ssl_grade", "")

                    # Store OSINT in DB and update health_score
                    bid = biz.get("id", 0) or 0
                    self.storage.store_osint(bid, osint_result)
                    self.storage.update_health(bid, biz["health_score"])
                    osint_count += 1
                    print(f"    -> Tech: {len(biz.get('tech_stack', []))} | Health: {biz['health_score']}/100 | SSL: {biz['ssl_grade']}")
                except Exception as e:
                    print(f"    -> Error: {e}")
                    biz["osint_data"] = {}
                    biz["health_score"] = 50

            self.run_stats["osint_scanned"] = osint_count
            print(f"  OSINT scanned: {osint_count} businesses")
        else:
            print("\n[Step 6/7] OSINT skipped (disabled)")
            self.run_stats["osint_scanned"] = 0

        # Step 7: Generate alerts + reports
        if enable_alerts:
            print("\n[Step 7/7] Generating alerts...")
            alerts = self.alert_engine.check_batch(businesses)
            self.run_stats["alerts_generated"] = len(alerts)
            critical = [a for a in alerts if a["level"] == "critical"]
            print(f"  Alerts: {len(alerts)} total, {len(critical)} critical")
        else:
            alerts = []

        if enable_reports:
            print("\n  Generating reports...")
            csv_path = self.report_gen.generate_csv(businesses)
            txt_path = self.report_gen.generate_text_report(businesses, alerts, self.run_stats)
            json_path = self.report_gen.generate_json(businesses)
            print(f"  CSV: {csv_path}")
            print(f"  TXT: {txt_path}")
            print(f"  JSON: {json_path}")

        # Finish
        duration = time.time() - start_time
        self.run_stats["duration_seconds"] = round(duration, 1)
        self.run_stats["end_time"] = datetime.now().isoformat()
        self.storage.end_run(run_id, len(businesses), self.run_stats["osint_scanned"],
                             emails_found, duration, "completed")

        print("\n" + "=" * 60)
        print("  Pipeline Complete!")
        print(f"  Businesses: {len(businesses)}")
        print(f"  Emails: {emails_found}")
        print(f"  OSINT: {self.run_stats['osint_scanned']}")
        print(f"  Alerts: {self.run_stats['alerts_generated']}")
        print(f"  Duration: {duration:.1f}s")
        print("=" * 60)

        return self.run_stats

    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return self.run_stats.copy()


if __name__ == "__main__":
    import argparse
    import duckdb

    parser = argparse.ArgumentParser(description="FindLeads Pipeline Orchestrator")
    parser.add_argument("--city", default="Austin", help="City to search")
    parser.add_argument("--sector", default="coffee shop", help="Business sector")
    parser.add_argument("--limit", type=int, default=10, help="Max businesses per city")
    parser.add_argument("--db", default=None, help="DuckDB path (default: data.duckdb)")
    parser.add_argument("--multi-city", action="store_true", help="Run across all configured cities")
    parser.add_argument("--no-osint", action="store_true", help="Skip OSINT scanning")
    args = parser.parse_args()

    db_path = args.db or os.path.join(os.path.dirname(__file__), "..", "data.duckdb")

    if args.multi_city:
        CITIES = [
            ("Dubai", "beauty salon"),
            ("Dubai", "dental clinic"),
            ("Dubai", "restaurant"),
            ("Abu Dhabi", "beauty salon"),
            ("Abu Dhabi", "dental clinic"),
            ("Riyadh", "beauty salon"),
            ("Riyadh", "dental clinic"),
            ("Jeddah", "beauty salon"),
            ("Austin", "coffee shop"),
            ("Miami", "dentist"),
        ]
        print("=" * 60)
        print("  FindLeads — MULTI-CITY PARALLEL RUN")
        print(f"  Cities: {len(CITIES)} targets")
        print(f"  DB: {db_path}")
        print("=" * 60)

        for city, sector in CITIES:
            print(f"\n>>> Running: {sector} in {city}")
            orch = PipelineOrchestrator(db_path=db_path)
            try:
                orch.run(city=city, sector=sector, limit=args.limit,
                         enable_osint=not args.no_osint)
            except Exception as e:
                print(f"  ERROR: {e}")
    else:
        print("=" * 60)
        print(f"  FindLeads — {args.sector} in {args.city}")
        print(f"  Limit: {args.limit} | DB: {db_path}")
        print("=" * 60)

        orchestrator = PipelineOrchestrator(db_path=db_path)
        stats = orchestrator.run(
            city=args.city,
            sector=args.sector,
            limit=args.limit,
            enable_osint=not args.no_osint,
            enable_alerts=True,
            enable_reports=True,
        )

        print("\n" + "=" * 60)
        print("  VERIFICATION: Querying DuckDB...")
        print("=" * 60)

        conn = duckdb.connect(db_path)
        try:
            rows = conn.execute("""
                SELECT id, name, city, sector, rating, review_count, website, email, health_score
                FROM businesses
                WHERE city = ? AND sector = ?
                ORDER BY id DESC LIMIT 10
            """, [args.city, args.sector]).fetchall()

            print(f"\n  Businesses in DuckDB: {len(rows)}")
            print(f"  {'ID':<4} {'Name':<30} {'Rating':<7} {'Reviews':<8} {'Health'}")
            print("  " + "-" * 70)
            for row in rows:
                bid, name, c, s, rating, reviews, website, email, health = row
                print(f"  {bid:<4} {(name or '')[:28]:<30} {rating or 0:<7.1f} {reviews or 0:<8} {health or 50}")

            snap_count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
            run_count = conn.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]
            print(f"\n  Total businesses: {total}")
            print(f"  Snapshots: {snap_count}")
            print(f"  Scan runs: {run_count}")
        finally:
            conn.close()

        print("\n" + "=" * 60)
        print("  PIPELINE COMPLETE")
        print("=" * 60)
