"""Quick test of Deep OSINT Engine"""
from osint.engine import DeepOSINTEngine

engine = DeepOSINTEngine()

print("Testing Deep OSINT Engine on mmdc.ae...")
print("=" * 60)

result = engine.analyze(
    domain="mmdc.ae",
    reviews=["Great dental clinic! Very professional staff.", "Terrible experience. Long waiting times.", "Dr. Ahmed is the best dentist in Dubai!"],
    rating=4.2,
    review_count=150,
    response_rate=25,
)

print(f"Modules run: {result['modules_run']}")
print(f"Elapsed: {result['elapsed_seconds']}s")
print(f"Errors: {result['errors']}")

if "tech" in result:
    t = result["tech"]
    print(f"\n--- Tech Stack ---")
    print(f"  Detected: {t.get('detected', [])}")
    print(f"  CMS: {t.get('cms', [])}")
    print(f"  Frameworks: {t.get('frameworks', [])}")
    print(f"  Analytics: {t.get('analytics', [])}")
    print(f"  Hosting: {t.get('hosting', [])}")
    print(f"  SSL: {t.get('ssl')}")
    print(f"  Mobile: {t.get('mobile_friendly')}")
    print(f"  Response: {t.get('response_time_ms')}ms")

if "whois" in result:
    w = result["whois"]
    print(f"\n--- WHOIS ---")
    print(f"  Registrar: {w.get('registrar')}")
    print(f"  Owner: {w.get('registrant_name')}")
    print(f"  Org: {w.get('registrant_org')}")
    print(f"  Country: {w.get('registrant_country')}")
    print(f"  Created: {w.get('created_date')}")
    print(f"  Expires: {w.get('expiry_date')}")
    print(f"  Days until expiry: {w.get('days_until_expiry')}")
    print(f"  Nameservers: {w.get('nameservers')}")
    print(f"  Emails: {w.get('emails')}")

if "dns" in result:
    d = result["dns"]
    print(f"\n--- DNS ---")
    print(f"  Has DNS: {d.get('has_dns')}")
    print(f"  A Records: {d.get('a_records')}")
    print(f"  MX Records: {d.get('mx_records')}")
    print(f"  NS Records: {d.get('ns_records')}")
    print(f"  Mail Provider: {d.get('mail_provider')}")
    print(f"  Hosting: {d.get('hosting_provider')}")
    print(f"  SPF: {d.get('spf_valid')}")
    print(f"  DMARC: {d.get('dmarc_valid')}")

if "ssl" in result:
    s = result["ssl"]
    print(f"\n--- SSL ---")
    print(f"  Has SSL: {s.get('has_ssl')}")
    print(f"  Valid: {s.get('valid')}")
    print(f"  Grade: {result.get('ssl_grade')}")
    print(f"  Issuer: {s.get('issuer')}")
    print(f"  Expires: {s.get('not_after')}")
    print(f"  Days: {s.get('days_until_expiry')}")
    print(f"  Self-signed: {s.get('is_self_signed')}")

if "sentiment" in result:
    sent = result["sentiment"]
    print(f"\n--- Sentiment ---")
    print(f"  Total reviews: {sent.get('total_reviews')}")
    print(f"  Average stars: {sent.get('average_stars')}")
    print(f"  Negative %: {sent.get('negative_percentage')}%")
    print(f"  Positive %: {sent.get('positive_percentage')}%")
    print(f"  Distribution: {sent.get('sentiment_distribution')}")

if "health" in result:
    h = result["health"]
    print(f"\n--- Health Score ---")
    print(f"  Score: {h.get('health_score')}/100")
    print(f"  Status: {h.get('status')}")
    print(f"  Opportunity: {h.get('opportunity')}")
    print(f"  Scores: {h.get('scores')}")
    print(f"  Warnings: {h.get('warnings')}")
    print(f"  Recommendations: {h.get('recommendations')}")

if "hidden_emails" in result:
    he = result["hidden_emails"]
    print(f"\n--- Hidden Emails ---")
    print(f"  Total: {he.get('total_found')}")
    print(f"  Valid: {he.get('valid_emails')}")
    print(f"  By source: {he.get('emails_by_source')}")

if "history" in result:
    hist = result["history"]
    print(f"\n--- Domain History ---")
    print(f"  Has history: {hist.get('has_history')}")
    print(f"  Total snapshots: {hist.get('total_snapshots')}")
    print(f"  First: {hist.get('first_snapshot')}")
    print(f"  Last: {hist.get('last_snapshot')}")
    print(f"  Frequency: {hist.get('frequency')}")
    print(f"  Snapshots/year: {hist.get('snapshots_per_year')}")

print(f"\n{'='*60}")
print(f"TEST COMPLETE - {len(result['modules_run'])} modules ran in {result['elapsed_seconds']}s")
print(f"{'='*60}")
