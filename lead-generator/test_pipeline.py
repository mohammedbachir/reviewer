"""
Phase 6 Comprehensive Test
Tests all 7 Pipeline modules (Automated Search & DB Storage).
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from pipeline.auto_scraper import AutoScraper
from pipeline.osint_runner import OSINTRunner
from pipeline.db_storage import DBStorage
from pipeline.temporal_tracker import TemporalTracker
from pipeline.alert_engine import AlertEngine
from pipeline.report_generator import ReportGenerator
from pipeline.orchestrator import PipelineOrchestrator


def test_phase6():
    """Run all Phase 6 tests."""
    print("=" * 70)
    print("  PHASE 6: AUTOMATED SEARCH & DB STORAGE — TEST")
    print("=" * 70)
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #1: AUTO SCRAPER
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #1: Auto Scraper (auto_scraper.py)")
    print("=" * 70)

    scraper = AutoScraper()
    stats = scraper.get_stats()
    print(f"  [OK] Stats: {stats}")
    print(f"  [OK] UA pool: {scraper.ua_rotator.get_stats()['total_ua_pool']}")
    print(f"  [OK] Delays: {scraper.delays.get_stats()['config']}")
    results = scraper.get_results()
    print(f"  [OK] Results: {len(results)} (empty before scraping)")
    assert stats["total_scraped"] == 0
    assert len(results) == 0
    print(f"  [OK] Test #1 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #2: OSINT RUNNER
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #2: OSINT Runner (osint_runner.py)")
    print("=" * 70)

    osint = OSINTRunner()
    stats = osint.get_stats()
    print(f"  [OK] Stats: {stats}")
    # Test scan_business with no website
    result = osint.scan_business({"name": "No Website Biz", "website": ""})
    print(f"  [OK] No website result: {result['status']}")
    assert result["status"] == "no_website"
    results = osint.get_results()
    print(f"  [OK] Results: {len(results)}")
    print(f"  [OK] Test #2 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #3: DB STORAGE
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #3: DB Storage (db_storage.py)")
    print("=" * 70)

    db = DBStorage(":memory:")
    stats = db.get_stats()
    print(f"  [OK] Initial stats: {stats}")
    assert stats["businesses"] == 0

    # Store businesses
    test_biz = [
        {"name": "Fresh Cuts", "city": "Dubai", "sector": "barbershops", "rating": 2.1, "review_count": 80, "website": "", "phone": "+971501234567", "target_priority": "high"},
        {"name": "Bloom Beauty", "city": "Dubai", "sector": "beauty salons", "rating": 4.0, "review_count": 25, "website": "https://bloom.com", "phone": "", "target_priority": "medium"},
        {"name": "Al Noor Dental", "city": "Sharjah", "sector": "dental clinics", "rating": 4.8, "review_count": 120, "website": "https://alnoor.com", "phone": "+9716543210", "target_priority": "low"},
    ]

    for biz in test_biz:
        biz_id = db.store_business(biz)
        print(f"  [OK] Stored: {biz['name']} (ID: {biz_id})")
        assert biz_id > 0

    # Test upsert (update existing)
    test_biz[0]["rating"] = 2.5
    updated_id = db.store_business(test_biz[0])
    print(f"  [OK] Updated: {test_biz[0]['name']} (ID: {updated_id})")
    assert updated_id == 1  # Same ID as first insert

    # Store OSINT
    db.store_osint(1, {"tech_stack": ["WordPress"], "ssl_grade": "B"})
    print(f"  [OK] OSINT stored for ID 1")

    # Take snapshot
    db.take_snapshot(1, test_biz[0])
    print(f"  [OK] Snapshot taken for ID 1")

    # Record run
    run_id = db.start_run("Dubai", "barbershops")
    print(f"  [OK] Run started (ID: {run_id})")
    db.end_run(run_id, 3, 2, 1, 45.5, "completed")
    print(f"  [OK] Run ended")

    final_stats = db.get_stats()
    print(f"  [OK] Final stats: {final_stats}")
    assert final_stats["businesses"] == 3
    assert final_stats["snapshots"] >= 1
    assert final_stats["scan_runs"] >= 1
    print(f"  [OK] Test #3 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #4: TEMPORAL TRACKER
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #4: Temporal Tracker (temporal_tracker.py)")
    print("=" * 70)

    # Use the same DB as DBStorage (test #3) so businesses exist
    test_db_path = os.path.join(os.path.dirname(__file__), "test_pipeline_temp.duckdb")
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    db4 = DBStorage(test_db_path)
    for biz in test_biz:
        db4.store_business(biz)

    tracker = TemporalTracker(test_db_path)

    # Take snapshots
    count = tracker.take_all_snapshots(test_biz)
    print(f"  [OK] Snapshots taken: {count}")
    assert count == 3

    # Detect changes (will be empty — only 1 snapshot per business)
    changes = tracker.detect_changes(1)
    print(f"  [OK] Changes detected: {len(changes)} (expected 0 with 1 snapshot)")

    # Get history
    history = tracker.get_business_history(1)
    print(f"  [OK] Business 1 history: {len(history)} snapshots")

    stats = tracker.get_stats()
    print(f"  [OK] Stats: {stats}")

    # Cleanup test db
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print(f"  [OK] Test #4 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #5: ALERT ENGINE
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #5: Alert Engine (alert_engine.py)")
    print("=" * 70)

    alerts_engine = AlertEngine(":memory:")
    alerts = alerts_engine.check_batch(test_biz)
    print(f"  [OK] Alerts generated: {len(alerts)}")
    for a in alerts:
        print(f"      [{a['level'].upper()}] {a['business']}: {a['message']}")

    critical = alerts_engine.get_critical_alerts()
    print(f"  [OK] Critical alerts: {len(critical)}")
    assert len(critical) > 0  # Fresh Cuts should have critical alerts

    stats = alerts_engine.get_stats()
    print(f"  [OK] Stats: {stats}")
    assert stats["total_alerts"] > 0
    print(f"  [OK] Test #5 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #6: REPORT GENERATOR
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #6: Report Generator (report_generator.py)")
    print("=" * 70)

    rg = ReportGenerator()

    csv_path = rg.generate_csv(test_biz)
    print(f"  [OK] CSV: {csv_path}")
    assert os.path.exists(csv_path)

    txt_path = rg.generate_text_report(test_biz, alerts, {"businesses_found": 3, "duration": 45.2})
    print(f"  [OK] TXT: {txt_path}")
    assert os.path.exists(txt_path)

    json_path = rg.generate_json(test_biz)
    print(f"  [OK] JSON: {json_path}")
    assert os.path.exists(json_path)

    files = rg.get_report_files()
    print(f"  [OK] Report files: {len(files)}")
    assert len(files) >= 3

    # Read and verify CSV
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
        print(f"  [OK] CSV rows: {len(lines)} (header + {len(lines) - 1} data)")
        assert len(lines) == 4  # header + 3 businesses

    # Read and verify TXT
    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()
        print(f"  [OK] TXT length: {len(content)} chars")
        assert "Fresh Cuts" in content
        assert "HIGH priority" in content

    print(f"  [OK] Test #6 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #7: PIPELINE ORCHESTRATOR
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #7: Pipeline Orchestrator (orchestrator.py)")
    print("=" * 70)

    orch = PipelineOrchestrator(db_path=":memory:")
    print(f"  [OK] Orchestrator initialized")
    print(f"  [OK] Storage: {orch.storage.get_stats()}")
    print(f"  [OK] Ready to run pipeline")
    print(f"  [OK] Usage: orch.run('Dubai', 'beauty salons', limit=20)")
    print(f"  [OK] Test #7 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════════════════════════════
    print("Cleaning up test reports...")
    for f in os.listdir(rg.output_dir):
        if f.startswith("findleads_"):
            os.remove(os.path.join(rg.output_dir, f))
    print("[OK] Cleanup done")

    # ═══════════════════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════════
    print()
    print("=" * 70)
    print("  PHASE 6: AUTOMATED SEARCH & DB STORAGE — COMPLETE")
    print("=" * 70)
    print()
    print("  Pipeline modules: 7/7")
    print("  Tests passed: 7/7")
    print()
    print("  Pipeline flow:")
    print("    Step 1: Record run start in DuckDB")
    print("    Step 2: Scrape Google Maps (with stealth)")
    print("    Step 3: Analyze review response rates")
    print("    Step 4: Find emails from business websites")
    print("    Step 5: Store everything in DuckDB")
    print("    Step 6: Run Deep OSINT (optional)")
    print("    Step 7: Generate alerts + CSV/TXT/JSON reports")
    print()
    print("=" * 70)


if __name__ == "__main__":
    test_phase6()
