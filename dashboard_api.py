"""
FindLeads — Dashboard Backend
Supabase queries + Kimi AI + Email Digest.
"""

import json
import os
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from curl_cffi import requests as cffi_requests

logger = logging.getLogger("dashboard")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "findleads2026")
KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
SCRAPE_SECRET = os.environ.get("SCRAPE_SECRET_KEY", "findleads2026")

HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}


def _sb_get(table, params="", count=False):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    h = dict(HEADERS)
    if count:
        h["Prefer"] = "count=exact"
    resp = cffi_requests.get(url, headers=h, timeout=15)
    if count:
        cr = resp.headers.get("content-range", "")
        total = 0
        if "/" in cr:
            try:
                total = int(cr.split("/")[1])
            except Exception:
                total = 0
        data = resp.json()
        if total == 0:
            total = len(data) if isinstance(data, list) else 0
        return data, total
    return resp.json()


def _sb_post(table, data, merge=True):
    h = dict(HEADERS)
    if merge:
        h["Prefer"] = "resolution=merge-duplicates"
    resp = cffi_requests.post(f"{SUPABASE_URL}/rest/v1/{table}", json=data, headers=h, timeout=10)
    return resp.status_code


def verify_token(token):
    if not token:
        return False
    expected = hashlib.sha256(DASHBOARD_PASSWORD.encode()).hexdigest()[:32]
    return token == expected


def login(password):
    if password == DASHBOARD_PASSWORD:
        return hashlib.sha256(password.encode()).hexdigest()[:32]
    return None


# ════════════════════════════════════════════════════════════════
# STATS
# ════════════════════════════════════════════════════════════════

def get_stats():
    businesses, total = _sb_get("businesses", "select=id", count=True)
    if total == 0:
        all_biz = _sb_get("businesses", "select=id")
        total = len(all_biz) if isinstance(all_biz, list) else 0

    all_data = _sb_get("businesses", "select=id,lead_temperature,email,health_score,name,city,sector,ssl_grade,created_at&limit=5000")
    emails = sum(1 for b in all_data if b.get("email"))
    hot = sum(1 for b in all_data if b.get("lead_temperature") == "HOT")
    warm = sum(1 for b in all_data if b.get("lead_temperature") == "WARM")
    cold = sum(1 for b in all_data if b.get("lead_temperature") == "COLD")

    health_vals = [b.get("health_score", 50) for b in all_data if b.get("health_score") is not None]
    avg_health = round(sum(health_vals) / max(len(health_vals), 1))

    cities = {}
    for b in all_data:
        c = b.get("city", "Unknown")
        cities[c] = cities.get(c, 0) + 1

    recent = sorted(all_data, key=lambda x: x.get("created_at") or "", reverse=True)[:10]

    return {
        "total_companies": total,
        "total_emails": emails,
        "hot_leads": hot,
        "warm_leads": warm,
        "cold_leads": cold,
        "avg_health_score": avg_health,
        "email_rate": round(emails / max(total, 1) * 100),
        "cities": cities,
        "recent_companies": recent,
        "temperature_distribution": {"HOT": hot, "WARM": warm, "COLD": cold},
    }


# ════════════════════════════════════════════════════════════════
# ALGORITHMS
# ════════════════════════════════════════════════════════════════

