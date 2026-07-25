"""
Shared Data Quality Filters — Enterprise Blacklist, Garbage Detection,
Domain-Level Dedup, Lead Tiering, Phone/Email Validation.

Used by: finder.py, app.py, local_daemon.py
"""

import re
from urllib.parse import urlparse
from typing import Optional

# ══════════════════════════════════════════════════════════════════
# ENTERPRISE / CHAIN BLACKLIST (word-boundary aware)
# ══════════════════════════════════════════════════════════════════

ENTERPRISE_BLACKLIST = [
    "Tesla", "Kaiser Permanente", "Pep Boys", "Goodyear", "Mejuri",
    "James Avery", "LA Fitness", "Great Clips", "Banfield", "Gerber",
    "Aamco", "24 Hour Fitness", "Planet Fitness", "Anytime Fitness",
    "Orangetheory", "F45", "Gold's Gym",
    "Subway", "Chipotle", "Chick-fil-A", "Wendy's", "McDonald",
    "Burger King", "Taco Bell", "Pizza Hut", "Domino", "Papa John",
    "Dunkin", "Starbucks", "Dutch Bros", "Panera", "Crumbl",
    "Jiffy Lube", "Firestone", "Midas", "Meineke",
    "Carl's Jr", "Jack in the Box", "Panda Express", "Wingstop",
    "Trader Joe", "Whole Foods", "Sprouts", "Aldi", "Lidl",
    "Sam's Club", "Costco", "Walmart", "Target", "Best Buy",
    "Home Depot", "Lowe", "Menards",
    "Petco", "PetSmart", "CVS", "Walgreens", "Rite Aid",
    "Dollar General", "Dollar Tree", "Family Dollar", "Five Below",
    "TJ Maxx", "Ross Dress", "Marshalls", "Burlington",
    "Nordstrom", "Macy's", "Dillard", "Saks", "Neiman Marcus",
    "Verizon", "AT&T", "T-Mobile", "Sprint", "Comcast", "Spectrum",
    "Geico", "State Farm", "Allstate", "Progressive", "Liberty Mutual",
    "Hertz", "Enterprise Rent", "Avis", "Budget", "U-Haul",
    "FedEx", "UPS Store", "USPS", "DHL", "Staples", "Office Depot",
    "Marriott", "Hilton", "Hyatt", "Westin", "Sheraton",
    "Hampton Inn", "Holiday Inn", "Best Western",
    "Airbnb", "VRBO", "Booking.com", "Expedia",
    "Amazon", "eBay", "Etsy", "Shopify", "Wayfair",
    "Apple Store", "Microsoft Store", "Samsung", "GameStop",
    "Sephora", "Ulta", "Nordstrom Rack",
    "Publix", "Kroger", "Safeway", "Wegmans",
    "Harris Teeter", "Food Lion", "Winn-Dixie",
    "Facebook", "Google", "Instagram", "Twitter", "LinkedIn",
    "Netflix", "Spotify", "Hulu", "Disney+", "HBO",
    "Uber", "Lyft", "DoorDash", "Grubhub", "Uber Eats",
    "Ford", "Chevrolet", "Toyota", "Honda", "BMW", "Mercedes",
    "Nissan", "Hyundai", "Kia", "Volkswagen", "Audi", "Porsche",
    "Lexus", "Acura", "Infiniti", "Buick", "GMC", "Cadillac",
    "Chrysler", "Dodge", "Jeep", "Ram", "Subaru", "Mazda",
    "Volvo", "Jaguar", "Land Rover", "Mini", "Fiat",
    "Pfizer", "Moderna", "Johnson & Johnson", "Merck", "Abbvie",
    "Coca-Cola", "PepsiCo", "Nestle", "Unilever", "Procter & Gamble",
    "Boeing", "Airbus", "Lockheed Martin", "Raytheon",
    "Shell", "ExxonMobil", "Chevron", "BP",
]

