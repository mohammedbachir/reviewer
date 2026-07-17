"""
#9 Sentiment Analysis
Analyzes sentiment of business reviews using VADER (English) and TextBlob.
Classifies reviews as positive/negative/neutral with confidence scores.
"""

from typing import Dict, List, Tuple

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False


_vader = None


def _get_vader():
    global _vader
    if _vader is None and VADER_AVAILABLE:
        _vader = SentimentIntensityAnalyzer()
    return _vader


def analyze_sentiment(text: str) -> Dict:
    """
    Analyze sentiment of a single text.
    
    Returns:
        Dict with sentiment scores and classification
    """
    result = {
        "text": text[:200],
        "polarity": 0.0,
        "subjectivity": 0.0,
        "compound": 0.0,
        "sentiment": "neutral",
        "confidence": 0.0,
        "star_implied": 3.0,
        "method": "none",
    }

    if not text or not text.strip():
        return result

    vader = _get_vader()
    if vader:
        scores = vader.polarity_scores(text)
        result["compound"] = scores["compound"]
        result["polarity"] = scores["compound"]
        result["method"] = "vader"

        if scores["compound"] >= 0.05:
            result["sentiment"] = "positive"
            result["confidence"] = min(abs(scores["compound"]) * 1.5, 1.0)
        elif scores["compound"] <= -0.05:
            result["sentiment"] = "negative"
            result["confidence"] = min(abs(scores["compound"]) * 1.5, 1.0)
        else:
            result["sentiment"] = "neutral"
            result["confidence"] = 1.0 - abs(scores["compound"])

        result["star_implied"] = _compound_to_stars(scores["compound"])

    elif TEXTBLOB_AVAILABLE:
        blob = TextBlob(text)
        result["polarity"] = blob.sentiment.polarity
        result["subjectivity"] = blob.sentiment.subjectivity
        result["method"] = "textblob"

        if blob.sentiment.polarity > 0.1:
            result["sentiment"] = "positive"
            result["confidence"] = min(abs(blob.sentiment.polarity) * 2, 1.0)
        elif blob.sentiment.polarity < -0.1:
            result["sentiment"] = "negative"
            result["confidence"] = min(abs(blob.sentiment.polarity) * 2, 1.0)
        else:
            result["sentiment"] = "neutral"
            result["confidence"] = 1.0 - abs(blob.sentiment.polarity)

        result["star_implied"] = _polarity_to_stars(blob.sentiment.polarity)

    return result


def analyze_reviews_batch(reviews: List[str]) -> Dict:
    """
    Analyze sentiment of multiple reviews and return aggregated results.
    
    Returns:
        Dict with individual and aggregated sentiment data
    """
    if not reviews:
        return {
            "total_reviews": 0,
            "average_sentiment": 0.0,
            "average_stars": 3.0,
            "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
            "negative_keywords": [],
            "positive_keywords": [],
            "individual": [],
        }

    results = [analyze_sentiment(review) for review in reviews]

    sentiments = [r["sentiment"] for r in results]
    distribution = {
        "positive": sentiments.count("positive"),
        "neutral": sentiments.count("neutral"),
        "negative": sentiments.count("negative"),
    }

    avg_polarity = sum(r["polarity"] for r in results) / len(results)
    avg_stars = sum(r["star_implied"] for r in results) / len(results)

    negative_keywords = []
    positive_keywords = []
    for r in results:
        words = r["text"].lower().split()
        if r["sentiment"] == "negative":
            negative_keywords.extend([w for w in words if len(w) > 4])
        elif r["sentiment"] == "positive":
            positive_keywords.extend([w for w in words if len(w) > 4])

    from collections import Counter
    neg_top = [w for w, _ in Counter(negative_keywords).most_common(10)]
    pos_top = [w for w, _ in Counter(positive_keywords).most_common(10)]

    return {
        "total_reviews": len(reviews),
        "average_sentiment": round(avg_polarity, 3),
        "average_stars": round(avg_stars, 1),
        "sentiment_distribution": distribution,
        "negative_percentage": round(distribution["negative"] / len(reviews) * 100, 1) if reviews else 0,
        "positive_percentage": round(distribution["positive"] / len(reviews) * 100, 1) if reviews else 0,
        "negative_keywords": neg_top,
        "positive_keywords": pos_top,
        "individual": results,
    }


def _compound_to_stars(compound: float) -> float:
    """Convert VADER compound score to implied star rating (1-5)."""
    if compound >= 0.5:
        return 5.0
    elif compound >= 0.2:
        return 4.0
    elif compound >= -0.2:
        return 3.0
    elif compound >= -0.5:
        return 2.0
    else:
        return 1.0


def _polarity_to_stars(polarity: float) -> float:
    """Convert TextBlob polarity to implied star rating (1-5)."""
    return round(max(1.0, min(5.0, (polarity + 1) * 2 + 1)), 1)


if __name__ == "__main__":
    test_reviews = [
        "Absolutely wonderful experience! The staff was incredibly friendly and professional.",
        "Terrible service. Waited 2 hours and nobody helped me. Never coming back.",
        "It was okay. Nothing special but not bad either.",
        "The best dental clinic in Dubai! Dr. Ahmed is amazing!",
        "Worst experience ever. Rude staff and dirty environment.",
    ]

    print("Single review analysis:")
    for review in test_reviews:
        result = analyze_sentiment(review)
        print(f"  [{result['sentiment']:>8}] ({result['star_implied']:.0f}*) {review[:60]}")

    print("\nBatch analysis:")
    batch = analyze_reviews_batch(test_reviews)
    print(f"  Total: {batch['total_reviews']}")
    print(f"  Average sentiment: {batch['average_sentiment']}")
    print(f"  Average stars: {batch['average_stars']}")
    print(f"  Distribution: {batch['sentiment_distribution']}")
    print(f"  Negative %: {batch['negative_percentage']}%")
    print(f"  Positive %: {batch['positive_percentage']}%")