def get_algorithms():
    stats = get_stats()
    total = stats["total_companies"]

    return [
        {
            "id": 1, "name": "finder.py", "name_ar": "محرك اكتشاف الشركات",
            "description": "DDG HTML search to discover businesses by city and sector",
            "description_ar": "بحث HTML عبر DuckDuckGo لاكتشاف الشركات حسب المدينة والقطاع",
            "inputs": "city + sector", "outputs": "businesses[]",
            "uses": total, "avg_time": "8s", "success_rate": "95%",
            "status": "active", "category": "wash",
        },
        {
            "id": 2, "name": "email_finder.py", "name_ar": "محرك الإيميلات",
            "description": "Email Permutation Engine with DNSMX + Gravatar + crt.sh + website crawl",
            "description_ar": "محرك توليد الإيميلات مع التحقق عبر DNSMX + Gravatar + crt.sh + زحف الموقع",
            "inputs": "website + name", "outputs": "email + confidence + source",
            "uses": total, "avg_time": "12s", "success_rate": "100%",
            "status": "active", "category": "wash",
        },
        {
            "id": 3, "name": "osint_engine.py", "name_ar": "محرك الاستخبارات",
            "description": "TechDetect HTTP signatures (100+ technologies) + SSL + DNS + Page Speed + Health Score",
            "description_ar": "بصمات HTTP لـ 100+ تكنولوجيا + شهادة SSL + DNS + سرعة الموقع + درجة الصحة",
            "inputs": "domain + rating + review_count", "outputs": "health_score + ssl_grade + tech_stack[]",
            "uses": total, "avg_time": "8s", "success_rate": "100%",
            "status": "active", "category": "fold",
        },
        {
            "id": 4, "name": "review_engine.py", "name_ar": "محرك تحليل المراجع",
            "description": "DDG review search + sentiment analysis + response detection",
            "description_ar": "بحث المراجع عبر DDG + تحليل المشاعر + كشف الردود",
            "inputs": "name + city + website", "outputs": "sentiment + responds_to_reviews + rating",
            "uses": total, "avg_time": "6s", "success_rate": "85%",
            "status": "active", "category": "fold",
        },
        {
            "id": 5, "name": "lead_scorer", "name_ar": "مُقيِّم درجة الحرارة",
            "description": "HOT/WARM/COLD classification based on SSL, rating, health, tech, sentiment",
            "description_ar": "تصنيف HOT/WARM/COLD بناءً على SSL والتقييم والصحة والتكنولوجيا والمشاعر",
            "inputs": "business signals", "outputs": "lead_temperature",
            "uses": total, "avg_time": "0s", "success_rate": "100%",
            "status": "active", "category": "fold",
        },
        {
            "id": 6, "name": "outreach_hook", "name_ar": "مولّد طُعم التواصل",
            "description": "Personalized outreach message based on pain points (SSL, health, reviews)",
            "description_ar": "رسالة تواصل شخصية بناءً على نقاط الألم (SSL، الصحة، المراجع)",
            "inputs": "business + temperature", "outputs": "personalized message",
            "uses": total, "avg_time": "0s", "success_rate": "100%",
            "status": "active", "category": "fold",
        },
        {
            "id": 7, "name": "target_rotation", "name_ar": "نظام الدوران",
            "description": "25 city/sector rotation with Supabase state tracking",
            "description_ar": "دوران 25 مدينة/قطاع مع تتبع الحالة عبر Supabase",
            "inputs": "system_state", "outputs": "target {city, sector}",
            "uses": total, "avg_time": "1s", "success_rate": "100%",
            "status": "active", "category": "closet",
        },
        {
            "id": 8, "name": "supabase_upsert", "name_ar": "مخزن البيانات",
            "description": "PostgreSQL storage with UPSERT (merge duplicates) + temporal snapshots",
            "description_ar": "تخزين PostgreSQL مع UPSET (دمج المكرر) + لقطات زمنية",
            "inputs": "enriched business", "outputs": "stored record",
            "uses": total, "avg_time": "1s", "success_rate": "100%",
            "status": "active", "category": "closet",
        },
        {
            "id": 9, "name": "crisis_predictor.py", "name_ar": "متنبئ الأزمات",
            "description": "Online ML (Hoeffding Tree) + Graph Risk Contagion + CVSS scoring for crisis prediction",
            "description_ar": "تعلم آلي + انتشار المخاطر بالرسوم البيانية + تقييم CVSS للتنبؤ بالأزمات",
            "inputs": "business features + snapshots + graph", "outputs": "crisis_probability + risk_level + recommendations",
            "uses": total, "avg_time": "2s", "success_rate": "100%",
            "status": "active", "category": "fold",
        },
    ]


# ════════════════════════════════════════════════════════════════
# COMPANIES
# ════════════════════════════════════════════════════════════════

def get_companies(page=1, per_page=20, city="", sector="", temp="", email_filter="", search="", sort="created_at.desc"):
    filters = []
    if city:
        filters.append(f"city=eq.{city}")
    if sector:
        filters.append(f"sector=eq.{sector}")
    if temp:
        filters.append(f"lead_temperature=eq.{temp}")
    if email_filter == "yes":
        filters.append("email=not.is.null")
    elif email_filter == "no":
        filters.append("email=is.null")
    if search:
        filters.append(f"name=ilike.*{search}*")

    params = "&".join(filters) if filters else ""
    if params:
        params += "&"
    params += f"order={sort}&limit={per_page}&offset={(page - 1) * per_page}"

    data, total = _sb_get("businesses", f"select=id,name,city,sector,lead_temperature,health_score,ssl_grade,email,email_confidence,sentiment,website,phone,instagram,facebook,rating,review_count,created_at&{params}", count=True)
    if total == 0 and data:
        total = len(data)

    return {
        "companies": data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
    }


def get_company(company_id):
    data = _sb_get("businesses", f"select=*&id=eq.{company_id}")
    if not data:
        return None
    biz = data[0]
    if isinstance(biz.get("tech_stack"), str):
        try:
            biz["tech_stack"] = json.loads(biz["tech_stack"])
        except Exception:
            pass
    for field in ["vulnerabilities", "open_ports", "security_warnings", "breach_names", "crisis_recommendations", "firebase", "archive", "api_keys", "crtsh", "sherlock"]:
        if isinstance(biz.get(field), str):
            try:
                biz[field] = json.loads(biz[field])
            except Exception:
                pass
    return biz


def get_cities():
    data = _sb_get("businesses", "select=city")
    cities = sorted(set(b.get("city", "") for b in data if b.get("city")))
    return cities


def get_sectors():
    data = _sb_get("businesses", "select=sector")
    sectors = sorted(set(b.get("sector", "") for b in data if b.get("sector")))
    return sectors


# ════════════════════════════════════════════════════════════════
# ANALYTICS
# ════════════════════════════════════════════════════════════════

