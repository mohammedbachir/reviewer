import sys
sys.path.insert(0, 'F:/reviewer')
from curl_cffi import requests as cffi
from urllib.parse import quote_plus
import re

session = cffi.Session(impersonate="chrome120")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

business = "Bella Family Dental"
city = "Dallas"

# Source 1: Bing
print("=" * 60)
print("SOURCE 1: Bing")
q = f'{business} {city} reviews'
url = f"https://www.bing.com/search?q={quote_plus(q)}"
resp = session.get(url, headers=headers, timeout=5)
print(f"Status: {resp.status_code}, Length: {len(resp.text)}")
html = resp.text
count_matches = re.findall(r'(\d[\d,]*)\s*(?:reviews?|ratings?)', html, re.IGNORECASE)
print(f"Review counts: {count_matches[:5]}")
rating_matches = re.findall(r'(\d+\.?\d*)\s*/\s*5|rating[:\s]+(\d+\.?\d*)|(\d+\.?\d*)\s*stars?', html, re.IGNORECASE)
print(f"Ratings: {rating_matches[:5]}")

# Source 2: DDG with different session (fresh)
print("\n" + "=" * 60)
print("SOURCE 2: DDG (fresh session)")
session2 = cffi.Session(impersonate="chrome")
q = f'{business} {city} reviews'
url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
resp = session2.get(url, headers=headers, timeout=5)
print(f"Status: {resp.status_code}, Length: {len(resp.text)}")
if resp.status_code == 200 and 'result__snippet' in resp.text:
    print("DDG WORKING!")
elif resp.status_code == 202:
    print("DDG BLOCKED (202 botnet challenge)")
else:
    print(f"DDG: status={resp.status_code}")

# Source 3: Yelp direct page
print("\n" + "=" * 60)
print("SOURCE 3: Yelp direct")
slug = business.lower().replace(' ', '-').replace(',', '').replace('.', '')
url = f"https://www.yelp.com/biz/{slug}-{city.lower().replace(' ', '-')}"
print(f"URL: {url}")
resp = session.get(url, headers=headers, timeout=5)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    html = resp.text
    # Look for JSON-LD
    ld = re.search(r'"aggregateRating"\s*:\s*\{[^}]*?"ratingValue"\s*:\s*([\d.]+)[^}]*?"reviewCount"\s*:\s*(\d+)', html)
    if ld:
        print(f"  Found: rating={ld.group(1)}, reviews={ld.group(2)}")
    # Look for rating in meta
    meta = re.search(r'content="([\d.]+)".*?(\d+)\s*review', html[:20000])
    if meta:
        print(f"  Meta: rating={meta.group(1)}, reviews={meta.group(2)}")
    # Check for rating data anywhere
    r1 = re.findall(r'"ratingValue"[:\s]*([\d.]+)', html)
    r2 = re.findall(r'"reviewCount"[:\s]*(\d+)', html)
    if r1 or r2:
        print(f"  JSON-LD: ratingValues={r1[:3]}, reviewCounts={r2[:3]}")
