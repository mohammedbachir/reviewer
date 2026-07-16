"""
FindLeads — OSINT Targeting
Searches for business owners and decision makers using Google and website data.
"""

import requests
import re
import time
from urllib.parse import quote_plus
from typing import Optional, List, Dict


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}


class OSINTSearcher:
    """Searches for business owners using OSINT techniques."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def find_owner(self, business_name: str, city: str = "", website: str = "") -> Dict:
        """
        Search for business owner/decision maker.
        
        Returns:
            Dict with owner information
        """
        result = {
            'business_name': business_name,
            'owner_name': '',
            'owner_title': '',
            'personal_email': '',
            'linkedin_url': '',
            'phone': '',
            'confidence': 0,
            'sources': [],
        }
        
        # Strategy 1: Search Google for owner
        google_results = self._search_google(business_name, city)
        if google_results:
            result.update(google_results)
        
        # Strategy 2: Check website for team/about page
        if website:
            website_results = self._check_website_team(website)
            if website_results:
                result.update(website_results)
        
        # Strategy 3: Search LinkedIn
        linkedin_results = self._search_linkedin(business_name, city)
        if linkedin_results:
            result.update(linkedin_results)
        
        # Calculate confidence
        result['confidence'] = self._calculate_confidence(result)
        
        return result
    
    def _search_google(self, business_name: str, city: str) -> Dict:
        """Search Google for owner information."""
        result = {}
        
        # Search queries
        queries = [
            f'"{business_name}" owner CEO founder {city}',
            f'"{business_name}" LinkedIn owner {city}',
            f'"{business_name}" email contact {city}',
        ]
        
        for query in queries:
            try:
                url = f"https://www.google.com/search?q={quote_plus(query)}"
                response = self.session.get(url, timeout=10)
                html = response.text
                
                # Extract owner name from search results
                name_patterns = [
                    r'(?:owner|CEO|founder|president|director|manager)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
                    r'(?:Dr\.|Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-z]+ [A-Z][a-z]+)',
                ]
                
                for pattern in name_patterns:
                    match = re.search(pattern, html)
                    if match:
                        result['owner_name'] = match.group(1).strip()
                        result['sources'].append('google_search')
                        break
                
                # Extract email from search results
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                emails = re.findall(email_pattern, html)
                
                # Filter for personal-looking emails
                for email in emails:
                    if not any(x in email.lower() for x in ['sentry', 'example', 'test', 'noreply', 'no-reply', 'google', 'facebook']):
                        result['personal_email'] = email
                        result['sources'].append('google_email')
                        break
                
                # Extract LinkedIn URL
                linkedin_pattern = r'linkedin\.com/(?:company|in)/[a-zA-Z0-9._-]+'
                linkedin_match = re.search(linkedin_pattern, html)
                if linkedin_match:
                    result['linkedin_url'] = linkedin_match.group(0)
                    result['sources'].append('google_linkedin')
                
                time.sleep(2)  # Rate limit
                
            except Exception:
                continue
        
        return result
    
    def _check_website_team(self, website: str) -> Dict:
        """Check website for team/about page."""
        result = {}
        
        if not website.startswith('http'):
            website = 'https://' + website
        
        # Pages to check
        pages = ['/about', '/about-us', '/team', '/our-team', '/staff', '/doctors']
        
        for page in pages:
            try:
                url = website.rstrip('/') + page
                response = self.session.get(url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    html = response.text
                    
                    # Look for owner/doctor names
                    name_patterns = [
                        r'(?:Dr\.|Doctor)\s+([A-Z][a-z]+ [A-Z][a-z]+)',
                        r'(?:Owner|CEO|Founder|Director)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
                        r'<h[23][^>]*>(?:Dr\.|Doctor)?\s*([A-Z][a-z]+ [A-Z][a-z]+)</h[23]>',
                    ]
                    
                    for pattern in name_patterns:
                        match = re.search(pattern, html)
                        if match:
                            result['owner_name'] = match.group(1).strip()
                            result['sources'].append('website_team')
                            break
                    
                    # Look for emails
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    emails = re.findall(email_pattern, html)
                    
                    for email in emails:
                        if not any(x in email.lower() for x in ['sentry', 'example', 'test', 'noreply', 'no-reply']):
                            if not result.get('personal_email'):
                                result['personal_email'] = email
                                result['sources'].append('website_email')
                            break
                    
                    break
                    
            except Exception:
                continue
        
        return result
    
    def _search_linkedin(self, business_name: str, city: str) -> Dict:
        """Search LinkedIn for owner."""
        result = {}
        
        try:
            query = f'site:linkedin.com "{business_name}" owner OR CEO OR founder {city}'
            url = f"https://www.google.com/search?q={quote_plus(query)}"
            response = self.session.get(url, timeout=10)
            html = response.text
            
            # Extract LinkedIn profile URL
            linkedin_pattern = r'linkedin\.com/in/[a-zA-Z0-9._-]+'
            match = re.search(linkedin_pattern, html)
            if match:
                result['linkedin_url'] = 'https://www.' + match.group(0)
                result['sources'].append('linkedin_search')
            
            # Try to extract name from LinkedIn URL
            if match:
                profile = match.group(0).split('/')[-1]
                name_parts = profile.replace('-', ' ').replace('.', ' ').split()
                if len(name_parts) >= 2:
                    # Capitalize first two parts as likely name
                    name = ' '.join(part.capitalize() for part in name_parts[:2])
                    result['owner_name'] = name
                    result['sources'].append('linkedin_name')
            
            time.sleep(2)
            
        except Exception:
            pass
        
        return result
    
    def _calculate_confidence(self, data: Dict) -> int:
        """Calculate confidence score (0-100)."""
        score = 0
        
        if data.get('owner_name'):
            score += 40
        if data.get('personal_email'):
            score += 30
        if data.get('linkedin_url'):
            score += 20
        if data.get('sources'):
            score += min(len(data['sources']) * 5, 10)
        
        return min(score, 100)
    
    def find_decision_maker(self, business_name: str, city: str = "", website: str = "") -> Dict:
        """
        Find the decision maker for outreach.
        
        Returns:
            Dict with personalized outreach data
        """
        owner_data = self.find_owner(business_name, city, website)
        
        # Generate personalized greeting
        if owner_data.get('owner_name'):
            first_name = owner_data['owner_name'].split()[0]
            owner_data['greeting'] = f"Hi {first_name}"
        else:
            owner_data['greeting'] = "Hi there"
        
        # Generate personalized email subject
        if owner_data.get('owner_name'):
            first_name = owner_data['owner_name'].split()[0]
            owner_data['subject'] = f"Quick question for {first_name}"
        else:
            owner_data['subject'] = f"Quick question for {business_name}"
        
        return owner_data


def find_owner(business_name: str, city: str = "", website: str = "") -> Dict:
    """
    Find business owner using OSINT.
    
    Returns:
        Dict with owner information
    """
    searcher = OSINTSearcher()
    return searcher.find_decision_maker(business_name, city, website)


if __name__ == "__main__":
    # Test
    test_businesses = [
        ("McGill Dental Center", "Dubai", "mmdc.ae"),
        ("Go Dental Clinic", "Dubai", "godentalclinic.com"),
    ]
    
    searcher = OSINTSearcher()
    
    for name, city, website in test_businesses:
        print(f"\n{'='*60}")
        print(f"Searching for owner of: {name}")
        print('='*60)
        
        result = searcher.find_decision_maker(name, city, website)
        
        print(f"Owner: {result.get('owner_name', 'Not found')}")
        print(f"Email: {result.get('personal_email', 'Not found')}")
        print(f"LinkedIn: {result.get('linkedin_url', 'Not found')}")
        print(f"Greeting: {result.get('greeting', 'N/A')}")
        print(f"Subject: {result.get('subject', 'N/A')}")
        print(f"Confidence: {result.get('confidence', 0)}%")
        print(f"Sources: {result.get('sources', [])}")