def get_analytics():
    businesses = _sb_get("businesses", "select=city,sector,lead_temperature,health_score,ssl_grade,email_confidence,sentiment&limit=5000")

    temp_dist = {"HOT": 0, "WARM": 0, "COLD": 0}
    city_health = {}
    city_counts = {}
    ssl_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
    email_conf_buckets = {"high": 0, "medium": 0, "low": 0, "none": 0}

    for b in businesses:
        t = b.get("lead_temperature", "COLD")
        if t in temp_dist:
            temp_dist[t] += 1

        city = b.get("city", "Unknown")
        h = b.get("health_score", 50)
        if city not in city_health:
            city_health[city] = []
            city_counts[city] = 0
        city_health[city].append(h)
        city_counts[city] += 1

        ssl = b.get("ssl_grade", "") or "F"
        if ssl in ssl_dist:
            ssl_dist[ssl] += 1

        s = b.get("sentiment", "neutral")
        if s in sentiment_dist:
            sentiment_dist[s] += 1

        conf = b.get("email_confidence", 0)
        if conf >= 70:
            email_conf_buckets["high"] += 1
        elif conf >= 50:
            email_conf_buckets["medium"] += 1
        elif conf > 0:
            email_conf_buckets["low"] += 1
        else:
            email_conf_buckets["none"] += 1

    city_avg_health = {c: round(sum(v) / len(v)) for c, v in city_health.items()}

    sector_dist = {}
    for b in businesses:
        s = b.get("sector", "Unknown")
        sector_dist[s] = sector_dist.get(s, 0) + 1

    return {
        "temperature_distribution": temp_dist,
        "city_health": city_avg_health,
        "city_counts": city_counts,
        "ssl_distribution": ssl_dist,
        "sentiment_distribution": sentiment_dist,
        "email_confidence": email_conf_buckets,
        "sector_distribution": sector_dist,
        "total": len(businesses),
    }


# ════════════════════════════════════════════════════════════════
# SECURITY
# ════════════════════════════════════════════════════════════════

def get_security():
    businesses = _sb_get("businesses", "select=id,name,city,sector,lead_temperature,health_score,ssl_grade,vulnerabilities,open_ports,breach_count,breach_names,security_warnings&limit=5000")

    total_vulns = 0
    total_breaches = 0
    total_ports = 0
    total_warnings = 0
    companies_with_vulns = 0
    companies_with_ports = 0
    companies_with_breaches = 0
    vuln_dist = {}
    port_dist = {}
    warning_dist = {}
    companies_with_issues = []

    for b in businesses:
        vulns = _parse_json_list(b.get("vulnerabilities"))
        ports = _parse_json_list(b.get("open_ports"))
        warnings = _parse_json_list(b.get("security_warnings"))
        breach_count = b.get("breach_count", 0) or 0
        breach_names = _parse_json_list(b.get("breach_names"))

        if vulns:
            companies_with_vulns += 1
            total_vulns += len(vulns)
            for v in vulns:
                vuln_dist[v] = vuln_dist.get(v, 0) + 1

        if ports:
            companies_with_ports += 1
            total_ports += len(ports)
            for p in ports:
                port_dist[str(p)] = port_dist.get(str(p), 0) + 1

        if breach_count:
            companies_with_breaches += 1
            total_breaches += breach_count
            for bn in breach_names:
                warning_dist[bn] = warning_dist.get(bn, 0) + 1

        if warnings:
            total_warnings += len(warnings)
            for w in warnings:
                warning_dist[w] = warning_dist.get(w, 0) + 1

        if vulns or ports or breach_count or warnings:
            companies_with_issues.append(b)

    companies_with_issues.sort(key=lambda x: (
        len(_parse_json_list(x.get("vulnerabilities"))),
        x.get("breach_count", 0) or 0,
        len(_parse_json_list(x.get("open_ports")))
    ), reverse=True)

    return {
        "total_vulnerabilities": total_vulns,
        "total_breaches": total_breaches,
        "total_open_ports": total_ports,
        "total_warnings": total_warnings,
        "companies_with_vulns": companies_with_vulns,
        "companies_with_ports": companies_with_ports,
        "companies_with_breaches": companies_with_breaches,
        "vulnerability_distribution": dict(sorted(vuln_dist.items(), key=lambda x: -x[1])[:15]),
        "port_distribution": dict(sorted(port_dist.items(), key=lambda x: -x[1])[:10]),
        "warning_distribution": dict(sorted(warning_dist.items(), key=lambda x: -x[1])[:10]),
        "companies_with_issues": companies_with_issues[:50],
    }


def _parse_json_list(val):
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


# ════════════════════════════════════════════════════════════════
# CRISIS PREDICTOR
# ════════════════════════════════════════════════════════════════

