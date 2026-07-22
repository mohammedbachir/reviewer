"""
FAST crtsh refetch — CertSpotter only (crt.sh is rate limited).
~3 seconds per business = ~77 minutes for 1548.
"""
import os, sys, json, time
from dotenv import load_dotenv
from curl_cffi import requests as cffi_requests
from urllib.parse import urlparse

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
LOG = "F:/reviewer/crtsh_progress.log"

def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def certspotter_subdomains(domain):
    session = cffi_requests.Session(impersonate="chrome120")
    url = f"https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true&expand=dns_names&match_wildcards=true&limit=100"
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            subs = set()
            for cert in data:
                for name in cert.get("dns_names", []):
                    name = name.strip().lower()
                    if name.endswith(f".{domain}") or name == domain:
                        if "*" not in name:
                            subs.add(name)
            return sorted(subs)
        return []
    except:
        return []

log("=== FAST CRTSH REFETCH ===")

# Fetch all businesses
all_biz = []
offset = 0
while True:
    r = cffi_requests.get(
        f"{SUPABASE_URL}/rest/v1/businesses?select=id,name,website,crtsh&order=id.asc&limit=1000&offset={offset}",
        headers=HEADERS, timeout=60
    )
    batch = r.json()
    if not batch: break
    all_biz.extend(batch)
    if len(batch) < 1000: break
    offset += 1000

log(f"Total: {len(all_biz)}")

# Find empty crtsh with website
empty = []
for b in all_biz:
    crt = b.get("crtsh")
    if isinstance(crt, str):
        try: crt = json.loads(crt)
        except: crt = {}
    if (not crt) or (isinstance(crt, dict) and crt.get("subdomain_count", 0) == 0):
        if b.get("website"):
            empty.append(b)

log(f"Empty crtsh with website: {len(empty)}")

# Process
updated = 0
errors = 0
t0 = time.time()

for i, biz in enumerate(empty):
    biz_id = biz["id"]
    name = (biz.get("name") or "")[:30]
    website = biz.get("website", "")

    try:
        parsed = urlparse(website)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        domain = domain.split("/")[0].split(":")[0]
    except:
        continue

    if not domain or "." not in domain:
        continue

    try:
        subs = certspotter_subdomains(domain)
        patch = {"crtsh": {
            "subdomains_found": subs[:50],
            "subdomain_count": len(subs),
            "emails_found": [],
            "email_count": 0,
            "subdomain_risk": "HIGH" if len(subs) > 20 else ("MEDIUM" if len(subs) > 5 else "NONE"),
        }}
        r = cffi_requests.patch(
            f"{SUPABASE_URL}/rest/v1/businesses?id=eq.{biz_id}",
            json=patch, headers=HEADERS, timeout=15
        )
        elapsed = int(time.time() - t0)
        remaining = len(empty) - i - 1
        eta = int((elapsed / (i + 1)) * remaining) if i > 0 else 0
        log(f"[{i+1}/{len(empty)}] {name} | {len(subs)} subs | {r.status_code} | ETA {eta}s")
        updated += 1

        if r.status_code == 429:
            time.sleep(5)

    except Exception as e:
        log(f"[{i+1}] {name} ERR: {e}")
        errors += 1
        time.sleep(1)

elapsed = int(time.time() - t0)
log(f"=== DONE in {elapsed}s ({elapsed//60}m): {updated} updated, {errors} errors ===")
