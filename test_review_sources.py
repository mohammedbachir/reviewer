import sys, json
sys.path.insert(0, 'F:/reviewer')
from curl_cffi import requests as cffi
from urllib.parse import quote_plus

session = cffi.Session(impersonate="chrome120")
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"}

# Test with a real business
test_queries = [
    '"Bella Family Dental" Dallas reviews',
    '"Dental Zone" Dallas yelp reviews',
    '"Bella Family Dental" Dallas site:yelp.com',
]

for q in test_queries:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
    resp = session.get(url, headers=headers, timeout=5)
    html = resp.text
    
    import re
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
    
    print(f"\n{'='*80}")
    print(f"QUERY: {q}")
    print(f"Results: {len(titles)} titles, {len(snippets)} snippets")
    for i, (t, s) in enumerate(zip(titles[:5], snippets[:5])):
        t_clean = re.sub(r'<[^>]+>', '', t).strip()
        s_clean = re.sub(r'<[^>]+>', '', s).strip()
        print(f"\n  [{i+1}] {t_clean[:80]}")
        print(f"      {s_clean[:150]}")
    
    # Check for rating patterns in full HTML
    rating_patterns = [
        r'(\d+\.?\d*)\s*\((\d+)\)',
        r'(\d+\.?\d*)\s*/\s*5.*?(\d+)',
        r'Rated\s+(\d+\.?\d*).*?(\d+)',
        r'(\d+\.?\d*)-star.*?(\d+)',
        r'rating.*?(\d+\.?\d*).*?(\d+)\s*review',
    ]
    for pat in rating_patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        if matches:
            print(f"\n  RATING MATCH [{pat[:30]}]: {matches[:3]}")
