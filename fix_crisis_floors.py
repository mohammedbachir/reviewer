"""Apply crisis probability floors to all businesses in batch."""
from dotenv import load_dotenv
import os, requests, time, json
load_dotenv(r'F:\reviewer\.env')
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
headers = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}

def fetch_all():
    all_biz = []
    offset = 0
    while True:
        r = requests.get(f'{url}/rest/v1/businesses', 
            headers={**headers, 'Range': f'{offset}-{offset+999}'},
            params={'select': 'id,name,ssl_grade,health_score,breach_count,vulnerabilities,open_ports,crisis_probability,crisis_risk_level'},
            timeout=30)
        batch = r.json()
        if not batch:
            break
        all_biz.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
        time.sleep(0.5)
    return all_biz

def compute_floor(biz):
    ssl_grade = biz.get('ssl_grade', '') or ''
    health = float(biz.get('health_score', 100) or 100)
    breaches = int(biz.get('breach_count', 0) or 0)
    
    vulns_raw = biz.get('vulnerabilities')
    if isinstance(vulns_raw, str):
        try:
            vulns_raw = json.loads(vulns_raw)
        except:
            vulns_raw = []
    vuln_count = len(vulns_raw) if isinstance(vulns_raw, list) else 0
    
    ports_raw = biz.get('open_ports')
    if isinstance(ports_raw, str):
        try:
            ports_raw = json.loads(ports_raw)
        except:
            ports_raw = []
    dangerous = [p for p in (ports_raw if isinstance(ports_raw, list) else []) if p in (23, 3389, 445, 1433, 3306, 5432, 6379, 27017)]
    dang_count = len(dangerous)
    
    score = 0.0
    level = 'LOW'
    
    if breaches > 0:
        score = max(score, 0.70)
        level = 'CRITICAL'
    
    if ssl_grade == 'F':
        score = max(score, 0.50)
        if level not in ('CRITICAL',):
            level = 'HIGH'
    
    if health < 40:
        score = max(score, 0.40)
        if level not in ('CRITICAL', 'HIGH'):
            level = 'ELEVATED'
    
    if vuln_count >= 3 or dang_count >= 2:
        score = max(score, 0.55)
        if level not in ('CRITICAL',):
            level = 'HIGH'
    
    if score == 0:
        return None
    
    current = float(biz.get('crisis_probability', 0) or 0)
    if score > current:
        return (round(score, 4), level)
    return None

print("Fetching all businesses...")
businesses = fetch_all()
print(f"Fetched {len(businesses)} businesses")

updates = []
for biz in businesses:
    floor = compute_floor(biz)
    if floor:
        updates.append({
            'id': biz['id'],
            'crisis_probability': floor[0],
            'crisis_risk_level': floor[1]
        })

print(f"Businesses needing crisis floor update: {len(updates)}")
for u in updates[:20]:
    print(f"  ID {u['id']}: crisis_probability={u['crisis_probability']}, level={u['crisis_risk_level']}")
if len(updates) > 20:
    print(f"  ... and {len(updates)-20} more")

success = 0
errors = 0
for u in updates:
    try:
        r = requests.patch(f'{url}/rest/v1/businesses', 
            headers=headers,
            json={'crisis_probability': u['crisis_probability'], 'crisis_risk_level': u['crisis_risk_level']},
            params={'id': f'eq.{u["id"]}'},
            timeout=15)
        if r.status_code in (200, 204):
            success += 1
        else:
            errors += 1
            if errors <= 3:
                print(f"  Error ID {u['id']}: {r.status_code} {r.text[:100]}")
    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f"  Exception ID {u['id']}: {e}")
    if (success + errors) % 100 == 0:
        print(f"  Progress: {success + errors}/{len(updates)}")
    time.sleep(0.15)

print(f"\nDone: {success} updated, {errors} errors")
