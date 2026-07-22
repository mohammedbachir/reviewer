from curl_cffi import requests as cffi
import re

s = cffi.Session(impersonate="chrome120")
h = {"User-Agent": "Mozilla/5.0 Chrome/125.0.0.0"}
r = s.get("https://www.bing.com/search?q=Bella+Family+Dental+Dallas+reviews+rating", headers=h, timeout=8)
html = r.text
text = re.sub(r'<[^>]+>', ' ', html)
text = re.sub(r'\s+', ' ', text)

# Find all "20" in context with review/rating
for m in re.finditer(r'.{0,40}20.{0,40}', text):
    ctx = m.group()
    if 'review' in ctx.lower() or 'rating' in ctx.lower() or 'star' in ctx.lower():
        print(f"20-in-review: {ctx[:120]}")

# Also look for any actual review counts (non-20)
counts = re.findall(r'(\d[\d,]+)\s*(?:reviews?|ratings?)', text, re.IGNORECASE)
print(f"\nAll review counts: {counts[:10]}")

# Look for ratings
ratings = re.findall(r'(\d+\.?\d*)\s*/\s*5|(\d+\.?\d*)\s*star|rating[:\s]+(\d+\.?\d*)', text, re.IGNORECASE)
print(f"All ratings: {ratings[:10]}")

# Look for knowledge panel
kp = re.findall(r'.{0,50}knowledge.{0,50}', text.lower())
print(f"\nKnowledge panel mentions: {len(kp)}")
for k in kp[:3]:
    print(f"  {k[:100]}")

# Look for Google Maps data in Bing
gm = re.findall(r'.{0,50}(?:google|maps).{0,50}', text.lower())
print(f"\nGoogle/Maps mentions: {len(gm)}")
for g in gm[:5]:
    print(f"  {g[:100]}")