# Pre-compile word-boundary patterns
_BLACKLIST_PATTERNS = [
    re.compile(r'\b' + re.escape(brand.strip()) + r'\b', re.IGNORECASE)
    for brand in ENTERPRISE_BLACKLIST
]


def is_enterprise(biz_name: str) -> bool:
    """Check if business name matches an enterprise/chain brand (word-boundary)."""
    if not biz_name:
        return False
    for pattern in _BLACKLIST_PATTERNS:
        if pattern.search(biz_name):
            return True
    return False


# ══════════════════════════════════════════════════════════════════
# GARBAGE / SEO / PLACEHOLDER NAME DETECTION
# ══════════════════════════════════════════════════════════════════

LATIN_PLACEHOLDER_WORDS = [
    "vestibulum", "lorem", "ipsum", "dolor", "amet",
    "consectetur", "adipiscing", "sed do eiusmod", "nunc",
    "mauris", "quisque", "aliquet", "pellentesque",
]

_GENERIC_SEO_PATTERNS = [
    re.compile(r'^\s*(home|contact\s*us?|about\s*us?|store\s*locator)\s*$', re.IGNORECASE),
    re.compile(r'\b(dui|criminal|injury)\s+lawyer\b.*\b(near\s*me|24/?7)\b', re.IGNORECASE),
    re.compile(r'^\s*untitled\s*(page|document)?\s*$', re.IGNORECASE),
    re.compile(r'^\s*(test|demo|sample)\s*(business|company|listing)?\s*$', re.IGNORECASE),
]

_LATIN_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in LATIN_PLACEHOLDER_WORDS) + r')\b',
    re.IGNORECASE
)

PLACEHOLDER_NAMES = [
    "test", "example", "sample", "untitled", "unnamed",
    "new business", "business name", "company name",
    "your business", "my business", "insert name",
    "placeholder", "temporary", "demo",
]

GENERIC_SECTOR_NAMES = [
    "dui lawyer", "personal injury lawyer", "car accident lawyer",
    "criminal defense lawyer", "divorce lawyer", "bankruptcy lawyer",
    "immigration lawyer", "tax lawyer", "real estate lawyer",
    "medical malpractice", "wrongful death", "workers compensation",
    "slip and fall", "truck accident", "dog bite lawyer",
]


def is_garbage_name(name: str) -> str:
    """Returns the reason if the name is garbage, empty string if valid."""
    if not name:
        return "empty_name"

    name_stripped = name.strip()
    name_lower = name_stripped.lower()

    if len(name_lower) < 4:
        return "too_short"

    if len(name_stripped) > 60:
        return "seo_spam_long_name"

    if re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', name_stripped):
        return "seo_spam_phone_in_name"

    if name_stripped.count(',') >= 3:
        return "seo_spam_too_many_commas"

    if _LATIN_PATTERN.search(name_stripped):
        return "latin_placeholder_text"

    for pattern in _GENERIC_SEO_PATTERNS:
        if pattern.search(name_stripped):
            return f"generic_seo_pattern"

    for pat in PLACEHOLDER_NAMES:
        if name_lower == pat or name_lower.startswith(pat):
            return f"placeholder:{pat}"

    for pat in GENERIC_SECTOR_NAMES:
        if name_lower == pat:
            return f"sector_as_name:{pat}"

    if re.match(r'^[\d\s\-\(\)\+\.]+$', name_stripped):
        return "only_numbers"

    return ""


# ══════════════════════════════════════════════════════════════════
# PHONE NORMALIZATION (E.164)
# ══════════════════════════════════════════════════════════════════

def normalize_phone(raw_phone: Optional[str]) -> Optional[str]:
    """
    Strip all formatting, validate US/CA length, return +1XXXXXXXXXX or None.
    Rejects obviously fake numbers (all same digit).
    """
    if not raw_phone:
        return None

    digits = re.sub(r'\D', '', str(raw_phone))

    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    elif len(digits) == 10:
        pass
    else:
        return None

    if len(set(digits)) == 1:
        return None

    return f"+1{digits}"


