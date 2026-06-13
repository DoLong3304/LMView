"""Tests for FinBERT and NLP utilities."""
from __future__ import annotations

import pytest
from ai_service.nlp.types import SentimentResult, EntityResult, NewsAnalysis
from ai_service.nlp.entity_extractor import (
    extract_entities,
    classify_event,
    extract_affected_assets,
    estimate_market_relevance,
)


class TestSentimentResult:
    def test_default_values(self):
        sr = SentimentResult()
        assert sr.score == 0.0
        assert sr.label == "neutral"
        assert sr.confidence == 0.0

    def test_to_dict(self):
        sr = SentimentResult(score=0.8, confidence=0.95, label="positive")
        d = sr.to_dict()
        assert d["score"] == 0.8
        assert d["label"] == "positive"


class TestEntityExtractor:
    def test_extract_bitcoin(self):
        entities = extract_entities("Bitcoin surges to new all-time high!")
        names = [e.text for e in entities]
        assert "BTC" in names

    def test_extract_multiple_entities(self):
        entities = extract_entities("Ethereum and Solana lead the altcoin rally")
        names = [e.text for e in entities]
        assert "ETH" in names
        assert "SOL" in names

    def test_extract_org(self):
        entities = extract_entities("SEC approves new crypto ETF")
        labels = {e.text: e.label for e in entities}
        assert "SEC" in labels
        assert labels["SEC"] == "ORG"

    def test_empty_text(self):
        assert extract_entities("") == []


class TestEventClassification:
    def test_regulatory_event(self):
        assert classify_event("SEC launches investigation into crypto exchange") == "regulatory"

    def test_hack_event(self):
        assert classify_event("Major crypto exchange hacked, $100M stolen") == "hack"

    def test_market_move(self):
        assert classify_event("Bitcoin surges past $100K in historic rally") == "market_move"

    def test_launch_event(self):
        assert classify_event("Ethereum mainnet upgrade goes live") == "launch"

    def test_general_event(self):
        assert classify_event("Crypto conference attracts thousands") == "general"


class TestAffectedAssets:
    def test_bitcoin_pair(self):
        pairs = extract_affected_assets("Bitcoin crashes amid selling pressure")
        assert "BTCUSDT" in pairs

    def test_multiple_assets(self):
        pairs = extract_affected_assets("ETH and SOL lead the recovery")
        assert "ETHUSDT" in pairs
        assert "SOLUSDT" in pairs

    def test_stablecoin_excluded(self):
        pairs = extract_affected_assets("USDT loses peg briefly")
        assert "USDTUSDT" not in pairs


class TestMarketRelevance:
    def test_high_relevance(self):
        score = estimate_market_relevance(
            "Bitcoin crashes 20% in massive selloff",
            target_symbol="BTCUSDT",
        )
        assert score >= 0.5

    def test_low_relevance(self):
        score = estimate_market_relevance(
            "Crypto conference scheduled for next month",
            target_symbol="BTCUSDT",
        )
        assert score < 0.5

    def test_empty_text(self):
        assert estimate_market_relevance("") == 0.0

    def test_urgency_boost(self):
        score1 = estimate_market_relevance("SEC announces new rules")
        score2 = estimate_market_relevance("BREAKING: SEC announces new rules")
        assert score2 > score1
