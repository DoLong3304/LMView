"""FinBERT NLP types — shared data classes for the sentiment pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SentimentResult:
    """Single-text sentiment analysis result from FinBERT."""
    score: float = 0.0           # -1.0 (very negative) to 1.0 (very positive)
    confidence: float = 0.0      # 0.0 to 1.0
    label: str = "neutral"       # "positive" | "negative" | "neutral"
    raw_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "confidence": self.confidence,
            "label": self.label,
            "raw_scores": self.raw_scores,
        }


@dataclass
class EntityResult:
    """Named entity extraction result."""
    text: str
    label: str                   # "CRYPTO", "ORG", "PERSON", "EVENT"
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "label": self.label, "confidence": self.confidence}


@dataclass
class NewsAnalysis:
    """Complete analysis of a news article."""
    title: str
    source: Optional[str] = None
    url: Optional[str] = None
    sentiment: Optional[SentimentResult] = None
    entities: List[EntityResult] = field(default_factory=list)
    event_category: str = "general"
    affected_assets: List[str] = field(default_factory=list)
    market_relevance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
            "entities": [e.to_dict() for e in self.entities],
            "event_category": self.event_category,
            "affected_assets": self.affected_assets,
            "market_relevance": self.market_relevance,
        }
