"""
FindLeads — Replit Entry Point (Keep-Alive Server)
====================================================
Flask server on port 8080.
UptimeRobot pings / every 5 min → keeps Replit alive.
Background thread runs full orchestrator every 6 hours.
"""

import os
import sys
import threading
import time
from datetime import datetime

# ── Add lead-generator to path ──────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LG_DIR = os.path.join(ROOT_DIR, "lead-generator")
sys.path.insert(0, LG_DIR)

DB_PATH = os.path.join(LG_DIR, "data.duckdb")

# ════════════════════════════════════════════════════════════════
# ORCHESTRATOR LOOP (runs in background thread)
# ════════════════════════════════════════════════════════════════

CITIES = [
    ("Dubai", "beauty salon"),
    ("Dubai", "dental clinic"),
    ("Riyadh", "beauty salon"),
    ("Riyadh", "dental clinic"),
    ("Austin", "coffee shop"),
]

_last_run = {"time": "Never", "status": "Waiting", "businesses": 0, "emails": 0}


def run_orchestrator_cycle():
    """Run the full pipeline for all cities, then sleep 6 hours."""
    global _last_run

    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'=' * 60}")
        print(f"  FindLeads — SCHEDULED RUN")
        print(f"  {now}")
        print(f"{'=' * 60}")

        total_biz = 0
        total_emails = 0
        status = "running"

        try:
            from pipeline.orchestrator import PipelineOrchestrator

            for city, sector in CITIES:
                print(f"\n>>> {sector} in {city}")
                try:
                    orch = PipelineOrchestrator(db_path=DB_PATH)
                    stats = orch.run(
                        city=city,
                        sector=sector,
                        limit=10,
                        enable_osint=True,
                        enable_alerts=True,
                        enable_reports=False,  # skip reports to save disk
                    )
                    total_biz += stats.get("businesses_found", 0)
                    total_emails += stats.get("emails_found", 0)
                except Exception as e:
                    print(f"  ERROR: {e}")

            status = "completed"

        except Exception as e:
            print(f"  FATAL: {e}")
            status = f"error: {e}"

        _last_run = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "businesses": total_biz,
            "emails": total_emails,
        }

        print(f"\n{'=' * 60}")
        print(f"  CYCLE DONE — {total_biz} businesses, {total_emails} emails")
        print(f"  Next run in 6 hours...")
        print(f"{'=' * 60}")

        time.sleep(21600)  # 6 hours


# ════════════════════════════════════════════════════════════════
# FLASK SERVER (UptimeRobot hits this to keep alive)
# ════════════════════════════════════════════════════════════════

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>FindLeads</title></head>
    <body style="font-family:monospace; background:#0f172a; color:#22d3ee; padding:40px;">
        <h1>FindLeads Scraper</h1>
        <p>Status: <span style="color:#4ade80;">RUNNING</span></p>
        <p>Last cycle: {_last_run['time']}</p>
        <p>Last result: {_last_run['status']}</p>
        <p>Businesses this run: {_last_run['businesses']}</p>
        <p>Emails found: {_last_run['emails']}</p>
        <hr style="border-color:#334155;">
        <p><a href="/stats" style="color:#22d3ee;">/stats</a> — Database statistics</p>
        <p><a href="/health" style="color:#22d3ee;">/health</a> — Health check</p>
    </body>
    </html>
    """


@app.route("/health")
def health():
    return "OK"


@app.route("/stats")
def stats():
    try:
        import duckdb
        conn = duckdb.connect(DB_PATH, read_only=True)
        total = conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]
        cities = conn.execute("SELECT COUNT(DISTINCT city) FROM businesses").fetchone()[0]
        sectors = conn.execute("SELECT COUNT(DISTINCT sector) FROM businesses").fetchone()[0]
        emails = conn.execute("SELECT COUNT(*) FROM businesses WHERE email != ''").fetchone()[0]
        snaps = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        runs = conn.execute("SELECT COUNT(*) FROM scan_runs").fetchone()[0]
        conn.close()

        return jsonify({
            "total_businesses": total,
            "cities": cities,
            "sectors": sectors,
            "emails_found": emails,
            "snapshots": snaps,
            "scan_runs": runs,
            "last_cycle": _last_run,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# STARTUP
# ════════════════════════════════════════════════════════════════

# Launch orchestrator in background thread (daemon=True → dies with main)
scraper_thread = threading.Thread(target=run_orchestrator_cycle, daemon=True)
scraper_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
