from ddgs import DDGS
import json

# Test ddgs with multi-engine fallback
businesses = [
    ("Bella Family Dental", "Dallas"),
    ("Dental Zone of Dallas", "Dallas"),
    ("A1 Autobody", "Vancouver"),
]

for biz, city in businesses:
    print(f"\n{'='*60}")
    print(f"BUSINESS: {biz}, {city}")

    query = f"{biz} {city} reviews rating"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            print(f"Results: {len(results)}")
            for i, r in enumerate(results[:5]):
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                print(f"  [{i}] {title[:80]}")
                print(f"      Body: {body[:150]}")
                print(f"      URL: {href[:80]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Try to extract rating/review count
    import re
    all_text = " ".join([r.get("body", "") + " " + r.get("title", "") for r in results])
    
    count_matches = re.findall(r'(\d[\d,]*)\s*(?:Google\s+)?reviews?', all_text, re.IGNORECASE)
    rating_matches = re.findall(r'(\d+\.?\d*)\s*\(\s*(\d[\d,]*)\s*\)|(\d+\.?\d*)\s*/\s*5|(\d+\.?\d*)-star|rating[:\s]+(\d+\.?\d*)', all_text, re.IGNORECASE)
    
    if count_matches:
        print(f"  Review counts: {count_matches}")
    if rating_matches:
        print(f"  Ratings: {rating_matches}")
