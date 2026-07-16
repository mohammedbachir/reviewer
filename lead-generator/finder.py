"""
Lead Generator — Business Finder
Uses Outscraper API to find businesses on Google Maps.
"""

import requests
import time


def find_businesses(city, business_type, limit=50, api_key=None):
    """
    Find businesses using Outscraper Google Maps API.
    
    Args:
        city: City name (e.g., "Dubai")
        business_type: Type of business (e.g., "dental clinic")
        limit: Maximum number of results
        api_key: Outscraper API key
    
    Returns:
        List of business dicts
    """
    if not api_key:
        raise ValueError("Outscraper API key is required. Get one at https://app.outscraper.com")

    url = "https://api.app.outscraper.com/maps/search-v3"
    
    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json"
    }
    
    query = f"{business_type} in {city}"
    
    params = {
        "query": query,
        "limit": limit,
        "language": "en",
        "region": "AE"
    }
    
    print(f"[Finder] Searching for: {query}")
    print(f"[Finder] Limit: {limit} businesses")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            print("[Finder] No results found")
            return []
        
        businesses = []
        for item in data["data"]:
            if not item:
                continue
                
            business = {
                "name": item.get("name", ""),
                "address": item.get("address", ""),
                "phone": item.get("phone", ""),
                "website": item.get("site", ""),
                "rating": item.get("rating", 0),
                "review_count": item.get("reviews", 0),
                "google_url": item.get("google_maps_url", ""),
                "place_id": item.get("place_id", ""),
                "city": city,
                "type": business_type
            }
            
            # Only include businesses with minimum reviews
            if business["review_count"] >= 5:
                businesses.append(business)
        
        print(f"[Finder] Found {len(businesses)} businesses with 5+ reviews")
        return businesses
        
    except requests.exceptions.RequestException as e:
        print(f"[Finder] API error: {e}")
        return []


def get_business_reviews(place_id, api_key, max_reviews=50):
    """
    Get reviews for a specific business using Outscraper API.
    
    Args:
        place_id: Google Place ID
        api_key: Outscraper API key
        max_reviews: Maximum reviews to fetch
    
    Returns:
        List of review dicts
    """
    if not api_key:
        raise ValueError("Outscraper API key is required")

    url = "https://api.app.outscraper.com/maps/reviews-v3"
    
    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json"
    }
    
    params = {
        "id": place_id,
        "limit": max_reviews,
        "language": "en"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            return []
        
        reviews = []
        for item in data["data"]:
            if not item:
                continue
            
            review = {
                "author": item.get("author", ""),
                "rating": item.get("rating", 0),
                "text": item.get("text", ""),
                "date": item.get("date", ""),
                "owner_reply": item.get("reply", ""),
                "has_owner_reply": bool(item.get("reply"))
            }
            reviews.append(review)
        
        return reviews
        
    except requests.exceptions.RequestException as e:
        print(f"[Finder] Reviews API error: {e}")
        return []
