"""
FindLeads — Hard Reset System State
Resets current_target_index to 0 in Supabase system_state table.
Run once after updating targets.json.
"""

import os
import sys
import json
from dotenv import load_dotenv
from curl_cffi import requests as cffi_requests

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lgbzpwzpkzbquuwwhbin.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def reset():
    # 1. Read current state
    resp = cffi_requests.get(
        f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
        headers=HEADERS,
        timeout=10,
    )
    if resp.status_code == 200 and resp.json():
        old = resp.json()[0]
        print(f"  Current index: {old.get('current_index', '?')}")
        print(f"  Total runs:    {old.get('total_runs', '?')}")
    else:
        print("  No system_state row found. Creating one.")

    # 2. Reset to 0
    patch_resp = cffi_requests.patch(
        f"{SUPABASE_URL}/rest/v1/system_state?id=eq.1",
        json={
            "current_index": 0,
            "last_target": "",
            "updated_at": "now()",
        },
        headers=HEADERS,
        timeout=10,
    )

    if patch_resp.status_code in (200, 204):
        print("  RESET OK — current_index = 0")
    else:
        print(f"  RESET FAILED: {patch_resp.status_code} {patch_resp.text[:200]}")
        return False

    # 3. Load targets and show what will run first
    targets_path = os.path.join(ROOT_DIR, "targets.json")
    with open(targets_path) as f:
        raw = json.load(f)
    targets = raw if isinstance(raw, list) else raw.get("targets", [])

    print(f"\n  Targets loaded: {len(targets)}")
    print(f"  First target:   {targets[0]}")
    print(f"  Last target:    {targets[-1]}")
    return True


if __name__ == "__main__":
    print("\n  === FindLeads — Hard Reset ===\n")
    ok = reset()
    sys.exit(0 if ok else 1)
