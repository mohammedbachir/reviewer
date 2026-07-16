"""
FindLeads — Email Warm-up & Load Balancing
Multi-account rotation, daily quotas, and human mimicry delays.
"""

import smtplib
import time
import random
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class SenderAccount:
    """Represents a Gmail sending account."""
    
    def __init__(self, email: str, password: str, daily_limit: int = 30):
        self.email = email
        self.password = password
        self.daily_limit = daily_limit
        self.sent_today = 0
        self.last_reset = datetime.now().date()
    
    def can_send(self) -> bool:
        """Check if this account can send today."""
        self._check_reset()
        return self.sent_today < self.daily_limit
    
    def record_send(self):
        """Record that an email was sent."""
        self._check_reset()
        self.sent_today += 1
    
    def _check_reset(self):
        """Reset counter if new day."""
        today = datetime.now().date()
        if today > self.last_reset:
            self.sent_today = 0
            self.last_reset = today
    
    def get_remaining(self) -> int:
        """Get remaining emails for today."""
        self._check_reset()
        return self.daily_limit - self.sent_today
    
    def to_dict(self) -> dict:
        """Convert to dict for saving."""
        return {
            'email': self.email,
            'daily_limit': self.daily_limit,
            'sent_today': self.sent_today,
            'last_reset': self.last_reset.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict, password: str) -> 'SenderAccount':
        """Create from dict."""
        account = cls(data['email'], password, data.get('daily_limit', 30))
        account.sent_today = data.get('sent_today', 0)
        account.last_reset = datetime.fromisoformat(data.get('last_reset', datetime.now().date().isoformat())).date()
        return account


