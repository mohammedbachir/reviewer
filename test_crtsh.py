"""Test crt.sh API directly to check if it works."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from curl_cffi import requests

session = requests.Session(impersonate="chrome120")
domains = [
    "realcleanutah.com",
    "mmdc.ae",
    "abccollision.com",
    "bettyeodayspa.com",
    "velvettaco.com",
]

for domain in domains:
    url = f"https://crt.sh/?q=%.{domain}&output=json"
    print(f"\n--- {domain} ---")
    print(f"URL: {url}")
    try:
        r = session.get(url, timeout=30)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Entries: {len(data)}")
            subdomains = set()
            emails = set()
            for entry in data:
                name_value = entry.get("name_value", "")
                for line in name_value.split("\n"):
                    line = line.strip().lower()
                    if line.endswith(f".{domain}") or line == domain:
                        if "*" not in line:
                            subdomains.add(line)
                    elif "@" in line and line.endswith(f"@{domain}"):
                        emails.add(line)
            print(f"Subdomains: {len(subdomains)}")
            for s in sorted(subdomains)[:5]:
                print(f"  {s}")
            print(f"Emails: {len(emails)}")
            for e in sorted(emails)[:5]:
                print(f"  {e}")
        elif r.status_code == 429:
            print("RATE LIMITED by crt.sh!")
            print(r.text[:300])
        else:
            print(f"Error body: {r.text[:300]}")
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
