"""
Shared Data Quality Filters — Enterprise Blacklist, Garbage Detection,
Domain-Level Dedup, Lead Tiering.

Used by: finder.py, app.py, local_daemon.py
"""

import re
from urllib.parse import urlparse

# ══════════════════════════════════════════════════════════════════
# ENTERPRISE / CHAIN BLACKLIST
# ══════════════════════════════════════════════════════════════════

ENTERPRISE_BLACKLIST = [
    "tesla", "kaiser", "pep boys", "goodyear", "mejuri", "james avery",
    "la fitness", "great clips", "banfield", "gerber", "aamco",
    "planet fitness", "orangetheory", "f45", "anytime fitness",
    "planet smoothie", "smoothie king",
    "subway", "chipotle", "chick-fil-a", "wendy", "mcdonald",
    "burger king", "taco bell", "pizza hut", "domino", "papa john",
    "dunkin", "starbucks", "dutch bros", "costa coffee", "panera",
    "crumbl", "insomnia cookies",
    "jiffy lube", "firestone", "midas", "meineke",
    "carl's jr", "jack in the box", "panda express", "wingstop",
    "zaxby", "raisin canes", "dave's hot chicken",
    "sweetgreen", "cava", "otle",
    "trader joe", "whole foods", "sprouts", "aldi", "lidl",
    "sam's club", "costco", "walmart", "target", "best buy",
    "home depot", "lowe", "menards",
    "petco", "petsmart", "cvs", "walgreens", "rite aid",
    "dollar general", "dollar tree", "family dollar", "five below",
    "tj maxx", "ross dress", "marshalls", "burlington",
    "nordstrom", "macys", "dillard", "saks", "neiman marcus",
    "bloomingdale",
    "verizon", "at&t", "t-mobile", "sprint", "comcast", "spectrum",
    "cox", "dishes", "directv", "hulu", "netflix", "spotify",
    "geico", "state farm", "allstate", "progressive", "liberty mutual",
    "nationwide", "usaa", "aflac", "metlife", "prudential",
    "cigna", "aetna", "united health", "humana", "blue cross",
    "hertz", "enterprise rent", "avis", "budget", "u-haul",
    "fedex", "ups store", "usps", "dhl", "staples", "office depot",
    "marriott", "hilton", "hyatt", "westin", "sheraton",
    "doubletree", "hampton inn", "holiday inn", "best western",
    "airbnb", "vrbo", "booking.com", "expedia", "kayak",
    "amazon", "ebay", "etsy", "shopify", "wayfair", "overstock",
    "apple store", "microsoft store", "google store", "samsung",
    "bestbuy", "gamestop", "bath and body", "victoria's secret",
    "sephora", "ulta", "benhof", "nordstrom rack", "saks off fifth",
    "aldi", "lidle", "publix", "kroger", "safeway", "wegmans",
    "heinen", "giant eagle", "harris teeter", "food lion",
    "winn-dixie", "piggly wiggly", "fresh market", "trader joe",
    "aldi", "whole foods", "sprouts", "natural grocers",
]

# ══════════════════════════════════════════════════════════════════
# GARBAGE NAME PATTERNS
# ══════════════════════════════════════════════════════════════════

LOREM_PATTERNS = [
    "vestibulum", "lorem", "ipsum", "dolor", "amet",
    "consectetur", "adipiscing", "sed do eiusmod", "nunc",
    "mauris", "quisque", "aliquet", "pellentesque",
]

GENERIC_SEO_NAMES = [
    "store locator", "contact us", "about us", "home",
    "privacy policy", "terms of service", "sitemap",
    "login", "sign up", "sign in", "faq", "frequently asked",
    "careers", "jobs", "apply now", "our team", "about me",
    "services", "welcome", "click here", "learn more",
    "read more", "view all", "see all", "show more",
]

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
    "general contractor", "plumbing", "electrical", "hvac",
    "landscaping", "cleaning", "painting", "roofing",
]

# ══════════════════════════════════════════════════════════════════
# DOMAIN EXTRACTION
# ══════════════════════════════════════════════════════════════════

_DOMAIN_CACHE = {}


def extract_root_domain(website: str) -> str:
    """Extract root domain from URL: www.site.com/path → site.com"""
    if not website:
        return ""
    website = website.strip().lower()
    if not website.startswith(("http://", "https://")):
        website = "https://" + website
    try:
        parsed = urlparse(website)
        host = parsed.netloc or ""
        if not host:
            return ""
        host = host.split(":")[0]
        host = host.split("@")[-1]
        host = host.rstrip(".")
        parts = host.split(".")
        if len(parts) >= 2:
            root = ".".join(parts[-2:])
        else:
            root = host
        return root
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════
# FILTER: Enterprise Blacklist
# ══════════════════════════════════════════════════════════════════

def is_enterprise(biz_name: str) -> bool:
    """Check if business name matches an enterprise/chain brand."""
    if not biz_name:
        return False
    name_lower = biz_name.lower().strip()
    for brand in ENTERPRISE_BLACKLIST:
        if brand in name_lower or name_lower in brand:
            return True
    return False


# ══════════════════════════════════════════════════════════════════
# FILTER: Garbage / SEO / Placeholder Names
# ══════════════════════════════════════════════════════════════════

def is_garbage_name(name: str) -> str:
    """
    Returns the reason if the name is garbage, empty string if valid.
    """
    if not name:
        return "empty_name"

    name_stripped = name.strip()
    name_lower = name_stripped.lower()

    if len(name_lower) < 4:
        return "too_short"

    if name_lower[0] in ",.-(\"'[":
        return "starts_with_punctuation"

    for pat in LOREM_PATTERNS:
        if pat in name_lower:
            return f"lorem_text:{pat}"

    for pat in GENERIC_SEO_NAMES:
        if name_lower == pat or name_lower.startswith(pat):
            return f"generic_seo:{pat}"

    for pat in PLACEHOLDER_NAMES:
        if name_lower == pat or name_lower.startswith(pat):
            return f"placeholder:{pat}"

    for pat in GENERIC_SECTOR_NAMES:
        if name_lower == pat:
            return f"sector_as_name:{pat}"

    if "|" in name_stripped or " near " in name_lower:
        return "directory_title_format"

    if "yellowpages" in name_lower or "yellow pages" in name_lower:
        return "yellowpages_title"

    if re.match(r'^[\d\s\-\(\)\+\.]+$', name_stripped):
        return "only_numbers"

    return ""


# ══════════════════════════════════════════════════════════════════
# FILTER: Combined Business Quality Check
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
            if brand in domain:
                return f"enterprise_domain:{brand}"

    return ""


# ══════════════════════════════════════════════════════════════════
# LEAD TIERING
# ══════════════════════════════════════════════════════════════════

def calculate_lead_tier(biz: dict) -> str:
    """
    TIER 1 (Premium):   Has email AND phone AND temperature in (HOT, WARM)
    TIER 2 (Standard):  Has email OR phone
    TIER 3 (Unqualified): No email AND no phone
    """
    has_email = bool(biz.get("email"))
    has_phone = bool(biz.get("phone"))
    temp = biz.get("lead_temperature", "COLD")

    if has_email and has_phone and temp in ("HOT", "WARM"):
        return "TIER_1"
    if has_email or has_phone:
        return "TIER_2"
    return "TIER_3"


# ══════════════════════════════════════════════════════════════════
# LEAD SCORE FIX: Fallbacks for missing data
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
