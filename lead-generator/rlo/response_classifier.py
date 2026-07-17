"""
#40 Response Classification
Classifies email replies as positive/negative/neutral/spam using VADER sentiment.
"""

import json
import os
from datetime import datetime
from typing import Dict, List


class ResponseClassifier:
    """Classifies email replies using sentiment analysis."""

    POSITIVE_KEYWORDS = [
        "interested", "yes", "sure", "tell me more", "schedule", "demo",
        "meeting", "call", "price", "information", "thanks", "great",
        "love", "perfect", "sounds good", "let's talk", "send details",
    ]

    NEGATIVE_KEYWORDS = [
        "not interested", "no thank", "unsubscribe", "stop", "spam",
        "remove", "don't contact", "leave me alone", "go away", "never",
    ]

    SPAM_KEYWORDS = [
        "viagra", "casino", "winner", "congratulations", "click here",
        "free money", "lottery", "nigerian prince", "wire transfer",
    ]

    def __init__(self):
        self.classifications: List[Dict] = []
        self.stats = {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "spam": 0,
        }
        self._vader = None
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
        except ImportError:
            pass

    def classify(self, email_data: Dict) -> Dict:
        """Classify a single email reply."""
        text = (email_data.get("text", "") + " " + email_data.get("subject", "")).lower()

        # Check for spam first
        spam_score = sum(1 for kw in self.SPAM_KEYWORDS if kw in text)
        if spam_score >= 2:
            result = {
                "classification": "spam",
                "confidence": min(spam_score / 3, 1.0),
                "reason": "spam_keywords_detected",
                "timestamp": datetime.now().isoformat(),
            }
            self.stats["spam"] += 1
            self.stats["total"] += 1
            self.classifications.append(result)
            return result

        # VADER sentiment analysis
        vader_score = 0
        if self._vader:
            scores = self._vader.polarity_scores(text)
            vader_score = scores.get("compound", 0)

        # Keyword matching
        positive_hits = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in text)
        negative_hits = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in text)

        # Combine scores
        if vader_score > 0.3 or positive_hits >= 2:
            classification = "positive"
            confidence = min(abs(vader_score) + positive_hits * 0.2, 1.0)
            self.stats["positive"] += 1
        elif vader_score < -0.3 or negative_hits >= 2:
            classification = "negative"
            confidence = min(abs(vader_score) + negative_hits * 0.2, 1.0)
            self.stats["negative"] += 1
        else:
            classification = "neutral"
            confidence = 0.5
            self.stats["neutral"] += 1

        result = {
            "classification": classification,
            "confidence": round(confidence, 3),
            "vader_score": vader_score,
            "positive_hits": positive_hits,
            "negative_hits": negative_hits,
            "timestamp": datetime.now().isoformat(),
        }

        self.stats["total"] += 1
        self.classifications.append(result)
        return result

    def classify_batch(self, emails: List[Dict]) -> List[Dict]:
        """Classify multiple emails."""
        results = []
        for email_data in emails:
            result = self.classify(email_data)
            result["from"] = email_data.get("from", "unknown")
            result["subject"] = email_data.get("subject", "")
            results.append(result)
        return results

    def get_positive_replies(self) -> List[Dict]:
        """Get all positive replies (leads to follow up)."""
        return [c for c in self.classifications if c["classification"] == "positive"]

    def get_negative_replies(self) -> List[Dict]:
        """Get all negative replies (stop contacting)."""
        return [c for c in self.classifications if c["classification"] == "negative"]

    def get_stats(self) -> Dict:
        """Get classification statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    classifier = ResponseClassifier()

    test_emails = [
        {"from": "ahmed@business.com", "subject": "Re: Partnership", "text": "Yes, I'm interested! Let's schedule a call."},
        {"from": "sara@business.com", "subject": "Re: Partnership", "text": "No thank you, not interested."},
        {"from": "spam@biz.com", "subject": "You won!", "text": "Congratulations! Click here for free money!"},
        {"from": "omar@business.com", "subject": "Re: Partnership", "text": "Can you send me more information about pricing?"},
    ]

    results = classifier.classify_batch(test_emails)
    for r in results:
        print(f"  {r['from']}: {r['classification']} ({r['confidence']:.2f})")

    stats = classifier.get_stats()
    print(f"\n  Stats: {stats}")
