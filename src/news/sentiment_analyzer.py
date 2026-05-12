"""Sentiment analysis service using VADER.

VADER (Valence Aware Dictionary and sEntiment Reasoner) is a lexicon and
rule-based sentiment analysis tool specifically attuned to sentiments
expressed in social media and news headlines.
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)

# Try to import vaderSentiment, but don't fail if not installed
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    log.warning("vaderSentiment not installed. Sentiment analysis will return neutral scores.")


class SentimentAnalyzer:
    """Sentiment analyzer using VADER.

    Usage::

        analyzer = SentimentAnalyzer()
        score = analyzer.analyze("Bitcoin surges to new all-time high!")
        # score = 0.8 (positive)
    """

    def __init__(self):
        if VADER_AVAILABLE:
            self.analyzer = SentimentIntensityAnalyzer()
            log.info("VADER sentiment analyzer initialized.")
        else:
            self.analyzer = None
            log.warning("VADER not available. Using fallback neutral sentiment.")

    def analyze(self, text: str) -> float:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze (news title, headline, etc.)

        Returns:
            Sentiment score from -1.0 (very negative) to 1.0 (very positive)
            0.0 is neutral
        """
        if not text or not text.strip():
            return 0.0

        if not self.analyzer:
            # Fallback: return neutral if VADER not available
            return 0.0

        try:
            # VADER returns dict with keys: neg, neu, pos, compound
            # compound is the normalized score from -1 to 1
            scores = self.analyzer.polarity_scores(text)
            compound_score = scores.get("compound", 0.0)

            log.debug("Sentiment analysis: '%s' -> %.3f", text[:50], compound_score)
            return compound_score

        except Exception as e:
            log.error("Sentiment analysis failed for text '%s': %s", text[:50], e)
            return 0.0

    def analyze_batch(self, texts: list[str]) -> list[float]:
        """Analyze sentiment for multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of sentiment scores in same order as input
        """
        return [self.analyze(text) for text in texts]

    def classify(self, score: float) -> str:
        """Classify sentiment score into category.

        Args:
            score: Sentiment score from -1.0 to 1.0

        Returns:
            Category: "very_negative", "negative", "neutral", "positive", "very_positive"
        """
        if score <= -0.6:
            return "very_negative"
        elif score <= -0.2:
            return "negative"
        elif score < 0.2:
            return "neutral"
        elif score < 0.6:
            return "positive"
        else:
            return "very_positive"


def main():
    """Test sentiment analyzer."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    analyzer = SentimentAnalyzer()

    test_texts = [
        "Bitcoin surges to new all-time high!",
        "Crypto market crashes amid regulatory concerns",
        "Ethereum upgrade scheduled for next month",
        "Major exchange hacked, millions stolen",
        "Institutional investors show growing interest in crypto",
    ]

    log.info("Testing sentiment analysis:")
    for text in test_texts:
        score = analyzer.analyze(text)
        category = analyzer.classify(score)
        log.info("  %.3f (%s): %s", score, category, text)


if __name__ == "__main__":
    main()
