"""
Fix existing OSINT data - convert string-stored JSON to proper JSONB.
Safe: only reads existing values, re-saves as proper JSONB objects.
"""
import os, json, time
from dotenv import load_dotenv
load_dotenv()
from curl_cffi import requests as cffi_requests

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

fixed = 0
total = 0
offset = 0

while True:
    resp = cffi_requests.get(
        f"{url}/rest/v1/businesses?select=id,firebase,archive,api_keys,crtsh,sherlock&firebase=neq.%7B%7D&offset={offset}&limit=100",
        headers=h, timeout=15,
    )
    data = resp.json()
    if not data:
        break

    for b in data:
        total += 1
        needs_fix = False
        patch = {}

        for col in ["firebase", "archive", "api_keys", "crtsh", "sherlock"]:
            val = b.get(col)
            if isinstance(val, str) and val:
                try:
                    parsed = json.loads(val)
                    patch[col] = parsed
                    needs_fix = True
                except Exception:
                    pass

        if needs_fix:
            resp_patch = cffi_requests.patch(
                f"{url}/rest/v1/businesses?id=eq.{b['id']}",
                json=patch, headers=h, timeout=10,
            )
            if resp_patch.status_code in (200, 204):
                fixed += 1
                print(f"  Fixed id={b['id']}")

    offset += len(data)
    if len(data) < 100:
        break
    time.sleep(0.5)

print(f"\nDone: {fixed}/{total} businesses fixed")
