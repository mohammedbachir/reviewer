"""
Live Progress Tracker - refreshes every 10 seconds in CMD.
"""
import os, json, time, sys
from dotenv import load_dotenv
load_dotenv()

try:
    import dns.resolver
    _r = dns.resolver.Resolver()
    _r.nameservers = ["8.8.8.8", "1.1.1.1"]
    dns.resolver.default_resolver = _r
except Exception:
    pass

from curl_cffi import requests as req

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

try:
    from scraper.osint_engine import analyze_domain
    from batch_osint import _extract_domain
except Exception:
    _extract_domain = lambda w: ""

start_time = time.time()

while True:
    try:
        resp = req.get(url + "/rest/v1/businesses?select=id&firebase=neq.%7B%7D&limit=1000", headers=h, timeout=20)
        processed = len(resp.json())

        resp2 = req.get(url + "/rest/v1/businesses?select=id&website=not.is.null&limit=1000", headers=h, timeout=20)
        total = len(resp2.json())

        resp3 = req.get(url + "/rest/v1/businesses?select=firebase,archive,api_keys,crtsh,sherlock&firebase=neq.%7B%7D&limit=1000", headers=h, timeout=20)
        data = resp3.json()

        fb_det = sum(1 for b in data if isinstance(b.get("firebase"), dict) and b["firebase"].get("firebase_risk") in ("DETECTED", "CRITICAL"))
        arc_hi = sum(1 for b in data if isinstance(b.get("archive"), dict) and b["archive"].get("archive_risk") in ("HIGH", "CRITICAL"))
        tot_ak = sum(len(b.get("api_keys", {}).get("api_keys_found", [])) for b in data if isinstance(b.get("api_keys"), dict))
        tot_sh = sum(b.get("sherlock", {}).get("profile_count", 0) for b in data if isinstance(b.get("sherlock"), dict))
        tot_cr = sum(b.get("crtsh", {}).get("subdomain_count", 0) for b in data if isinstance(b.get("crtsh"), dict))

        elapsed = time.time() - start_time
        pct = processed * 100 // total if total > 0 else 0
        remaining = total - processed
        rate = processed / elapsed if elapsed > 0 else 1
        eta = remaining / rate if rate > 0 else 0

        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)

        import subprocess
        subprocess.run("cls", shell=True, capture_output=True)

        print("=" * 60)
        print("       CRISORA OSINT - LIVE TRACKER")
        print("=" * 60)
        print()
        print(f"  [{bar}] {pct}%")
        print(f"  {processed} / {total} businesses")
        print(f"  Remaining: {remaining}")
        print()
        print("-" * 60)
        print(f"  Firebase detected:   {fb_det}")
        print(f"  High-risk archive:   {arc_hi}")
        print(f"  API keys exposed:    {tot_ak}")
        print(f"  Social profiles:     {tot_sh}")
        print(f"  Subdomains:          {tot_cr}")
        print("-" * 60)
        print(f"  Speed: {rate:.1f} biz/min")
        mins = int(eta // 60)
        secs = int(eta % 60)
        print(f"  ETA: {mins}m {secs}s")
        print(f"  Elapsed: {int(elapsed//60)}m {int(elapsed%60)}s")
        print("=" * 60)
        print("  Press Ctrl+C to stop")
        print("  Refreshes every 10 seconds")

    except Exception as e:
        print(f"\n  Error: {e}")
        print("  Retrying in 10s...")

    time.sleep(10)
