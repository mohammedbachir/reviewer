"""Fix DB quality: bad phones, duplicates, crisis probability floors."""
import re
import json
import os
import sys
from curl_cffi import requests as cffi_requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lgbzpwzpkzbquuwwhbin.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

SSL_GRADE_MAP = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}


def fetch_all():
    data = []
    offset = 0
    while True:
        resp = cffi_requests.get(
            f"{SUPABASE_URL}/rest/v1/businesses?select=id,name,phone,website,ssl_grade,health_score,breach_count,vulnerabilities,open_ports,crisis_probability,crisis_risk_level,lead_temperature&offset={offset}&limit=1000",
            headers=HEADERS, timeout=15
        )
        batch = resp.json()
        if not isinstance(batch, list) or not batch:
            break
        data.extend(batch)
        offset += 1000
    return data


def validate_phone(phone):
    if not phone:
        return None
    digits = re.sub(r'[^0-9]', '', str(phone))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "23456789":
        return digits
    return None


def parse_list(val):
    if not val:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def fix_crisis_floors(biz):
    """Enforce minimum crisis probability."""
    ssl = (biz.get("ssl_grade") or "").strip().upper()
    health = int(float(biz.get("health_score") or 50))
    breach = int(float(biz.get("breach_count") or 0))
    vulns = len(parse_list(biz.get("vulnerabilities")))
    dangerous = len([p for p in parse_list(biz.get("open_ports")) if p in {3306, 5432, 6379, 27017, 9200, 11211}])

    prob = float(biz.get("crisis_probability") or 0)
    if ssl == "F":
        prob = max(prob, 0.50)
    if health < 40:
        prob = max(prob, 0.40)
    if breach > 0:
        prob = max(prob, 0.70)
    if vulns >= 3 or dangerous >= 2:
        prob = max(prob, 0.55)
    prob = min(prob, 1.0)

    if prob >= 0.75:
        level = "CRITICAL"
    elif prob >= 0.50:
        level = "HIGH"
    elif prob >= 0.25:
        level = "ELEVATED"
    elif prob >= 0.10:
        level = "MODERATE"
    else:
        level = "LOW"

    return prob, level


def main():
    print("Fetching all businesses...")
    businesses = fetch_all()
    print(f"Total: {len(businesses)}")

    phone_fixes = 0
    crisis_fixes = 0
    dup_ids = []

    seen_websites = {}
    seen_phones = {}

    for biz in businesses:
        bid = biz["id"]

        phone = validate_phone(biz.get("phone"))
        if biz.get("phone") and not phone:
            print(f"  Bad phone: {biz['name']} -> '{biz['phone']}' -> null")
            phone_fixes += 1

        website = (biz.get("website") or "").lower().strip().rstrip("/").replace("www.", "")

        is_dup = False
        if website and website in seen_websites:
            is_dup = True
            print(f"  Dup by website: {biz['name']} ({website})")
        elif phone and phone in seen_phones:
            is_dup = True
            print(f"  Dup by phone: {biz['name']} ({phone})")

        if is_dup:
            dup_ids.append(bid)
        else:
            if website:
                seen_websites[website] = bid
            if phone:
                seen_phones[phone] = bid

        new_prob, new_level = fix_crisis_floors(biz)
        old_prob = float(biz.get("crisis_probability") or 0)
        if new_prob > old_prob + 0.01:
            print(f"  Crisis fix: {biz['name']} -> {old_prob:.2f} -> {new_prob:.2f} ({new_level})")
            crisis_fixes += 1

    print(f"\nSummary:")
    print(f"  Bad phones to null: {phone_fixes}")
    print(f"  Duplicates to remove: {len(dup_ids)}")
    print(f"  Crisis probabilities to fix: {crisis_fixes}")

    if dup_ids:
        print(f"\nDeleting {len(dup_ids)} duplicates...")
        for did in dup_ids:
            try:
                cffi_requests.delete(
                    f"{SUPABASE_URL}/rest/v1/businesses?id=eq.{did}",
                    headers=HEADERS, timeout=5
                )
            except Exception:
                pass
        print("  Done.")

    print("\nFixing phones + crisis probabilities...")
    for biz in businesses:
        bid = biz["id"]
        if bid in dup_ids:
            continue

        phone = validate_phone(biz.get("phone"))
        new_prob, new_level = fix_crisis_floors(biz)
        old_prob = float(biz.get("crisis_probability") or 0)

        update = {}
        if biz.get("phone") and not phone:
            update["phone"] = None
        if new_prob > old_prob + 0.01:
            update["crisis_probability"] = round(new_prob, 4)
            update["crisis_risk_level"] = new_level

        if update:
            try:
                cffi_requests.patch(
                    f"{SUPABASE_URL}/rest/v1/businesses?id=eq.{bid}",
                    json=update,
                    headers=HEADERS, timeout=5
                )
            except Exception:
                pass

    print("All fixes applied!")


if __name__ == "__main__":
    main()
