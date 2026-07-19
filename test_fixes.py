"""Test all 3 fixes"""
import sys, os
sys.path.insert(0, 'F:/reviewer')
os.chdir('F:/reviewer')

from scraper.finder import _clean_business_name

# Fix 1: Name cleaning
tests = [
    ("Medspa", "https://miamimed-spa.com"),
    ("Plastic Surgery", "https://www.jrosenbergmd.com"),
    ("Solar Panel Installer", "https://sunnysolar.com"),
    ("HVAC Contractor", "https://chimneyrockac.com"),
    ("Shuman Legal", "https://www.shumanlegal.com"),
    ("Best Dental Implants in Toronto", "https://smiledental.ca"),
]
print("=== Fix 1: Name Cleaning ===")
for title, url in tests:
    result = _clean_business_name(title, url)
    print(f"  {title:<40} -> {result}")

# Fix 2: Lead scoring
print("\n=== Fix 2: Lead Scoring ===")
sys.path.insert(0, 'F:/reviewer')
from app import _score_lead

cases = [
    {"name": "Shuman Legal", "ssl_grade": "F", "breach_count": 9, "health_score": 58},
    {"name": "CandelTech", "ssl_grade": "B", "breach_count": 1, "health_score": 93},
    {"name": "Medspa", "ssl_grade": "C", "breach_count": 0, "health_score": 70},
    {"name": "BadSite", "ssl_grade": "F", "breach_count": 0, "health_score": 30},
    {"name": "HealthySite", "ssl_grade": "A", "breach_count": 0, "health_score": 95},
]
for c in cases:
    temp = _score_lead(c)
    print(f"  {c['name']:<20} SSL={c['ssl_grade']} Breaches={c['breach_count']} Health={c['health_score']} -> {temp}")
