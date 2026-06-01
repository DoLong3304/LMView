/**
 * useAiChat — hook for AI chat state management.
 *
 * Manages messages, session state, and API/mock dispatching.
 */

import { useCallback, useState } from "react";
import { useAuth } from "@/features/auth/AuthContext";
import { aiChat, shouldUseMockAi } from "@/services/aiService";
import { generateMockAiResponse } from "@/data/mockAi";
import type { AiChatState, AiMessage, ChartContextForAi } from "@/features/ai/types";

interface UseAiChatReturn extends AiChatState {
  sendMessage: (message: string, context?: ChartContextForAi | null) => Promise<void>;
  clearChat: () => void;
}

export function useAiChat(): UseAiChatReturn {
  const { isAuthenticated } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (message: string, context?: ChartContextForAi | null) => {
      const trimmed = message.trim();
      if (!trimmed) return;

      // Add user message immediately
      const userMsg: AiMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      setError(null);

      try {
        if (shouldUseMockAi() || !isAuthenticated) {
          // Local mock response
          const mockResp = generateMockAiResponse(trimmed, context);
          setMessages((prev) => [...prev, mockResp]);
        } else {
          // Backend API call
          const chartContext = context
            ? {
                symbol: context.symbol,
                exchange: context.exchange,
                timeframe: context.timeframe,
                chart_type: context.chart_type,
                selected_indicators: context.selected_indicators,
                latest_candle: context.latest_candle,
              }
            : null;

          const resp = await aiChat({
            session_id: sessionId,
            mode: "ask",
            message: trimmed,
            chart_context: chartContext,
          });

          if (!sessionId && resp.session_id) {
            setSessionId(resp.session_id);
          }

          const assistantMsg: AiMessage = {
            id: resp.message_id || `resp-${Date.now()}`,
            role: "assistant",
            content: resp.content,
            is_mock: resp.is_mock,
            provider: resp.provider,
            created_at: resp.created_at,
            warnings: resp.warnings,
            suggested_actions: resp.suggested_actions,
          };
          setMessages((prev) => [...prev, assistantMsg]);
        }
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : "AI request failed";
        setError(errMsg);

        // Add error message to chat
        const errorMsg: AiMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `Error: ${errMsg}. The AI backend may be unavailable.`,
          is_mock: true,
          provider: "error",
          warnings: [errMsg],
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setLoading(false);
      }
    },
    [isAuthenticated, sessionId],
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setError(null);
  }, []);

  return {
    sessionId,
    messages,
    loading,
    error,
    sendMessage,
    clearChat,
  };
}