# ══════════════════════════════════════════════════════════════════
# EMAIL VALIDATION
# ══════════════════════════════════════════════════════════════════

_EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

_JUNK_EMAIL_VALUES = {
    "n/a", "none", "null", "-", "example@example.com",
    "test@test.com", "email", "info@", "contact@",
    "no email", "noemail", "not available",
}


def is_valid_email(email: Optional[str]) -> bool:
    """Validates format AND filters known junk/placeholder values."""
    if not email or not email.strip():
        return False
    email = email.strip().lower()
    if email in _JUNK_EMAIL_VALUES:
        return False
    return bool(_EMAIL_PATTERN.match(email))


# ══════════════════════════════════════════════════════════════════
# REVIEW COUNT VALIDATION
# ══════════════════════════════════════════════════════════════════

MAX_REALISTIC_REVIEWS = 50000


def safe_review_count(count) -> int:
    """Cap impossible review counts. Yelp's most-reviewed has ~30K."""
    if count is None:
        return 0
    try:
        c = int(count)
    except (ValueError, TypeError):
        return 0
    if c < 0:
        return 0
    if c > MAX_REALISTIC_REVIEWS:
        return 0
    return c


# ══════════════════════════════════════════════════════════════════
# DOMAIN NORMALIZATION (for dedup)
# ══════════════════════════════════════════════════════════════════

def normalize_domain(website: Optional[str]) -> Optional[str]:
    """
    Normalize URL to bare root domain: www.site.com/path → site.com
    """
    if not website or not website.strip():
        return None

    website = website.strip()
    if not re.match(r'^https?://', website, re.IGNORECASE):
        website = 'https://' + website

    try:
        parsed = urlparse(website)
        domain = parsed.netloc.lower()
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.split(':')[0]
        return domain if domain else None
    except Exception:
        return None


def extract_root_domain(website: str) -> str:
    """Extract root domain: www.blog.site.com → site.com"""
    full = normalize_domain(website)
    if not full:
        return ""
    parts = full.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return full


# ══════════════════════════════════════════════════════════════════
# MASTER FILTER
# ══════════════════════════════════════════════════════════════════

def should_skip_business(biz: dict) -> str:
    """
    Master filter. Returns skip reason string if business should be
    rejected, empty string if it passes all checks.
    """
    name = biz.get("name", "")
    website = biz.get("website", "")

    if is_enterprise(name):
        return "enterprise_brand"

    garbage_reason = is_garbage_name(name)
    if garbage_reason:
        return f"garbage_name:{garbage_reason}"

    domain = extract_root_domain(website) if website else ""
    if domain:
        for brand in ENTERPRISE_BLACKLIST:
            if brand.lower() in domain:
                return f"enterprise_domain:{brand}"

    return ""


# ══════════════════════════════════════════════════════════════════
# LEAD TIERING (with validation)
# ══════════════════════════════════════════════════════════════════

def calculate_lead_tier(biz: dict) -> str:
    """
    TIER 1 (Premium):   valid email AND valid phone AND (HOT or WARM)
    TIER 2 (Standard):  valid email OR valid phone
    TIER 3 (Unqualified): neither
    """
    email_ok = is_valid_email(biz.get("email"))
    phone_ok = bool(normalize_phone(biz.get("phone")))
    temp = biz.get("lead_temperature", "COLD")

    if email_ok and phone_ok and temp in ("HOT", "WARM"):
        return "TIER_1"
    if email_ok or phone_ok:
        return "TIER_2"
    return "TIER_3"


# ══════════════════════════════════════════════════════════════════
# SSL / HEALTH FALLBACKS
# ══════════════════════════════════════════════════════════════════

def safe_ssl_grade(grade) -> str:
    """Normalize SSL grade: empty/None → 'C' (unknown, not worst)."""
    if not grade or grade not in ("A", "B", "C", "D", "F"):
        return "C"
    return grade


def safe_health_score(score) -> int:
    """Normalize health score: None/0 → 50 (neutral default)."""
    if score is None or score == 0:
        return 50
    return int(score)
