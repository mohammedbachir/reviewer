"""
Lead Generator — Email Sender
Sends outreach emails via Gmail SMTP.
"""

import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def create_email(to_email, business_name, unanswered_reviews, sender_name, subject, body_template):
    """
    Create an email message.
    
    Args:
        to_email: Recipient email
        business_name: Business name
        unanswered_reviews: Number of unanswered reviews
        sender_name: Your name
        subject: Email subject
        body_template: Email body template
    
    Returns:
        MIMEText email object
    """
    msg = MIMEMultipart()
    msg['From'] = sender_name
    msg['To'] = to_email
    msg['Subject'] = subject
    
    body = body_template.format(
        business_name=business_name,
        unanswered_reviews=unanswered_reviews,
        sender_name=sender_name
    )
    
    msg.attach(MIMEText(body, 'plain'))
    return msg


def send_email(msg, gmail_user, gmail_password):
    """
    Send an email via Gmail SMTP.
    
    Args:
        msg: MIMEText email object
        gmail_user: Gmail address
        gmail_password: Gmail App Password
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.close()
        return True
    except Exception as e:
        print(f"[Sender] Error: {e}")
        return False


def send_outreach_emails(leads, config):
    """
    Send outreach emails to all leads.
    
    Args:
        leads: List of lead business dicts
        config: Configuration dict
    
    Returns:
        Number of emails sent
    """
    gmail_user = config.get('gmail_user')
    gmail_password = config.get('gmail_password')
    sender_name = config.get('sender_name', '')
    subject = config.get('subject', 'Your customers are waiting for a reply')
    body_template = config.get('body_template', '')
    delay = config.get('email_delay', 30)
    
    if not gmail_user or not gmail_password:
        print("[Sender] Gmail credentials not configured")
        return 0
    
    sent_count = 0
    
    for lead in leads:
        email = lead.get('email')
        if not email:
            continue
        
        # Skip if already sent
        if lead.get('status') == 'sent':
            continue
        
        business_name = lead.get('name', 'Unknown')
        unanswered = lead.get('unanswered_reviews', 0)
        
        print(f"[Sender] Sending to: {business_name} ({email})")
        
        msg = create_email(
            to_email=email,
            business_name=business_name,
            unanswered_reviews=unanswered,
            sender_name=sender_name,
            subject=subject,
            body_template=body_template
        )
        
        if send_email(msg, gmail_user, gmail_password):
            lead['status'] = 'sent'
            lead['sent_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            sent_count += 1
            print(f"[Sender] Sent successfully")
        else:
            lead['status'] = 'failed'
            print(f"[Sender] Failed to send")
        
        # Wait between emails
        if delay > 0:
            time.sleep(delay)
    
    print(f"\n[Sender] Sent {sent_count} emails out of {len(leads)} leads")
    return sent_count