def get_crisis():
    businesses = _sb_get("businesses", "select=id,name,city,sector,lead_temperature,health_score,ssl_grade,crisis_probability,crisis_risk_level,cvss_severity,cvss_max,breach_count,vulnerabilities,open_ports,crisis_recommendations&limit=5000")

    risk_dist = {"CRITICAL": 0, "HIGH": 0, "ELEVATED": 0, "MODERATE": 0, "LOW": 0, "UNKNOWN": 0}
    cvss_dist = {"CRITICAL": 0, "HIGH": 0, "ELEVATED": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    risk_companies = []
    total_prob = 0
    prob_count = 0

    for b in businesses:
        level = b.get("crisis_risk_level", "UNKNOWN")
        if level in risk_dist:
            risk_dist[level] += 1

        cvss_sev = b.get("cvss_severity", "NONE")
        if cvss_sev in cvss_dist:
            cvss_dist[cvss_sev] += 1

        prob = b.get("crisis_probability", 0) or 0
        if prob > 0:
            total_prob += prob
            prob_count += 1

        recs = _parse_json_list(b.get("crisis_recommendations"))

        if level in ("CRITICAL", "HIGH", "ELEVATED") or prob > 0.25:
            risk_companies.append({
                "id": b.get("id"),
                "name": b.get("name", ""),
                "city": b.get("city", ""),
                "sector": b.get("sector", ""),
                "crisis_probability": prob,
                "crisis_risk_level": level,
                "cvss_severity": cvss_sev,
                "cvss_max": b.get("cvss_max", 0) or 0,
                "breach_count": b.get("breach_count", 0) or 0,
                "recommendations_count": len(recs),
                "top_recommendation": recs[0] if recs else None,
            })

    risk_companies.sort(key=lambda x: x.get("crisis_probability", 0), reverse=True)

    avg_prob = round(total_prob / max(prob_count, 1), 4)

    return {
        "total_companies": len(businesses),
        "risk_distribution": risk_dist,
        "cvss_distribution": cvss_dist,
        "avg_crisis_probability": avg_prob,
        "companies_at_risk": risk_companies[:50],
        "critical_count": risk_dist.get("CRITICAL", 0),
        "high_count": risk_dist.get("HIGH", 0),
        "elevated_count": risk_dist.get("ELEVATED", 0),
    }


# ════════════════════════════════════════════════════════════════
# OSINT INTELLIGENCE
# ════════════════════════════════════════════════════════════════

def get_osint_stats():
    businesses = _sb_get("businesses", "select=id,name,city,sector,lead_temperature,firebase,archive,api_keys,crtsh,sherlock&limit=5000")

    firebase_detected = 0
    firebase_open = 0
    archive_high = 0
    archive_total_sensitive = 0
    api_keys_found = 0
    api_keys_total = 0
    api_exposure_high = 0
    sherlock_profiles_total = 0
    sherlock_high = 0
    sherlock_medium = 0
    crtsh_subdomains_total = 0
    crtsh_emails_total = 0
    crtsh_with_data = 0
    companies_with_any_osint = 0

    firebase_dist = {"DETECTED": 0, "NONE": 0}
    archive_dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    api_dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    sherlock_dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    crtsh_dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}

    top_exposed = []

    for b in businesses:
        has_osint = False

        fb = b.get("firebase") or {}
        if isinstance(fb, str):
            try:
                fb = json.loads(fb)
            except Exception:
                fb = {}
        fb_risk = fb.get("firebase_risk", "NONE")
        if fb_risk in firebase_dist:
            firebase_dist[fb_risk] += 1
        if fb.get("firebase_detected"):
            firebase_detected += 1
            has_osint = True
        if fb.get("firebase_open"):
            firebase_open += 1

        ar = b.get("archive") or {}
        if isinstance(ar, str):
            try:
                ar = json.loads(ar)
            except Exception:
                ar = {}
        ar_risk = ar.get("archive_risk", "NONE")
        if ar_risk in archive_dist:
            archive_dist[ar_risk] += 1
        if ar_risk == "HIGH":
            archive_high += 1
            has_osint = True
        sensitive = ar.get("archive_sensitive_files") or []
        if isinstance(sensitive, list):
            archive_total_sensitive += len(sensitive)

        ak = b.get("api_keys") or {}
        if isinstance(ak, str):
            try:
                ak = json.loads(ak)
            except Exception:
                ak = {}
        ak_risk = ak.get("api_exposure_risk", "NONE")
        if ak_risk in api_dist:
            api_dist[ak_risk] += 1
        ak_count = ak.get("api_key_count", 0) or 0
        if ak_count > 0:
            api_keys_found += 1
            api_keys_total += ak_count
            has_osint = True
        if ak_risk == "HIGH":
            api_exposure_high += 1

        sh = b.get("sherlock") or {}
        if isinstance(sh, str):
            try:
                sh = json.loads(sh)
            except Exception:
                sh = {}
        sh_risk = sh.get("sherlock_risk", "NONE")
        if sh_risk in sherlock_dist:
            sherlock_dist[sh_risk] += 1
        sh_count = sh.get("profile_count", 0) or 0
        if sh_count > 0:
            sherlock_profiles_total += sh_count
        if sh_risk == "HIGH":
            sherlock_high += 1
        if sh_risk == "MEDIUM":
            sherlock_medium += 1

        cr = b.get("crtsh") or {}
        if isinstance(cr, str):
            try:
                cr = json.loads(cr)
            except Exception:
                cr = {}
        cr_risk = cr.get("subdomain_risk", "NONE")
        if cr_risk in crtsh_dist:
            crtsh_dist[cr_risk] += 1
        sub_count = cr.get("subdomain_count", 0) or 0
        email_count = cr.get("email_count", 0) or 0
        if sub_count > 0 or email_count > 0:
            crtsh_subdomains_total += sub_count
            crtsh_emails_total += email_count
            crtsh_with_data += 1
            has_osint = True

        if has_osint:
            companies_with_any_osint += 1

        risk_score = 0
        if fb_risk == "DETECTED":
            risk_score += 30
        if ar_risk == "HIGH":
            risk_score += 25
        if ak_risk == "HIGH":
            risk_score += 25
        if sh_risk == "HIGH":
            risk_score += 10
        if cr_risk == "HIGH":
            risk_score += 10

        if risk_score > 0:
            top_exposed.append({
                "id": b.get("id"),
                "name": b.get("name", ""),
                "city": b.get("city", ""),
                "sector": b.get("sector", ""),
                "lead_temperature": b.get("lead_temperature", "COLD"),
                "risk_score": risk_score,
                "firebase_risk": fb_risk,
                "archive_risk": ar_risk,
                "api_risk": ak_risk,
                "sherlock_risk": sh_risk,
                "crtsh_risk": cr_risk,
                "api_key_count": ak_count,
                "profile_count": sh_count,
                "subdomain_count": sub_count,
            })

    top_exposed.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "total_companies": len(businesses),
        "companies_with_osint": companies_with_any_osint,
        "firebase": {
            "detected": firebase_detected,
            "open": firebase_open,
            "distribution": firebase_dist,
        },
        "archive": {
            "high_risk": archive_high,
            "total_sensitive_files": archive_total_sensitive,
            "distribution": archive_dist,
        },
        "api_keys": {
            "companies_with_keys": api_keys_found,
            "total_keys": api_keys_total,
            "high_exposure": api_exposure_high,
            "distribution": api_dist,
        },
        "sherlock": {
            "total_profiles": sherlock_profiles_total,
            "high_risk": sherlock_high,
            "medium_risk": sherlock_medium,
            "distribution": sherlock_dist,
        },
        "crtsh": {
            "companies_with_data": crtsh_with_data,
            "total_subdomains": crtsh_subdomains_total,
            "total_emails": crtsh_emails_total,
            "distribution": crtsh_dist,
        },
        "top_exposed": top_exposed[:30],
    }


