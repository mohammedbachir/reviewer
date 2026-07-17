"""
#44 LangGraph State Machine
Build AI "state machine" for smart agent using simple state transitions.
(Using dict-based states instead of LangGraph dependency)
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class StateMachine:
    """Simple state machine for the autonomous agent."""

    STATES = {
        "idle": {"next": ["reading_email", "checking_inbox"], "description": "Waiting for work"},
        "reading_email": {"next": ["classifying", "idle"], "description": "Reading incoming email"},
        "classifying": {"next": ["generating_reply", "scheduling_meeting", "idle"], "description": "Classifying email intent"},
        "generating_reply": {"next": ["sending_reply", "idle"], "description": "Generating auto-reply"},
        "sending_reply": {"next": ["logging", "idle"], "description": "Sending reply via SMTP"},
        "scheduling_meeting": {"next": ["sending_invite", "idle"], "description": "Scheduling meeting"},
        "sending_invite": {"next": ["logging", "idle"], "description": "Sending meeting invite"},
        "logging": {"next": ["idle"], "description": "Logging results to DuckDB"},
        "checking_inbox": {"next": ["reading_email", "idle"], "description": "Checking for new emails"},
        "error": {"next": ["idle"], "description": "Error occurred"},
    }

    def __init__(self):
        self.current_state = "idle"
        self.history: List[Dict] = []
        self.context: Dict = {}

    def transition(self, new_state: str, data: Dict = None) -> bool:
        """Transition to a new state."""
        if new_state not in self.STATES:
            print(f"[StateMachine] Invalid state: {new_state}")
            return False

        if new_state not in self.STATES.get(self.current_state, {}).get("next", []):
            print(f"[StateMachine] Cannot transition from {self.current_state} to {new_state}")
            return False

        old_state = self.current_state
        self.current_state = new_state
        self.history.append({
            "from": old_state,
            "to": new_state,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        })

        print(f"[StateMachine] {old_state} -> {new_state}")
        return True

    def get_state(self) -> Dict:
        """Get current state info."""
        return {
            "current": self.current_state,
            "description": self.STATES[self.current_state]["description"],
            "next_states": self.STATES[self.current_state]["next"],
            "transitions": len(self.history),
        }

    def get_history(self) -> List[Dict]:
        """Get state transition history."""
        return self.history.copy()

    def set_context(self, key: str, value):
        """Set context data for current state."""
        self.context[key] = value

    def get_context(self, key: str = None):
        """Get context data."""
        if key:
            return self.context.get(key)
        return self.context.copy()

    def reset(self):
        """Reset state machine to idle."""
        self.current_state = "idle"
        self.context = {}


if __name__ == "__main__":
    sm = StateMachine()
    print(f"[Test] Initial state: {sm.get_state()}")

    sm.transition("checking_inbox")
    sm.transition("reading_email", {"email_from": "test@biz.com"})
    sm.transition("classifying", {"intent": "interested"})
    sm.transition("generating_reply")
    sm.transition("sending_reply")
    sm.transition("logging")

    print(f"\n[Test] Final state: {sm.get_state()}")
    print(f"[Test] History: {len(sm.get_history())} transitions")
    for h in sm.get_history():
        print(f"  {h['from']} -> {h['to']}")
