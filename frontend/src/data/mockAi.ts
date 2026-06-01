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

  const contextParts: string[] = [];
  contextParts.push(`symbol=${symbol}`);
  contextParts.push(`timeframe=${timeframe}`);
  if (indicators.length > 0) {
    contextParts.push(`indicators=${indicators.join(", ")}`);
  }

  const contextSummary = contextParts.join("; ");

  mockMessageCounter += 1;

  return {
    id: `mock-msg-${Date.now()}-${mockMessageCounter}`,
    role: "assistant",
    content:
      `[Local Mock] Received your question about "${userMessage.slice(0, 60)}". ` +
      `Chart context: ${contextSummary}. ` +
      `This is a local mock response — the real AI backend is not connected. ` +
      `When connected, this will return grounded market analysis.`,
    is_mock: true,
    provider: "local_mock",
    created_at: new Date().toISOString(),
    warnings: ["Local mock response — no backend connection."],
    suggested_actions: [
      `What is the current trend for ${symbol}?`,
      `Explain the RSI signal for ${symbol}.`,
      `Find support levels for ${symbol} on ${timeframe}.`,
    ],
  };
}
