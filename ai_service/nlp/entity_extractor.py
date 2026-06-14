"""Crypto entity extractor — identifies crypto assets in text.

Uses regex and a curated symbol dictionary for fast entity extraction
without heavy NLP model dependencies.
"""
from __future__ import annotations

import re
from typing import Dict, List, Set

from ai_service.nlp.types import EntityResult

# Top crypto assets by market cap — curated dictionary
_CRYPTO_SYMBOLS: Dict[str, Set[str]] = {
    "BTC": {"bitcoin", "btc"},
    "ETH": {"ethereum", "eth", "ether"},
    "BNB": {"bnb", "binance coin"},
    "SOL": {"solana", "sol"},
    "XRP": {"xrp", "ripple"},
    "ADA": {"cardano", "ada"},
    "DOGE": {"dogecoin", "doge"},
    "DOT": {"polkadot", "dot"},
    "AVAX": {"avalanche", "avax"},
    "MATIC": {"polygon", "matic"},
    "LINK": {"chainlink", "link"},
    "UNI": {"uniswap", "uni"},
    "USDT": {"tether", "usdt"},
    "USDC": {"usdc", "usd coin"},
    "LTC": {"litecoin", "ltc"},
    "ATOM": {"cosmos", "atom"},
    "FIL": {"filecoin", "fil"},
    "NEAR": {"near", "near protocol"},
    "APT": {"aptos", "apt"},
    "ARB": {"arbitrum", "arb"},
    "OP": {"optimism"},
    "TRX": {"tron", "trx"},
    "SHIB": {"shiba", "shib"},
    "SUI": {"sui"},
    "SEI": {"sei"},
    "TIA": {"celestia", "tia"},
}

# Regulatory / institutional entities
_ORG_PATTERNS = [
    (re.compile(r"\bSEC\b"), "SEC"),
    (re.compile(r"\bCFTC\b"), "CFTC"),
    (re.compile(r"\bFed\b|Federal Reserve", re.IGNORECASE), "Federal Reserve"),
    (re.compile(r"\bCoinbase\b", re.IGNORECASE), "Coinbase"),
    (re.compile(r"\bBinance\b", re.IGNORECASE), "Binance"),
    (re.compile(r"\bBlackRock\b", re.IGNORECASE), "BlackRock"),
    (re.compile(r"\bGrayscale\b", re.IGNORECASE), "Grayscale"),
    (re.compile(r"\bFidelity\b", re.IGNORECASE), "Fidelity"),
    (re.compile(r"\bMicroStrategy\b", re.IGNORECASE), "MicroStrategy"),
]

# Event category patterns
_EVENT_PATTERNS = {
    "regulatory": re.compile(r"\bregulat|SEC|CFTC|lawsuit|compliance|ban|restrict", re.IGNORECASE),
    "hack": re.compile(r"\bhack|exploit|breach|stolen|vulnerability|attack", re.IGNORECASE),
    "partnership": re.compile(r"\bpartner|collaborat|integrat|alliance", re.IGNORECASE),
    "launch": re.compile(r"\blaunch|mainnet|testnet|upgrade|fork|release", re.IGNORECASE),
    "market_move": re.compile(r"\bsurge|crash|pump|dump|rally|plunge|all.time", re.IGNORECASE),
    "adoption": re.compile(r"\badopt|institutional|ETF|fund|invest", re.IGNORECASE),
    "defi": re.compile(r"\bDeFi|yield|liquidity|swap|lending|staking", re.IGNORECASE),
}


def extract_entities(text: str) -> List[EntityResult]:
    """Extract crypto-relevant entities from text."""
    if not text:
        return []

    entities: List[EntityResult] = []
    text_lower = text.lower()

    # Extract crypto symbols
    for symbol, aliases in _CRYPTO_SYMBOLS.items():
        for alias in aliases:
            if alias in text_lower:
                entities.append(EntityResult(text=symbol, label="CRYPTO", confidence=0.9))
                break

    # Extract organizations
    for pattern, name in _ORG_PATTERNS:
        if pattern.search(text):
            entities.append(EntityResult(text=name, label="ORG", confidence=0.85))

    return entities


def classify_event(text: str) -> str:
    """Classify a news headline into event category."""
    if not text:
        return "general"

    for category, pattern in _EVENT_PATTERNS.items():
        if pattern.search(text):
            return category

    return "general"


def extract_affected_assets(text: str) -> List[str]:
    """Extract trading pair symbols from text (e.g., BTCUSDT)."""
    entities = extract_entities(text)
    crypto_entities = [e.text for e in entities if e.label == "CRYPTO"]

    # Map to USDT pairs
    pairs = []
    for symbol in crypto_entities:
        if symbol not in {"USDT", "USDC"}:
            pairs.append(f"{symbol}USDT")

    return pairs


def estimate_market_relevance(text: str, target_symbol: str = "") -> float:
    """Estimate how market-relevant a news headline is.

    Returns 0.0 (irrelevant) to 1.0 (highly relevant).
    """
    if not text:
        return 0.0

    score = 0.0
    text_lower = text.lower()

    # Check if target symbol is mentioned
    if target_symbol:
        target_clean = target_symbol.replace("USDT", "").lower()
        for symbol, aliases in _CRYPTO_SYMBOLS.items():
            if symbol.lower() == target_clean or target_clean in aliases:
                if any(a in text_lower for a in aliases):
                    score += 0.4
                break

    # Check for market-moving event categories
    event = classify_event(text)
    event_weights = {
        "market_move": 0.3,
        "regulatory": 0.25,
        "hack": 0.25,
        "launch": 0.15,
        "adoption": 0.2,
        "partnership": 0.1,
        "defi": 0.1,
        "general": 0.05,
    }
    score += event_weights.get(event, 0.05)

    # Check for urgency words
    urgency = re.compile(r"\bbreaking|urgent|alert|just in|flash", re.IGNORECASE)
    if urgency.search(text):
        score += 0.15

    return min(1.0, round(score, 3))
