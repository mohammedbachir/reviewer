"""
#10 Financial Health Analysis
Derives business financial health from multiple signals:
- Review sentiment trends
- WHOIS domain age/expiry
- Tech stack freshness
- Response rate to reviews
- Rating trends
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta


def calculate_health_score(
    rating: float = 0.0,
    review_count: int = 0,
    response_rate: float = 0.0,
    sentiment_data: Optional[Dict] = None,
    whois_data: Optional[Dict] = None,
    tech_data: Optional[Dict] = None,
    last_review_days: Optional[int] = None,
) -> Dict:
    """
    Calculate business health score (0-100) from multiple signals.
    
    Returns:
        Dict with health score, warning signs, and recommendations
    """
    scores = {}
    warnings = []
    recommendations = []

    if rating > 0:
        rating_score = min(rating / 5.0 * 100, 100)
        scores["rating"] = rating_score
        if rating < 3.0:
            warnings.append(f"Low rating: {rating}/5")
            recommendations.append("Business has poor customer satisfaction")
        elif rating < 4.0:
            warnings.append(f"Below average rating: {rating}/5")

    if review_count > 0:
        if review_count >= 100:
            scores["review_volume"] = 100
        elif review_count >= 50:
            scores["review_volume"] = 80
        elif review_count >= 20:
            scores["review_volume"] = 60
        elif review_count >= 5:
            scores["review_volume"] = 40
        else:
            scores["review_volume"] = 20
            warnings.append(f"Very few reviews: {review_count}")
            recommendations.append("Low online presence - opportunity to help them grow")

    scores["response_rate"] = min(response_rate, 100)
    if response_rate < 10:
        warnings.append(f"Almost no responses to reviews: {response_rate:.0f}%")
        recommendations.append("High opportunity - they clearly need help with review management")
    elif response_rate < 50:
        warnings.append(f"Low response rate: {response_rate:.0f}%")

    if sentiment_data:
        neg_pct = sentiment_data.get("negative_percentage", 0)
        avg_stars = sentiment_data.get("average_stars", 3.0)
        sentiment_score = max(0, 100 - neg_pct * 2)
        scores["sentiment"] = sentiment_score
        if neg_pct > 50:
            warnings.append(f"Majority negative reviews: {neg_pct:.0f}%")
            recommendations.append("Business is losing customers - urgent outreach opportunity")
        elif neg_pct > 30:
            warnings.append(f"High negative reviews: {neg_pct:.0f}%")

    if whois_data:
        expiry_days = whois_data.get("days_until_expiry")
        created_date = whois_data.get("created_date", "")

        if expiry_days is not None:
            if expiry_days < 0:
                scores["domain"] = 0
                warnings.append("Domain has EXPIRED")
                recommendations.append("Critical: domain expired - business may be closing")
            elif expiry_days < 30:
                scores["domain"] = 20
                warnings.append(f"Domain expires in {expiry_days} days")
                recommendations.append("Domain expiring soon - opportunity to offer help")
            elif expiry_days < 90:
                scores["domain"] = 50
                warnings.append(f"Domain expires in {expiry_days} days")
            else:
                scores["domain"] = 100

        if created_date:
            try:
                created = datetime.strptime(created_date, "%Y-%m-%d")
                age_years = (datetime.now() - created).days / 365
                if age_years < 1:
                    warnings.append(f"New domain: registered {age_years:.1f} years ago")
                elif age_years > 10:
                    scores["domain_age"] = 100
                else:
                    scores["domain_age"] = min(age_years * 10, 100)
            except Exception:
                pass

    if tech_data:
        detected = tech_data.get("detected", [])
        ssl = tech_data.get("ssl", False)
        mobile = tech_data.get("mobile_friendly", False)
        response_ms = tech_data.get("response_time_ms", 0)

        tech_score = 50
        if ssl:
            tech_score += 15
        else:
            warnings.append("No SSL certificate")
            recommendations.append("Website lacks SSL - security concern")
        if mobile:
            tech_score += 15
        else:
            warnings.append("Website not mobile-friendly")
            recommendations.append("Website not optimized for mobile")
        if response_ms > 5000:
            tech_score -= 20
            warnings.append(f"Very slow website: {response_ms}ms")
            recommendations.append("Website is very slow - bad for business")
        elif response_ms > 3000:
            tech_score -= 10
            warnings.append(f"Slow website: {response_ms}ms")
        if len(detected) > 5:
            tech_score += 10

        scores["tech"] = max(0, min(tech_score, 100))

    if last_review_days is not None:
        if last_review_days > 180:
            scores["activity"] = 10
            warnings.append(f"No reviews for {last_review_days} days")
            recommendations.append("Business appears dormant")
        elif last_review_days > 90:
            scores["activity"] = 30
            warnings.append(f"No reviews for {last_review_days} days")
        elif last_review_days > 30:
            scores["activity"] = 60
        else:
            scores["activity"] = 100

    if scores:
        health_score = round(sum(scores.values()) / len(scores))
    else:
        health_score = 50

    if health_score >= 80:
        status = "healthy"
        opportunity = "low"
    elif health_score >= 60:
        status = "moderate"
        opportunity = "medium"
    elif health_score >= 40:
        status = "declining"
        opportunity = "high"
    elif health_score >= 20:
        status = "critical"
        opportunity = "very_high"
    else:
        status = "dying"
        opportunity = "urgent"

    if not recommendations:
        if opportunity in ("high", "very_high", "urgent"):
            recommendations.append("Good opportunity for outreach - business needs help")
        else:
            recommendations.append("Business seems healthy - may not need services")

    return {
        "health_score": health_score,
        "status": status,
        "opportunity": opportunity,
        "scores": scores,
        "warnings": warnings,
        "recommendations": recommendations,
    }


if __name__ == "__main__":
    test_cases = [
        {
            "name": "Healthy Business",
            "rating": 4.5,
            "review_count": 200,
            "response_rate": 85,
            "sentiment_data": {"negative_percentage": 5, "average_stars": 4.5},
            "whois_data": {"days_until_expiry": 365, "created_date": "2015-03-15"},
            "tech_data": {"ssl": True, "mobile_friendly": True, "response_time_ms": 1500, "detected": ["WordPress", "Google Analytics"]},
        },
        {
            "name": "Struggling Business",
            "rating": 2.1,
            "review_count": 45,
            "response_rate": 5,
            "sentiment_data": {"negative_percentage": 65, "average_stars": 2.0},
            "whois_data": {"days_until_expiry": 15, "created_date": "2022-06-01"},
            "tech_data": {"ssl": False, "mobile_friendly": False, "response_time_ms": 8000, "detected": ["WordPress"]},
        },
    ]

    for case in test_cases:
        print(f"\n{'='*60}")
        print(f"Health Score: {case['name']}")
        print("=" * 60)
        result = calculate_health_score(
            rating=case["rating"],
            review_count=case["review_count"],
            response_rate=case["response_rate"],
            sentiment_data=case["sentiment_data"],
            whois_data=case["whois_data"],
            tech_data=case["tech_data"],
        )
        print(f"  Score: {result['health_score']}/100")
        print(f"  Status: {result['status']}")
        print(f"  Opportunity: {result['opportunity']}")
        print(f"  Scores: {result['scores']}")
        print(f"  Warnings: {result['warnings']}")
        print(f"  Recommendations: {result['recommendations']}")
