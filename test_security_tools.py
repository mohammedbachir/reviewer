import sys, os, json
sys.path.insert(0, 'F:/reviewer')
from dotenv import load_dotenv
load_dotenv('F:/reviewer/.env')
from curl_cffi import requests as cffi

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
headers = {'apikey': key, 'Authorization': f'Bearer {key}'}

print("=" * 80)
print("SECURITY TOOLS VERIFICATION (Tasks 10-14)")
print("=" * 80)

# Get businesses with security warnings
r = cffi.get(
    f'{url}/rest/v1/businesses?select=name,security_warnings,ssl_grade,health_score&order=created_at.desc&limit=20',
    headers=headers
)
businesses = r.json()

print(f"\nLatest 20 businesses — security data:")
print(f"{'Name':30s} | {'SSL':4s} | {'Health':6s} | Security Warnings")
print("-" * 100)
for b in businesses:
    name = (b.get('name', '?') or '?')[:28]
    ssl = b.get('ssl_grade', '?')
    health = b.get('health_score', '?')
    warnings = b.get('security_warnings', '')
    if isinstance(warnings, str):
        try:
            warnings = json.loads(warnings) if warnings else []
        except:
            warnings = [warnings] if warnings else []
    warn_str = ', '.join(warnings[:3]) if warnings else 'none'
    print(f"{name:30s} | {ssl:4s} | {health:>6} | {warn_str}")

# Count stats
r2 = cffi.get(
    f'{url}/rest/v1/businesses?select=security_warnings,ssl_grade',
    headers=headers
)
all_biz = r2.json()
total = len(all_biz)
with_warnings = 0
for b in all_biz:
    w = b.get('security_warnings', '')
    if isinstance(w, str):
        try:
            w = json.loads(w) if w else []
        except:
            w = [w] if w else []
    if w:
        with_warnings += 1

ssl_dist = {}
for b in all_biz:
    g = b.get('ssl_grade', '?') or '?'
    ssl_dist[g] = ssl_dist.get(g, 0) + 1

print(f"\n{'='*80}")
print(f"AGGREGATE:")
print(f"  Total: {total}")
print(f"  With security warnings: {with_warnings}")
print(f"  SSL distribution: {ssl_dist}")
print(f"{'='*80}")
