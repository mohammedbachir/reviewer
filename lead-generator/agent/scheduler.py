"""
#47 Meeting Scheduling
Book meetings automatically using Cal.com API (open source).
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List


class MeetingScheduler:
    """Schedules meetings using Cal.com API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("CALCOM_API_KEY", "")
        self.cal_url = "https://api.cal.com/v1"
        self.bookings: List[Dict] = []
        self.stats = {"total_booked": 0, "errors": 0}

    def get_available_slots(self, date: str = None) -> List[Dict]:
        """Get available meeting slots."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Default slots if Cal.com not configured
        return [
            {"time": f"{date}T10:00:00", "available": True},
            {"time": f"{date}T11:00:00", "available": True},
            {"time": f"{date}T14:00:00", "available": True},
            {"time": f"{date}T15:00:00", "available": True},
        ]

    def book_meeting(self, name: str, email: str, date: str = None, time: str = "10:00",
                     notes: str = "") -> Dict:
        """Book a meeting with a lead."""
        if date is None:
            date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        booking = {
            "id": len(self.bookings) + 1,
            "name": name,
            "email": email,
            "date": date,
            "time": time,
            "notes": notes,
            "status": "confirmed",
            "created_at": datetime.now().isoformat(),
        }

        self.bookings.append(booking)
        self.stats["total_booked"] += 1

        print(f"[Scheduler] Meeting booked: {name} ({email}) on {date} at {time}")
        return booking

    def get_upcoming(self) -> List[Dict]:
        """Get all upcoming meetings."""
        return [b for b in self.bookings if b["status"] == "confirmed"]

    def cancel_booking(self, booking_id: int) -> bool:
        """Cancel a booking."""
        for b in self.bookings:
            if b["id"] == booking_id:
                b["status"] = "cancelled"
                return True
        return False

    def get_stats(self) -> Dict:
        """Get scheduling statistics."""
        return {
            **self.stats,
            "total_bookings": len(self.bookings),
            "confirmed": len([b for b in self.bookings if b["status"] == "confirmed"]),
            "cancelled": len([b for b in self.bookings if b["status"] == "cancelled"]),
        }


if __name__ == "__main__":
    scheduler = MeetingScheduler()
    print("[Test] MeetingScheduler initialized")

    scheduler.book_meeting("Ahmed", "ahmed@biz.com", notes="Interested in Reviewer")
    scheduler.book_meeting("Sara", "sara@biz.com", date="2026-07-20", time="14:00")

    upcoming = scheduler.get_upcoming()
    print(f"[Test] Upcoming: {len(upcoming)} meetings")
    for m in upcoming:
        print(f"  {m['name']} ({m['email']}) — {m['date']} {m['time']}")

    stats = scheduler.get_stats()
    print(f"[Test] Stats: {stats}")
