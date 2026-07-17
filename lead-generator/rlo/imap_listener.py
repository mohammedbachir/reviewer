"""
#39 IMAP IDLE Listener
Receives email replies instantly via IMAP push notifications.
Uses imap_tools for IDLE (free, real-time, no polling).
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Callable


class IMAPListener:
    """Listens for incoming emails via IMAP IDLE (push notifications)."""

    def __init__(self, email: str = None, password: str = None, server: str = "imap.gmail.com"):
        self.email = email or os.environ.get("GMAIL_USER", "programmedesigners@gmail.com")
        self.password = password or os.environ.get("GMAIL_PASS", "owbc hwpi dpmh mtcl")
        self.server = server
        self.callbacks: List[Callable] = []
        self.is_listening = False
        self.received_emails: List[Dict] = []
        self.stats = {
            "total_received": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "spam": 0,
        }

    def register_callback(self, callback: Callable):
        """Register a callback function to be called when a reply arrives."""
        self.callbacks.append(callback)

    def start_listening(self, folder: str = "INBOX"):
        """Start listening for new emails via IMAP IDLE."""
        self.is_listening = True
        print(f"[IMAPListener] Listening on {self.email} ({folder})")

        try:
            from imap_tools import MailBox, MailMessage

            with MailBox(self.server).login(self.email, self.password) as mailbox:
                print(f"[IMAPListener] Connected to {self.server}")
                print(f"[IMAPListener] Waiting for new emails...")

                for msg in mailbox.idle.start(timeout=300):
                    if not self.is_listening:
                        break

                    email_data = {
                        "from": msg.from_,
                        "subject": msg.subject,
                        "text": msg.text or msg.html or "",
                        "date": msg.date.isoformat() if msg.date else datetime.now().isoformat(),
                        "uid": msg.uid,
                        "folder": folder,
                    }

                    self.received_emails.append(email_data)
                    self.stats["total_received"] += 1

                    print(f"[IMAPListener] New email from: {msg.from_}")
                    print(f"[IMAPListener] Subject: {msg.subject}")

                    for callback in self.callbacks:
                        try:
                            callback(email_data)
                        except Exception as e:
                            print(f"[IMAPListener] Callback error: {e}")

                mailbox.idle.stop()

        except ImportError:
            print("[IMAPListener] imap_tools not installed. Install: pip install imap-tools")
        except Exception as e:
            print(f"[IMAPListener] Error: {e}")

    def stop_listening(self):
        """Stop listening for emails."""
        self.is_listening = False
        print("[IMAPListener] Stopped listening")

    def get_received(self) -> List[Dict]:
        """Get all received emails."""
        return self.received_emails.copy()

    def get_stats(self) -> Dict:
        """Get listener statistics."""
        return self.stats.copy()

    def check_inbox_once(self, folder: str = "INBOX", limit: int = 10) -> List[Dict]:
        """Check inbox once without IDLE (for testing)."""
        emails = []
        try:
            from imap_tools import MailBox

            with MailBox(self.server).login(self.email, self.password) as mailbox:
                for msg in mailbox.fetch(limit=limit, reverse=True):
                    email_data = {
                        "from": msg.from_,
                        "subject": msg.subject,
                        "text": msg.text or msg.html or "",
                        "date": msg.date.isoformat() if msg.date else datetime.now().isoformat(),
                        "uid": msg.uid,
                    }
                    emails.append(email_data)
                    print(f"[IMAPListener] Found: {msg.from_} — {msg.subject}")

        except ImportError:
            print("[IMAPListener] imap_tools not installed")
        except Exception as e:
            print(f"[IMAPListener] Check error: {e}")

        return emails


if __name__ == "__main__":
    listener = IMAPListener()
    print(f"[Test] Email: {listener.email}")
    print(f"[Test] Server: {listener.server}")
    print(f"[Test] Stats: {listener.get_stats()}")
    print("[Test] Ready to listen")
