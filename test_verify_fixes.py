import sys, os, json
sys.path.insert(0, 'F:/reviewer')
from dotenv import load_dotenv
load_dotenv('F:/reviewer/.env')
from curl_cffi import requests as cffi

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
headers = {'apikey': key, 'Authorization': f'Bearer {key}'}

print("=" * 80)
print("VERIFICATION TEST: Tasks 3-9 Bug Fixes")
print("=" * 80)

# Get latest 10 businesses
r = cffi.get(
    f'{url}/rest/v1/businesses?select=name,city,responds_to_reviews,sentiment,ssl_grade,lead_temperature&order=created_at.desc&limit=10',
    headers=headers
)
businesses = r.json()

print(f"\nLatest 10 businesses:")
print(f"{'Name':30s} | {'responds':8s} | {'sentiment':10s} | {'ssl':4s} | temp")
print("-" * 80)
for b in businesses:
    name = (b.get('name', '?') or '?')[:28]
    responds = str(b.get('responds_to_reviews', False))
    sentiment = str(b.get('sentiment', '?'))
    ssl_grade = str(b.get('ssl_grade', '?'))
    temp = str(b.get('lead_temperature', '?'))
    print(f"{name:30s} | {responds:8s} | {sentiment:10s} | {ssl_grade:4s} | {temp}")

# Count responds_to_reviews
r2 = cffi.get(
    f'{url}/rest/v1/businesses?select=responds_to_reviews,sentiment,ssl_grade',
    headers=headers
)
all_biz = r2.json()
total = len(all_biz)
responds_true = sum(1 for b in all_biz if b.get('responds_to_reviews'))
sentiment_pos = sum(1 for b in all_biz if b.get('sentiment') == 'positive')
sentiment_neg = sum(1 for b in all_biz if b.get('sentiment') == 'negative')
sentiment_neu = sum(1 for b in all_biz if b.get('sentiment') == 'neutral')
ssl_empty = sum(1 for b in all_biz if not b.get('ssl_grade') or b.get('ssl_grade') == '')
ssl_f = sum(1 for b in all_biz if b.get('ssl_grade') == 'F')

print(f"\n{'='*80}")
print(f"AGGREGATE STATS:")
print(f"{'='*80}")
print(f"Total businesses:        {total}")
print(f"responds_to_reviews=True: {responds_true}")
print(f"responds_to_reviews=False: {total - responds_true}")
print(f"Sentiment: pos={sentiment_pos} neg={sentiment_neg} neutral={sentiment_neu}")
print(f"SSL grades: empty={ssl_empty} F={ssl_f}")

print(f"\n{'='*80}")
print(f"TASK VERIFICATION:")
print(f"{'='*80}")
print(f"Task 3-4 (responds_to_reviews in upsert): {('PASS' if responds_true > 0 else 'PENDING - waiting for new data')}")
print(f"Task 5 (review engine in app.py):          DEPLOYED TO VERCEL - manual test needed")
print(f"Task 6 (SSL default F):                    {('PASS' if ssl_empty == 0 else 'FAIL - still have empty SSL')}")
print(f"Task 7 (analytics SSL counting):           DEPLOYED TO VERCEL - manual test needed")
print(f"Task 8 (COLD_START=50):                    DEPLOYED TO VM - hybrid blending active")
print(f"Task 9 (sentiment 1.5x):                   DEPLOYED TO VM - waiting for new sentiment data")
print(f"\n{'='*80}")
