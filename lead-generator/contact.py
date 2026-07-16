"""
Lead Generator — Contact Finder
Finds email addresses from business websites.
"""

import re
import requests
from urllib.parse import urljoin, urlparse


# Common contact page paths
CONTACT_PATHS = [
    "/contact",
    "/contact-us",
    "/contactus",
    "/contact.html",
    "/contact-us.html",
    "/about",
    "/about-us",
    "/about.html",
]

# Email regex pattern
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# Emails to skip (generic/unreliable)
SKIP_EMAILS = {
    'noreply@', 'no-reply@', 'donotreply@',
    'support@', 'abuse@', 'spam@',
    'postmaster@', 'webmaster@',
    '.png', '.jpg', '.gif', '.svg',
    'example.com', 'test.com', 'sentry.io',
    'wixpress.com', 'squarespace.com',
}


def find_email_from_website(url, timeout=10):
    """
    Find email address from a business website.
    
    Args:
        url: Website URL
        timeout: Request timeout in seconds
    
    Returns:
        Email address or None
    """
    if not url:
        return None
    
    # Normalize URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    emails = set()
    
    # Try contact pages first
    for path in CONTACT_PATHS:
        try:
            contact_url = urljoin(url, path)
            response = requests.get(contact_url, timeout=timeout, 
                                   headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code == 200:
                found = extract_emails(response.text)
                emails.update(found)
        except:
            continue
    
    # Also try main page
    try:
        response = requests.get(url, timeout=timeout,
                               headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            found = extract_emails(response.text)
            emails.update(found)
    except:
        pass
    
    # Filter and return best email
    return filter_emails(emails)


def extract_emails(text):
    """Extract all emails from HTML text."""
    found = EMAIL_PATTERN.findall(text)
    return set(found)


def filter_emails(emails):
    """
    Filter emails to find the best one.
    
    Priority:
    1. info@, contact@, hello@
    2. Any @domain.com
    """
    if not emails:
        return None
    
    # Clean and filter
    valid_emails = []
    for email in emails:
        email = email.lower().strip()
        
        # Skip if matches skip list
        if any(skip in email for skip in SKIP_EMAILS):
            continue
        
        # Skip if too long (probably not real)
        if len(email) > 50:
            continue
        
        valid_emails.append(email)
    
    if not valid_emails:
        return None
    
    # Priority order
    priority_prefixes = ['info@', 'contact@', 'hello@', 'hi@', 'admin@']
    
    for prefix in priority_prefixes:
        for email in valid_emails:
            if email.startswith(prefix):
                return email
    
    # Return first valid email
    return valid_emails[0] if valid_emails else None


def find_email_from_google(business_name, city, api_key=None):
    """
    Fallback: Find email using Google search via Outscraper.
    
    Args:
        business_name: Business name
        city: City name
        api_key: Outscraper API key (optional)
    
    Returns:
        Email or None
    """
    # This is a placeholder - would need Google Search API
    # For now, return None
    return None


def enrich_with_emails(businesses):
    """
    Find emails for a list of businesses.
    
    Args:
        businesses: List of business dicts
    
    Returns:
        Updated list with emails
    """
    found_count = 0
    
    for biz in businesses:
        if biz.get("email"):
            continue
        
        website = biz.get("website")
        if not website:
            continue
        
        print(f"[Contact] Searching: {biz.get('name', 'Unknown')}...")
        
        email = find_email_from_website(website)
        
        if email:
            biz["email"] = email
            found_count += 1
            print(f"[Contact] Found: {email}")
        else:
            biz["email"] = None
            print(f"[Contact] No email found")
    
    print(f"\n[Contact] Found {found_count} emails out of {len(businesses)} businesses")
    return businesses
