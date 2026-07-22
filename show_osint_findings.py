import os, json
from dotenv import load_dotenv
load_dotenv()
from curl_cffi import requests

sb = os.environ.get("SUPABASE_URL","")
sk = os.environ.get("SUPABASE_SERVICE_ROLE_KEY","")
h = {"apikey":sk,"Authorization":f"Bearer {sk}"}

# Find businesses with interesting OSINT data
print("=== FIREBASE DETECTED ===")
r = requests.get(f"{sb}/rest/v1/businesses?select=id,name,firebase&firebase->>firebase_detected=eq.true&limit=5", headers=h)
for d in r.json():
    print(json.dumps(d, indent=2, default=str))

print("\n=== API KEYS FOUND (count > 0) ===")
r = requests.get(f"{sb}/rest/v1/businesses?select=id,name,api_keys&api_keys->>api_key_count=gt.0&order=api_keys->>api_key_count.desc&limit=3", headers=h)
for d in r.json():
    print(json.dumps(d, indent=2, default=str))

print("\n=== ARCHIVE SENSITIVE ===")
r = requests.get(f"{sb}/rest/v1/businesses?select=id,name,archive&archive->>archive_sensitive_files=neq.[]&limit=3", headers=h)
data = r.json()
if data:
    for d in data:
        print(json.dumps(d, indent=2, default=str))
else:
    print("None found, trying JSONB contains...")
    r = requests.get(f"{sb}/rest/v1/businesses?select=id,name,archive&archive->>archive_risk=eq.HIGH&limit=3", headers=h)
    for d in r.json():
        print(json.dumps(d, indent=2, default=str))

print("\n=== SHERLOCK MULTIPLE PROFILES ===")
r = requests.get(f"{sb}/rest/v1/businesses?select=id,name,sherlock&sherlock->>profile_count=gte.3&order=sherlock->>profile_count.desc&limit=3", headers=h)
for d in r.json():
    print(json.dumps(d, indent=2, default=str))

print("\n=== CRTSH SUBDOMAINS ===")
r = requests.get(f"{sb}/rest/v1/businesses?select=id,name,crtsh&crtsh->>subdomain_count=gt.0&limit=3", headers=h)
data = r.json()
if data:
    for d in data:
        print(json.dumps(d, indent=2, default=str))
else:
    print("None found")
    r = requests.get(f"{sb}/rest/v1/businesses?select=id,name,crtsh&crtsh->>email_count=gt.0&limit=3", headers=h)
    for d in r.json():
        print(json.dumps(d, indent=2, default=str))
