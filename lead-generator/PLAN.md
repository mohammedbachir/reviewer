# FindLeads — Build Plan

## Overview
Python script that finds businesses not replying to their Google Maps reviews, collects their emails, and sends outreach emails explaining the Reviewer tool.

## Algorithms (ALL COMPLETED ✅)

### Algorithm 1: Email Validation & Catch-All Bypass (validator.py)
- MX record validation via Google DNS (8.8.8.8)
- Disposable email detection (30+ domains)
- Role-based email detection (info@, contact@, support@)
- File extension detection (.png, .jpg, etc.)
- SMTP VRFY support for catch-all detection

### Algorithm 2: Hyper-Personalization (personalizer.py)
- WhatsApp button detection
- SSL certificate status
- Phone number detection
- Email detection
- Social media link detection
- Contact form detection
- Blog presence detection
- Page speed estimation
- Technology detection (WordPress, Shopify, React, etc.)
- Pain point identification

### Algorithm 3: Email Warm-up & Load Balancing (warmup.py)
- Multi-account rotation
- Daily quota management
- Round-robin distribution
- Human mimicry delays (2-15 minutes)
- State persistence

### Algorithm 4: OSINT Targeting (osint.py)
- Google search for owner information
- Website team/about page scraping
- LinkedIn profile discovery
- Owner name extraction
- Personalized greeting generation

### Algorithm 5: Trojan Horse Asset Generator (mockup.py)
- Review response mockups
- Website improvement mockups
- Statistics mockups
- Professional PNG images

## Pipeline Integration

```
Step 1: Find businesses (finder.py)
    ↓
Step 2: Analyze reviews (analyzer.py)
    ↓
Step 3: Find emails (contact.py)
    ↓
Step 4: Validate emails (validator.py)
    ↓
Step 5: Personalize outreach (personalizer.py + osint.py)
    ↓
Step 6: Send emails with warmup (sender.py + warmup.py)
    ↓
Step 7: Save results (PDF + CSV)
```

## File Structure

```
lead-generator/
├── config.py              # Gmail credentials, settings
├── finder.py              # Playwright-based Google Maps scraper
├── analyzer.py            # Review response rate analysis
├── contact.py             # Email finder from websites
├── sender.py              # Gmail SMTP sender
├── validator.py           # Email validation (Algorithm 1)
├── personalizer.py        # Website analysis (Algorithm 2)
├── warmup.py              # Email warm-up (Algorithm 3)
├── osint.py               # OSINT targeting (Algorithm 4)
├── mockup.py              # Mockup generator (Algorithm 5)
├── main.py                # Pipeline orchestrator
├── PLAN.md                # This file
├── requirements.txt       # Dependencies
├── FindLeads.bat          # One-click launcher
└── mockups/               # Generated mockups
```

## Usage

### Interactive Mode
```bash
python main.py
```

### Command Line Mode
```bash
python main.py --city "Dubai" --type "dental clinic" --limit 20 --send
```

### One-Click Launcher
```bash
FindLeads.bat
```

## Cost

| Item | Cost |
|---|---|
| Playwright | Free |
| Gmail SMTP | Free |
| Python | Free |
| Hosting | Local (Free) |
| **Total** | **$0/month** |

## Test Results

### Algorithm 1: Email Validation
- Valid emails correctly identified: ✅
- Invalid emails correctly rejected: ✅
- MX record check: ✅
- SMTP verification: ✅

### Algorithm 2: Hyper-Personalization
- WhatsApp detection: ✅
- SSL status: ✅
- Pain point identification: ✅
- Technology detection: ✅

### Algorithm 3: Warm-up
- Round-robin distribution: ✅
- Daily quotas: ✅
- State persistence: ✅
- Human mimicry delays: ✅

### Algorithm 4: OSINT
- Owner name extraction: ✅
- Website team page scraping: ✅
- LinkedIn discovery: ✅

### Algorithm 5: Mockups
- Review response mockup: ✅
- Website improvement mockup: ✅
- Statistics mockup: ✅

### Pipeline Integration
- End-to-end test: ✅
- Email validation: ✅
- Personalization: ✅
- PDF export: ✅

## Next Steps

1. Test with real email sending
2. Add more business types
3. Optimize scraping speed
4. Add email tracking
5. Build web dashboard
