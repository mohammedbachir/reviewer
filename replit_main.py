"""FindLeads — Replit Entry Point"""
import os
import sys
import subprocess
import threading
import time
from datetime import datetime

# Install dependencies
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "flask", "apscheduler", "duckdb", "requests", "beautifulsoup4", "playwright"], check=False)

# Install Playwright
subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lead-generator"))

DB_PATH = os.path.join(os.path.dirname(__file__), "lead-generator", "data.duckdb")

# ═══════════════════════════════════════════════════════════════
# Simple Scraper (for Replit free tier)
# ═══════════════════════════════════════════════════════════════
import requests
from bs4 import BeautifulSoup

def simple_scrape(city, sector, limit=10):
    """Simple scraping using requests."""
    import duckdb
    query = f"{sector} in {city}"
    print(f"[Scraper] Searching: {query}")

    businesses = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        resp = requests.get(f"https://www.google.com/search?q={query}", headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select("div.g")[:limit]:
            title_el = result.select_one("h3")
            link_el = result.select_one("a")
            snippet_el = result.select_one(".VwiC3b")

            if title_el and link_el:
                businesses.append({
                    "name": title_el.get_text(strip=True),
                    "city": city,
                    "sector": sector,
                    "website": link_el.get("href", ""),
                    "rating": 0,
                    "review_count": 0,
                    "email": "",
                    "health_score": 50,
                })

        print(f"[Scraper] Found {len(businesses)} businesses")
    except Exception as e:
        print(f"[Scraper] Error: {e}")

    # Store in DuckDB
    if businesses:
        try:
            conn = duckdb.connect(DB_PATH)
            try:
                conn.execute("CREATE SEQUENCE IF NOT EXISTS node_id_seq START 1")
            except:
                pass
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS businesses (
                        id INTEGER DEFAULT nextval('node_id_seq'),
                        name TEXT, city TEXT, sector TEXT, country TEXT DEFAULT 'UAE',
                        rating REAL DEFAULT 0, review_count INTEGER DEFAULT 0,
                        website TEXT DEFAULT '', email TEXT DEFAULT '', phone TEXT DEFAULT '',
                        address TEXT DEFAULT '', google_url TEXT DEFAULT '', category TEXT DEFAULT '',
                        response_rate INTEGER DEFAULT 0, unanswered_reviews INTEGER DEFAULT 0,
                        target_priority TEXT DEFAULT 'low', health_score INTEGER DEFAULT 50,
                        osint_data TEXT DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (id)
                    )
                """)
            except:
                pass
            for biz in businesses:
                try:
                    conn.execute("""
                        INSERT INTO businesses (name, city, sector, rating, review_count, website, email, health_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [biz["name"], biz["city"], biz["sector"], biz["rating"],
                          biz["review_count"], biz["website"], biz["email"], biz["health_score"]])
                except:
                    pass
            total = conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]
            conn.close()
            print(f"[Scraper] Total in DB: {total}")
        except Exception as e:
            print(f"[Scraper] DB error: {e}")

    return businesses

# ═══════════════════════════════════════════════════════════════
# Scheduled Job
# ═══════════════════════════════════════════════════════════════
CITIES = [
    ("Dubai", "beauty salon"),
    ("Dubai", "dental clinic"),
    ("Riyadh", "beauty salon"),
    ("Austin", "coffee shop"),
]

def run_scheduled():
    print(f"\n{'='*60}")
    print(f"  FindLeads — SCHEDULED RUN")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    for city, sector in CITIES:
        print(f"\n>>> {sector} in {city}")
        try:
            simple_scrape(city, sector, limit=5)
        except Exception as e:
            print(f"  ERROR: {e}")
    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"{'='*60}")

# ═══════════════════════════════════════════════════════════════
# Flask Server (keeps Replit alive)
# ═══════════════════════════════════════════════════════════════
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

@app.route("/")
def home():
    return f"""
    <h1>FindLeads Scraper</h1>
    <p>Status: Running</p>
    <p>Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><a href="/stats">View Stats</a></p>
    <p><a href="/run">Run Now</a></p>
    """

@app.route("/stats")
def stats():
    import duckdb
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        total = conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]
        cities = conn.execute("SELECT COUNT(DISTINCT city) FROM businesses").fetchone()[0]
        emails = conn.execute("SELECT COUNT(*) FROM businesses WHERE email != ''").fetchone()[0]
        conn.close()
        return f"<h2>Stats</h2><p>Total: {total}</p><p>Cities: {cities}</p><p>Emails: {emails}</p>"
    except:
        return "<p>No data yet</p>"

@app.route("/run")
def run_now():
    threading.Thread(target=run_scheduled, daemon=True).start()
    return "<p>Started! Check /stats in 30 seconds.</p>"

@app.route("/health")
def health():
    return "OK"

# ═══════════════════════════════════════════════════════════════
# Start
# ═══════════════════════════════════════════════════════════════
scheduler = BackgroundScheduler()
scheduler.add_job(run_scheduled, "interval", hours=6)
scheduler.start()

# Run on startup
threading.Thread(target=run_scheduled, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
