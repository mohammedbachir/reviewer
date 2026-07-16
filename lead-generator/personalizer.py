"""
FindLeads — Hyper-Personalization
Scrapes business websites to extract data for personalized outreach.
"""

import requests
import re
import time
from urllib.parse import urljoin, urlparse
from typing import Optional


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


class WebsiteAnalyzer:
    """Analyzes business websites for hyper-personalization."""
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def analyze(self, website_url: str) -> dict:
        """
        Analyze a business website.
        
        Returns:
            Dict with website analysis data
        """
        result = {
            'url': website_url,
            'has_whatsapp': False,
            'whatsapp_link': '',
            'services': [],
            'has_contact_form': False,
            'has_phone': False,
            'phone_numbers': [],
            'has_email': False,
            'emails_found': [],
            'has_social_media': False,
            'social_links': {},
            'has_blog': False,
            'is_ssl': False,
            'page_speed_estimate': 'unknown',
            'technologies': [],
            'pain_points': [],
        }
        
        try:
            # Normalize URL
            if not website_url.startswith('http'):
                website_url = 'https://' + website_url
            
            # Check SSL
            result['is_ssl'] = website_url.startswith('https')
            
            # Fetch homepage
            response = self.session.get(website_url, timeout=self.timeout, allow_redirects=True)
            html = response.text
            final_url = response.url
            
            # Update SSL based on final URL
            result['is_ssl'] = final_url.startswith('https')
            
            # Analyze HTML
            result.update(self._analyze_html(html, final_url))
            
            # Check contact page
            contact_data = self._check_contact_page(final_url)
            result.update(contact_data)
            
            # Estimate page speed
            result['page_speed_estimate'] = self._estimate_speed(response)
            
            # Detect technologies
            result['technologies'] = self._detect_technologies(html)
            
            # Identify pain points
            result['pain_points'] = self._identify_pain_points(result)
            
        except requests.exceptions.Timeout:
            result['pain_points'].append('Website is slow or unreachable')
        except requests.exceptions.SSLError:
            result['is_ssl'] = False
            result['pain_points'].append('No SSL certificate')
        except Exception as e:
            result['pain_points'].append(f'Website analysis failed: {str(e)[:50]}')
        
        return result
    
    def _analyze_html(self, html: str, base_url: str) -> dict:
        """Analyze HTML content."""
        data = {}
        
        # WhatsApp detection
        whatsapp_patterns = [
            r'wa\.me/([0-9]+)',
            r'api\.whatsapp\.com/send\?phone=([0-9]+)',
            r'whatsapp://send\?phone=([0-9]+)',
            r'chat\.whatsapp\.com/',
        ]
        
        for pattern in whatsapp_patterns:
            match = re.search(pattern, html)
            if match:
                data['has_whatsapp'] = True
                data['whatsapp_link'] = match.group(0)
                break
        
        # Phone numbers
        phone_patterns = [
            r'(?:\+?[0-9]{1,3}[-.\s]?)?\(?[0-9]{3,5}\)?[-.\s]?[0-9]{3,5}[-.\s]?[0-9]{3,5}',
            r'tel:([+\d\s\-\(\)]+)',
        ]
        
        phones = set()
        for pattern in phone_patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                phone = match.strip()
                if len(phone) >= 8:
                    phones.add(phone)
        
        if phones:
            data['has_phone'] = True
            data['phone_numbers'] = list(phones)[:3]
        
        # Email detection
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = set(re.findall(email_pattern, html))
        # Filter out common non-personal emails
        filtered_emails = [e for e in emails if not any(x in e.lower() for x in ['sentry', 'example', 'test', 'noreply', 'no-reply'])]
        
        if filtered_emails:
            data['has_email'] = True
            data['emails_found'] = list(filtered_emails)[:3]
        
        # Social media links
        social_patterns = {
            'facebook': r'facebook\.com/[a-zA-Z0-9._-]+',
            'instagram': r'instagram\.com/[a-zA-Z0-9._-]+',
            'twitter': r'twitter\.com/[a-zA-Z0-9._-]+',
            'linkedin': r'linkedin\.com/(?:company|in)/[a-zA-Z0-9._-]+',
            'youtube': r'youtube\.com/(?:c/|channel/|@)[a-zA-Z0-9._-]+',
            'tiktok': r'tiktok\.com/@[a-zA-Z0-9._-]+',
        }
        
        social_links = {}
        for platform, pattern in social_patterns.items():
            match = re.search(pattern, html)
            if match:
                social_links[platform] = match.group(0)
        
        if social_links:
            data['has_social_media'] = True
            data['social_links'] = social_links
        
        # Services detection
        service_keywords = [
            'services', 'our services', 'what we do', 'what we offer',
            'treatments', 'procedures', 'solutions', 'products',
            'dental', 'clinic', 'medical', 'health', 'care',
            'consultation', 'checkup', 'cleaning', 'whitening',
        ]
        
        services = []
        for keyword in service_keywords:
            if keyword.lower() in html.lower():
                services.append(keyword)
        
        data['services'] = services[:5]
        
        # Contact form detection
        form_patterns = [
            r'<form[^>]*action=["\']?[^"\']*(?:contact|submit|send|inquiry)',
            r'<form[^>]*class=["\']?[^"\']*(?:contact|form)',
            r'id=["\']?contact[-_]?form',
        ]
        
        for pattern in form_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                data['has_contact_form'] = True
                break
        
        # Blog detection
        if re.search(r'/blog/|/news/|/articles/|/posts/', html, re.IGNORECASE):
            data['has_blog'] = True
        
        return data
    
    def _check_contact_page(self, base_url: str) -> dict:
        """Check contact page for additional info."""
        data = {}
        
        contact_paths = ['/contact', '/contact-us', '/contactus', '/about', '/about-us']
        
        for path in contact_paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    html = response.text
                    
                    # Check for WhatsApp on contact page
                    if 'whatsapp' in html.lower() or 'wa.me' in html:
                        data['has_whatsapp'] = True
                    
                    # Check for phone on contact page
                    phone_match = re.search(r'(?:\+?[0-9]{1,3}[-.\s]?)?\(?[0-9]{3,5}\)?[-.\s]?[0-9]{3,5}[-.\s]?[0-9]{3,5}', html)
                    if phone_match:
                        data['has_phone'] = True
                        if 'phone_numbers' not in data:
                            data['phone_numbers'] = []
                        data['phone_numbers'].append(phone_match.group(0))
                    
                    break
                    
            except Exception:
                continue
        
        return data
    
    def _estimate_speed(self, response) -> str:
        """Estimate page speed based on response time."""
        response_time = response.elapsed.total_seconds()
        
        if response_time < 1:
            return 'fast'
        elif response_time < 3:
            return 'medium'
        else:
            return 'slow'
    
    def _detect_technologies(self, html: str) -> list:
        """Detect technologies used on the website."""
        technologies = []
        
        tech_patterns = {
            'WordPress': r'wp-content|wordpress',
            'Shopify': r'shopify|cdn\.shopify',
            'WooCommerce': r'woocommerce',
            'React': r'react|ReactDOM',
            'Vue.js': r'vue\.js|vue\.min\.js',
            'Angular': r'angular|ng-app',
            'jQuery': r'jquery',
            'Bootstrap': r'bootstrap',
            'Tailwind CSS': r'tailwindcss',
            'Google Analytics': r'google-analytics|gtag|ga\(',
            'Facebook Pixel': r'fbq\(|facebook.*pixel',
            'Stripe': r'stripe\.com',
            'PayPal': r'paypal\.com',
            'Intercom': r'intercom',
            'Zendesk': r'zendesk',
            'HubSpot': r'hubspot',
            'Mailchimp': r'mailchimp',
            'Cloudflare': r'cloudflare',
        }
        
        for tech, pattern in tech_patterns.items():
            if re.search(pattern, html, re.IGNORECASE):
                technologies.append(tech)
        
        return technologies
    
    def _identify_pain_points(self, data: dict) -> list:
        """Identify pain points from analysis."""
        pain_points = []
        
        if not data.get('has_whatsapp'):
            pain_points.append('No WhatsApp button (80% of customers prefer WhatsApp)')
        
        if not data.get('has_phone'):
            pain_points.append('No visible phone number')
        
        if not data.get('has_contact_form'):
            pain_points.append('No contact form')
        
        if not data.get('is_ssl'):
            pain_points.append('No SSL certificate (browser shows "Not Secure")')
        
        if data.get('page_speed_estimate') == 'slow':
            pain_points.append('Slow website loading speed')
        
        if not data.get('has_social_media'):
            pain_points.append('No social media presence')
        
        if not data.get('has_blog'):
            pain_points.append('No blog (bad for SEO)')
        
        if data.get('page_speed_estimate') == 'slow' and not data.get('has_whatsapp'):
            pain_points.append('Customers leaving due to slow speed + no instant contact')
        
        return pain_points


