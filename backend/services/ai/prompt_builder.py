"""
Prompt builder — constructs structured prompts for Ask Mode.

Assembles the system prompt, chart context, RAG chunks, conversation history,
and output format instructions into a message list for the LLM provider.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.models.ai.providers import LLMMessage
from backend.models.ai.rag import RAGChunkResult

logger = logging.getLogger("backend.services.ai.prompt_builder")

# ── System Prompts ────────────────────────────────────────────────────────────

ASK_MODE_SYSTEM_PROMPT = """You are LMView AI, a bilingual (English/Vietnamese) cryptocurrency technical analysis assistant.

## Your Role
- Provide educational technical analysis support for cryptocurrency markets.
- Explain indicators, chart patterns, market structure, and risk management concepts.
- Use the provided chart context, market data, and knowledge base to ground your analysis.
- Always be honest about data limitations and uncertainties.

## Important Rules
1. You are NOT a financial advisor. Never give direct buy/sell recommendations.
2. Always include an educational disclaimer about trading risks.
3. When data is stale, placeholder, or unavailable, explicitly state this.
4. Trades data shown is ticker-derived, NOT a true exchange trade tape.
5. Market overview data may be placeholder — check metadata flags.
6. Order book data may be stale, synthetic, or from a fallback source.
7. News/sentiment data may be unavailable or in-memory cached only.
8. Never execute code, SQL, shell commands, or browser automation.
9. Never auto-trade or suggest specific entry/exit prices as guaranteed.
10. Respond in the same language the user writes in.

## Response Structure
When analyzing a chart or market, structure your response as:

1. **Market Context** — Current market environment and broader context
2. **Trend & Momentum** — Overall trend direction and momentum signals
3. **Key Levels** — Important support/resistance levels
4. **Indicator Evidence** — What indicators are showing
5. **Volume & Liquidity** — Volume patterns and order book analysis
6. **News/Sentiment** — Any relevant news or sentiment context
7. **Knowledge Base** — Relevant educational context from the knowledge base
8. **Risk Notes** — Key risks and considerations
9. **Confidence** — Your confidence level (low/medium/high) and reasoning
10. **⚠️ Disclaimer** — Educational purposes only, not financial advice

