#!/usr/bin/env python3
"""Standalone diagnostic script — run on VM to see exact errors."""
import os, sys, json, traceback

sys.path.insert(0, "/home/mc/crisora")
os.chdir("/home/mc/crisora")
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("  CRISORA DIAGNOSTIC — Source Data Pipeline Test")
print("=" * 60)

# 1. Env vars
print("\n[1] Environment Variables")
print(f"  CENSUS_API_KEY: {'SET' if os.environ.get('CENSUS_API_KEY') else 'MISSING'}")
print(f"  GOOGLE_PLACES_API_KEY: {'SET' if os.environ.get('GOOGLE_PLACES_API_KEY') else 'MISSING'}")
print(f"  SUPABASE_URL: {'SET' if os.environ.get('SUPABASE_URL') else 'MISSING'}")

# 2. Census
print("\n[2] Census API")
try:
    from scraper.sources.census_api import get_city_demographics
    result = get_city_demographics("Houston")
    print(f"  get_city_demographics('Houston') = {json.dumps(result)[:200]}")
    print(f"  Type: {type(result).__name__}, Empty: {not bool(result)}")
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

# 3. Social Discovery
print("\n[3] Social Discovery")
try:
    from scraper.sources.social_discovery import discover_social_presence
    result = discover_social_presence("Greig Motors", "Houston")
    print(f"  Result: {json.dumps(result)[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

# 4. BBB
print("\n[4] BBB API")
try:
    from scraper.sources.bbb_api import search_business as bbb_search
    result = bbb_search("Greig Motors", "Houston")
    print(f"  Result: {json.dumps(result)[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

# 5. Google Places
print("\n[5] Google Places API")
try:
    from scraper.finder import search_businesses
    results = search_businesses("Houston", "Car Dealer", 2)
    print(f"  Found {len(results)} businesses")
    for b in results[:2]:
        print(f"    - {b.get('name')}: website={bool(b.get('website'))}")
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

# 6. Full enrichment pipeline
print("\n[6] Full Enrichment Pipeline")
try:
    from local_daemon import CrisoraDaemon
    daemon = CrisoraDaemon()
    test_biz = {
        "name": "Test Diagnostic",
        "city": "Houston",
        "sector": "Car Dealer",
        "website": "https://www.greigmotorsinc.com"
    }
    result = daemon.enrich_business(test_biz)
    new_fields = [
        "social_presence_score", "linkedin_url", "facebook_url", "yelp_url",
        "bbb_url", "bbb_rating", "bbb_accredited", "bbb_complaints",
        "census_data", "social_platforms_found"
    ]
    print("  New source fields after enrich_business():")
    for f in new_fields:
        val = result.get(f)
        print(f"    {f}: {val}")
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

# 7. Test upsert with on_conflict
print("\n[7] Upsert Test (on_conflict)")
try:
    from curl_cffi import requests as cffi_requests
    from dotenv import load_dotenv
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    H = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    
    # Test census upsert
    census_data = {"test_diagnostic": True, "population": 12345}
    data = {
        "name": "DIAGNOSTIC TEST",
        "city": "Houston",
        "sector": "Car Dealer",
        "census_data": census_data,
        "social_presence_score": 77,
        "bbb_rating": "DIAG_A+",
    }
    resp = cffi_requests.post(
        f"{url}/rest/v1/businesses?on_conflict=name,city,sector",
        json=data,
        headers={**H, "Prefer": "resolution=merge-duplicates,return=representation"},
        timeout=10,
    )
    print(f"  Status: {resp.status_code}")
    if resp.status_code in (200, 201):
        rows = resp.json()
        if rows:
            print(f"  census_data in DB: {rows[0].get('census_data')}")
            print(f"  social_presence_score in DB: {rows[0].get('social_presence_score')}")
            print(f"  bbb_rating in DB: {rows[0].get('bbb_rating')}")
    else:
        print(f"  Response: {resp.text[:300]}")

    # Cleanup
    cffi_requests.delete(
        f"{url}/rest/v1/businesses?name=eq.DIAGNOSTIC%20TEST&city=eq.Houston&sector=eq.Car%20Dealer",
        headers={**H, "Prefer": "return=minimal"},
        timeout=10,
    )
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("  DIAGNOSTIC COMPLETE")
print("=" * 60)
