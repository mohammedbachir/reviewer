"""Deep analysis of data quality on the VM"""
from curl_cffi import requests as r
import os, json
from dotenv import load_dotenv
load_dotenv(r"F:\reviewer\.env")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
url = os.environ.get("SUPABASE_URL", "https://lgbzpwzpkzbquuwwhbin.supabase.co")
h = {"apikey": key, "Authorization": f"Bearer {key}"}

# Full stats
resp = r.get(f"{url}/rest/v1/businesses?select=id", headers=h, timeout=5)
total = len(resp.json())

resp2 = r.get(f"{url}/rest/v1/businesses?select=id&email=neq.", headers=h, timeout=5)
with_email = len(resp2.json())

resp3 = r.get(f"{url}/rest/v1/businesses?select=id&health_score=gt.0", headers=h, timeout=5)
with_health = len(resp3.json())

resp4 = r.get(f"{url}/rest/v1/businesses?select=id&ssl_grade=neq.", headers=h, timeout=5)
with_ssl = len(resp4.json())

resp5 = r.get(f"{url}/rest/v1/businesses?select=id&lead_temperature=neq.COLD", headers=h, timeout=5)
scored = len(resp5.json())

resp6 = r.get(f"{url}/rest/v1/businesses?select=id&outreach_hook=neq.", headers=h, timeout=5)
with_hook = len(resp6.json())

resp7 = r.get(f"{url}/rest/v1/businesses?select=id&crisis_probability=gt.0", headers=h, timeout=5)
with_crisis = len(resp7.json())

resp8 = r.get(f"{url}/rest/v1/businesses?select=id&tech_stack=neq.[]", headers=h, timeout=5)
with_tech = len(resp8.json())

print(f"=== DATA QUALITY REPORT ===")
print(f"Total businesses:     {total}")
print(f"With email:           {with_email}/{total} ({100*with_email//max(total,1)}%)")
print(f"With health_score:    {with_health}/{total} ({100*with_health//max(total,1)}%)")
print(f"With ssl_grade:       {with_ssl}/{total} ({100*with_ssl//max(total,1)}%)")
print(f"With lead_temp:       {scored}/{total} ({100*scored//max(total,1)}%)")
print(f"With outreach_hook:   {with_hook}/{total} ({100*with_hook//max(total,1)}%)")
print(f"With crisis_pred:     {with_crisis}/{total} ({100*with_crisis//max(total,1)}%)")
print(f"With tech_stack:      {with_tech}/{total} ({100*with_tech//max(total,1)}%)")

# Check for bad data
resp9 = r.get(f"{url}/rest/v1/businesses?select=name,website,health_score,ssl_grade,lead_temperature&health_score=is.null&limit=10", headers=h, timeout=5)
bad = resp9.json()
print(f"\n=== MISSING health_score (no enrichment) ===")
for b in bad:
    print(f"  {b['name'][:35]:35} | website:{b.get('website','')[:40]}")

# Check websites that are directory sites
resp10 = r.get(f"{url}/rest/v1/businesses?select=name,website&limit=100", headers=h, timeout=5)
all_biz = resp10.json()
bad_sites = []
for b in all_biz:
    w = b.get("website", "")
    if any(d in w for d in ["nextdoor.com", "mapcarta.com", "411.info", "local.us-info.com",
                             "sanantonio.com", "us-info.com", "yellowpages", "yelp.com",
                             "facebook.com", "google.com"]):
        bad_sites.append(b)
print(f"\n=== DIRECTORY/WRONG websites ===")
for b in bad_sites:
    print(f"  {b['name'][:35]:35} | {b.get('website','')[:50]}")
print(f"  Total bad: {len(bad_sites)}")

# Check email quality
resp11 = r.get(f"{url}/rest/v1/businesses?select=name,email,lead_temperature,health_score&email=neq.&order=id.desc&limit=20", headers=h, timeout=5)
recent = resp11.json()
print(f"\n=== LAST 20 WITH EMAIL ===")
for b in recent:
    print(f"  {b['name'][:28]:28} | {b.get('email','')[:30]:30} | {b.get('lead_temperature','?'):5} | h:{b.get('health_score','?')}")
