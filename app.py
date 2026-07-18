"""
FindLeads — Hugging Face Spaces Entry Point
Runs the orchestrator on a schedule using APScheduler.
Deployed as a "sleeping" web app that wakes up every 6 hours.
"""

import os
import sys
import threading
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify

# Add lead-generator to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lead-generator"))

from pipeline.orchestrator import PipelineOrchestrator

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════
DB_PATH = os.path.join(os.path.dirname(__file__), "lead-generator", "data.duckdb")

CITIES = [
    ("Dubai", "beauty salon"),
    ("Dubai", "dental clinic"),
    ("Abu Dhabi", "beauty salon"),
    ("Riyadh", "beauty salon"),
    ("Riyadh", "dental clinic"),
    ("Austin", "coffee shop"),
    ("Miami", "dentist"),
]

LIMIT_PER_CITY = 10

# ═══════════════════════════════════════════════════════════════
# Flask App (keeps Hugging Face happy)
# ═══════════════════════════════════════════════════════════════
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "service": "FindLeads Data Engine",
        "cities": len(CITIES),
        "limit_per_city": LIMIT_PER_CITY,
        "db_path": DB_PATH,
        "timestamp": datetime.now().isoformat(),
    })

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

@app.route("/stats")
def stats():
    try:
        import duckdb
        conn = duckdb.connect(DB_PATH, read_only=True)
        total = conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]
        cities = conn.execute("SELECT COUNT(DISTINCT city) FROM businesses").fetchone()[0]
        emails = conn.execute("SELECT COUNT(*) FROM businesses WHERE email != ''").fetchone()[0]
        snaps = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        conn.close()
        return jsonify({
            "businesses": total,
            "cities": cities,
            "emails": emails,
            "snapshots": snaps,
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# ═══════════════════════════════════════════════════════════════
# Scraper Job (runs every 6 hours)
# ═══════════════════════════════════════════════════════════════
def run_scraper():
    """Main scraper job — runs all cities."""
    print(f"\n{'='*60}")
    print(f"  FindLeads — SCHEDULED RUN")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Cities: {len(CITIES)}")
    print(f"{'='*60}")

    for city, sector in CITIES:
        print(f"\n>>> {sector} in {city}")
        try:
            orch = PipelineOrchestrator(db_path=DB_PATH)
            orch.run(
                city=city,
                sector=sector,
                limit=LIMIT_PER_CITY,
                enable_osint=True,
                enable_alerts=True,
                enable_reports=False,
            )
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n{'='*60}")
    print(f"  SCHEDULED RUN COMPLETE")
    print(f"{'='*60}")

# ═══════════════════════════════════════════════════════════════
# Scheduler Setup
# ═══════════════════════════════════════════════════════════════
scheduler = BackgroundScheduler()
scheduler.add_job(
    run_scraper,
    "interval",
    hours=6,
    id="findleads_scraper",
    name="FindLeads Scraper",
)
scheduler.start()

# Run immediately on startup (first 6 hours)
print("[Scheduler] Starting first run immediately...")
threading.Thread(target=run_scraper, daemon=True).start()

# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)
