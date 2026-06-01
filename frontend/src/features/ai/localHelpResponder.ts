import type { AiMessage, ChartContextForAi } from "@/features/ai/types";

const MARKET_REASONING_PATTERNS = [
  /\b(predict|prediction|forecast|target|price target)\b/i,
  /\b(buy|sell|long|short|entry|exit|stop loss|take profit)\b/i,
  /\b(should i|trade advice|financial advice)\b/i,
  /\b(analyze|analysis|trend|momentum|bullish|bearish)\b/i,
  /\b(support|resistance)\b/i,
];

const HELP_PATTERNS = [
  /\b(lmview|website|site|app|platform|purpose)\b/i,
  /\b(ai|helper|assistant)\b/i,
  /\b(drawing|draw|tool|trendline|rectangle|fib|fibonacci|ruler|replay)\b/i,
  /\b(indicator|rsi|macd|ema|sma|vwap|bollinger|atr|mfi)\b/i,
  /\b(watchlist|order book|trades|news|market overview|settings)\b/i,
  /\b(login|register|session|account|theme|timeframe|chart type)\b/i,
];

function isStaticConceptQuestion(message: string): boolean {
  return (
    /\b(what is|explain|how to|how do|purpose of|meaning of)\b/i.test(message) &&
    /\b(tool|drawing|indicator|rsi|macd|ema|sma|trendline|fibonacci|support|resistance|replay|watchlist|settings)\b/i.test(message) &&
    !/\b(current|now|today|this chart|this symbol|price action|entry|exit)\b/i.test(message)
  );
}

function createMessage(content: string, warnings: string[] = []): AiMessage {
  return {
    id: `local-help-${Date.now()}`,
    role: "assistant",
    content,
    provider: "lmview_help",
    is_mock: false,
    created_at: new Date().toISOString(),
    warnings,
  };
}

export function generateLmviewHelpResponse(
  userMessage: string,
  context?: ChartContextForAi | null,
): AiMessage {
  const message = userMessage.trim();
  const wantsMarketReasoning = MARKET_REASONING_PATTERNS.some((pattern) => pattern.test(message));
  const wantsHelp = HELP_PATTERNS.some((pattern) => pattern.test(message));

  if (wantsMarketReasoning && !isStaticConceptQuestion(message)) {
    return createMessage(
      "AI market analysis is unavailable in API mode. LMView Help can explain app features, drawing tools, indicators, replay, watchlist, settings, auth/session, and market/news UI. It cannot interpret the current chart, predict price, or provide trade advice until a real AI service is connected.",
      ["AI market analysis unavailable."],
    );
  }

  if (!wantsHelp) {
    return createMessage(
      "LMView Help only answers product-help questions right now. Ask about LMView, AI Helper purpose, drawing tools, indicators, replay, watchlist, settings, auth/session, or market/news UI.",
      ["Question outside help scope."],
    );
  }

  const lower = message.toLowerCase();
  const symbol = context?.symbol || "selected symbol";
  const timeframe = context?.timeframe?.toUpperCase() || "current timeframe";

  if (lower.includes("ai") || lower.includes("helper") || lower.includes("assistant")) {
    return createMessage(
      "AI Helper is gated behind login. In API mode the real AI service is not implemented, so Ask mode uses LMView Help only. Interact mode is unavailable until backend AI actions exist.",
    );
  }

  if (lower.includes("drawing") || lower.includes("trendline") || lower.includes("fibonacci") || lower.includes("ruler")) {
    return createMessage(
      "Drawing tools let you annotate the chart. Use cursor to select, trendline and rays for directional structure, horizontal/vertical lines for levels, rectangles/ellipses for zones, Fibonacci tools for retracement/extension references, text tools for notes, and ruler/price range tools for measurement.",
    );
  }

  if (lower.includes("support") || lower.includes("resistance")) {
    return createMessage(
      "Support and resistance are chart concepts for areas where price has historically reacted. In LMView you can mark them with horizontal lines, rays, rectangles, text notes, or Fibonacci tools. LMView Help cannot identify live levels for the current chart until real AI analysis is connected.",
    );
  }

  if (lower.includes("indicator") || lower.includes("rsi") || lower.includes("macd") || lower.includes("ema") || lower.includes("sma")) {
    return createMessage(
      "Indicators are local chart overlays and panes. LMView supports trend tools like SMA, EMA, VWAP, Ichimoku, Supertrend, and PSAR; momentum tools like RSI, MACD, Stochastic, and MFI; volatility tools like Bollinger Bands and ATR; plus volume overlays.",
    );
  }

  if (lower.includes("replay")) {
    return createMessage(
      "Replay lets you pick a historical candle and step forward through later candles. It is for reviewing chart behavior, not live trading automation.",
    );
  }

  if (lower.includes("watchlist") || lower.includes("order book") || lower.includes("trades")) {
    return createMessage(
      `Right panel shows ${symbol} context on ${timeframe}: watchlist prices, order book depth, recent trades, and AI Helper when logged in. API mode uses backend market endpoints only.`,
    );
  }

  if (lower.includes("settings") || lower.includes("theme") || lower.includes("timeframe") || lower.includes("chart type")) {
    return createMessage(
      "Settings contains Account, Customization, AI Helper, About, and Debug. Account, Customization, and AI Helper require login. Debug requires an admin account. Current customization wiring supports theme, default timeframe, and default chart type; other controls are unavailable until wired.",
    );
  }

  if (lower.includes("login") || lower.includes("register") || lower.includes("session") || lower.includes("account")) {
    return createMessage(
      "Login and register use backend auth in API mode and local mock auth in mock mode. The current session is restored with /auth/me when a stored session token exists.",
    );
  }

  if (lower.includes("news") || lower.includes("market overview")) {
    return createMessage(
      "Markets & News reads market overview, top movers, latest news, search, and trending symbols from real backend endpoints in API mode. Placeholder or mock-tagged API payloads are shown as unavailable.",
    );
  }

  return createMessage(
    "LMView is a real-time crypto technical-analysis workspace with charts, drawing tools, indicators, replay, watchlist, order book, recent trades, market overview, news, auth sessions, settings, and a gated AI Helper.",
  );
}
