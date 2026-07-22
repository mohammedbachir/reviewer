import sys
sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
try:
    from scraper.osint_engine import analyze_domain
    print("OSINT engine imported OK")
except Exception as e:
    print(f"Import error: {e}")
