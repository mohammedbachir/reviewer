import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, 'F:/reviewer')
from scraper.osint_engine import check_subdomains_emails, analyze_domain

# Test 1: subdomain lookup
r = check_subdomains_emails('mmdc.ae')
print(f"mmdc.ae: {r['subdomain_count']} subs, {r['email_count']} emails, risk={r['subdomain_risk']}")
for s in r['subdomains_found']:
    print(f"  {s}")

# Test 2: full analyze_domain (what new businesses get)
print("\n--- Full analyze_domain test ---")
result = analyze_domain('mmdc.ae')
print(f"Health: {result['health_score']}/100")
print(f"SSL: {result['ssl_grade']}")
print(f"Tech: {len(result['tech_stack'])}")
print(f"crtsh: {result.get('crtsh', {}).get('subdomain_count', 0)} subs")
print(f"firebase: {result.get('firebase', {}).get('firebase_detected', False)}")
print(f"archive: {result.get('archive', {}).get('archive_total_urls', 0)} urls")
print(f"api_keys: {result.get('api_keys', {}).get('key_count', 0)} keys")
print(f"sherlock: {result.get('sherlock', {}).get('profile_count', 0)} profiles")