# ════════════════════════════════════════════════════════════════
# AI ADVISOR (OpenRouter + Kimi)
# ════════════════════════════════════════════════════════════════

def _build_ai_context():
    """Build comprehensive DB context for the AI advisor."""
    try:
        stats = get_stats()
    except Exception:
        stats = {"total_companies": 0, "total_emails": 0, "email_rate": 0, "hot_leads": 0,
                 "warm_leads": 0, "cold_leads": 0, "avg_health_score": 0, "cities": {}}

    try:
        analytics = get_analytics()
    except Exception:
        analytics = {"temperature_distribution": {}, "ssl_distribution": {}, "sentiment_distribution": {}}

    try:
        hot_leads = _sb_get("businesses",
            "select=name,city,sector,health_score,ssl_grade,outreach_hook,lead_temperature,"
            "breach_count,crisis_probability,rating,review_count,email,owner_name"
            "&order=health_score.asc&limit=15")
        if not isinstance(hot_leads, list):
            hot_leads = []
    except Exception:
        hot_leads = []

    try:
        crisis_data = _sb_get("businesses",
            "select=name,city,sector,crisis_probability,health_score,ssl_grade,breach_count"
            "&crisis_probability=gt.0.3&order=crisis_probability.desc&limit=10")
        if not isinstance(crisis_data, list):
            crisis_data = []
    except Exception:
        crisis_data = []

    try:
        all_leads = _sb_get("businesses",
            "select=lead_temperature,city,sector,ssl_grade,sentiment,responds_to_reviews"
            "&limit=500")
        if not isinstance(all_leads, list):
            all_leads = []
    except Exception:
        all_leads = []

    sectors = {}
    cities = {}
    ssl_grades = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for lead in all_leads:
        if not isinstance(lead, dict):
            continue
        temp = lead.get("lead_temperature", "COLD")
        city = lead.get("city", "Unknown")
        sector = lead.get("sector", "Unknown")
        ssl = lead.get("ssl_grade", "") or "F"
        sectors[sector] = sectors.get(sector, 0) + 1
        cities[city] = cities.get(city, 0) + 1
        if ssl in ssl_grades:
            ssl_grades[ssl] += 1

    responding = sum(1 for l in all_leads if l.get("responds_to_reviews"))
    sentiments = [l.get("sentiment", "neutral") for l in all_leads]
    pos = sum(1 for s in sentiments if s == "positive")
    neg = sum(1 for s in sentiments if s == "negative")
    neu = sum(1 for s in sentiments if s == "neutral")
    avg_sentiment = round((pos - neg) / max(len(sentiments), 1), 2)

    hot_list = []
    for h in hot_leads:
        if not isinstance(h, dict):
            continue
        entry = {
            "name": h.get("name", "")[:40],
            "city": h.get("city", ""),
            "sector": h.get("sector", ""),
            "health": h.get("health_score"),
            "ssl": h.get("ssl_grade", ""),
            "hook": (h.get("outreach_hook") or "")[:80],
            "crisis": h.get("crisis_probability"),
            "breaches": h.get("breach_count", 0),
        }
        hot_list.append(entry)

    crisis_list = []
    for c in crisis_data:
        if not isinstance(c, dict):
            continue
        crisis_list.append({
            "name": c.get("name", "")[:40],
            "city": c.get("city", ""),
            "crisis_pct": round((c.get("crisis_probability") or 0) * 100),
            "ssl": c.get("ssl_grade", ""),
            "breaches": c.get("breach_count", 0),
        })

    context = {
        "platform": "Crisora — AI-powered lead generation engine for local businesses",
        "what_we_do": (
            "We scrape businesses (Google Maps, Overpass, BizData, DuckDuckGo), "
            "enrich them (email finder, OSINT, SSL check, tech detection, crisis prediction), "
            "score leads (HOT/WARM/COLD), and generate outreach hooks for email campaigns. "
            "The user is the platform owner who uses the dashboard to monitor and grow."
        ),
        "total_companies": stats["total_companies"],
        "total_emails": stats["total_emails"],
        "email_rate": f"{stats['email_rate']}%",
        "hot_leads": stats["hot_leads"],
        "warm_leads": stats["warm_leads"],
        "cold_leads": stats["cold_leads"],
        "avg_health_score": stats["avg_health_score"],
        "sectors_breakdown": sectors,
        "cities_breakdown": cities,
        "ssl_grades": ssl_grades,
        "responding_to_reviews_pct": round(responding / max(len(all_leads), 1) * 100),
        "avg_sentiment": avg_sentiment,
        "sentiment_distribution": {"positive": pos, "negative": neg, "neutral": neu},
        "top_hot_leads": hot_list[:10],
        "at_risk_companies": crisis_list[:5],
    }
    return context


