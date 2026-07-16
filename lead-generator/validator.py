"""
FindLeads — Email Validator
Validates emails using MX records, SMTP verification, and disposable email filtering.
"""

import re
import dns.resolver
import smtplib
import socket
from typing import Optional, Tuple


# Disposable email domains (common ones)
DISPOSABLE_DOMAINS = {
    'mailinator.com', '10minutemail.com', 'guerrillamail.com', 'tempmail.com',
    'throwaway.email', 'temp-mail.org', 'fakeinbox.com', 'sharklasers.com',
    'guerrillamailblock.com', 'grr.la', 'dispostable.com', 'yopmail.com',
    'yopmail.fr', 'maildrop.cc', 'mailsac.com', 'mailcatch.com',
    'tempail.com', 'tempmailer.com', 'tempmailer.net', 'tempail.com',
    'throwawayemailaddress.com', 'tempinbox.com', 'tempinbox.co.uk',
    'mailnull.com', 'mailnull.org', 'tempail.net', 'tmpmail.net',
    'tmpmail.org', 'temp-mail.io', 'tempmail.dev', 'disposable.email',
    'discard.email', 'discardmail.com', 'discardmail.de', 'mailforspam.com',
    'spamgourmet.com', 'spamgourmet.net', 'spamgourmet.org',
}

# Role-based emails (not personal)
ROLE_PREFIXES = {
    'noreply', 'no-reply', 'donotreply', 'do-not-reply',
    'support', 'help', 'info', 'contact', 'admin', 'webmaster',
    'postmaster', 'hostmaster', 'abuse', 'spam', 'billing',
    'sales', 'marketing', 'hr', 'careers', 'jobs', 'press',
    'media', 'team', 'office', 'hello', 'hi', 'feedback',
    'service', 'customerservice', 'customer-service', 'techsupport',
    'security', 'privacy', 'legal', 'compliance', 'info+',
}

# Invalid TLDs
INVALID_TLDS = {
    'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp', 'ico',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'mp3', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm',
    'zip', 'rar', '7z', 'tar', 'gz',
}


