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

# Test 1: Bing - look at actual content
q = 'Bella Family Dental Dallas TX reviews rating stars'
url = f"https://www.bing.com/search?q={quote_plus(q)}"
resp = session.get(url, headers=headers, timeout=5)
html = resp.text

# Save for analysis
with open("F:/reviewer/test_bing_output.html", "w", encoding="utf-8") as f:
    f.write(html)

# Extract all text content (strip HTML)
text = re.sub(r'<[^>]+>', ' ', html)
text = re.sub(r'\s+', ' ', text)

# Look for rating mentions
for pat in [r'(\d+\.?\d*)\s*stars?', r'(\d+\.?\d*)\s*/\s*5', r'rating\s*(\d+\.?\d*)', r'(\d+\.?\d*)\s*reviews?', r'(\d+)\s*reviews?\s*on\s*google']:
    matches = re.findall(pat, text, re.IGNORECASE)
    if matches:
        print(f"PATTERN [{pat[:30]}]: {matches[:5]}")

# Look for specific Bing rich results (Knowledge Graph)
kg = re.search(r'aria-label="[^"]*(\d+\.?\d*)\s*(?:out of|/)\s*5[^"]*(\d+)\s*reviews?', text, re.IGNORECASE)
if kg:
    print(f"\nKNOWLEDGE GRAPH: rating={kg.group(1)}, reviews={kg.group(2)}")

# Look for review snippets in Bing sidebar
sidebar = re.findall(r'Bella Family Dental[^<]*(?:rating|star|review|Google|Yelp)[^<]{0,200}', text, re.IGNORECASE)
print(f"\nSidebar mentions: {len(sidebar)}")
for s in sidebar[:5]:
    print(f"  -> {s[:200]}")

# Look for Google Maps knowledge panel data
gp = re.search(r'(?:Google|Maps)[^<]{0,50}?(\d+\.?\d*)\s*(?:stars?|/5)[^<]{0,50}?(\d+)\s*reviews?', text, re.IGNORECASE)
if gp:
    print(f"\nGOOGLE MAPS: rating={gp.group(1)}, reviews={gp.group(2)}")

# Broader search for numbers near "review"
review_context = re.findall(r'.{0,50}review.{0,50}', text.lower())
for rc in review_context[:10]:
    nums = re.findall(r'\d+\.?\d*', rc)
    if nums:
        print(f"  Review context: '{rc[:120]}' nums={nums}")

# Test 2: DDG with different impersonation
print("\n" + "="*60)
print("TEST 2: DDG with impersonate=chrome131")
session3 = cffi.Session(impersonate="chrome131")
q = 'Bella Family Dental Dallas reviews'
url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
resp = session3.get(url, headers=headers, timeout=5)
print(f"Status: {resp.status_code}")
if 'result__snippet' in resp.text:
    print("WORKING!")
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    print(f"Snippets: {len(snippets)}")
    for s in snippets[:3]:
        clean = re.sub(r'<[^>]+>', '', s).strip()
        print(f"  -> {clean[:150]}")
elif resp.status_code == 202:
    print("BLOCKED")
