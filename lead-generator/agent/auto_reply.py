"""
#46 Auto-Reply Generation
Generate appropriate auto-reply using OpenRouter (llama-3.1-8b:free).
"""

import json
import os
import urllib.request
from datetime import datetime
from typing import Dict


class AutoReplyGenerator:
    """Generates auto-replies to customer emails using LLM."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.model = "meta-llama/llama-3.1-8b-instruct:free"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.stats = {"total_generated": 0, "errors": 0}

    def generate_reply(self, email_text: str, email_subject: str = "",
                       business_name: str = "", intent: str = "interested") -> Dict:
        """Generate an appropriate reply to a customer email."""
        prompt = f"""You are a friendly business development representative for Reviewer — a tool that helps businesses respond to their Google Maps reviews using AI.

A customer named {business_name or 'the business'} has sent this email:
Subject: {email_subject}
Message: {email_text}

Their intent appears to be: {intent}

Generate a professional, friendly reply. Rules:
1. Be concise (2-4 sentences max)
2. Address their specific concern
3. If interested: offer a quick demo or call
4. If pricing inquiry: mention it's free to start
5. If not interested: thank them politely
6. Match their language (if they write in Arabic, reply in Arabic)
7. Do NOT mention AI or automation
8. Sign as "Reviewer Team"

Return ONLY the reply text, nothing else."""

        try:
            payload = json.dumps({
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.7,
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

            reply_text = data["choices"][0]["message"]["content"].strip()
            self.stats["total_generated"] += 1

            return {
                "reply_text": reply_text,
                "intent": intent,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.stats["errors"] += 1
            return {"reply_text": "", "error": str(e)}

    def generate_by_intent(self, email_text: str, intent: str, business_name: str = "") -> Dict:
        """Generate reply based on classified intent."""
        return self.generate_reply(email_text, business_name=business_name, intent=intent)

    def get_stats(self) -> Dict:
        """Get generator statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    gen = AutoReplyGenerator()
    print(f"[Test] Model: {gen.model}")
    print(f"[Test] Stats: {gen.get_stats()}")
    print("[Test] Ready to generate replies")
