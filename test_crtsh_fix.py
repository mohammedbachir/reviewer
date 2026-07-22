import os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, 'F:/reviewer')
from scraper.osint_engine import check_subdomains_emails

domains = ['realcleanutah.com', 'mmdc.ae', 'abccollision.com']
for d in domains:
    print(f'\n--- {d} ---')
    r = check_subdomains_emails(d)
    print(f'  subdomains: {r["subdomain_count"]}')
    print(f'  emails: {r["email_count"]}')
    for s in r['subdomains_found'][:5]:
        print(f'    {s}')
