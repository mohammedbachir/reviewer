from scraper.crisis_predictor import predict_crisis

cases = [
    {"name": "Firebase OPEN", "firebase": {"firebase_detected": True, "firebase_open": True}, "api_keys": {"api_key_count": 0}, "archive": {}, "sherlock": {}, "crtsh": {}},
    {"name": "API Keys 96 + Archive HIGH", "firebase": {"firebase_detected": False}, "api_keys": {"api_key_count": 96}, "archive": {"archive_risk": "HIGH", "archive_sensitive_files": [{"a":1}]*15, "archive_admin_panels": [{"a":1}]*6}, "sherlock": {}, "crtsh": {}},
    {"name": "Clean company", "firebase": {"firebase_detected": False}, "api_keys": {"api_key_count": 0}, "archive": {"archive_risk": "NONE", "archive_sensitive_files": [], "archive_admin_panels": []}, "sherlock": {"profile_count": 1}, "crtsh": {}},
    {"name": "SSL=F only", "firebase": {"firebase_detected": False}, "api_keys": {"api_key_count": 0}, "archive": {"archive_risk": "NONE", "archive_sensitive_files": [], "archive_admin_panels": []}, "sherlock": {}, "crtsh": {}},
    {"name": "API Keys 10", "firebase": {"firebase_detected": False}, "api_keys": {"api_key_count": 10}, "archive": {"archive_risk": "NONE", "archive_sensitive_files": [], "archive_admin_panels": []}, "sherlock": {}, "crtsh": {}},
    {"name": "Sherlock 5 profiles", "firebase": {"firebase_detected": False}, "api_keys": {"api_key_count": 0}, "archive": {"archive_risk": "NONE", "archive_sensitive_files": [], "archive_admin_panels": []}, "sherlock": {"profile_count": 5}, "crtsh": {}},
]

base = {"ssl_grade": "B", "health_score": 75, "breach_count": 0, "vulnerabilities": [], "open_ports": [], "security_warnings": [], "rating": 4.0, "review_count": 30, "sentiment": "positive", "responds_to_reviews": False}

for case in cases:
    biz = {**base, **case}
    result = predict_crisis(biz)
    prob = result["crisis_probability"] * 100
    level = result["risk_level"]
    recs = len(result["recommendations"])
    print(f"{case['name']:<30} {prob:5.1f}% {level:<10} ({recs} recs)")
