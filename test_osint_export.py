import hashlib
from curl_cffi import requests

token = hashlib.sha256("findleads2026".encode()).hexdigest()[:32]
base = "https://reviewer-lovat.vercel.app/api/dashboard"

# Test 1: Firebase detected
r = requests.get(f"{base}/osint-export?token={token}&firebase=yes", timeout=30)
d = r.json()
print("=== Firebase Detected ===")
print(f"Total: {d.get('total')}, Columns: {len(d.get('columns', []))}")
if d.get('rows'):
    print(f"First: {d['rows'][0].get('name')} - project: {d['rows'][0].get('firebase_project')}")

# Test 2: API Keys HIGH
r2 = requests.get(f"{base}/osint-export?token={token}&api_risk=HIGH&min_keys=5", timeout=30)
d2 = r2.json()
print("\n=== API Keys HIGH (5+) ===")
print(f"Total: {d2.get('total')}")
if d2.get('rows'):
    for row in d2['rows'][:3]:
        print(f"  {row.get('name')}: {row.get('api_count')} keys ({row.get('api_types')})")

# Test 3: Risk Score 50+
r3 = requests.get(f"{base}/osint-export?token={token}&min_risk_score=50", timeout=30)
d3 = r3.json()
print("\n=== Risk Score 50+ ===")
print(f"Total: {d3.get('total')}")
if d3.get('rows'):
    for row in d3['rows'][:5]:
        print(f"  {row.get('name')} (score: {row.get('risk_score')}, fb: {row.get('firebase_risk')}, ar: {row.get('archive_risk')}, ak: {row.get('api_risk')})")

# Test 4: Archive HIGH
r4 = requests.get(f"{base}/osint-export?token={token}&archive_risk=HIGH", timeout=30)
d4 = r4.json()
print(f"\n=== Archive HIGH ===")
print(f"Total: {d4.get('total')}")

# Test 5: Sherlock 3+ profiles
r5 = requests.get(f"{base}/osint-export?token={token}&min_profiles=3", timeout=30)
d5 = r5.json()
print(f"\n=== Sherlock 3+ profiles ===")
print(f"Total: {d5.get('total')}")
if d5.get('rows'):
    for row in d5['rows'][:3]:
        print(f"  {row.get('name')}: {row.get('sherlock_count')} profiles ({row.get('sherlock_platforms')})")

# Test 6: Full intel (Risk 30+, HOT)
r6 = requests.get(f"{base}/osint-export?token={token}&min_risk_score=30&temp=HOT", timeout=30)
d6 = r6.json()
print(f"\n=== Full Intel (Risk 30+, HOT) ===")
print(f"Total: {d6.get('total')}")

# Test 7: Custom columns
r7 = requests.get(f"{base}/osint-export?token={token}&min_risk_score=30&columns=name,city,risk_score,firebase_risk,api_count,sherlock_count", timeout=30)
d7 = r7.json()
print(f"\n=== Custom Columns ===")
print(f"Columns: {d7.get('columns')}")
print(f"Total: {d7.get('total')}")
if d7.get('rows'):
    for row in d7['rows'][:3]:
        print(f"  {row}")
