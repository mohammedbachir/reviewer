"""Test fixed multi-source finder"""
import sys
sys.path.insert(0, r"F:\reviewer")
import logging
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from scraper.finder import search_businesses

# Test 1: HVAC in Houston (BizData was returning 400 before)
print("=" * 60)
print("TEST 1: HVAC in Houston")
print("=" * 60)
results = search_businesses("Houston", "HVAC Contractor", limit=5)
print(f"Results: {len(results)}")
for r in results:
    print(f"  {r['name'][:30]:30} | website:{bool(r.get('website'))} | email:{bool(r.get('email'))} | src:{r.get('source','?')}")

# Test 2: Solar in Phoenix
print("\n" + "=" * 60)
print("TEST 2: Solar in Phoenix")
print("=" * 60)
results2 = search_businesses("Phoenix", "Solar Panel Installer", limit=5)
print(f"Results: {len(results2)}")
for r in results2:
    print(f"  {r['name'][:30]:30} | website:{bool(r.get('website'))} | email:{bool(r.get('email'))} | src:{r.get('source','?')}")
