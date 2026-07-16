"""
Lead Generator — Configuration
"""

# ─── Settings ───────────────────────────────────────────────────────────────
SEARCH_LIMIT = 50        # Max businesses per search
MIN_REVIEWS = 5          # Minimum reviews to consider
MAX_RESPONSE_RATE = 30   # Target businesses with response rate below this %
EMAIL_DELAY = 30         # Seconds between emails (avoid spam)
LEADS_FILE = "leads.csv"

# ─── Gmail SMTP ─────────────────────────────────────────────────────────────
GMAIL_USER = ""          # your.email@gmail.com
GMAIL_APP_PASSWORD = ""  # App Password from Google Account settings
SENDER_NAME = ""         # Your name

# ─── Email Template ─────────────────────────────────────────────────────────
SUBJECT = "Your customers are waiting for a reply"

BODY_TEMPLATE = """
Hi {business_name},

I noticed you have {unanswered_reviews} unanswered reviews on Google Maps.

Customers often decide based on reviews — and no reply can look like you don't care.

I built a free tool that writes human-like replies to Google reviews in 10 seconds. No robot talk, no corporate speak.

Worth checking out: https://reviewer-lovat.vercel.app/landing.html

— {sender_name}
"""
