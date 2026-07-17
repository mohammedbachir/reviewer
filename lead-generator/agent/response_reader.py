"""
#45 Response Reading
Read and understand customer replies using OpenRouter (llama-3.1-8b:free).
"""

import json
import os
import urllib.request
from datetime import datetime
from typing import Dict


class ResponseReader:
    """Reads and understands customer email replies using LLM."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.model = "meta-llama/llama-3.1-8b-instruct:free"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.stats = {"total_read": 0, "errors": 0}

    def read_reply(self, email_text: str, email_subject: str = "") -> Dict:
        """Read and understand a customer reply."""
        prompt = f"""Analyze this email reply and extract structured information.

Subject: {email_subject}
Email: {email_text}

Return ONLY a JSON object with these fields:
- intent: "interested" | "not_interested" | "question" | "meeting_request" | "pricing_inquiry" | "spam"
- sentiment: "positive" | "negative" | "neutral"
- key_points: list of key points mentioned
- suggested_action: "reply" | "schedule_meeting" | "send_pricing" | "stop_contacting" | "ignore"
- urgency: "high" | "medium" | "low"
- summary: one sentence summary

JSON only, no explanation."""

        try:
            payload = json.dumps({
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.3,
            }).encode("utf-8")

            req = urllib.request.Request(
                self.api_url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )

            response = urllib.request.urlopen(req, timeout=30)
            data = json.loads(response.read().decode())

            content = data["choices"][0]["message"]["content"]
            # Try to parse JSON from response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0]

            result = json.loads(content)
            self.stats["total_read"] += 1
            return result

        except json.JSONDecodeError:
            self.stats["errors"] += 1
            return {"intent": "unknown", "sentiment": "neutral", "error": "parse_error"}
        except Exception as e:
            self.stats["errors"] += 1
            return {"intent": "error", "sentiment": "neutral", "error": str(e)}

    def get_stats(self) -> Dict:
        """Get reader statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    reader = ResponseReader()
    print(f"[Test] Model: {reader.model}")
    print(f"[Test] API: {reader.api_url}")
    print(f"[Test] Stats: {reader.get_stats()}")
    print("[Test] Ready to read replies")
