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
from sender import send_outreach_emails, create_email, send_email, send_bulk_sync
from validator import validate_email
from personalizer import analyze_business
from warmup import WarmupManager, SenderAccount
from osint import find_owner
from mockup import generate_mockup
from progress import FindLeadsProgress, console


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
    console.print()
    console.print("[bold cyan]════════════════════════════════════════════════════════════[/]")
    console.print("[bold white]                        FINDLEADS[/]")
    console.print("[bold cyan]════════════════════════════════════════════════════════════[/]")
    
    # Get city
    city = input("\n  City (e.g., Dubai, Abu Dhabi, Cairo): ").strip()
    if not city:
        console.print("  [red]City is required[/]")
        sys.exit(1)
    
    # Get business type
    console.print("\n  [dim]Common business types:[/]")
    for i, bt in enumerate(BUSINESS_TYPES[:10], 1):
        console.print(f"    [cyan]{i:2d}.[/] {bt}")
    
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
    console.print()
    console.print("[dim]────────────────────────────────────────────────────────────[/]")
    console.print(f"  [cyan]City:[/]            {city}")
    console.print(f"  [cyan]Business type:[/]   {business_type}")
    console.print(f"  [cyan]Max results:[/]     {limit}")
    console.print(f"  [cyan]Save PDF to:[/]     {save_path}")
    console.print(f"  [cyan]Send emails:[/]     {'[green]Yes[/]' if send_emails else '[yellow]No (save only)[/]'}")
    console.print("[dim]────────────────────────────────────────────────────────────[/]")
    
    confirm = input("\n  Start? (y/n): ").strip().lower()
    if confirm not in ('y', 'yes'):
        console.print("  [yellow]Cancelled.[/]")
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
    
    # Initialize warmup manager with default account
    default_account = SenderAccount(
        email=GMAIL_USER,
        password=GMAIL_APP_PASSWORD,
        daily_limit=50
    )
    warmup = WarmupManager([default_account])
    
    # Start progress display
    with FindLeadsProgress() as progress:
        progress.start_pipeline(city, business_type, limit)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Find businesses
        # ═══════════════════════════════════════════════════════════════
        progress.start_step(1, "Finding businesses", total_items=limit)
        
        # We'll update progress as businesses are found
        businesses = find_businesses(
            city=city,
            business_type=business_type,
            limit=limit
        )
        
        if not businesses:
            progress.print_error("No businesses found. Exiting.")
            return
        
        progress.set_step_progress(len(businesses))
        progress.finish_step()
        progress.print_success(f"Found {len(businesses)} businesses")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Analyze review responses
        # ═══════════════════════════════════════════════════════════════
        progress.start_step(2, "Analyzing reviews", total_items=len(businesses))
        
        analyzed = []
        for i, biz in enumerate(businesses):
            analyzed_biz = analyze_response_rate(biz)
            analyzed.append(analyzed_biz)
            progress.update_step(1)
        
        progress.finish_step()
        
        # Count priorities
        high = sum(1 for b in analyzed if b.get('priority') == 'high')
        progress.print_success(f"Analyzed {len(analyzed)} businesses — {high} high priority")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Find contact emails
        # ═══════════════════════════════════════════════════════════════
        progress.start_step(3, "Finding emails", total_items=len(analyzed))
        
        leads = enrich_with_emails(analyzed)
        
        # Filter for qualified leads
        qualified = filter_leads(
            leads,
            max_response_rate=MAX_RESPONSE_RATE,
            min_reviews=MIN_REVIEWS
        )
        
        progress.set_step_progress(len(analyzed))
        progress.finish_step()
        
        emails_found = sum(1 for l in qualified if l.get('email'))
        progress.print_success(f"Found {len(qualified)} qualified leads ({emails_found} with emails)")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Validate emails
        # ═══════════════════════════════════════════════════════════════
        progress.start_step(4, "Validating emails", total_items=len(qualified))
        
        validated_leads = []
        for lead in qualified:
            if lead.get('email'):
                is_valid, status = validate_email(lead['email'])
                lead['email_valid'] = is_valid
                lead['email_status'] = status
                if is_valid:
                    validated_leads.append(lead)
                    progress.print_success(f"{lead['email']}")
                else:
                    progress.print_error(f"{lead['email']} — {status}")
            else:
                lead['email_valid'] = False
                lead['email_status'] = 'no_email'
                validated_leads.append(lead)
            progress.update_step(1)
        
        progress.finish_step()
        valid_count = sum(1 for l in validated_leads if l.get('email_valid'))
        progress.print_success(f"{valid_count} valid emails out of {len(qualified)}")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Personalize outreach (THE SLOW ONE)
        # ═══════════════════════════════════════════════════════════════
        progress.start_step(5, "Personalizing outreach", total_items=len(validated_leads) * 3)
        
        for i, lead in enumerate(validated_leads):
            # OSINT: Find owner
            if lead.get('website'):
                progress.print_info(f"[{i+1}/{len(validated_leads)}] Searching for owner: {lead['name'][:30]}...")
                owner_data = find_owner(lead['name'], city, lead['website'])
                lead['owner_name'] = owner_data.get('owner_name', '')
                lead['greeting'] = owner_data.get('greeting', 'Hi there')
                lead['subject'] = owner_data.get('subject', f"Quick question for {lead['name']}")
                if lead['owner_name']:
                    progress.print_success(f"  Found owner: {lead['owner_name']}")
            progress.update_step(1)
            
            # Personalizer: Analyze website
            if lead.get('website'):
                progress.print_info(f"  Analyzing website: {lead['website'][:40]}...")
                website_data = analyze_business(lead['website'])
                lead['pain_points'] = website_data.get('pain_points', [])
                lead['has_whatsapp'] = website_data.get('has_whatsapp', False)
                lead['has_ssl'] = website_data.get('has_ssl', False)
                if lead['pain_points']:
                    progress.print_warning(f"  Found {len(lead['pain_points'])} pain points")
            progress.update_step(1)
            
            # Generate mockup
            if lead.get('name'):
                mockup_path = generate_mockup(
                    lead['name'],
                    'review',
                    output_dir='mockups',
                    review_text="Great service!",
                    response_text="Thank you for your kind words!"
                )
                lead['mockup_path'] = mockup_path
            progress.update_step(1)
        
        progress.finish_step()
        owners_found = sum(1 for l in validated_leads if l.get('owner_name'))
        progress.print_success(f"Personalized {len(validated_leads)} leads ({owners_found} owners found)")
        
        # ═══════════════════════════════════════════════════════════════
        # Show qualified leads table
        # ═══════════════════════════════════════════════════════════════
        from rich.table import Table
        
        table = Table(title="QUALIFIED LEADS", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("Business", style="white", width=35)
        table.add_column("Reviews", justify="right")
        table.add_column("Rating", justify="right")
        table.add_column("Email", justify="center")
        table.add_column("Owner", style="green")
        
        for i, lead in enumerate(validated_leads, 1):
            email_status = "[green]OK[/]" if lead.get('email_valid') else "[red]NO EMAIL[/]"
            owner = lead.get('owner_name', '[dim]—[/]')
            table.add_row(
                str(i),
                lead['name'][:35],
                str(lead['review_count']),
                str(lead['rating']),
                email_status,
                owner
            )
        
        console.print()
        console.print(table)
        console.print()
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 6: Send emails
        # ═══════════════════════════════════════════════════════════════
        if send_emails and validated_leads:
            emails_to_send = []
            for lead in validated_leads:
                if lead.get('email_valid'):
                    greeting = lead.get('greeting', 'Hi there')
                    
                    subject = f"Quick question for {lead['name']}"
                    body = f"""{greeting},

I noticed {lead['name']} has {lead['review_count']} Google reviews but only {lead.get('response_rate', 0):.0f}% response rate.

We built an AI tool that helps businesses like yours reply to every review in 30 seconds — personalized, professional, and human-like.

Would you like to see how it works?

Best,
Reviewer Team"""
                    
                    emails_to_send.append({
                        'to': lead['email'],
                        'subject': subject,
                        'body': body,
                    })
            
            if emails_to_send:
                progress.start_step(6, "Sending emails (FAST MODE)", total_items=len(emails_to_send))
                
                progress.print_info(f"Sending {len(emails_to_send)} emails concurrently...")
                
                results = send_bulk_sync(
                    emails=emails_to_send,
                    gmail_user=GMAIL_USER,
                    gmail_password=GMAIL_APP_PASSWORD,
                    sender_name=SENDER_NAME,
                    max_concurrent=3
                )
                
                progress.set_step_progress(results['sent'])
                progress.finish_step()
                
                progress.print_success(f"Sent {results['sent']} emails, {results['failed']} failed")
                
                if results['errors']:
                    for err in results['errors']:
                        progress.print_error(f"  {err['email']}: {err['error']}")
        else:
            progress.start_step(6, "Email sending", total_items=1)
            progress.set_step_progress(1)
            progress.finish_step()
            progress.print_info("Email sending disabled")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 7: Save results
        # ═══════════════════════════════════════════════════════════════
        progress.start_step(7, "Saving results", total_items=2)
        
        save_to_pdf(validated_leads, save_path, city=city, business_type=business_type)
        progress.update_step(1)
        
        csv_path = save_path.replace('.pdf', '.csv')
        save_to_csv(validated_leads, csv_path)
        progress.update_step(1)
        
        progress.finish_step()
        progress.print_success(f"PDF saved: {save_path}")
        progress.print_success(f"CSV saved: {csv_path}")
        
        # ═══════════════════════════════════════════════════════════════
        # Final results
        # ═══════════════════════════════════════════════════════════════
        results = {
            "Businesses scanned": len(businesses),
            "Qualified leads": len(validated_leads),
            "Valid emails": valid_count,
            "Owners found": owners_found,
            "Mockups generated": sum(1 for l in validated_leads if l.get('mockup_path')),
        }
        
        if send_emails:
            results["Emails sent"] = results.get("Emails sent", 0)
        
        results["Results saved to"] = save_path
        
        progress.show_results(results)


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
