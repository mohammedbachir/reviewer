import sys
sys.path.insert(0, 'F:/reviewer')
from curl_cffi import requests as cffi
from urllib.parse import quote_plus
import re

session = cffi.Session(impersonate="chrome120")
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"}

q = '"Bella Family Dental" Dallas reviews'
url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
resp = session.get(url, headers=headers, timeout=5)
html = resp.text

# Check what we actually got
print(f"Status: {resp.status_code}")
print(f"Length: {len(html)}")
print(f"Has result__snippet: {'result__snippet' in html}")
print(f"Has result__a: {'result__a' in html}")

# Look for snippets
snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
print(f"\nSnippets found: {len(snippets)}")
for i, s in enumerate(snippets[:3]):
    clean = re.sub(r'<[^>]+>', '', s).strip()
    print(f"  [{i}] {clean[:200]}")

# Look for titles
titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
print(f"\nTitles found: {len(titles)}")
for i, t in enumerate(titles[:5]):
    clean = re.sub(r'<[^>]+>', '', t).strip()
    print(f"  [{i}] {clean[:100]}")

# Count patterns
count_patterns = [
    r'(\d[\d,]*)\s*(?:Google\s+)?(?:reviews?|Ratings?)',
    r'(\d[\d,]*)\s*customer\s+reviews?',
    r'(\d[\d,]*)\s*(?:Yelp\s+)?reviews?',
]
for pat in count_patterns:
    matches = re.findall(pat, html, re.IGNORECASE)
    if matches:
        print(f"\n  COUNT [{pat[:40]}]: {matches[:5]}")

# Rating patterns
rating_patterns = [
    r'(\d+\.?\d*)\s*\(\s*(\d[\d,]*)\s*\)',
    r'(\d+\.?\d*)\s*/\s*5',
    r'Rated\s+(\d+\.?\d*)',
    r'(\d+\.?\d*)-star',
    r'rating[:\s]+(\d+\.?\d*)',
]
for pat in rating_patterns:
    matches = re.findall(pat, html, re.IGNORECASE)
    if matches:
        print(f"\n  RATING [{pat[:40]}]: {matches[:5]}")

# Print first 2000 chars of HTML for debugging
print(f"\n{'='*80}")
print("RAW HTML (first 3000 chars):")
print(html[:3000])
