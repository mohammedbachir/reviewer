import sys, os
sys.path.insert(0, 'F:/reviewer')
from dotenv import load_dotenv
load_dotenv('F:/reviewer/.env')
from curl_cffi import requests as cffi

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
headers = {'apikey': key, 'Authorization': f'Bearer {key}'}

# Get all businesses and find empty ssl_grade
r = cffi.get(f'{url}/rest/v1/businesses?select=id,ssl_grade', headers=headers)
all_biz = r.json()
empty = [b['id'] for b in all_biz if not b.get('ssl_grade') or b['ssl_grade'] == '']
print(f"Found {len(empty)} businesses with empty SSL grade out of {len(all_biz)} total")

for bid in empty:
    cffi.patch(
        f'{url}/rest/v1/businesses?id=eq.{bid}',
        json={'ssl_grade': 'F'},
        headers={**headers, 'Prefer': 'return=minimal'},
        timeout=5
    )
    print(f"  Fixed: {bid}")

print("Done! Re-checking...")
r2 = cffi.get(f'{url}/rest/v1/businesses?select=id,ssl_grade', headers=headers)
still_empty = [b for b in r2.json() if not b.get('ssl_grade') or b['ssl_grade'] == '']
print(f"Remaining empty SSL: {len(still_empty)}")
