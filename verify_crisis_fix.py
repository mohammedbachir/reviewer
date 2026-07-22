import hashlib
from curl_cffi import requests

token = hashlib.sha256("findleads2026".encode()).hexdigest()[:32]
base = "https://reviewer-lovat.vercel.app/api/dashboard"

# 1. Verify Abccollision crisis is now correct
r = requests.get(f"{base}/company/4121?token={token}", timeout=30)
d = r.json()
print("=== Abccollision (was 8.3% LOW) ===")
print(f"Crisis: {d.get('crisis_probability', 0)*100:.1f}% ({d.get('crisis_risk_level')})")
recs = d.get("crisis_recommendations", [])
if isinstance(recs, str):
    import json
    recs = json.loads(recs)
print(f"Recommendations: {len(recs)}")
for r in recs[:3]:
    print(f"  [{r.get('priority')}] {r.get('category')}: {r.get('message', '')[:70]}")

# 2. Overall crisis stats
r2 = requests.get(f"{base}/crisis?token={token}", timeout=30)
d2 = r2.json()
print(f"\n=== Crisis Distribution (post-OSINT) ===")
for level, count in d2.get("risk_distribution", {}).items():
    if count > 0:
        print(f"  {level}: {count}")

# 3. Count companies with crisis > 50%
risk_companies = d2.get("companies_at_risk", [])
print(f"\nCompanies at risk (>25%): {len(risk_companies)}")
critical = [c for c in risk_companies if c.get("crisis_risk_level") == "CRITICAL"]
high = [c for c in risk_companies if c.get("crisis_risk_level") == "HIGH"]
print(f"  CRITICAL: {len(critical)}")
print(f"  HIGH: {len(high)}")