class EmailValidator:
    """Validates email addresses using multiple checks."""
    
    def __init__(self, timeout: int = 10, check_smtp: bool = True):
        """
        Args:
            timeout: DNS/SMTP timeout in seconds
            check_smtp: Whether to verify via SMTP (slower but more accurate)
        """
        self.timeout = timeout
        self.check_smtp = check_smtp
    
    def validate(self, email: str) -> Tuple[bool, str, dict]:
        """
        Validate an email address.
        
        Returns:
            Tuple of (is_valid, reason, details)
        """
        details = {
            'email': email,
            'syntax_valid': False,
            'has_mx': False,
            'is_disposable': False,
            'is_role': False,
            'smtp_valid': False,
            'reason': '',
        }
        
        # Step 1: Syntax check
        if not self._check_syntax(email):
            details['reason'] = 'Invalid syntax'
            return False, 'Invalid syntax', details
        
        details['syntax_valid'] = True
        
        # Step 2: Extract domain
        domain = email.split('@')[1].lower()
        
        # Step 3: Check disposable
        if self._is_disposable(domain):
            details['is_disposable'] = True
            details['reason'] = 'Disposable email'
            return False, 'Disposable email', details
        
        # Step 4: Check TLD
        if not self._check_tld(domain):
            details['reason'] = 'Invalid TLD'
            return False, 'Invalid TLD', details
        
        # Step 5: MX record check
        mx_records = self._check_mx(domain)
        if not mx_records:
            details['reason'] = 'No MX records'
            return False, 'No MX records', details
        
        details['has_mx'] = True
        details['mx_records'] = mx_records
        
        # Step 6: Check role-based (flag but don't reject)
        local_part = email.split('@')[0].lower()
        if self._is_role(local_part):
            details['is_role'] = True
        
        # Step 7: SMTP verification (optional)
        if self.check_smtp:
            smtp_valid = self._smtp_verify(email, mx_records)
            details['smtp_valid'] = smtp_valid
            if not smtp_valid:
                details['reason'] = 'SMTP verification failed'
                return False, 'SMTP verification failed', details
        
        # Role-based emails are valid but flagged
        if details['is_role']:
            details['reason'] = 'Valid (role-based)'
            return True, 'Valid (role-based)', details
        
        details['reason'] = 'Valid'
        return True, 'Valid', details
    
    def _check_syntax(self, email: str) -> bool:
        """Check email syntax."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False
        
        # Check if local part looks like a file (e.g., image.png)
        local_part = email.split('@')[0]
        file_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp', 'ico',
                          'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                          'mp3', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm',
                          'zip', 'rar', '7z', 'tar', 'gz'}
        
        # Check if local part ends with a file extension
        if '.' in local_part:
            parts = local_part.split('.')
            if len(parts) > 1 and parts[-1].lower() in file_extensions:
                return False
        
        return True
    
    def _is_disposable(self, domain: str) -> bool:
        """Check if domain is disposable."""
        return domain in DISPOSABLE_DOMAINS
    
    def _is_role(self, local_part: str) -> bool:
        """Check if email is role-based."""
        # Check exact match
        if local_part in ROLE_PREFIXES:
            return True
        # Check if starts with role prefix + special character
        for prefix in ROLE_PREFIXES:
            if local_part.startswith(prefix + '+') or local_part.startswith(prefix + '.'):
                return True
        return False
    
    def _check_tld(self, domain: str) -> bool:
        """Check if TLD is valid."""
        tld = domain.split('.')[-1].lower()
        return tld not in INVALID_TLDS
    
    def _check_mx(self, domain: str) -> list:
        """Check MX records for domain."""
        try:
            # Use Google's public DNS
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
            resolver.timeout = 5
            resolver.lifetime = 5
            
            mx_records = resolver.resolve(domain, 'MX')
            return [(mx.preference, str(mx.exchange).rstrip('.')) for mx in mx_records]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            return []
        except Exception:
            return []
    
    def _smtp_verify(self, email: str, mx_records: list) -> bool:
        """Verify email via SMTP."""
        if not mx_records:
            return False
        
        # Sort by priority
        mx_records.sort(key=lambda x: x[0])
        
        for priority, mx_host in mx_records[:3]:  # Try top 3 MX servers
            try:
                # Connect to SMTP server
                server = smtplib.SMTP(timeout=self.timeout)
                server.connect(mx_host, 25)
                server.helo('findleads.local')
                server.mail('test@findleads.local')
                
                # Try RCPT TO
                code, message = server.rcpt(email)
                
                server.quit()
                
                # 250 = OK, 550/551/552/553 = rejected
                if code == 250:
                    return True
                elif code in (550, 551, 552, 553):
                    return False
                # Other codes = uncertain, try next MX
                continue
                
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
                    socket.timeout, socket.error, ConnectionRefusedError):
                continue
            except Exception:
                continue
        
        # If all MX servers failed, assume valid (don't reject)
        return True
    
    def validate_batch(self, emails: list) -> dict:
        """
        Validate a batch of emails.
        
        Returns:
            Dict with 'valid', 'invalid', and 'stats'
        """
        valid = []
        invalid = []
        
        for email in emails:
            is_valid, reason, details = self.validate(email)
            if is_valid:
                valid.append(details)
            else:
                invalid.append(details)
        
        return {
            'valid': valid,
            'invalid': invalid,
            'stats': {
                'total': len(emails),
                'valid_count': len(valid),
                'invalid_count': len(invalid),
                'valid_rate': len(valid) / len(emails) * 100 if emails else 0,
            }
        }


def validate_email(email: str, check_smtp: bool = True) -> Tuple[bool, str]:
    """
    Simple wrapper for single email validation.
    
    Returns:
        Tuple of (is_valid, reason)
    """
    validator = EmailValidator(check_smtp=check_smtp)
    is_valid, reason, _ = validator.validate(email)
    return is_valid, reason


if __name__ == "__main__":
    # Test
    test_emails = [
        "info@mmdc.ae",
        "test@mailinator.com",
        "noreply@google.com",
        "invalid-email",
        "user@nonexistentdomain12345.com",
        "real@example.com",
    ]
    
    validator = EmailValidator(check_smtp=False)
    results = validator.validate_batch(test_emails)
    
    print(f"Total: {results['stats']['total']}")
    print(f"Valid: {results['stats']['valid_count']}")
    print(f"Invalid: {results['stats']['invalid_count']}")
    print()
    
    for item in results['valid']:
        print(f"  VALID: {item['email']}")
    
    for item in results['invalid']:
        print(f"  INVALID: {item['email']} - {item['reason']}")
