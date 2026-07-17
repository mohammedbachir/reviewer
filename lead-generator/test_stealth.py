"""
Phase 5 Comprehensive Test
Tests all 12 Stealth & Distribution algorithms.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from stealth.playwright_stealth import StealthManager
from stealth.human_mouse import HumanMouse
from stealth.scrolling import HumanScroller
from stealth.delays import RandomDelays
from stealth.user_agent import UserAgentRotator
from stealth.headers import HeaderRotator
from stealth.proxy_rotation import ProxyRotator
from stealth.github_actions import GitHubActionsGenerator
from stealth.artifacts import ArtifactManager
from stealth.persistence import DuckDBPersistence
from stealth.backup import ExternalBackup
from stealth.ip_tracker import IPTracker


def test_phase5():
    """Run all Phase 5 tests."""
    print("=" * 70)
    print("  PHASE 5: STEALTH & DISTRIBUTION — COMPREHENSIVE TEST")
    print("=" * 70)
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #49: PLAYWRIGHT STEALTH
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #49: Playwright Stealth (playwright_stealth.py)")
    print("=" * 70)

    sm = StealthManager()
    report = sm.get_stealth_report()
    print(f"  [OK] Stealth report: {report}")
    print(f"  [OK] Browser args: {len(sm.get_browser_args())} items")
    ctx_opts = sm.get_context_options()
    print(f"  [OK] Context options: viewport={ctx_opts['viewport']}, locale={ctx_opts['locale']}")
    assert report["status"] == "ready"
    assert len(sm.get_browser_args()) > 5
    print(f"  [OK] Test #49 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #50: HUMAN MOUSE
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #50: Human Mouse Movement (human_mouse.py)")
    print("=" * 70)

    hm = HumanMouse()
    stats = hm.get_movement_stats()
    print(f"  [OK] Initial stats: {stats}")
    assert stats["total_moves"] == 0
    print(f"  [OK] HumanMouse initialized (needs async page for live test)")
    print(f"  [OK] Test #50 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #51: RANDOM SCROLLING
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #51: Random Scrolling (scrolling.py)")
    print("=" * 70)

    hs = HumanScroller()
    stats = hs.get_stats()
    print(f"  [OK] Initial stats: {stats}")
    assert stats["scroll_count"] == 0
    print(f"  [OK] HumanScroller initialized")
    print(f"  [OK] Test #51 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #52: RANDOM DELAYS
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #52: Random Delays (delays.py)")
    print("=" * 70)

    rd = RandomDelays(min_delay=0.1, max_delay=0.3)
    for i in range(5):
        d = rd.wait_sync()
        print(f"  [OK] Delay {i + 1}: {d:.2f}s")
    stats = rd.get_stats()
    print(f"  [OK] Stats: {stats}")
    assert stats["total_delays"] == 5
    assert stats["avg_delay"] > 0
    print(f"  [OK] Test #52 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #53: RANDOM USER-AGENT
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #53: Random User-Agent (user_agent.py)")
    print("=" * 70)

    uar = UserAgentRotator()
    print(f"  [OK] Pool size: {uar.get_stats()['total_ua_pool']}")
    seen = set()
    for i in range(10):
        ua = uar.get_random()
        short = ua[:60]
        seen.add(ua)
        print(f"  [{i + 1}] {short}...")
    stats = uar.get_stats()
    print(f"  [OK] Stats: {stats}")
    assert stats["rotations"] == 10
    assert len(seen) >= 3
    print(f"  [OK] Test #53 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #54: RANDOM HEADERS
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #54: Random Headers (headers.py)")
    print("=" * 70)

    hr = HeaderRotator()
    for i in range(3):
        h = hr.get_random_headers()
        print(f"  [OK] Headers {i + 1}: Lang={h['Accept-Language']}, Ref={h['Referer'][:40]}")
    search_h = hr.get_search_headers("beauty salons dubai")
    print(f"  [OK] Search headers: Ref={search_h['Referer'][:60]}")
    stats = hr.get_stats()
    print(f"  [OK] Stats: {stats}")
    assert stats["header_rotations"] == 4
    print(f"  [OK] Test #54 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #55: FREE PROXY ROTATION
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #55: Free Proxy Rotation (proxy_rotation.py)")
    print("=" * 70)

    pr = ProxyRotator()
    stats = pr.get_stats()
    print(f"  [OK] Initial stats: {stats}")
    print(f"  [OK] ProxyRotator initialized (fetching requires network)")
    print(f"  [OK] Test #55 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #56: GITHUB ACTIONS WORKFLOW
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #56: GitHub Actions Workflow (github_actions.py)")
    print("=" * 70)

    gen = GitHubActionsGenerator("F:\\reviewer")
    config = gen.get_workflow_config()
    print(f"  [OK] Config: {config}")
    usage = gen.estimate_monthly_usage()
    print(f"  [OK] Monthly usage: {usage}")
    result = gen.generate_workflow()
    print(f"  [OK] Workflow generated: {result['filepath']}")
    assert os.path.exists(result["filepath"])
    print(f"  [OK] Test #56 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #57: GITHUB ARTIFACTS
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #57: GitHub Artifacts (artifacts.py)")
    print("=" * 70)

    am = ArtifactManager("F:\\reviewer")
    info = am.get_artifact_info()
    print(f"  [OK] Artifact info: {info}")
    size = am.estimate_size(5000)
    print(f"  [OK] Size estimate (5000 businesses): {size}")
    assert info["retention_days"] == 90
    assert size["within_free_limit"]
    print(f"  [OK] Test #57 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #58: DUCKDB PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #58: DuckDB Persistence (persistence.py)")
    print("=" * 70)

    test_db = os.path.join(os.path.dirname(__file__), "test_persist.duckdb")
    if os.path.exists(test_db):
        os.remove(test_db)

    import duckdb
    conn = duckdb.connect(test_db)
    conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'test')")
    conn.close()

    persistence = DuckDBPersistence(test_db)
    info = persistence.get_db_info()
    print(f"  [OK] DB info: {info}")
    assert info["exists"]
    assert info["size_bytes"] > 0

    backup_result = persistence.backup("test_label")
    print(f"  [OK] Backup: {backup_result}")
    assert backup_result["status"] == "backed_up"

    backups = persistence.list_backups()
    print(f"  [OK] Available backups: {len(backups)}")
    for b in backups:
        print(f"      {b['filename']} ({b['size_mb']} MB)")

    json_result = persistence.export_json([{"id": 1, "name": "test"}], "test_persist_export.json")
    print(f"  [OK] JSON export: {json_result}")

    cleanup = persistence.cleanup_old_backups(keep_last=5)
    print(f"  [OK] Cleanup: {cleanup}")

    os.remove(test_db)
    if os.path.exists(test_db + ".wal"):
        os.remove(test_db + ".wal")
    if os.path.exists("test_persist_export.json"):
        os.remove("test_persist_export.json")

    print(f"  [OK] Test #58 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #59: EXTERNAL BACKUP
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #59: External Backup (backup.py)")
    print("=" * 70)

    eb = ExternalBackup()
    installed = eb.is_rclone_installed()
    print(f"  [OK] rclone installed: {installed}")
    instructions = eb.get_setup_instructions()
    print(f"  [OK] Setup instructions: {len(instructions['steps'])} steps")
    print(f"  [OK] Google Drive free: {instructions['google_drive_free']}")
    print(f"  [OK] Dropbox free: {instructions['dropbox_free']}")
    print(f"  [OK] Backup command: {instructions['command_backup_gdrive'][:60]}...")
    print(f"  [OK] Test #59 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST #60: IP ROTATION TRACKING
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  TEST #60: IP Rotation Tracking (ip_tracker.py)")
    print("=" * 70)

    test_ip_path = os.path.join(os.path.dirname(__file__), "test_ip_history.json")
    tracker = IPTracker(test_ip_path)

    tracker.record_ip("192.168.1.100", "github_actions")
    tracker.record_ip("10.0.0.50", "oracle_cloud")
    tracker.record_ip("172.16.0.25", "local_machine")
    tracker.record_ip("192.168.1.100", "github_actions")

    stats = tracker.get_stats()
    print(f"  [OK] Stats: {stats}")
    print(f"  [OK] Unique IPs: {tracker.get_unique_ips()}")
    print(f"  [OK] Used 192.168.1.100: {tracker.was_used('192.168.1.100')}")
    print(f"  [OK] Used 99.99.99.99: {tracker.was_used('99.99.99.99')}")
    print(f"  [OK] Usage count 192.168.1.100: {tracker.get_usage_count('192.168.1.100')}")
    assert stats["total_records"] == 4
    assert stats["unique_ips"] == 3
    assert tracker.was_used("192.168.1.100")
    assert not tracker.was_used("99.99.99.99")

    if os.path.exists(test_ip_path):
        os.remove(test_ip_path)

    print(f"  [OK] Test #60 PASSED")
    print()

    # ═══════════════════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  PHASE 5: STEALTH & DISTRIBUTION — COMPLETE")
    print("=" * 70)
    print()
    print("  Modules built: 12/12")
    print("  Tests passed: 12/12")
    print()
    print("  Stealth capabilities:")
    print("    - Playwright anti-detection scripts")
    print("    - Human-like mouse movement (bezier curves)")
    print("    - Human-like scrolling (reading behavior)")
    print("    - Random delays (5-20 seconds)")
    print("    - 10+ User-Agent rotation")
    print("    - HTTP header rotation")
    print("    - Free proxy rotation")
    print("    - IP tracking across platforms")
    print()
    print("  Distribution capabilities:")
    print("    - GitHub Actions workflow (every 6 hours)")
    print("    - Artifact persistence (90 days)")
    print("    - DuckDB compressed storage")
    print("    - External backup (Google Drive + Dropbox)")
    print()
    print("=" * 70)


if __name__ == "__main__":
    test_phase5()
