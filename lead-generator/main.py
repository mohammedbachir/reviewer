"""
Lead Generator — Main Orchestrator
Runs the full pipeline: Find → Analyze → Contact → Send
"""

import argparse
import csv
import time
from datetime import datetime

from config import (
    GMAIL_USER,
    GMAIL_APP_PASSWORD,
    SENDER_NAME,
    SEARCH_LIMIT,
    MIN_REVIEWS,
    MAX_RESPONSE_RATE,
    EMAIL_DELAY,
    LEADS_FILE,
    SUBJECT,
    BODY_TEMPLATE
)
from finder import find_businesses
from analyzer import analyze_response_rate, filter_leads, print_analysis
from contact import enrich_with_emails
from sender import send_outreach_emails


def save_leads(leads, filename):
    """Save leads to CSV file."""
    if not leads:
        print("[Main] No leads to save")
        return
    
    fieldnames = [
        'name', 'address', 'phone', 'email', 'website',
        'rating', 'review_count', 'response_rate', 'unanswered_reviews',
        'status', 'sent_at', 'city', 'type'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for lead in leads:
            row = {field: lead.get(field, '') for field in fieldnames}
            writer.writerow(row)
    
    print(f"[Main] Saved {len(leads)} leads to {filename}")


def load_leads(filename):
    """Load leads from CSV file."""
    leads = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                leads.append(row)
        print(f"[Main] Loaded {len(leads)} leads from {filename}")
    except FileNotFoundError:
        print(f"[Main] No existing file: {filename}")
    return leads


def run_pipeline(city, business_type, limit=50, send_emails=False, resume=False):
    """
    Run the full lead generation pipeline.
    
    Args:
        city: City to search
        business_type: Type of business
        limit: Maximum businesses to find
        send_emails: Whether to send emails
        resume: Whether to resume from existing leads
    """
    print("\n" + "="*60)
    print("LEAD GENERATOR — Pipeline Started")
    print("="*60)
    print(f"City: {city}")
    print(f"Type: {business_type}")
    print(f"Limit: {limit}")
    print(f"Send emails: {send_emails}")
    print("="*60 + "\n")
    
    # Load existing leads if resuming
    leads = []
    if resume:
        leads = load_leads(LEADS_FILE)
    
    # Step 1: Find businesses
    print("[Step 1/4] Finding businesses...")
    businesses = find_businesses(
        city=city,
        business_type=business_type,
        limit=limit
    )
    
    if not businesses:
        print("[Main] No businesses found. Exiting.")
        return
    
    print(f"[Step 1/4] Found {len(businesses)} businesses\n")
    
    # Step 2: Analyze review responses
    print("[Step 2/4] Analyzing review responses...")
    analyzed = []
    for i, biz in enumerate(businesses):
        print(f"[Step 2/4] Analyzing {i+1}/{len(businesses)}: {biz.get('name', 'Unknown')}")
        analyzed_biz = analyze_response_rate(biz)
        analyzed.append(analyzed_biz)
    
    print_analysis(analyzed)
    
    # Step 3: Find contact emails
    print("[Step 3/4] Finding contact emails...")
    leads = enrich_with_emails(analyzed)
    
    # Filter for qualified leads
    qualified = filter_leads(
        leads,
        max_response_rate=MAX_RESPONSE_RATE,
        min_reviews=MIN_REVIEWS
    )
    
    print(f"[Step 3/4] Found {len(qualified)} qualified leads\n")
    
    # Step 4: Send emails (if enabled)
    if send_emails and qualified:
        print("[Step 4/4] Sending outreach emails...")
        
        config = {
            'gmail_user': GMAIL_USER,
            'gmail_password': GMAIL_APP_PASSWORD,
            'sender_name': SENDER_NAME,
            'subject': SUBJECT,
            'body_template': BODY_TEMPLATE,
            'email_delay': EMAIL_DELAY
        }
        
        sent = send_outreach_emails(qualified, config)
        print(f"[Step 4/4] Sent {sent} emails\n")
    else:
        print("[Step 4/4] Email sending disabled (use --send to enable)\n")
    
    # Save results
    save_leads(qualified, LEADS_FILE)
    
    # Summary
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"Businesses scanned: {len(businesses)}")
    print(f"Analyzed: {len(analyzed)}")
    print(f"Qualified leads: {len(qualified)}")
    print(f"Emails found: {sum(1 for l in qualified if l.get('email'))}")
    if send_emails:
        print(f"Emails sent: {sum(1 for l in qualified if l.get('status') == 'sent')}")
    print(f"Results saved to: {LEADS_FILE}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Lead Generator for Reviewer')
    parser.add_argument('--city', required=True, help='City to search')
    parser.add_argument('--type', required=True, help='Business type (e.g., dental clinic)')
    parser.add_argument('--limit', type=int, default=50, help='Max businesses to find')
    parser.add_argument('--send', action='store_true', help='Send outreach emails')
    parser.add_argument('--resume', action='store_true', help='Resume from existing leads')
    
    args = parser.parse_args()
    
    run_pipeline(
        city=args.city,
        business_type=args.type,
        limit=args.limit,
        send_emails=args.send,
        resume=args.resume
    )


if __name__ == '__main__':
    main()
