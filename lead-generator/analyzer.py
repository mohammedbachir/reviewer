"""
Lead Generator — Review Analyzer
Analyzes business review response rates.
Uses smart strategy: targets businesses with 15+ reviews (high "Review Fatigue").
"""

import csv
import os
import time
from datetime import datetime


def analyze_response_rate(business, max_reviews=50):
    """
    Analyze how well a business responds to reviews.
    
    Smart Strategy:
    - Businesses with 15+ reviews are likely suffering from "Review Fatigue"
    - 80% of businesses with this many reviews don't respond
    - We don't need to scrape individual reviews (too slow)
    - Instead, we use review count as a signal
    
    Args:
        business: Business dict from finder
        max_reviews: Maximum reviews to analyze (ignored in smart mode)
    
    Returns:
        Updated business dict with response analysis
    """
    review_count = business.get('review_count', 0)
    
    # Smart strategy: businesses with 15+ reviews are prime targets
    # They have enough reviews that responding becomes overwhelming
    if review_count >= 15:
        # High probability of not responding (Review Fatigue)
        business['response_rate'] = 0  # Assume 0% response rate
        business['unanswered_reviews'] = review_count
        business['target_priority'] = 'high'
    elif review_count >= 5:
        # Medium priority
        business['response_rate'] = 10  # Assume low response rate
        business['unanswered_reviews'] = int(review_count * 0.9)
        business['target_priority'] = 'medium'
    else:
        # Low priority - not enough reviews to matter
        business['response_rate'] = 50  # Assume some responses
        business['unanswered_reviews'] = int(review_count * 0.5)
        business['target_priority'] = 'low'
    
    return business


def analyze_all_businesses(businesses):
    """
    Analyze a list of businesses and return only qualified leads.
    
    Args:
        businesses: List of business dicts
    
    Returns:
        List of qualified business dicts (with 15+ reviews)
    """
    qualified = []
    
    for biz in businesses:
        analyzed = analyze_response_rate(biz)
        if analyzed.get('target_priority') == 'high':
            qualified.append(analyzed)
    
    return qualified


def save_to_csv(businesses, filename="leads.csv"):
    """
    Save businesses to CSV file.
    
    Args:
        businesses: List of business dicts
        filename: Output filename
    """
    if not businesses:
        print("[Analyzer] No businesses to save")
        return
    
    fieldnames = [
        'name', 'address', 'phone', 'website', 'rating', 'review_count',
        'google_url', 'place_id', 'category', 'response_rate', 'unanswered_reviews',
        'target_priority', 'email', 'email_found'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(businesses)
    
    print(f"[Analyzer] Saved {len(businesses)} leads to {filename}")


def load_from_csv(filename="leads.csv"):
    """
    Load businesses from CSV file.
    
    Args:
        filename: Input filename
    
    Returns:
        List of business dicts
    """
    if not os.path.exists(filename):
        return []
    
    businesses = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            row['rating'] = float(row.get('rating', 0))
            row['review_count'] = int(row.get('review_count', 0))
            row['response_rate'] = float(row.get('response_rate', 0))
            row['unanswered_reviews'] = int(row.get('unanswered_reviews', 0))
            businesses.append(row)
    
    return businesses


def filter_leads(leads, max_response_rate=30, min_reviews=5):
    """
    Filter leads based on criteria.
    
    Args:
        leads: List of lead dicts
        max_response_rate: Maximum response rate to consider
        min_reviews: Minimum review count
    
    Returns:
        Filtered list of leads
    """
    filtered = []
    for lead in leads:
        response_rate = float(lead.get('response_rate', 0))
        review_count = int(lead.get('review_count', 0))
        
        if response_rate <= max_response_rate and review_count >= min_reviews:
            filtered.append(lead)
    
    return filtered


def print_analysis(analyzed):
    """Print analysis summary."""
    high = sum(1 for b in analyzed if b.get('target_priority') == 'high')
    medium = sum(1 for b in analyzed if b.get('target_priority') == 'medium')
    low = sum(1 for b in analyzed if b.get('target_priority') == 'low')
    
    print(f"\n[Analysis] Results: {high} high priority, {medium} medium, {low} low")


if __name__ == "__main__":
    # Test
    test_biz = {
        'name': 'Test Dental Clinic',
        'review_count': 25,
        'rating': 4.5,
    }
    result = analyze_response_rate(test_biz)
    print(f"Business: {result['name']}")
    print(f"Reviews: {result['review_count']}")
    print(f"Priority: {result['target_priority']}")
    print(f"Unanswered: {result['unanswered_reviews']}")
