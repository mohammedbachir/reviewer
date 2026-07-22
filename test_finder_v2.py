"""Test the updated finder.py with all sources"""
import sys
sys.path.insert(0, r"F:\reviewer")
import logging
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from scraper.finder import search_businesses

print("=" * 60)
print("TEST: All sources combined")
print("=" * 60)

results = search_businesses("Miami", "dentist", limit=10)
print(f"\nTotal results: {len(results)}")

# Count by source
sources = {}
for r in results:
    s = r.get("source", "unknown")
    sources[s] = sources.get(s, 0) + 1
print(f"By source: {sources}")

for i, r in enumerate(results, 1):
    print(f"\n  {i}. {r['name']}")
    print(f"     Phone: {r.get('phone', '')}")
    print(f"     Website: {r.get('website', '')[:60]}")
    print(f"     Address: {r.get('address', '')[:60]}")
    print(f"     Source: {r.get('source', '?')}")
