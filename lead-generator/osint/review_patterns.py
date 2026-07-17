"""
#65 Review Pattern Analysis
Detect fake reviews and analyze review patterns.
"""

import re
import os
from datetime import datetime
from typing import Dict, List


class ReviewPatternAnalyzer:
    """Analyzes review patterns to detect fake reviews."""

    FAKE_INDICATORS = {
        "generic_phrases": [
            "great place", "highly recommend", "best ever", "amazing experience",
            "love this place", "five stars", "will come back", "perfect",
        ],
        "suspicious_patterns": [
            r"!{3,}",  # Multiple exclamation marks
            r"[A-Z]{5,}",  # All caps words
            r"\b(100%|perfect|best|worst)\b",  # Extreme words
        ],
        "timing_patterns": [
            "just visited", "yesterday", "today", "just now",
        ],
    }

    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.stats = {"total_analyzed": 0, "suspicious": 0, "clean": 0}

    def analyze_review(self, review_text: str, rating: float = None,
                       reviewer_name: str = "", date: str = "") -> Dict:
        """Analyze a single review for fake indicators."""
        text = review_text.lower()
        flags = []
        score = 0

        # Check generic phrases
        generic_hits = [p for p in self.FAKE_INDICATORS["generic_phrases"] if p in text]
        if generic_hits:
            flags.append(f"generic_phrases: {len(generic_hits)}")
            score += len(generic_hits) * 10

        # Check suspicious patterns
        for pattern in self.FAKE_INDICATORS["suspicious_patterns"]:
            if re.search(pattern, review_text):
                flags.append(f"suspicious_pattern: {pattern}")
                score += 15

        # Check for very short reviews
        if len(review_text.split()) < 5:
            flags.append("very_short_review")
            score += 10

        # Check rating extremes
        if rating is not None:
            if rating == 5.0 and len(review_text.split()) < 10:
                flags.append("5_star_short_review")
                score += 15
            if rating == 1.0 and len(review_text.split()) < 5:
                flags.append("1_star_no_detail")
                score += 10

        # Check for repeated words
        words = text.split()
        if len(words) > 3:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.4:
                flags.append("low_word_variety")
                score += 10

        # Classify
        if score >= 30:
            classification = "suspicious"
            self.stats["suspicious"] += 1
        elif score >= 15:
            classification = "possibly_fake"
            self.stats["suspicious"] += 1
        else:
            classification = "clean"
            self.stats["clean"] += 1

        result = {
            "text_preview": review_text[:100],
            "rating": rating,
            "classification": classification,
            "score": score,
            "flags": flags,
            "timestamp": datetime.now().isoformat(),
        }

        self.stats["total_analyzed"] += 1
        return result

    def analyze_batch(self, reviews: List[Dict]) -> Dict:
        """Analyze a batch of reviews."""
        results = []
        for review in reviews:
            result = self.analyze_review(
                review.get("text", ""),
                review.get("rating"),
                review.get("reviewer", ""),
                review.get("date", ""),
            )
            results.append(result)

        suspicious_count = sum(1 for r in results if r["classification"] in ("suspicious", "possibly_fake"))
        return {
            "total": len(results),
            "suspicious": suspicious_count,
            "clean": len(results) - suspicious_count,
            "results": results,
        }

    def get_pattern_summary(self, reviews: List[Dict]) -> Dict:
        """Get summary of review patterns."""
        ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
        if not ratings:
            return {"error": "no_ratings"}

        avg_rating = sum(ratings) / len(ratings)
        distribution = {}
        for r in ratings:
            bucket = str(int(r))
            distribution[bucket] = distribution.get(bucket, 0) + 1

        return {
            "total_reviews": len(reviews),
            "average_rating": round(avg_rating, 2),
            "rating_distribution": distribution,
            "has_rating_gaps": self._check_gaps(ratings),
        }

    def _check_gaps(self, ratings: List[float]) -> bool:
        """Check if there are suspicious gaps in ratings (e.g., no 2-4 stars)."""
        unique_ratings = set(int(r) for r in ratings)
        expected = {1, 2, 3, 4, 5}
        missing = expected - unique_ratings
        return len(missing) >= 2

    def get_stats(self) -> Dict:
        """Get analysis statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    analyzer = ReviewPatternAnalyzer()
    print("[Test] ReviewPatternAnalyzer initialized")

    test_reviews = [
        {"text": "AMAZING PLACE!!! Best ever! Highly recommend! 100% perfect!", "rating": 5.0},
        {"text": "Good food and friendly staff. Will come back.", "rating": 4.0},
        {"text": "Great!", "rating": 5.0},
        {"text": "The service was okay but the wait time was too long.", "rating": 3.0},
    ]

    for review in test_reviews:
        result = analyzer.analyze_review(review["text"], review["rating"])
        print(f"  [{result['classification'].upper()}] {review['text'][:50]}... (score: {result['score']})")

    stats = analyzer.get_stats()
    print(f"\n  Stats: {stats}")
