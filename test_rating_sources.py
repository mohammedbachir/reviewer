import sys, re, json
sys.path.insert(0, '/home/mc/crisora')
from curl_cffi import requests as cffi

session = cffi.Session(impersonate="chrome120")

# Test 1: OSM Overpass — check for review/rating data
print("=" * 60)
print("TEST 1: OSM Overpass rating/review tags")
query = """
[out:json][timeout:10];
(
  node["name"="Bella Family Dental"]["addr:city"="Dallas"](32.7,-96.9,32.9,-96.7);
  way["name"="Bella Family Dental"]["addr:city"="Dallas"](32.7,-96.9,32.9,-96.7);
);
out tags;
"""
resp = session.post("https://overpass-api.de/api/interpreter", data={"data": query}, timeout=15)
if resp.status_code == 200:
    data = resp.json()
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        print(f"  Tags: {json.dumps(tags, indent=2)}")
else:
    print(f"  Overpass: {resp.status_code}")

# Test 2: Overpass with more businesses — check what tags exist
print("\n" + "=" * 60)
print("TEST 2: Sample of businesses with rating/review tags")
query2 = """
[out:json][timeout:10];
area["name"="Dallas"]->.searchArea;
(
  node["amenity"="dentist"](area.searchArea);
  node["amenity"="restaurant"](area.searchArea);
);
out tags limit 20;
"""
resp2 = session.post("https://overpass-api.de/api/interpreter", data={"data": query2}, timeout=15)
if resp2.status_code == 200:
    data2 = resp2.json()
    rating_tags = set()
    for el in data2.get("elements", []):
        tags = el.get("tags", {})
        for k in tags:
            if any(w in k.lower() for w in ["rating", "review", "star", "google", "yelp", "score"]):
                rating_tags.add(k)
        if "contact:website" in tags:
            print(f"  {tags.get('name', '?')}: website={tags['contact:website']}")
    print(f"\n  Rating-related tags found: {rating_tags}")
else:
    print(f"  Overpass: {resp2.status_code}")

# Test 3: Bing search for reviews (with delays)
print("\n" + "=" * 60)
print("TEST 3: Bing review extraction")
import time
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"}

biz = "Bella Family Dental Dallas TX"
q = f"{biz} reviews google maps"
url = f"https://www.bing.com/search?q={q.replace(' ', '+')}"
resp3 = session.get(url, headers=headers, timeout=8)
html = resp3.text
print(f"Status: {resp3.status_code}, len={len(html)}")

# Extract text
text = re.sub(r'<[^>]+>', ' ', html)
text = re.sub(r'\s+', ' ', text)

# Look for ANY numbers near review/rating keywords
for keyword in ["review", "rating", "star", "google", "yelp", "4.", "5.", "3."]:
    idx = 0
    while True:
        idx = text.lower().find(keyword, idx)
        if idx == -1:
            break
        context = text[max(0,idx-30):idx+50]
        nums = re.findall(r'\d+\.?\d*', context)
        if nums and any(1 <= float(n) <= 5 for n in nums if n.replace('.','').isdigit()):
            print(f"  Found '{keyword}': ...{context}... nums={nums}")
        idx += len(keyword)
