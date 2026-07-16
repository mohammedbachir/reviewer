"""
Lead Generator — Review Analyzer
Analyzes business reviews to find those with low response rates.
"""

from finder import get_business_reviews


def analyze_response_rate(business, api_key, max_reviews=50):
    """
    Analyze how well a business responds to reviews.
    
    Args:
        business: Business dict from finder
        api_key: Outscraper API key
        max_reviews: Maximum reviews to analyze
    
    Returns:
        Updated business dict with response analysis
    """
    place_id = business.get("place_id")
    if not place_id:
        business["response_rate"] = 0
        business["unanswered_reviews"] = business.get("review_count", 0)
        return business
    
    reviews = get_business_reviews(place_id, api_key, max_reviews)
    
    if not reviews:
        business["response_rate"] = 0
        business["unanswered_reviews"] = business.get("review_count", 0)
        return business    
    total_reviews = len(reviews)
    replied_reviews = sum(1 for r in reviews if r.get("has_owner_reply"))
    
    response_rate = (replied_reviews / total_reviews * 100) if total_reviews > 0 else 0
    unanswered = total_reviews - replied_reviews
    
    business["total_reviews_analyzed"] = total_reviews
    business["replied_reviews"] = replied_reviews
    business["unanswered_reviews"] = unanswered
    business["response_rate"] = round(response_rate, 1)
    business["sample_reviews"] = reviews[:3]  # Keep 3 sample reviews
    
    return business


def filter_leads(businesses, max_response_rate=30, min_reviews=5):
    """
    Filter businesses to find good leads (low response rate).
    
    Args:
        businesses: List of analyzed business dicts
        max_response_rate: Maximum response rate to consider (default 30%)
        min_reviews: Minimum total reviews required
    
    Returns:
        Filtered list of lead businesses
    """
    leads = []
    
    for biz in businesses:
        # Skip if not enough reviews
        if biz.get("review_count", 0) < min_reviews:
            continue
        
        # Skip if response rate is too high
        if biz.get("response_rate", 0) > max_response_rate:
            continue
        
        # Skip if no website (need for email finding)
        if not biz.get("website"):
            continue
        
        leads.append(biz)
    
    return leads


def print_analysis(businesses):
    """Print analysis summary."""
    if not businesses:
        print("[Analyzer] No businesses to analyze")
        return
    
    total = len(businesses)
    low_response = sum(1 for b in businesses if b.get("response_rate", 100) <= 30)
    has_website = sum(1 for b in businesses if b.get("website"))
    qualified = sum(1 for b in businesses if 
                    b.get("response_rate", 100) <= 30 and 
                    b.get("website") and 
                    b.get("review_count", 0) >= 5)
    
    print(f"\n[Analyzer] === Analysis Summary ===")
    print(f"Total businesses analyzed: {total}")
    print(f"Low response rate (<=30%): {low_response}")
    print(f"Have website: {has_website}")
    print(f"Qualified leads: {qualified}")
    print(f"================================\n")
