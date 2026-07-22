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

businesses = [
    ("Bella Family Dental", "Dallas"),
    ("Dental Zone of Dallas", "Dallas"),
    ("A1 Autobody", "Vancouver"),
]

for biz, city in businesses:
    print(f"\n{'='*60}")
    print(f"BUSINESS: {biz}, {city}")

    q = f'{biz} {city} reviews'
    url = f"https://www.bing.com/search?q={quote_plus(q)}"
    resp = session.get(url, headers=headers, timeout=5)
    html = resp.text
    print(f"Bing: status={resp.status_code}, len={len(html)}")

    # All review count patterns
    count_patterns = [
        (r'(\d[\d,]*)\s*(?:Google\s+)?reviews?', "reviews"),
        (r'(\d[\d,]*)\s*(?:Google\s+)?ratings?', "ratings"),
        (r'(\d[\d,]*)\s*customer\s+reviews?', "customer"),
        (r'(\d[\d,]*)\s*reviews?\s+on\s+', "on_platform"),
        (r'Rated\s+(\d[\d,]*)', "rated"),
    ]
    for pat, label in count_patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        if matches:
            print(f"  COUNT [{label}]: {matches[:5]}")

    # Rating patterns
    rating_patterns = [
        (r'(\d+\.?\d*)\s*\(\s*(\d[\d,]*)\s*\)', "paren"),
        (r'(\d+\.?\d*)\s*/\s*5', "over5"),
        (r'Rated\s+(\d+\.?\d*)', "rated"),
        (r'(\d+\.?\d*)-star', "star"),
        (r'rating[:\s]+(\d+\.?\d*)', "label"),
        (r'(\d+\.?\d*)\s*out of\s*5', "out_of"),
    ]
    for pat, label in rating_patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        if matches:
            print(f"  RATING [{label}]: {matches[:5]}")

    # Extract snippets
    snippets = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    review_snippets = []
    for s in snippets:
        clean = re.sub(r'<[^>]+>', '', s).strip()
        if len(clean) > 50 and any(w in clean.lower() for w in ["review", "rating", "star", "great", "terrible", "recommend"]):
            review_snippets.append(clean[:200])
    print(f"  Review snippets: {len(review_snippets)}")
    for s in review_snippets[:3]:
        print(f"    -> {s[:150]}")