Not every response needs all sections — use judgment based on the question.
"""

FINANCIAL_SAFETY_ADDENDUM = """
## Financial Safety
- NEVER claim guaranteed profits or returns.
- NEVER provide specific price predictions as certainties.
- ALWAYS acknowledge that past performance does not guarantee future results.
- ALWAYS remind users that cryptocurrency trading carries significant risk.
- If asked to predict exact prices, provide analysis ranges with confidence levels instead.
"""


def build_ask_prompt(
    user_message: str,
    chart_context: Optional[Dict[str, Any]] = None,
    rag_chunks: Optional[List[RAGChunkResult]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    language: Optional[str] = None,
    data_caveats: Optional[List[str]] = None,
) -> List[LLMMessage]:
    """
    Build the full prompt for Ask Mode.

    Returns a list of LLMMessage objects ready for the provider.
    """
    messages: List[LLMMessage] = []

    # System prompt
    now_utc = datetime.now(timezone.utc)
    runtime_context = (
        "\n## Runtime Context\n"
        f"- Current server time (UTC): {now_utc.isoformat()}\n"
        f"- Current epoch milliseconds: {int(now_utc.timestamp() * 1000)}\n"
        "- Chart candle times are live runtime Unix epoch milliseconds unless explicitly labeled otherwise.\n"
        "- Do not reject or call chart times invalid because they are later than your model training cutoff.\n"
        "- If a timestamp is numerically aligned to the requested timeframe, treat it as valid runtime data.\n"
    )
    system_content = ASK_MODE_SYSTEM_PROMPT + FINANCIAL_SAFETY_ADDENDUM + runtime_context

    if language and language.lower() in ("vi", "vietnamese"):
        system_content += "\nThe user prefers Vietnamese. Respond in Vietnamese when appropriate.\n"

    messages.append(LLMMessage(role="system", content=system_content))

    # Chart context as system context
    if chart_context:
        context_text = _format_chart_context(chart_context, data_caveats)
        messages.append(LLMMessage(
            role="system",
            content=f"## Current Chart Context\n{context_text}",
            name="chart_context",
        ))

    # RAG knowledge chunks as system context
    if rag_chunks:
        kb_text = _format_rag_chunks(rag_chunks)
        messages.append(LLMMessage(
            role="system",
            content=f"## Knowledge Base Context\n{kb_text}",
            name="knowledge_base",
        ))

    # Conversation history
    if conversation_history:
        for msg in conversation_history[-10:]:  # Last 10 messages max
            messages.append(LLMMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
            ))

    # Current user message
    messages.append(LLMMessage(role="user", content=user_message))

    return messages


def _format_chart_context(
    ctx: Dict[str, Any],
    data_caveats: Optional[List[str]] = None,
) -> str:
    """Format chart context into a readable string for the LLM."""
    parts = []

    parts.append(f"- Symbol: {ctx.get('symbol', 'unknown')}")
    parts.append(f"- Exchange: {ctx.get('exchange', 'binance')}")
    parts.append(f"- Timeframe: {ctx.get('timeframe', 'unknown')}")
    parts.append(f"- Chart type: {ctx.get('chart_type', 'candles')}")

    indicators = ctx.get("selected_indicators", [])
    if indicators:
        parts.append(f"- Active indicators: {', '.join(indicators)}")

    candle = ctx.get("latest_candle")
    if candle and isinstance(candle, dict):
        parts.append("- Latest candle:")
        for k, v in candle.items():
            if v is not None:
                parts.append(f"  - {k}: {v}")
                if k in {"open_time", "close_time", "timestamp"} and isinstance(v, (int, float)):
                    parts.append(f"  - {k}_utc: {_format_epoch_ms(v)}")

    ob = ctx.get("orderbook_summary")
    if ob and isinstance(ob, dict):
        parts.append("- Order book summary:")
        parts.append(f"  - Source: {ob.get('source', 'unknown')}")
        if ob.get("best_bid"):
            parts.append(f"  - Best bid: {ob['best_bid']}")
        if ob.get("best_ask"):
            parts.append(f"  - Best ask: {ob['best_ask']}")
        if ob.get("spread"):
            parts.append(f"  - Spread: {ob['spread']}")
        if ob.get("imbalance"):
            parts.append(f"  - Imbalance: {ob['imbalance']}")

    trades = ctx.get("trades_summary")
    if trades and isinstance(trades, dict):
        parts.append("- Trade summary:")
        parts.append(f"  - Data type: {trades.get('data_type', 'ticker_derived')}")
        parts.append(f"  - True trade tape: {trades.get('is_true_trade_tape', False)}")

    news = ctx.get("news_summary")
    if news and isinstance(news, dict):
        parts.append("- News summary:")
        parts.append(f"  - Articles: {news.get('article_count', 0)}")
        if news.get("avg_sentiment") is not None:
            parts.append(f"  - Avg sentiment: {news['avg_sentiment']}")

    market = ctx.get("market_overview_summary")
    if market and isinstance(market, dict):
        is_placeholder = market.get("is_placeholder", True)
        parts.append(f"- Market overview: {'PLACEHOLDER DATA' if is_placeholder else 'live'}")
        if market.get("btc_dominance"):
            parts.append(f"  - BTC dominance: {market['btc_dominance']}")

    # Data caveats
    if data_caveats:
        parts.append("\n⚠️ DATA CAVEATS:")
        for caveat in data_caveats:
            parts.append(f"  - {caveat}")

    return "\n".join(parts)


def _format_epoch_ms(value: int | float) -> str:
    """Format epoch milliseconds for prompt readability."""
    try:
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return "unparseable"


def _format_rag_chunks(chunks: List[RAGChunkResult]) -> str:
    """Format RAG chunks into a readable string for the LLM."""
    parts = []
    parts.append(f"Retrieved {len(chunks)} relevant knowledge base entries:\n")

    for i, chunk in enumerate(chunks, 1):
        source = chunk.source_title or chunk.document_title
        heading = f" > {chunk.heading}" if chunk.heading else ""
        parts.append(f"[{i}] Source: {source}{heading}")
        parts.append(f"    Relevance: {chunk.score:.2f}")
        parts.append(f"    Content: {chunk.text[:800]}")
        parts.append("")

    parts.append(
        "Use these knowledge base entries to ground your response where relevant. "
        "Cite sources by number when referencing specific information."
    )

    return "\n".join(parts)


def estimate_prompt_tokens(messages: List[LLMMessage]) -> int:
    """Rough token count estimate for a message list."""
    total_chars = sum(len(m.content) for m in messages)
    # Add ~4 tokens per message for role/formatting overhead
    return (total_chars // 4) + (len(messages) * 4)
