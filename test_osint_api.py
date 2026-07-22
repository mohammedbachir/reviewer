import hashlib
from curl_cffi import requests

token = hashlib.sha256("findleads2026".encode()).hexdigest()[:32]
base = "https://reviewer-lovat.vercel.app/api/dashboard"

r = requests.get(f"{base}/osint?token={token}", timeout=30)
data = r.json()
print("Status:", r.status_code)
print("Total companies:", data.get("total_companies"))
print("Firebase detected:", data.get("firebase", {}).get("detected"))
print("Archive high:", data.get("archive", {}).get("high_risk"))
print("API keys total:", data.get("api_keys", {}).get("total_keys"))
print("Sherlock profiles:", data.get("sherlock", {}).get("total_profiles"))
print("crt.sh subs:", data.get("crtsh", {}).get("total_subdomains"))
print("Companies with OSINT:", data.get("companies_with_osint"))
print("Top exposed count:", len(data.get("top_exposed", [])))
if data.get("top_exposed"):
    top = data["top_exposed"][0]
    print(f"Top exposed: {top['name']} (score: {top['risk_score']}, firebase: {top['firebase_risk']}, archive: {top['archive_risk']}, api: {top['api_risk']}, sherlock: {top['sherlock_risk']}, crtsh: {top['crtsh_risk']})")
print("Errors:", data.get("error"))
