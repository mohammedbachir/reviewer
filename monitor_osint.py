"""
Monitor batch OSINT progress.
Uses dnspython to bypass broken system DNS.
"""
import os, json, sys
from dotenv import load_dotenv
load_dotenv()

# Fix DNS before any network call
try:
    import dns.resolver
    _resolver = dns.resolver.Resolver()
    _resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
    dns.resolver.default_resolver = _resolver
except Exception:
    pass

from curl_cffi import requests as r

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

try:
    resp = r.get(url + "/rest/v1/businesses?select=id&firebase=neq.%7B%7D&limit=1000", headers=h, timeout=20)
    processed = len(resp.json())

    resp2 = r.get(url + "/rest/v1/businesses?select=id&website=not.is.null&limit=1000", headers=h, timeout=20)
    total = len(resp2.json())

    resp3 = r.get(url + "/rest/v1/businesses?select=name,firebase,archive,api_keys,crtsh,sherlock&firebase=neq.%7B%7D&limit=500", headers=h, timeout=20)
    data = resp3.json()

    fb_detect = sum(1 for b in data if isinstance(b.get("firebase"), dict) and b["firebase"].get("firebase_risk") in ("DETECTED", "CRITICAL"))
    arc_high = sum(1 for b in data if isinstance(b.get("archive"), dict) and b["archive"].get("archive_risk") in ("HIGH", "CRITICAL"))
    total_ak = sum(len(b.get("api_keys", {}).get("api_keys_found", [])) for b in data if isinstance(b.get("api_keys"), dict))
    total_sh = sum(b.get("sherlock", {}).get("profile_count", 0) for b in data if isinstance(b.get("sherlock"), dict))
    total_cr = sum(b.get("crtsh", {}).get("subdomain_count", 0) for b in data if isinstance(b.get("crtsh"), dict))

    pct = processed * 100 // total if total > 0 else 0
    print(f"Progress: {processed}/{total} ({pct}%)")
    print(f"  Firebase detected: {fb_detect}")
    print(f"  High-risk archive: {arc_high}")
    print(f"  API keys exposed: {total_ak}")
    print(f"  Sherlock profiles: {total_sh}")
    print(f"  Subdomains: {total_cr}")
except Exception as e:
    print(f"Error: {e}")
