"""Verify data quality fix — check name extraction"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper.finder import search_businesses

print("=" * 70)
print("  Data Quality Verification Test")
print("=" * 70)

tests = [
    ("Miami", "Med Spa"),
    ("Houston", "HVAC Contractor"),
    ("Chicago", "Personal Injury Lawyer"),
]

for city, sector in tests:
    print(f"\n--- {city} / {sector} ---")
    businesses = search_businesses(city, sector, 3)
    for b in businesses:
        name = b.get("name", "")
        website = b.get("website", "")
        bad_kw = ["near", "yellowpages", "bbb", "yelp", "best ", "top ", "compare", "home |", "contact us"]
        is_bad = any(kw in name.lower() for kw in bad_kw)
        is_long = len(name) > 60
        has_pipe = "|" in name
        status = "BAD" if (is_bad or is_long or has_pipe) else "OK"
        print(f"  [{status}] {name[:55]}")
        print(f"       Website: {website[:50]}")
        time.sleep(1)
