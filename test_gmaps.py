from curl_cffi import requests as cffi
import re, json

s = cffi.Session(impersonate="chrome120")
h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"}

# Test: Google Maps search page
q = "Bella Family Dental Dallas"
url = f"https://www.google.com/maps/search/{q.replace(' ', '+')}"
r = s.get(url, headers=h, timeout=8, allow_redirects=True)
html = r.text
print(f"Google Maps: status={r.status_code}, len={len(html)}")

# Look for JSON-LD
ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"JSON-LD blocks: {len(ld_matches)}")
for m in ld_matches[:3]:
    try:
        data = json.loads(m)
        print(f"  JSON-LD: {json.dumps(data, indent=2)[:500]}")
    except:
        print(f"  JSON-LD (raw): {m[:200]}")

# Look for rating in full HTML
ratings = re.findall(r'"ratingValue"[:\s]*"?(\d+\.?\d*)"?|"reviewCount"[:\s]*"?(\d+)"?|"bestRating"[:\s]*"?(\d+\.?\d*)"?|"aggregateRating"[^}]*?"ratingValue"[:\s]*"?(\d+\.?\d*)"?|"rating"[:\s]*(\d+\.?\d*)', html)
print(f"\nRating data: {ratings[:10]}")

# Look for review count in full HTML
reviews = re.findall(r'"reviewCount"[:\s]*"?(\d+)"?|"numberOfReviews"[:\s]*"?(\d+)"?|"reviews?"[:\s]*"?(\d+)"?', html)
print(f"Review counts: {reviews[:10]}")

# Look for star rating patterns
stars = re.findall(r'(\d+\.?\d*)\s*(?:stars?|star rating|out of 5|/5)', html, re.IGNORECASE)
print(f"Star ratings: {stars[:10]}")

# Look for any JSON with rating
json_blocks = re.findall(r'\{[^{}]{0,500}"rating"[^{}]{0,500}\}', html)
print(f"\nJSON blocks with 'rating': {len(json_blocks)}")
for jb in json_blocks[:3]:
    print(f"  {jb[:200]}")

# Try Google Maps place search API (no key needed for some endpoints)
print(f"\n{'='*60}")
print("Google Maps internal search API:")
search_url = f"https://www.google.com/search?q={q.replace(' ', '+')}+reviews"
r2 = s.get(search_url, headers=h, timeout=8)
html2 = r2.text
print(f"Google Search: status={r2.status_code}, len={len(html2)}")

# Look for knowledge panel data
kp_rating = re.findall(r'(\d+\.?\d*)\s*\((\d[\d,]*)\)', html2)
print(f"Rating (N) patterns: {kp_rating[:5]}")

kp_reviews = re.findall(r'(\d[\d,]*)\s*(?:Google\s+)?reviews?', html2, re.IGNORECASE)
print(f"Review counts: {kp_reviews[:5]}")
