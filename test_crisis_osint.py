import json
from scraper.crisis_predictor import predict_crisis

biz = {
    'id': 4121,
    'name': 'Abccollision',
    'ssl_grade': 'C',
    'health_score': 67,
    'breach_count': 0,
    'vulnerabilities': [],
    'open_ports': [],
    'security_warnings': [],
    'rating': 4.5,
    'review_count': 50,
    'sentiment': 'positive',
    'responds_to_reviews': False,
    'firebase': {'firebase_detected': True, 'firebase_open': False, 'firebase_project_id': '7abd56be', 'firebase_risk': 'DETECTED'},
    'api_keys': {'api_key_count': 96, 'api_exposure_risk': 'HIGH', 'api_keys_found': [{'type': 'Heroku_API_Key', 'value': 'xxx'}]},
    'archive': {'archive_risk': 'NONE', 'archive_sensitive_files': [], 'archive_admin_panels': []},
    'sherlock': {'profile_count': 1, 'sherlock_risk': 'MEDIUM'},
    'crtsh': {'subdomain_count': 0, 'email_count': 0},
}

result = predict_crisis(biz)
prob = result["crisis_probability"] * 100
level = result["risk_level"]
model = result["model_type"]
print(f"Crisis: {prob:.1f}% ({level})")
print(f"Model: {model}")
print("Recommendations:")
for r in result["recommendations"]:
    print(f"  [{r['priority']}] {r['category']}: {r['message'][:80]}")
