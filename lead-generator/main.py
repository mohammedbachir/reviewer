"""
FindLeads — Main Orchestrator
Interactive mode: asks for city and business type.
"""

import argparse
import csv
import os
import sys
import time
import logging
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
from sender import send_outreach_emails, create_email, send_email
from validator import validate_email
from personalizer import analyze_business
from warmup import WarmupManager, SenderAccount
from osint import find_owner
from mockup import generate_mockup


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
    print(f"  Save PDF to:     {save_path}")
    print(f"  Send emails:     {'Yes' if send_emails else 'No (save only)'}")
    print("-"*60)
    
    confirm = input("\n  Start? (y/n): ").strip().lower()
    if confirm not in ('y', 'yes'):
        print("  Cancelled.")
        sys.exit(0)
    
    return city, business_type, limit, send_emails, save_path


def run_pipeline(city, business_type, limit=50, send_emails=False, save_path=None):
    """Run the full lead generation pipeline with all 5 algorithms."""
    if save_path is None:
        save_path = LEADS_FILE
    
    # Setup logging
    log_file = f"findleads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Pipeline started: {city} / {business_type} / limit={limit}")
    
    print("\n" + "="*60)
    print("  PIPELINE STARTED")
    print("="*60)
    print(f"  City: {city}")
    print(f"  Type: {business_type}")
    print(f"  Limit: {limit}")
    print(f"  Save to: {save_path}")
    print("="*60 + "\n")
    
    # Initialize warmup manager with default account
    default_account = SenderAccount(
        email=GMAIL_USER,
        password=GMAIL_APP_PASSWORD,
        daily_limit=50
    )
    warmup = WarmupManager([default_account])
    
    # Step 1: Find businesses
    print("[Step 1/7] Finding businesses...")
    businesses = find_businesses(
        city=city,
        business_type=business_type,
        limit=limit
    )
    
    if not businesses:
        print("[Main] No businesses found. Exiting.")
        return
    
    print(f"[Step 1/7] Found {len(businesses)} businesses\n")
    
    # Step 2: Analyze review responses
    print("[Step 2/7] Analyzing review responses...")
    analyzed = []
    for i, biz in enumerate(businesses):
        analyzed_biz = analyze_response_rate(biz)
        analyzed.append(analyzed_biz)
    
    print_analysis(analyzed)
    
    # Step 3: Find contact emails
    print("\n[Step 3/7] Finding contact emails...")
    leads = enrich_with_emails(analyzed)
    
    # Filter for qualified leads
    qualified = filter_leads(
        leads,
        max_response_rate=MAX_RESPONSE_RATE,
        min_reviews=MIN_REVIEWS
    )
    
    print(f"[Step 3/7] Found {len(qualified)} qualified leads\n")
    
    # Step 4: Validate emails (Algorithm 1)
    print("\n[Step 4/7] Validating emails...")
    validated_leads = []
    for lead in qualified:
        if lead.get('email'):
            is_valid, status = validate_email(lead['email'])
            lead['email_valid'] = is_valid
            lead['email_status'] = status
            if is_valid:
                validated_leads.append(lead)
                print(f"  [OK] {lead['email']}")
            else:
                print(f"  [FAIL] {lead['email']} - {status}")
        else:
            lead['email_valid'] = False
            lead['email_status'] = 'no_email'
            validated_leads.append(lead)
    
    print(f"\n[Step 4/7] {len(validated_leads)} leads with valid emails\n")
    
    # Step 5: Personalize outreach (Algorithm 2 + Algorithm 4)
    print("[Step 5/7] Personalizing outreach...")
    for lead in validated_leads:
        # OSINT: Find owner
        if lead.get('website'):
            owner_data = find_owner(lead['name'], city, lead['website'])
            lead['owner_name'] = owner_data.get('owner_name', '')
            lead['greeting'] = owner_data.get('greeting', 'Hi there')
            lead['subject'] = owner_data.get('subject', f"Quick question for {lead['name']}")
        
        # Personalizer: Analyze website
        if lead.get('website'):
            website_data = analyze_business(lead['website'])
            lead['pain_points'] = website_data.get('pain_points', [])
            lead['has_whatsapp'] = website_data.get('has_whatsapp', False)
            lead['has_ssl'] = website_data.get('has_ssl', False)
        
        # Generate mockup (Algorithm 5)
        if lead.get('name'):
            mockup_path = generate_mockup(
                lead['name'],
                'review',
                output_dir='mockups',
                review_text="Great service!",
                response_text="Thank you for your kind words!"
            )
            lead['mockup_path'] = mockup_path
    
    print(f"[Step 5/7] Personalized {len(validated_leads)} leads\n")
    
    # Show results table
    print("\n" + "="*60)
    print("  QUALIFIED LEADS")
    print("="*60)
    for i, lead in enumerate(validated_leads, 1):
        email_status = "OK" if lead.get('email_valid') else "NO EMAIL"
        owner = lead.get('owner_name', 'Unknown')
        print(f"  {i:2d}. {lead['name'][:40]:<40}")
        print(f"      Reviews: {lead['review_count']} | Rating: {lead['rating']} | Email: {email_status} | Owner: {owner}")
    print("="*60)
    
    # Step 6: Send emails (if enabled)
    if send_emails and validated_leads:
        print("\n[Step 6/7] Sending outreach emails...")
        
        # Prepare emails with warmup rotation
        emails_to_send = []
        for lead in validated_leads:
            if lead.get('email_valid'):
                # Get next account from rotation
                account = warmup.get_next_account()
                if account is None:
                    print("  [!] All email accounts exhausted daily quota")
                    break
                
                # Personalize email
                greeting = lead.get('greeting', 'Hi there')
                name = lead.get('owner_name', '').split()[0] if lead.get('owner_name') else 'there'
                
                subject = f"Quick question for {lead['name']}"
                body = f"""{greeting},

I noticed {lead['name']} has {lead['review_count']} Google reviews but only {lead.get('response_rate', 0):.0f}% response rate.

We built an AI tool that helps businesses like yours reply to every review in 30 seconds — personalized, professional, and human-like.

Would you like to see how it works?

Best,
{SENDER_NAME}
FindLeads Team"""
                
                emails_to_send.append({
                    'to': lead['email'],
                    'subject': subject,
                    'body': body,
                    'account': account,
                    'lead': lead
                })
        
        # Send with delays
        sent = 0
        for email_data in emails_to_send:
            try:
                logger.info(f"Sending to {email_data['to']} via {email_data['account'].email}")
                
                # Create email message
                msg = create_email(
                    to_email=email_data['to'],
                    business_name=email_data['lead']['name'],
                    unanswered_reviews=email_data['lead'].get('unanswered_reviews', 0),
                    sender_name=SENDER_NAME,
                    subject=email_data['subject'],
                    body_template=email_data['body']
                )
                
                # Send email
                success = send_email(msg, email_data['account'].email, email_data['account'].password)
                
                if success:
                    # Update warmup state
                    email_data['account'].record_send()
                    sent += 1
                    print(f"  [SENT] {email_data['to']} via {email_data['account'].email}")
                    logger.info(f"Sent successfully to {email_data['to']}")
                else:
                    print(f"  [FAILED] {email_data['to']}")
                    logger.error(f"Failed to send to {email_data['to']}")
                
                # Random delay between emails
                import random
                delay = random.uniform(2, 15) * 60  # 2-15 minutes in seconds
                print(f"  Waiting {delay/60:.1f} minutes before next email...")
                logger.info(f"Waiting {delay/60:.1f} minutes before next email...")
                time.sleep(min(delay, 300))  # Cap at 5 minutes for testing
                
            except Exception as e:
                print(f"  [ERROR] {email_data['to']}: {str(e)}")
                logger.error(f"Failed to send to {email_data['to']}: {str(e)}", exc_info=True)
        
        print(f"\n[Step 6/7] Sent {sent} emails\n")
    else:
        print("[Step 6/7] Email sending disabled\n")
    
    # Step 7: Save results
    print("[Step 7/7] Saving results...")
    save_to_pdf(validated_leads, save_path, city=city, business_type=business_type)
    
    # Also save CSV as backup
    csv_path = save_path.replace('.pdf', '.csv')
    save_to_csv(validated_leads, csv_path)
    
    # Summary
    print("\n" + "="*60)
    print("  PIPELINE COMPLETE")
    print("="*60)
    print(f"  Businesses scanned: {len(businesses)}")
    print(f"  Qualified leads:    {len(validated_leads)}")
    print(f"  Emails validated:   {sum(1 for l in validated_leads if l.get('email_valid'))}")
    print(f"  Owners found:       {sum(1 for l in validated_leads if l.get('owner_name'))}")
    print(f"  Mockups generated:  {sum(1 for l in validated_leads if l.get('mockup_path'))}")
    if send_emails:
        print(f"  Emails sent:        {sum(1 for l in validated_leads if l.get('status') == 'sent')}")
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
