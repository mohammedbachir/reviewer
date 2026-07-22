"""Add data_source column to Supabase"""
from curl_cffi import requests as r
import os
from dotenv import load_dotenv
load_dotenv(r"F:\reviewer\.env")

key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
url = os.environ.get("SUPABASE_URL", "https://lgbzpwzpkzbquuwwhbin.supabase.co")

sql = "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS data_source TEXT DEFAULT 'ddg';"

resp = r.post(
    f"{url}/sql",
    data=sql,
    headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    timeout=10,
)
print(f"SQL status: {resp.status_code}")
print(resp.text[:500])

# Verify
resp2 = r.get(
    f"{url}/rest/v1/businesses?select=data_source&limit=1",
    headers={"apikey": key, "Authorization": f"Bearer {key}"},
    timeout=5,
)
print(f"\nVerify: {resp2.status_code}")
print(resp2.text[:200])
