"""
Reset OSINT data for re-processing with fixed patterns.
Safe: only resets the 5 new columns, nothing else.
"""
import os, json, time
from dotenv import load_dotenv
load_dotenv()

try:
    import dns.resolver
    _r = dns.resolver.Resolver()
    _r.nameservers = ["8.8.8.8", "1.1.1.1"]
    dns.resolver.default_resolver = _r
except Exception:
    pass

from curl_cffi import requests as r

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

reset_count = 0
offset = 0

while True:
    resp = r.get(
        url + f"/rest/v1/businesses?select=id,firebase&firebase=neq.%7B%7D&offset={offset}&limit=100",
        headers=h, timeout=20,
    )
    data = resp.json()
    if not data:
        break

    ids = [str(b["id"]) for b in data]
    id_filter = ",".join(ids)

    empty = {"firebase": {}, "archive": {}, "api_keys": {}, "crtsh": {}, "sherlock": {}}
    resp_patch = r.patch(
        url + f"/rest/v1/businesses?id=in.({id_filter})",
        json=empty,
        headers=h, timeout=15,
    )

    if resp_patch.status_code in (200, 204):
        reset_count += len(ids)
        print(f"  Reset {len(ids)} businesses (total: {reset_count})")
    else:
        print(f"  Error: {resp_patch.status_code} {resp_patch.text[:100]}")

    offset += len(data)
    if len(data) < 100:
        break
    time.sleep(0.5)

print(f"\nDone: {reset_count} businesses reset for re-processing")
