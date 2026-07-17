"""
Deep OSINT Engine — Orchestrator
Runs all 8 OSINT modules on a business and returns comprehensive intelligence.
"""

import time
from typing import Dict, Optional

from .tech_detector import detect_tech_stack
from .whois_lookup import whois_lookup
from .dns_intel import dns_intelligence
from .sentiment import analyze_sentiment, analyze_reviews_batch
from .financial_health import calculate_health_score
from .hidden_emails import find_hidden_emails
from .domain_history import get_domain_history
from .ssl_intel import ssl_intelligence, get_ssl_grade


class DeepOSINTEngine:
    """
    Runs all Deep OSINT modules on a business website/domain.
    
    Usage:
        engine = DeepOSINTEngine()
        result = engine.analyze("mmdc.ae", reviews=["Great service!", "Terrible..."])
    """

    def __init__(self, skip_modules: Optional[list] = None):
        self.skip_modules = skip_modules or []

    def analyze(
        self,
        domain: str,
        reviews: Optional[list] = None,
        rating: float = 0.0,
        review_count: int = 0,
        response_rate: float = 0.0,
        last_review_days: Optional[int] = None,
    ) -> Dict:
        """
        Run full Deep OSINT analysis on a domain.
        
        Returns comprehensive intelligence report.
        """
        start = time.time()

        result = {
            "domain": domain,
            "modules_run": [],
            "errors": [],
        }

        if "tech" not in self.skip_modules:
            try:
                result["tech"] = detect_tech_stack(domain)
                result["modules_run"].append("tech")
            except Exception as e:
                result["errors"].append(f"tech: {e}")
                result["tech"] = {}

        if "whois" not in self.skip_modules:
            try:
                clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
                result["whois"] = whois_lookup(clean_domain)
                result["modules_run"].append("whois")
            except Exception as e:
                result["errors"].append(f"whois: {e}")
                result["whois"] = {}

        if "dns" not in self.skip_modules:
            try:
                clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
                result["dns"] = dns_intelligence(clean_domain)
                result["modules_run"].append("dns")
            except Exception as e:
                result["errors"].append(f"dns: {e}")
                result["dns"] = {}

        if "sentiment" not in self.skip_modules and reviews:
            try:
                result["sentiment"] = analyze_reviews_batch(reviews)
                result["modules_run"].append("sentiment")
            except Exception as e:
                result["errors"].append(f"sentiment: {e}")
                result["sentiment"] = {}

        if "ssl" not in self.skip_modules:
            try:
                result["ssl"] = ssl_intelligence(domain)
                result["ssl_grade"] = get_ssl_grade(result["ssl"])
                result["modules_run"].append("ssl")
            except Exception as e:
                result["errors"].append(f"ssl: {e}")
                result["ssl"] = {}

        if "hidden_emails" not in self.skip_modules:
            try:
                result["hidden_emails"] = find_hidden_emails(domain)
                result["modules_run"].append("hidden_emails")
            except Exception as e:
                result["errors"].append(f"hidden_emails: {e}")
                result["hidden_emails"] = {}

        if "history" not in self.skip_modules:
            try:
                clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
                result["history"] = get_domain_history(clean_domain)
                result["modules_run"].append("history")
            except Exception as e:
                result["errors"].append(f"history: {e}")
                result["history"] = {}

        if "health" not in self.skip_modules:
            try:
                result["health"] = calculate_health_score(
                    rating=rating,
                    review_count=review_count,
                    response_rate=response_rate,
                    sentiment_data=result.get("sentiment"),
                    whois_data=result.get("whois"),
                    tech_data=result.get("tech"),
                    last_review_days=last_review_days,
                )
                result["modules_run"].append("health")
            except Exception as e:
                result["errors"].append(f"health: {e}")
                result["health"] = {}

        elapsed = round(time.time() - start, 2)
        result["elapsed_seconds"] = elapsed

        return result

    def quick_scan(self, domain: str) -> Dict:
        """Quick scan with only fast modules (tech, ssl, dns)."""
        return self.analyze(
            domain=domain,
            skip_modules=["whois", "sentiment", "hidden_emails", "history", "health"],
        )

    def full_scan(self, domain: str, reviews: Optional[list] = None, **kwargs) -> Dict:
        """Full scan with all modules."""
        return self.analyze(domain=domain, reviews=reviews, **kwargs)


def analyze_business_osint(
    domain: str,
    reviews: Optional[list] = None,
    rating: float = 0.0,
    review_count: int = 0,
    response_rate: float = 0.0,
) -> Dict:
    """
    Convenience function for full OSINT analysis.
    """
    engine = DeepOSINTEngine()
    return engine.analyze(
        domain=domain,
        reviews=reviews,
        rating=rating,
        review_count=review_count,
        response_rate=response_rate,
    )


if __name__ == "__main__":
    engine = DeepOSINTEngine()
    test_domain = "mmdc.ae"
    test_reviews = [
        "Great dental clinic! Very professional staff.",
        "Terrible experience. Long waiting times.",
        "Dr. Ahmed is the best dentist in Dubai!",
    ]

    print(f"Running Deep OSINT on: {test_domain}")
    print("=" * 60)

    result = engine.analyze(
        domain=test_domain,
        reviews=test_reviews,
        rating=4.2,
        review_count=150,
        response_rate=25,
    )

    print(f"\nModules run: {result['modules_run']}")
    print(f"Elapsed: {result['elapsed_seconds']}s")
    print(f"Errors: {result['errors']}")

    if "tech" in result:
        print(f"\nTech Stack: {result['tech'].get('detected', [])}")
    if "whois" in result:
        w = result["whois"]
        print(f"WHOIS: Registrar={w.get('registrar')}, Expires={w.get('expiry_date')}, Days={w.get('days_until_expiry')}")
    if "dns" in result:
        d = result["dns"]
        print(f"DNS: Mail={d.get('mail_provider')}, Hosting={d.get('hosting_provider')}")
    if "ssl" in result:
        s = result["ssl"]
        print(f"SSL: Valid={s.get('valid')}, Grade={result.get('ssl_grade')}, Expires={s.get('not_after')}")
    if "sentiment" in result:
        sent = result["sentiment"]
        print(f"Sentiment: Avg={sent.get('average_stars')}*, Neg={sent.get('negative_percentage')}%")
    if "health" in result:
        h = result["health"]
        print(f"Health: {h.get('health_score')}/100 ({h.get('status')})")
        print(f"  Warnings: {h.get('warnings')}")
        print(f"  Opportunity: {h.get('opportunity')}")
    if "hidden_emails" in result:
        he = result["hidden_emails"]
        print(f"Hidden Emails: {he.get('total_found')} found")
    if "history" in result:
        hist = result["history"]
        print(f"History: {hist.get('total_snapshots')} snapshots, First={hist.get('first_snapshot')}")
