"""
FindLeads — Main Orchestrator
Interactive mode: asks for city and business type.
"""

import argparse
import csv
import os
import sys
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
from analyzer import analyze_response_rate, filter_leads, print_analysis, save_to_csv, save_to_pdf
from contact import enrich_with_emails
from sender import send_outreach_emails


# Common business types for quick selection
BUSINESS_TYPES = [
    "dental clinic",
    "restaurant",
    "cafe",
    "gym",
    "salon",
    "hotel",
    "car repair",
    "real estate",
    "law firm",
    "medical clinic",
    "pharmacy",
    "bakery",
    "gym",
    "yoga studio",
    "dentist",
    "doctor",
    "vet",
    "plumber",
    "electrician",
]


def show_menu():
    """Show interactive menu and get user input."""
    print("\n" + "="*60)
    print("  FINDLEADS")
    print("="*60)
    
    # Get city
    city = input("\n  City (e.g., Dubai, Abu Dhabi, Cairo): ").strip()
    if not city:
        print("  [!] City is required")
        sys.exit(1)
    
    # Get business type
    print("\n  Common business types:")
    for i, bt in enumerate(BUSINESS_TYPES[:10], 1):
        print(f"    {i:2d}. {bt}")
    
    type_input = input("\n  Business type (number or custom text): ").strip()
    
    # Check if user entered a number
    if type_input.isdigit():
        idx = int(type_input) - 1
        if 0 <= idx < len(BUSINESS_TYPES):
            business_type = BUSINESS_TYPES[idx]
        else:
            business_type = type_input
    else:
        business_type = type_input
    
    # Get limit
    limit_input = input("\n  Max businesses to find [20]: ").strip()
    limit = int(limit_input) if limit_input.isdigit() else 20
    
    # Get save path
    default_pdf = f"{business_type.replace(' ', '_')}_{city.replace(' ', '_')}.pdf"
    csv_input = input(f"\n  Save PDF to [F:\\reviewer\\lead-generator\\{default_pdf}]: ").strip()
    save_path = csv_input if csv_input else f"F:\\reviewer\\lead-generator\\{default_pdf}"
    
    # Get send option
    send_input = input("\n  Send emails? (y/n) [n]: ").strip().lower()
    send_emails = send_input in ('y', 'yes')
    
    # Show confirmation
    print("\n" + "-"*60)
    print(f"  City:            {city}")
    print(f"  Business type:   {business_type}")
    print(f"  Max results:     {limit}")
    print(f"  Save CSV to:     {save_path}")
    print(f"  Send emails:     {'Yes' if send_emails else 'No (save only)'}")
    print("-"*60)
    
    confirm = input("\n  Start? (y/n): ").strip().lower()
    if confirm not in ('y', 'yes'):
        print("  Cancelled.")
        sys.exit(0)
    
    return city, business_type, limit, send_emails, save_path


def run_pipeline(city, business_type, limit=50, send_emails=False, save_path=None):
    """Run the full lead generation pipeline."""
    if save_path is None:
        save_path = LEADS_FILE
    
    print("\n" + "="*60)
    print("  PIPELINE STARTED")
    print("="*60)
    print(f"  City: {city}")
    print(f"  Type: {business_type}")
    print(f"  Limit: {limit}")
    print(f"  Save to: {save_path}")
    print("="*60 + "\n")
    
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
        analyzed_biz = analyze_response_rate(biz)
        analyzed.append(analyzed_biz)
    
    print_analysis(analyzed)
    
    # Step 3: Find contact emails
    print("\n[Step 3/4] Finding contact emails...")
    leads = enrich_with_emails(analyzed)
    
    # Filter for qualified leads
    qualified = filter_leads(
        leads,
        max_response_rate=MAX_RESPONSE_RATE,
        min_reviews=MIN_REVIEWS
    )
    
    print(f"[Step 3/4] Found {len(qualified)} qualified leads\n")
    
    # Show results table
    print("\n" + "="*60)
    print("  QUALIFIED LEADS")
    print("="*60)
    for i, lead in enumerate(qualified, 1):
        email_status = "OK" if lead.get('email') else "NO EMAIL"
        print(f"  {i:2d}. {lead['name'][:40]:<40}")
        print(f"      Reviews: {lead['review_count']} | Rating: {lead['rating']} | Email: {email_status}")
    print("="*60)
    
    # Step 4: Send emails (if enabled)
    if send_emails and qualified:
        print("\n[Step 4/4] Sending outreach emails...")
        
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
        print("[Step 4/4] Email sending disabled\n")
    
    # Save results
    save_to_pdf(qualified, save_path, city=city, business_type=business_type)
    
    # Also save CSV as backup
    csv_path = save_path.replace('.pdf', '.csv')
    save_to_csv(qualified, csv_path)
    
    # Summary
    print("\n" + "="*60)
    print("  PIPELINE COMPLETE")
    print("="*60)
    print(f"  Businesses scanned: {len(businesses)}")
    print(f"  Qualified leads:    {len(qualified)}")
    print(f"  Emails found:       {sum(1 for l in qualified if l.get('email'))}")
    if send_emails:
        print(f"  Emails sent:        {sum(1 for l in qualified if l.get('status') == 'sent')}")
    print(f"  Results saved to:   {save_path}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='FindLeads — Business Lead Generator')
    parser.add_argument('--city', help='City to search (interactive if not set)')
    parser.add_argument('--type', help='Business type (interactive if not set)')
    parser.add_argument('--limit', type=int, default=20, help='Max businesses to find')
    parser.add_argument('--send', action='store_true', help='Send outreach emails')
    parser.add_argument('--save', help='CSV file path to save results')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    # Interactive mode if no city/type provided
    if args.city and args.type:
        run_pipeline(
            city=args.city,
            business_type=args.type,
            limit=args.limit,
            send_emails=args.send,
            save_path=args.save
        )
    else:
        city, business_type, limit, send_emails, save_path = show_menu()
        run_pipeline(
            city=city,
            business_type=business_type,
            limit=limit,
            send_emails=send_emails,
            save_path=save_path
        )


if __name__ == '__main__':
    main()