def ask_ai(question, openrouter_key="", kimi_key=""):
    """Ask AI advisor with full DB context."""
    try:
        context = _build_ai_context()
    except Exception as e:
        logger.error(f"AI context build error: {e}")
        try:
            stats = get_stats()
            context = {
                "total_companies": stats.get("total_companies", 0),
                "total_emails": stats.get("total_emails", 0),
                "hot_leads": stats.get("hot_leads", 0),
                "warm_leads": stats.get("warm_leads", 0),
                "cold_leads": stats.get("cold_leads", 0),
                "avg_health_score": stats.get("avg_health_score", 0),
            }
        except Exception:
            context = {"error": "Could not load database context"}

    system_prompt = f"""You are Crisora AI Advisor — an expert business analyst for the platform owner.

PLATFORM OVERVIEW:
{json.dumps(context, indent=2, default=str)}

ROLE & RULES:
- You are talking to the platform owner (developer) who built Crisora
- The platform scrapes businesses, enriches them with OSINT/SSL/tech/crisis data, scores leads, and sends outreach emails
- Answer in the same language the user writes in (Arabic or English)
- Be concise and actionable (max 200 words)
- Reference specific numbers, names, and data from the context above
- Never fabricate data — only use what's provided above
- When asked about strategy, suggest which sectors/cities to target next
- When asked about a specific business, use the data provided
- When asked about health scores, explain what they mean (100=perfect, 0=critical)
- When asked about SSL grades: A=excellent, B=good, C=fair, D=poor, F=failing
- When asked about lead temperature: HOT=breaches/SSL F/low health, WARM=risk indicators, COLD=healthy
- When asked about crisis prediction: percentage = likelihood of security incident in next 90 days
- Suggest concrete next steps based on the data"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    # Try OpenRouter first (multiple free models)
    if openrouter_key:
        models_to_try = [
            "google/gemma-4-26b-a4b-it:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "google/gemma-4-31b-it:free",
            "nvidia/nemotron-nano-9b-v2:free",
        ]
        for model in models_to_try:
            try:
                resp = cffi_requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 500,
                    },
                    headers={
                        "Authorization": f"Bearer {openrouter_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://reviewer-lovat.vercel.app",
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if answer:
                        return {"answer": answer}
                elif resp.status_code == 429:
                    continue
            except Exception:
                continue

    # Fallback to Kimi (if key is valid)
    if kimi_key:
        try:
            resp = cffi_requests.post(
                "https://api.moonshot.cn/v1/chat/completions",
                json={"model": "moonshot-v1-8k", "messages": messages, "temperature": 0.7, "max_tokens": 500},
                headers={"Authorization": f"Bearer {kimi_key}", "Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"answer": data["choices"][0]["message"]["content"]}
        except Exception:
            pass

    return {"error": "AI service temporarily unavailable. Please try again."}


# ════════════════════════════════════════════════════════════════
# EMAIL DIGEST
# ════════════════════════════════════════════════════════════════

def generate_digest():
    stats = get_stats()
    hot_leads = _sb_get("businesses", "select=name,city,sector,health_score,ssl_grade,outreach_hook&lead_temperature=eq.HOT&order=health_score.asc&limit=5")

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    hot_list = ""
    for i, h in enumerate(hot_leads, 1):
        hot_list += f"  {i}. {h['name'][:40]} ({h['city']}) — Health: {h['health_score']}, SSL: {h['ssl_grade']}\n"

    if not hot_list:
        hot_list = "  No HOT leads found today.\n"

    return f"""
FindLeads Daily Digest — {today}
{'=' * 50}

DATABASE OVERVIEW:
  Total Companies: {stats['total_companies']}
  Total Emails: {stats['total_emails']} ({stats['email_rate']}% rate)
  HOT Leads: {stats['hot_leads']}
  WARM Leads: {stats['warm_leads']}
  COLD Leads: {stats['cold_leads']}
  Average Health: {stats['avg_health_score']}/100

TOP 5 HOT LEADS (Ready to Contact):
{hot_list}
CITIES SCANNED:
""" + "\n".join(f"  {c}: {n} companies" for c, n in sorted(stats["cities"].items(), key=lambda x: -x[1])) + f"""

