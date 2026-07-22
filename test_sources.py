"""Test all data sources before integration"""
import json
import re
from curl_cffi import requests as r

# Source 1: BizData API (OpenStreetMap)
print("=" * 60)
print("SOURCE 1: BizData API")
print("=" * 60)
try:
    resp = r.get("https://bizdata-web.vercel.app/api/businesses?location=Miami&category=dentist&limit=5", timeout=10)
    data = resp.json()
    print(f"Status: {resp.status_code}, Total: {data.get('total', 0)}")
    for b in data.get("businesses", [])[:3]:
        print(f"  - {b.get('name','?')} | addr: {b.get('address','?')[:50]} | phone: {b.get('phone','')}")
    print(f"Fields available: {list(data.get('businesses', [{}])[0].keys()) if data.get('businesses') else 'none'}")
except Exception as e:
    print(f"ERROR: {e}")

# Source 2: Google Maps via DDG
print("\n" + "=" * 60)
print("SOURCE 2: Google Maps via DDG")
print("=" * 60)
try:
    session = r.Session(impersonate="chrome120")
    url = "https://html.duckduckgo.com/html/?q=dental+clinic+in+Miami+site:google.com/maps"
    resp = session.get(url, timeout=10, headers={"Accept-Language": "en-US,en;q=0.9"})
    print(f"DDG Status: {resp.status_code}")
    # Extract google maps place names
    maps_urls = re.findall(r'google\.com/maps/place/([^/"]+)', resp.text)
    print(f"Maps URLs found: {len(maps_urls)}")
    for u in maps_urls[:5]:
        print(f"  - {u[:80]}")
    # Extract result snippets
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    print(f"DDG titles found: {len(titles)}")
except Exception as e:
    print(f"ERROR: {e}")

# Source 3: Yelp (no API key, scrape HTML)
print("\n" + "=" * 60)
print("SOURCE 3: Yelp search via DDG")
print("=" * 60)
try:
    session = r.Session(impersonate="chrome120")
    url = "https://html.duckduckgo.com/html/?q=site:yelp.com+dental+clinic+Miami"
    resp = session.get(url, timeout=10, headers={"Accept-Language": "en-US,en;q=0.9"})
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    links = re.findall(r'class="result__url"[^>]*>\s*(.*?)\s*</a>', resp.text, re.DOTALL)
    print(f"Yelp results via DDG: {len(titles)}")
    for i in range(min(len(titles), 3)):
        t = re.sub(r'<[^>]+>', '', titles[i]).strip()
        l = re.sub(r'<[^>]+>', '', links[i]).strip() if i < len(links) else ""
        print(f"  - {t[:60]} | {l[:60]}")
except Exception as e:
    print(f"ERROR: {e}")

# Source 4: OpenStreetMap Nominatim (direct)
print("\n" + "=" * 60)
print("SOURCE 4: Nominatim + Overpass (OSM direct)")
print("=" * 60)
try:
    # Step 1: Get bounding box for city
    nom_resp = r.get("https://nominatim.openstreetmap.org/search?q=Miami&format=json&limit=1",
                      headers={"User-Agent": "FindLeadsBot/1.0"}, timeout=10)
    nom_data = nom_resp.json()
    if nom_data:
        bb = nom_data[0].get("boundingbox", [])
        print(f"City: {nom_data[0].get('display_name','?')[:60]}")
        print(f"Bounding box: {bb}")
        # Step 2: Query Overpass for dentists
        if len(bb) == 4:
            south, north, west, east = bb[0], bb[1], bb[2], bb[3]
            overpass_query = f"""
            [out:json][timeout:10];
            (
              node["amenity"="dentist"]({south},{west},{north},{east});
              way["amenity"="dentist"]({south},{west},{north},{east});
            );
            out center 10;
            """
            o_resp = r.post("https://overpass-api.de/api/interpreter",
                           data={"data": overpass_query}, timeout=15)
            o_data = o_resp.json()
            elements = o_data.get("elements", [])
            print(f"Dentists found via Overpass: {len(elements)}")
            for e in elements[:3]:
                tags = e.get("tags", {})
                print(f"  - {tags.get('name','?')} | phone: {tags.get('phone','')} | website: {tags.get('website','')}")
    else:
        print("Could not geocode Miami")
except Exception as e:
    print(f"ERROR: {e}")