class WarmupManager:
    """Manages email warm-up and load balancing."""
    
    def __init__(self, accounts: List[SenderAccount], state_file: str = "sender_state.json"):
        self.accounts = accounts
        self.state_file = state_file
        self._load_state()
    
    def _load_state(self):
        """Load sender state from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                
                # Restore account states
                for acc_data in data.get('accounts', []):
                    for account in self.accounts:
                        if account.email == acc_data['email']:
                            account.sent_today = acc_data.get('sent_today', 0)
                            account.last_reset = datetime.fromisoformat(
                                acc_data.get('last_reset', datetime.now().date().isoformat())
                            ).date()
                            break
            except Exception:
                pass
    
    def _save_state(self):
        """Save sender state to file."""
        data = {
            'accounts': [acc.to_dict() for acc in self.accounts],
            'last_updated': datetime.now().isoformat(),
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_next_account(self) -> Optional[SenderAccount]:
        """
        Get the next available account using round-robin.
        
        Returns:
            Next available account or None if all exhausted
        """
        # Sort by sent_today (prefer accounts with fewer sends)
        available = [acc for acc in self.accounts if acc.can_send()]
        
        if not available:
            return None
        
        # Round-robin: prefer the one that sent least
        available.sort(key=lambda acc: acc.sent_today)
        return available[0]
    
    def get_total_remaining(self) -> int:
        """Get total remaining emails across all accounts."""
        return sum(acc.get_remaining() for acc in self.accounts)
    
    def get_status(self) -> dict:
        """Get status of all accounts."""
        return {
            'total_accounts': len(self.accounts),
            'active_accounts': sum(1 for acc in self.accounts if acc.can_send()),
            'total_sent_today': sum(acc.sent_today for acc in self.accounts),
            'total_remaining': self.get_total_remaining(),
            'accounts': [
                {
                    'email': acc.email,
                    'sent': acc.sent_today,
                    'remaining': acc.get_remaining(),
                    'limit': acc.daily_limit,
                }
                for acc in self.accounts
            ]
        }


class EmailSender:
    """Sends emails with warm-up and load balancing."""
    
    def __init__(self, accounts: List[SenderAccount], 
                 min_delay: int = 120,   # 2 minutes
                 max_delay: int = 900,   # 15 minutes
                 state_file: str = "sender_state.json"):
        """
        Args:
            accounts: List of sender accounts
            min_delay: Minimum delay between emails (seconds)
            max_delay: Maximum delay between emails (seconds)
            state_file: File to save sender state
        """
        self.warmup = WarmupManager(accounts, state_file)
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.accounts = accounts
    
    def send_email(self, to_email: str, subject: str, body: str, 
                   from_name: str = None) -> Tuple[bool, str, str]:
        """
        Send an email using the next available account.
        
        Returns:
            Tuple of (success, message, sender_email)
        """
        # Get next available account
        account = self.warmup.get_next_account()
        
        if not account:
            return False, "All accounts exhausted for today", ""
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{from_name} <{account.email}>" if from_name else account.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send via Gmail SMTP
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
            server.login(account.email, account.password)
            server.sendmail(account.email, to_email, msg.as_string())
            server.quit()
            
            # Record send
            account.record_send()
            self.warmup._save_state()
            
            return True, "Sent successfully", account.email
            
        except smtplib.SMTPAuthenticationError:
            return False, f"Authentication failed for {account.email}", account.email
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {str(e)}", account.email
        except Exception as e:
            return False, f"Error: {str(e)}", account.email
    
    def send_batch(self, emails: List[dict], from_name: str = None) -> dict:
        """
        Send a batch of emails with delays.
        
        Args:
            emails: List of dicts with 'to', 'subject', 'body'
            from_name: Sender name
        
        Returns:
            Dict with results
        """
        results = {
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'details': [],
        }
        
        for i, email_data in enumerate(emails):
            # Check if any account can send
            if self.warmup.get_total_remaining() == 0:
                print(f"\n[Warmup] All accounts exhausted. Sent {results['sent']}, failed {results['failed']}")
                results['skipped'] = len(emails) - i
                break
            
            # Send email
            to_email = email_data.get('to')
            subject = email_data.get('subject')
            body = email_data.get('body')
            
            print(f"[{i+1}/{len(emails)}] Sending to {to_email}...")
            
            success, message, sender = self.send_email(to_email, subject, body, from_name)
            
            if success:
                results['sent'] += 1
                print(f"  OK - Sent from {sender}")
            else:
                results['failed'] += 1
                print(f"  FAIL - {message}")
            
            results['details'].append({
                'to': to_email,
                'success': success,
                'message': message,
                'sender': sender,
            })
            
            # Random delay between emails (human mimicry)
            if i < len(emails) - 1 and self.warmup.get_total_remaining() > 0:
                delay = random.randint(self.min_delay, self.max_delay)
                print(f"  Waiting {delay} seconds before next email...")
                time.sleep(delay)
        
        return results
    
    def get_status(self) -> dict:
        """Get current status."""
        return self.warmup.get_status()


def create_sender(gmail_user: str, gmail_password: str, 
                  daily_limit: int = 30, min_delay: int = 120, max_delay: int = 900) -> EmailSender:
    """
    Create an email sender with warm-up.
    
    Args:
        gmail_user: Gmail address
        gmail_password: App password
        daily_limit: Max emails per day
        min_delay: Min delay between emails (seconds)
        max_delay: Max delay between emails (seconds)
    
    Returns:
        EmailSender instance
    """
    account = SenderAccount(gmail_user, gmail_password, daily_limit)
    return EmailSender([account], min_delay, max_delay)


if __name__ == "__main__":
    # Test with dummy accounts
    accounts = [
        SenderAccount("test1@example.com", "pass1", daily_limit=10),
        SenderAccount("test2@example.com", "pass2", daily_limit=15),
        SenderAccount("test3@example.com", "pass3", daily_limit=20),
    ]
    
    manager = WarmupManager(accounts)
    
    print("Initial status:")
    status = manager.get_status()
    print(f"  Total accounts: {status['total_accounts']}")
    print(f"  Active accounts: {status['active_accounts']}")
    print(f"  Total remaining: {status['total_remaining']}")
    
    # Simulate sends
    for i in range(5):
        account = manager.get_next_account()
        if account:
            account.record_send()
            print(f"  Send {i+1}: Used {account.email} ({account.sent_today}/{account.daily_limit})")
    
    print("\nAfter 5 sends:")
    status = manager.get_status()
    for acc in status['accounts']:
        print(f"  {acc['email']}: {acc['sent']}/{acc['limit']} sent, {acc['remaining']} remaining")
