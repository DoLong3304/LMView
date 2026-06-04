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
      "LMView Help can explain app features, drawing tools, indicators, replay, watchlist, settings, accounts, and market/news UI. It does not provide live chart interpretation, price prediction, or trade advice.",
      ["Market analysis is not available in Help mode."],
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
      "AI Helper requires login. Ask mode can explain LMView features and workflows. Interact mode will be enabled when chart action approval is ready for users.",
    );
  }

  if (lower.includes("drawing") || lower.includes("trendline") || lower.includes("fibonacci") || lower.includes("ruler")) {
    return createMessage(
      "Drawing tools let you annotate the chart. Use cursor to select, trendline and rays for directional structure, horizontal/vertical lines for levels, rectangles/ellipses for zones, Fibonacci tools for retracement/extension references, text tools for notes, and ruler/price range tools for measurement.",
    );
  }

  if (lower.includes("support") || lower.includes("resistance")) {
    return createMessage(
      "Support and resistance are chart concepts for areas where price has historically reacted. In LMView you can mark them with horizontal lines, rays, rectangles, text notes, or Fibonacci tools.",
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
      `Right panel shows ${symbol} context on ${timeframe}: watchlist prices, order book depth, recent trades, and AI Helper when logged in.`,
    );
  }

  if (lower.includes("settings") || lower.includes("theme") || lower.includes("timeframe") || lower.includes("chart type")) {
    return createMessage(
      "Settings contains Account, Notifications, Customization, AI Helper, and About. Admin accounts also see Debug and account-management tools. Saved defaults are applied on login or reload.",
    );
  }

  if (lower.includes("login") || lower.includes("register") || lower.includes("session") || lower.includes("account")) {
    return createMessage(
      "Login, registration, profile editing, password changes, and account deactivation are available from Account settings. Sessions restore automatically when a valid session exists.",
    );
  }

  if (lower.includes("news") || lower.includes("market overview")) {
    return createMessage(
      "Markets & News shows market overview, top movers, latest news, search, and trending symbols when data is available.",
    );
  }

  return createMessage(
    "LMView is a real-time crypto technical-analysis workspace with charts, drawing tools, indicators, replay, watchlist, order book, recent trades, market overview, news, auth sessions, settings, and a gated AI Helper.",
  );
}
