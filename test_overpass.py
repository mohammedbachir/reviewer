"""Test Overpass API with correct syntax"""
from curl_cffi import requests as r

# Test Overpass with a simpler query
query = """
[out:json][timeout:10];
(
  node["amenity"="dentist"](25.709,-80.320,25.856,-80.139);
  way["amenity"="dentist"](25.709,-80.320,25.856,-80.139);
);
out center 5;
"""
print("Testing Overpass API...")
resp = r.post("https://overpass-api.de/api/interpreter",
              data={"data": query}, timeout=15,
              headers={"User-Agent": "FindLeadsBot/1.0"})
print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('content-type','?')}")
print(f"Response[:200]: {resp.text[:200]}")

data = resp.json()
elements = data.get("elements", [])
print(f"Elements found: {len(elements)}")
for e in elements[:5]:
    tags = e.get("tags", {})
    lat = e.get("lat") or e.get("center", {}).get("lat", "")
    lon = e.get("lon") or e.get("center", {}).get("lon", "")
    print(f"  - {tags.get('name','?')} | phone: {tags.get('phone','')} | website: {tags.get('website','')} | ({lat},{lon})")

# Test with category mapping for Overpass
print("\n\nTesting category mapping...")
CATEGORY_MAP = {
    "dentist": "amenity=dentist",
    "dental clinic": "amenity=dentist",
    "beauty salon": "amenity=beauty_salon",
    "hair salon": "shop=hairdresser",
    "spa": "amenity=spa",
    "med spa": "amenity=clinic",
    "plastic surgery": "amenity=clinic",
    "solar": "shop=solar_panels",
    "hvac": "shop=heating",
    "plumber": "craft=plumber",
    "electrician": "craft=electrician",
    "restaurant": "amenity=restaurant",
    "cafe": "amenity=cafe",
    "gym": "leisure=fitness_centre",
    "pharmacy": "amenity=pharmacy",
    "lawyer": "office=lawyer",
    "accountant": "office=accountant",
    "car repair": "shop=car_repair",
    "real estate": "office=estate_agent",
    "moving company": "office=moving_company",
}
for cat, osm_tag in CATEGORY_MAP.items():
    print(f"  {cat} -> {osm_tag}")
