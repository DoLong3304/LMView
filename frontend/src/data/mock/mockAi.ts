/**
 * Local mock AI responses for VITE_DATA_SOURCE=mock mode.
 */

import type { AiMessage, ChartContextForAi } from "@/features/ai/types";

let mockMessageCounter = 0;

export function generateMockAiResponse(
  userMessage: string,
  context?: ChartContextForAi | null,
): AiMessage {
  const symbol = context?.symbol ?? "BTCUSDT";
  const timeframe = context?.timeframe ?? "1m";
  const indicators = context?.selected_indicators ?? [];

  mockMessageCounter += 1;

  const lowerMsg = userMessage.toLowerCase();
  
  // Dynamic sentiment based on the message or symbol
  let sentimentDir = "neutral";
  let sentimentScore = 0.05;
  if (lowerMsg.includes("bull") || lowerMsg.includes("buy") || lowerMsg.includes("rally") || lowerMsg.includes("surge") || lowerMsg.includes("up")) {
    sentimentDir = "bullish";
    sentimentScore = 0.65;
  } else if (lowerMsg.includes("bear") || lowerMsg.includes("sell") || lowerMsg.includes("crash") || lowerMsg.includes("dump") || lowerMsg.includes("down")) {
    sentimentDir = "bearish";
    sentimentScore = -0.58;
  }

  // Risk events generation
  const riskEvents: string[] = [];
  if (lowerMsg.includes("hack") || lowerMsg.includes("exploit")) {
    riskEvents.push(`[Mock Alert] Security exploit reported on smart contract relating to ${symbol.slice(0, 3)} ecosystems.`);
  }
  if (lowerMsg.includes("crash") || lowerMsg.includes("dump") || lowerMsg.includes("drop")) {
    riskEvents.push(`[Mock Alert] High-volume market sell-off triggered liquidations near support levels.`);
  }
  if (lowerMsg.includes("sec") || lowerMsg.includes("regulation") || lowerMsg.includes("lawsuit") || lowerMsg.includes("court")) {
    riskEvents.push(`[Mock Alert] Regulatory scrutiny increases as SEC files inquiry regarding ${symbol.slice(0, 3)} compliance.`);
  }

  // Standard mock news context
  const newsContextSummary = {
    symbol: symbol,
    article_count: 4,
    source_count: 3,
    top_headlines: [
      {
        title: `[Mock] ${symbol} exhibits interesting price structure near local ranges`,
        source: "coindesk",
        sentiment: sentimentDir,
        sentiment_score: sentimentScore,
        published_at: new Date(Date.now() - 1.5 * 3600 * 1000).toISOString(),
        symbols: [symbol],
      },
      {
        title: "[Mock] Institutional inflows shift momentum across major technical pairings",
        source: "cointelegraph",
        sentiment: "bullish",
        sentiment_score: 0.42,
        published_at: new Date(Date.now() - 4.2 * 3600 * 1000).toISOString(),
        symbols: ["BTC", "ETH"],
      },
      {
        title: "[Mock] Regulatory changes proposed for decentralized serving layers",
        source: "blockworks",
        sentiment: "neutral",
        sentiment_score: -0.05,
        published_at: new Date(Date.now() - 8.1 * 3600 * 1000).toISOString(),
        symbols: [symbol],
      },
      {
        title: `[Mock] Market volume surges for ${symbol} indicators list`,
        source: "decrypt",
        sentiment: sentimentDir === "bearish" ? "bearish" : "neutral",
        sentiment_score: sentimentDir === "bearish" ? -0.35 : 0.1,
        published_at: new Date(Date.now() - 12.0 * 3600 * 1000).toISOString(),
        symbols: [symbol, "USDT"],
      },
    ],
    sentiment_summary: {
      direction: sentimentDir,
      avg_score: sentimentScore,
      positive_count: sentimentDir === "bullish" ? 2 : 1,
      neutral_count: 2,
      negative_count: sentimentDir === "bearish" ? 2 : 1,
      confidence: "0.88",
      symbol_specific: true,
    },
    freshness: {
      newest_age_hours: 1.5,
      oldest_age_hours: 12.0,
      newest_at: new Date(Date.now() - 1.5 * 3600 * 1000).toISOString(),
      is_stale: false,
    },
    risk_events: riskEvents,
    caveats: [
      "[Mock Caveat] News data is simulated for frontend mock workspace.",
      `[Mock Caveat] Market indicator context for ${symbol} uses simulated feed.`,
    ],
    trending_symbols: [
      { symbol: "BTC", mention_count: 45, avg_sentiment: 0.28 },
      { symbol: "ETH", mention_count: 32, avg_sentiment: 0.15 },
      { symbol: symbol.replace("USDT", ""), mention_count: 24, avg_sentiment: sentimentScore },
    ],
  };

  return {
    id: `mock-msg-${Date.now()}-${mockMessageCounter}`,
    role: "assistant",
    content:
      `### [Local Mock] AI Analysis for ${symbol}\n\n` +
      `We detected that the chart context is set to **${symbol}** on the **${timeframe}** timeframe. ` +
      `The selected indicators are: ${indicators.length > 0 ? indicators.map(ind => `\`${ind}\``).join(", ") : "_none_"}.\n\n` +
      `Based on the simulated **${sentimentDir}** market sentiment (average score: \`${sentimentScore}\`), ` +
      `here is a high-level summary of the mock setup:\n\n` +
      `- **Support Level:** $${(1000).toLocaleString()}\n` +
      `- **Resistance Level:** $${(1100).toLocaleString()}\n` +
      `- **Mock Feedback:** You asked: "${userMessage}". This is fully routed through the local mock adapter.\n\n` +
      `*This is a local mockup of Phase 1 Ask Mode which includes metadata, confidence parameters, sources and news context.*`,
    is_mock: true,
    provider: "local_mock",
    model_name: "mock-qwen-2.5",
    created_at: new Date().toISOString(),
    warnings: ["Local mock response — no backend connection."],
    suggested_actions: [
      `What is the current trend for ${symbol}?`,
      `Explain the RSI signal for ${symbol}.`,
      `Find support levels for ${symbol} on ${timeframe}.`,
    ],
    confidence: 0.85,
    sources: [
      {
        chunk_id: "doc-grounding",
        title: "LMView AI Grounding",
        source: "approved/lmview_ai_grounding.md",
        score: 0.95,
        heading: "System Overview",
      },
      {
        chunk_id: "doc-caveats",
        title: "LMView Data Caveats",
        source: "approved/lmview_data_caveats.md",
        score: 0.82,
        heading: "Data Freshness Boundaries",
      },
    ],
    data_caveats: [
      `Simulated ${symbol} news context is active.`,
      "RAG vectors are populated from mock grounding indices.",
      "Live orderbook and transaction streams are disabled.",
    ],
    provider_metadata: {
      effective_provider: "local_mock_provider",
      model: "mock-qwen-3.5-plus",
      latency_ms: 120,
    },
    token_input: 980,
    token_output: 340,
    estimated_cost_usd: 0.0018,
    news_context: newsContextSummary,
  };
}
