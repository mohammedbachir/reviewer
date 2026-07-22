import sys, re, json
sys.path.insert(0, '/home/mc/crisora')
from curl_cffi import requests as cffi
from urllib.parse import quote_plus
import time

session = cffi.Session(impersonate="chrome120")
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"}

business = "Bella Family Dental"
city = "Dallas"

q = f'"{business}" {city} reviews'
url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
resp = session.get(url, headers=headers, timeout=5)
print(f"Status: {resp.status_code}")

if resp.status_code == 200 and 'result__snippet' in resp.text:
    html = resp.text
    
    # Extract titles
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
    print(f"\nTitles ({len(titles)}):")
    for i, t in enumerate(titles[:10]):
        clean = re.sub(r'<[^>]+>', '', t).strip()
        print(f"  [{i}] {clean[:100]}")
    
    # Extract snippets
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
    print(f"\nSnippets ({len(snippets)}):")
    for i, s in enumerate(snippets[:10]):
        clean = re.sub(r'<[^>]+>', '', s).strip()
        print(f"  [{i}] {clean[:200]}")
    
    # Count patterns in full HTML
    text = re.sub(r'<[^>]+>', ' ', html)
    count_patterns = [
        r'(\d[\d,]*)\s*(?:Google\s+)?reviews?',
        r'(\d[\d,]*)\s*customer\s+reviews?',
        r'(\d[\d,]*)\s*(?:Yelp\s+)?reviews?',
        r'Rated\s+(\d[\d,]*)',
    ]
    for pat in count_patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            print(f"\n  COUNT [{pat[:30]}]: {matches[:5]}")
    
    # Rating patterns
    rating_patterns = [
        r'(\d+\.?\d*)\s*\(\s*(\d[\d,]*)\s*\)',
        r'(\d+\.?\d*)\s*/\s*5',
        r'Rated\s+(\d+\.?\d*)',
        r'(\d+\.?\d*)-star',
        r'rating[:\s]+(\d+\.?\d*)',
    ]
    for pat in rating_patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            print(f"\n  RATING [{pat[:30]}]: {matches[:5]}")

    # Owner response
    if "owner" in text.lower() and "response" in text.lower():
        print("\n  OWNER RESPONSE: detected!")
else:
    print("BLOCKED or no results")
    print(resp.text[:500])