def analyze_business(website_url: str) -> dict:
    """
    Analyze a business website for hyper-personalization.
    
    Returns:
        Dict with analysis data
    """
    analyzer = WebsiteAnalyzer()
    return analyzer.analyze(website_url)


def generate_personalized_insight(analysis: dict, business_name: str) -> str:
    """
    Generate personalized insight from website analysis.
    
    Returns:
        String with personalized observations
    """
    insights = []
    
    # WhatsApp
    if not analysis.get('has_whatsapp'):
        insights.append(f"I noticed {business_name} doesn't have a WhatsApp button — 80% of customers prefer instant messaging")
    
    # SSL
    if not analysis.get('is_ssl'):
        insights.append("Your website shows 'Not Secure' in browsers — this scares away customers")
    
    # Speed
    if analysis.get('page_speed_estimate') == 'slow':
        insights.append("Your website takes too long to load — 53% of visitors leave after 3 seconds")
    
    # Social media
    if not analysis.get('has_social_media'):
        insights.append("No social media links found — you're missing free traffic")
    
    # Contact form
    if not analysis.get('has_contact_form'):
        insights.append("No contact form makes it hard for customers to reach you")
    
    # Phone
    if not analysis.get('has_phone'):
        insights.append("No visible phone number — customers can't call you directly")
    
    # Technologies (for tech-specific insights)
    techs = analysis.get('technologies', [])
    if 'Google Analytics' not in techs:
        insights.append("No Google Analytics — you can't track your visitors")
    
    if 'Facebook Pixel' not in techs:
        insights.append("No Facebook Pixel — you can't retarget visitors")
    
    return insights


if __name__ == "__main__":
    # Test
    test_urls = [
        "mmdc.ae",
        "godentalclinic.com",
    ]
    
    analyzer = WebsiteAnalyzer()
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Analyzing: {url}")
        print('='*60)
        
        result = analyzer.analyze(url)
        
        print(f"SSL: {result['is_ssl']}")
        print(f"WhatsApp: {result['has_whatsapp']}")
        print(f"Phone: {result['has_phone']}")
        print(f"Email: {result['has_email']}")
        print(f"Social Media: {result['has_social_media']}")
        print(f"Contact Form: {result['has_contact_form']}")
        print(f"Blog: {result['has_blog']}")
        print(f"Speed: {result['page_speed_estimate']}")
        print(f"Technologies: {result['technologies']}")
        print(f"Pain Points: {result['pain_points']}")
        
        insights = generate_personalized_insight(result, url)
        if insights:
            print(f"\nPersonalized Insights:")
            for insight in insights:
                print(f"  - {insight}")
