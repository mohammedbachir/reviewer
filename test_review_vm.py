import sys, re
sys.path.insert(0, '/home/mc/crisora')
from curl_cffi import requests as cffi
from urllib.parse import quote_plus

session = cffi.Session(impersonate="chrome120")
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"}

businesses = [
    ("Bella Family Dental", "Dallas"),
    ("Dental Zone of Dallas", "Dallas"),
]

# Test DDG
for biz, city in businesses:
    q = f'"{biz}" {city} reviews'
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
    resp = session.get(url, headers=headers, timeout=5)
    print(f"DDG {biz}: status={resp.status_code}, len={len(resp.text)}, has_snippet={'result__snippet' in resp.text}")

# Test Bing
for biz, city in businesses:
    q = f'{biz} {city} reviews rating'
    url = f"https://www.bing.com/search?q={quote_plus(q)}"
    resp = session.get(url, headers=headers, timeout=8)
    html = resp.text
    count = re.findall(r'(\d[\d,]*)\s*(?:reviews?|ratings?)', html, re.IGNORECASE)
    rating = re.findall(r'(\d+\.?\d*)\s*\(\s*(\d[\d,]*)\s*\)|rating[:\s]+(\d+\.?\d*)|(\d+\.?\d*)\s*/\s*5', html, re.IGNORECASE)
    print(f"Bing {biz}: status={resp.status_code}, len={len(html)}, counts={count[:5]}, ratings={rating[:5]}")
