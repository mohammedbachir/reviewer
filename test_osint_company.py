import hashlib, json
from curl_cffi import requests

token = hashlib.sha256("findleads2026".encode()).hexdigest()[:32]
base = "https://reviewer-lovat.vercel.app/api/dashboard"

# Test company with Firebase
r = requests.get(f"{base}/company/4121?token={token}", timeout=30)
data = r.json()
print("=== Abccollision (ID 4121) ===")
print("Firebase:", json.dumps(data.get("firebase", {}), indent=2))
print("Archive:", json.dumps(data.get("archive", {}), indent=2))
print("API Keys:", json.dumps(data.get("api_keys", {}), indent=2))
print("Sherlock:", json.dumps(data.get("sherlock", {}), indent=2))
print("crt.sh:", json.dumps(data.get("crtsh", {}), indent=2))

# Test company with API keys
r2 = requests.get(f"{base}/company/2696?token={token}", timeout=30)
data2 = r2.json()
print("\n=== Moononyc (ID 2696) ===")
ak = data2.get("api_keys", {})
print(f"API keys: {ak.get('api_key_count', 0)}")
print(f"Risk: {ak.get('api_exposure_risk', 'NONE')}")
keys = ak.get("api_keys_found", [])[:3]
for k in keys:
    print(f"  {k.get('type')}: {k.get('value', '')[:30]}...")
