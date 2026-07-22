"""
Check which businesses still have 0/NULL crisis and re-predict only those.
"""
import os, sys, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import load_dotenv
from curl_cffi import requests as cffi_requests

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper.crisis_predictor import (
    CrisisModel, extract_features, calculate_cvss_risk_score,
    generate_recommendations, _enforce_crisis_floors
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

# Fetch all businesses, find those with NULL/0 crisis_probability
all_biz = []
offset = 0
while True:
    r = cffi_requests.get(
        f"{SUPABASE_URL}/rest/v1/businesses?select=*&order=id.asc&limit=500&offset={offset}",
        headers=HEADERS, timeout=30
    )
    batch = r.json()
    if not batch: break
    all_biz.extend(batch)
    if len(batch) < 500: break
    offset += 500

print(f"Total: {len(all_biz)}")

missing = []
for biz in all_biz:
    prob = biz.get("crisis_probability")
    level = biz.get("crisis_risk_level")
    if prob is None or prob == 0 or level is None or level == "UNKNOWN":
        missing.append(biz)

print(f"Missing crisis data: {len(missing)}")

if not missing:
    print("All businesses have crisis data!")
    sys.exit(0)

model = CrisisModel()
updated = 0
errors = 0

for i, biz in enumerate(missing):
    biz_id = biz.get("id")
    name = (biz.get("name") or "")[:35]
    try:
        features = extract_features(biz)
        hybrid_result = model.predict(features)
        prob = _enforce_crisis_floors(biz, hybrid_result["crisis_probability"])
        risk_level = CrisisModel._prob_to_level(prob)
        cvss = calculate_cvss_risk_score(biz.get("vulnerabilities", []))
        recs = generate_recommendations(features, {"crisis_probability": prob, "risk_level": risk_level}, cvss, [])

        patch = {
            "crisis_probability": round(prob, 4),
            "crisis_risk_level": risk_level,
            "cvss_severity": cvss["severity"],
            "cvss_max": cvss["cvss_max"],
            "crisis_recommendations": json.dumps(recs),
        }

        r = cffi_requests.patch(
            f"{SUPABASE_URL}/rest/v1/businesses?id=eq.{biz_id}",
            json=patch, headers=HEADERS, timeout=15
        )

        prob_pct = prob * 100
        print(f"[{i+1}/{len(missing)}] {name:<35} | {prob_pct:5.1f}% {risk_level:<10} | HTTP {r.status_code}")
        updated += 1

        if r.status_code == 429:
            time.sleep(2)

    except Exception as e:
        print(f"[{i+1}] {name}: {e}")
        errors += 1
        time.sleep(5)

print(f"\nDONE: {updated} updated, {errors} errors")