{'=' * 50}
View Dashboard: https://reviewer-lovat.vercel.app/dashboard
"""


def send_digest_email():
    digest = generate_digest()
    logger.info(f"Digest generated:\n{digest}")
    return {"status": "ok", "digest": digest}


# ════════════════════════════════════════════════════════════════
# EXPORT DATA (CSV-ready, full DB with filters)
# ════════════════════════════════════════════════════════════════

ALL_EXPORT_COLUMNS = [
    "name", "city", "sector", "website", "phone", "email", "email_confidence",
    "lead_temperature", "health_score", "ssl_grade", "rating", "review_count",
    "sentiment", "responds_to_reviews", "outreach_hook", "tech_stack",
    "vulnerabilities", "open_ports", "security_warnings", "breach_count",
    "breach_names", "cvss_severity", "cvss_max", "crisis_probability",
    "crisis_risk_level", "crisis_recommendations", "instagram", "facebook",
    "firebase", "archive", "api_keys", "crtsh", "sherlock",
    "created_at",
]


def get_export_data(temp="", city="", sector="", ssl="", email="", search="",
                    health_min="", health_max="", min_crisis="", columns=""):
    filters = []
    if temp:
        filters.append(f"lead_temperature=eq.{temp}")
    if city:
        filters.append(f"city=eq.{city}")
    if sector:
        filters.append(f"sector=eq.{sector}")
    if ssl:
        filters.append(f"ssl_grade=eq.{ssl}")
    if email == "yes":
        filters.append("email=not.is.null")
    elif email == "no":
        filters.append("email=is.null")
    if search:
        filters.append(f"name=ilike.*{search}*")
    if health_min:
        filters.append(f"health_score=gte.{health_min}")
    if health_max:
        filters.append(f"health_score=lte.{health_max}")
    if min_crisis:
        filters.append(f"crisis_probability=gte.{min_crisis}")

    params = "&".join(filters) if filters else ""
    if params:
        params += "&"
    params += "order=lead_temperature.desc,health_score.asc&limit=5000"

    select_cols = ",".join(ALL_EXPORT_COLUMNS)
    data = _sb_get("businesses", f"select={select_cols}&{params}")

    if not isinstance(data, list):
        data = []

    selected_cols = [c.strip() for c in columns.split(",") if c.strip()] if columns else ALL_EXPORT_COLUMNS
    selected_cols = [c for c in selected_cols if c in ALL_EXPORT_COLUMNS]

    return {
        "total": len(data),
        "columns": selected_cols,
        "rows": data,
    }


# ════════════════════════════════════════════════════════════════
# OSINT EXPORT
# ════════════════════════════════════════════════════════════════

OSINT_EXPORT_COLUMNS = [
    "name", "city", "sector", "website", "phone", "email", "lead_temperature",
    "health_score", "ssl_grade", "firebase", "archive", "api_keys", "crtsh",
    "sherlock", "breach_count", "crisis_probability", "outreach_hook",
]


def get_osint_export(firebase="", archive_risk="", api_risk="", sherlock_risk="",
                     crtsh_min="", min_keys="", min_profiles="", min_subs="",
                     temp="", city="", sector="", ssl="", search="",
                     min_risk_score="", columns=""):
    businesses = _sb_get("businesses",
        "select=id,name,city,sector,website,phone,email,lead_temperature,"
        "health_score,ssl_grade,firebase,archive,api_keys,crtsh,sherlock,"
        "breach_count,crisis_probability,outreach_hook")

    if not isinstance(businesses, list):
        businesses = []

    filtered = []
    for b in businesses:
        fb = b.get("firebase") or {}
        if isinstance(fb, str):
            try: fb = json.loads(fb)
            except: fb = {}
        ar = b.get("archive") or {}
        if isinstance(ar, str):
            try: ar = json.loads(ar)
            except: ar = {}
        ak = b.get("api_keys") or {}
        if isinstance(ak, str):
            try: ak = json.loads(ak)
            except: ak = {}
        sh = b.get("sherlock") or {}
        if isinstance(sh, str):
            try: sh = json.loads(sh)
            except: sh = {}
        cr = b.get("crtsh") or {}
        if isinstance(cr, str):
            try: cr = json.loads(cr)
            except: cr = {}

        risk_score = 0
        if fb.get("firebase_detected"): risk_score += 30
        if ar.get("archive_risk") == "HIGH": risk_score += 25
        if ak.get("api_exposure_risk") == "HIGH": risk_score += 25
        if sh.get("sherlock_risk") == "HIGH": risk_score += 10
        if cr.get("subdomain_risk") == "HIGH": risk_score += 10
        b["_risk_score"] = risk_score
        b["_firebase_risk"] = fb.get("firebase_risk", "NONE")
        b["_firebase_detected"] = fb.get("firebase_detected", False)
        b["_firebase_open"] = fb.get("firebase_open", False)
        b["_firebase_project"] = fb.get("firebase_project_id", "")
        b["_firebase_url"] = fb.get("firebase_url", "")
        b["_archive_risk"] = ar.get("archive_risk", "NONE")
        b["_archive_urls"] = ar.get("archive_total_urls", 0)
        b["_archive_years"] = ar.get("archive_years_span", "")
        b["_archive_sensitive_count"] = len(ar.get("archive_sensitive_files") or [])
        b["_archive_admin_count"] = len(ar.get("archive_admin_panels") or [])
        b["_api_risk"] = ak.get("api_exposure_risk", "NONE")
        b["_api_count"] = ak.get("api_key_count", 0) or 0
        b["_api_types"] = list(set(k.get("type", "") for k in (ak.get("api_keys_found") or [])))
        b["_sherlock_risk"] = sh.get("sherlock_risk", "NONE")
        b["_sherlock_count"] = sh.get("profile_count", 0) or 0
        b["_sherlock_platforms"] = list((sh.get("profiles_found") or {}).keys())
        b["_crtsh_risk"] = cr.get("subdomain_risk", "NONE")
        b["_crtsh_subs"] = cr.get("subdomain_count", 0) or 0
        b["_crtsh_emails"] = cr.get("email_count", 0) or 0
        b["_crtsh_sub_list"] = cr.get("subdomains_found") or []

        if firebase == "yes" and not b["_firebase_detected"]: continue
        if firebase == "no" and b["_firebase_detected"]: continue
        if firebase == "open" and not b["_firebase_open"]: continue

        if archive_risk and b["_archive_risk"] != archive_risk: continue

        if api_risk and b["_api_risk"] != api_risk: continue
        if min_keys and b["_api_count"] < int(min_keys): continue

        if sherlock_risk and b["_sherlock_risk"] != sherlock_risk: continue
        if min_profiles and b["_sherlock_count"] < int(min_profiles): continue

        if crtsh_min and b["_crtsh_subs"] < int(crtsh_min): continue
        if min_subs and b["_crtsh_subs"] < int(min_subs): continue
        if min_risk_score and risk_score < int(min_risk_score): continue

        if temp and b.get("lead_temperature") != temp: continue
        if city and b.get("city") != city: continue
        if sector and b.get("sector") != sector: continue
        if ssl and (b.get("ssl_grade") or "F") != ssl: continue
        if search and search.lower() not in (b.get("name") or "").lower(): continue

        filtered.append(b)

    filtered.sort(key=lambda x: x["_risk_score"], reverse=True)

    all_cols = [
        "name", "city", "sector", "website", "phone", "email", "lead_temperature",
        "health_score", "ssl_grade", "rating", "review_count",
        "firebase_detected", "firebase_project", "firebase_url", "firebase_risk",
        "archive_risk", "archive_urls", "archive_years", "archive_sensitive_count", "archive_admin_count",
        "api_risk", "api_count", "api_types",
        "sherlock_risk", "sherlock_count", "sherlock_platforms",
        "crtsh_risk", "crtsh_subs", "crtsh_emails", "crtsh_sub_list",
        "risk_score", "breach_count", "crisis_probability", "outreach_hook",
    ]

    selected_cols = [c.strip() for c in columns.split(",") if c.strip()] if columns else all_cols
    selected_cols = [c for c in selected_cols if c in all_cols]

    rows = []
    for b in filtered:
        row = {}
        for c in selected_cols:
            if c.startswith("firebase_"):
                key = c.replace("firebase_", "")
                if c == "firebase_detected":
                    row[c] = b["_firebase_detected"]
                elif c == "firebase_project":
                    row[c] = b["_firebase_project"]
                elif c == "firebase_url":
                    row[c] = b["_firebase_url"]
                elif c == "firebase_risk":
                    row[c] = b["_firebase_risk"]
            elif c.startswith("archive_"):
                row[c] = b.get("_" + c, "")
            elif c.startswith("api_"):
                row[c] = b.get("_" + c, "")
            elif c.startswith("sherlock_"):
                row[c] = b.get("_" + c, "")
            elif c.startswith("crtsh_"):
                row[c] = b.get("_" + c, "")
            elif c == "risk_score":
                row[c] = b["_risk_score"]
            else:
                row[c] = b.get(c)
        rows.append(row)

    return {
        "total": len(rows),
        "columns": selected_cols,
        "rows": rows,
    }


# ════════════════════════════════════════════════════════════════
# QUALITY GATE QG-02: Human Review Queue
# ════════════════════════════════════════════════════════════════

def get_review_queue():
    try:
        r = _sb_get("businesses", "select=id,name,city,sector,website,crisis_probability,crisis_risk_level,requires_review,review_flags,health_score,ssl_grade,lead_temperature&requires_review=eq.true&order=crisis_probability.desc&limit=100")
        businesses = r.json() if r.status_code == 200 else []
        total = _sb_get("businesses", "select=id&requires_review=eq.true", count=True)
        count = int(total.headers.get("content-range", "0").split("/")[1]) if total.status_code == 200 else 0
        return {"businesses": businesses, "total": count}
    except Exception as e:
        logger.error(f"Review queue error: {e}")
        return {"businesses": [], "total": 0}


def approve_review(biz_id):
    try:
        r = _sb_patch("businesses", f"id=eq.{biz_id}", {"requires_review": False, "review_flags": None})
        return {"ok": r.status_code in (200, 204)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def dismiss_review(biz_id):
    try:
        r = _sb_patch("businesses", f"id=eq.{biz_id}", {"requires_review": False, "review_flags": None})
        return {"ok": r.status_code in (200, 204)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
