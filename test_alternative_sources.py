import sys
sys.path.insert(0, 'F:/reviewer')
from curl_cffi import requests as cffi
from urllib.parse import quote_plus
import re, json

session = cffi.Session(impersonate="chrome120")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

business = "Bella Family Dental"
city = "Dallas"

# Source 1: Brave Search (no bot challenge)
print("=" * 80)
print("SOURCE 1: Brave Search")
q = f'{business} {city} reviews rating'
url = f"https://search.brave.com/search?q={quote_plus(q)}"
resp = session.get(url, headers=headers, timeout=5)
print(f"Status: {resp.status_code}, Length: {len(resp.text)}")
html = resp.text

# Check for review data in Brave
count_matches = re.findall(r'(\d[\d,]*)\s*(?:reviews?|ratings?)', html, re.IGNORECASE)
print(f"Review counts found: {count_matches[:5]}")
rating_matches = re.findall(r'(\d+\.?\d*)\s*/\s*5|(\d+\.?\d*)\s*stars?|rating[:\s]+(\d+\.?\d*)', html, re.IGNORECASE)
print(f"Ratings found: {rating_matches[:5]}")

# Source 2: Bing
print("\n" + "=" * 80)
print("SOURCE 2: Bing")
q = f'{business} {city} reviews'
url = f"https://www.bing.com/search?q={quote_plus(q)}"
resp = session.get(url, headers=headers, timeout=5)
print(f"Status: {resp.status_code}, Length: {len(resp.text)}")
html = resp.text

count_matches = re.findall(r'(\d[\d,]*)\s*(?:reviews?|ratings?)', html, re.IGNORECASE)
print(f"Review counts found: {count_matches[:5]}")

# Source 3: Google Places Text Search (free tier)
print("\n" + "=" * 80)
print("SOURCE 3: Google Maps (non-JS)")
# Try the Google Maps API endpoint that returns JSON
q = f'{business} {city}'
url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={quote_plus(q)}&key=AIzaSyDummy"
# Can't use without real key, but let's try the place details approach

# Source 4: Yelp Fusion API (free tier - need key)
# Skip for now

# Source 5: Direct Yelp page scraping
print("\n" + "=" * 80)
print("SOURCE 5: Yelp page scraping")
q = f'{business} {city}'
url = f"https://www.yelp.com/biz/{quote_plus(q.lower().replace(' ', '-').replace(',', '').replace('.', ''))}"
print(f"Trying: {url}")
resp = session.get(url, headers=headers, timeout=5)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    html = resp.text
    # Look for JSON-LD rating data
    ld_match = re.search(r'"aggregateRating"\s*:\s*\{[^}]*"ratingValue"\s*:\s*([\d.]+)[^}]*"reviewCount"\s*:\s*(\d+)', html)
    if ld_match:
        print(f"  Rating: {ld_match.group(1)}, Reviews: {ld_match.group(2)}")
    else:
        ld_match2 = re.search(r'"ratingValue"\s*:\s*([\d.]+).*?"reviewCount"\s*:\s*(\d+)', html[:50000])
        if ld_match2:
            print(f"  Rating: {ld_match2.group(1)}, Reviews: {ld_match2.group(2)}")
        else:
            print("  No rating found in Yelp HTML")

# Source 6: Google Maps place details (no API key - scrape)
print("\n" + "=" * 80)
print("SOURCE 6: Google Maps scrape")
q = f'{business} {city}'
# Use Google Maps search URL
url = f"https://www.google.com/maps/search/{quote_plus(q)}"
resp = session.get(url, headers=headers, timeout=5, allow_redirects=True)
print(f"Status: {resp.status_code}, Final URL: {resp.url[:100]}")
html = resp.text
# Look for rating data in Google Maps HTML
rating_match = re.search(r'(\d+\.?\d*)\s*\((\d[\d,]*)\)', html)
if rating_match:
    print(f"  Rating: {rating_match.group(1)}, Reviews: {rating_match.group(2)}")
else:
    print("  No rating in Google Maps HTML")
