import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/features/auth/AuthContext";
import {
  deleteLocalAiSession,
  loadLocalAiSessions,
  upsertLocalAiSession,
} from "@/features/ai/localAiSessions";
import { generateLmviewHelpResponse } from "@/features/ai/localHelpResponder";
import { shouldUseMockAi, aiChat } from "@/services/aiService";
import { getMockDataAdapter } from "@/services/dataSourceAdapter";
import type {
  AiChatState,
  AiMessage,
  ChartContextForAi,
} from "@/features/ai/types";
import type { AiMode, LocalAiHelpSession } from "@/types";

const mockDataAdapter = getMockDataAdapter();

interface UseAiChatReturn extends AiChatState {
  mode: AiMode;
  sessions: LocalAiHelpSession[];
  sendMessage: (message: string, context?: ChartContextForAi | null) => Promise<void>;
  clearChat: () => void;
  setMode: (mode: AiMode) => void;
  loadSession: (session: LocalAiHelpSession) => void;
  deleteSession: (sessionId: string) => void;
}

function titleFromMessage(message: string): string {
  const trimmed = message.trim();
  if (trimmed.length <= 48) return trimmed || "LMView Help";
  return `${trimmed.slice(0, 45)}...`;
}

export function useAiChat(): UseAiChatReturn {
  const { user, isAuthenticated } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [sessions, setSessions] = useState<LocalAiHelpSession[]>([]);
  const [mode, setMode] = useState<AiMode>("ask");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.id) {
      setSessions([]);
      return;
    }
    setSessions(loadLocalAiSessions(user.id));
  }, [user?.id]);

  const persistSession = useCallback(
    (nextMessages: AiMessage[], firstMessage: string, nextSessionId: string | null) => {
      if (!user?.id || nextMessages.length === 0) return null;
      const session = upsertLocalAiSession({
        userId: user.id,
        sessionId: nextSessionId,
        title: titleFromMessage(firstMessage),
        mode,
        messages: nextMessages,
      });
      setSessions(loadLocalAiSessions(user.id));
      setSessionId(session.id);
      return session.id;
    },
    [mode, user?.id],
  );

  const sendMessage = useCallback(
    async (message: string, context?: ChartContextForAi | null) => {
      const trimmed = message.trim();
      if (!trimmed || loading) return;

      const userMsg: AiMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };
      const baseMessages = [...messages, userMsg];
      setMessages(baseMessages);
      setLoading(true);
      setError(null);

      try {
        let assistantMsg: AiMessage;

        if (!isAuthenticated) {
          assistantMsg = {
            id: `auth-required-${Date.now()}`,
            role: "assistant",
            content: "You must log in to use AI Helper.",
            provider: "auth_gate",
            is_mock: false,
            created_at: new Date().toISOString(),
            warnings: ["Login required."],
          };
          setError("You must log in to use AI Helper.");
        } else if (mode === "interact") {
          assistantMsg = {
            id: `interact-unavailable-${Date.now()}`,
            role: "assistant",
            content: "AI Interact mode is unavailable until a real AI action service exists.",
            provider: "unavailable",
            is_mock: false,
            created_at: new Date().toISOString(),
            warnings: ["AI Interact unavailable."],
          };
        } else if (shouldUseMockAi()) {
          assistantMsg = mockDataAdapter.generateAiResponse(trimmed, context);
        } else {
          // Phase 1: Call real backend API for Ask Mode
          try {
            const response = await aiChat({
              session_id: sessionId,
              mode: "ask",
              message: trimmed,
              chart_context: context as Record<string, unknown> | null,
            });
            assistantMsg = {
              id: response.message_id || `api-${Date.now()}`,
              role: "assistant",
              content: response.content,
              is_mock: response.is_mock,
              provider: response.provider,
              model_name: response.model_name,
              created_at: response.created_at ?? new Date().toISOString(),
              warnings: response.warnings,
              suggested_actions: response.suggested_actions,
              confidence: response.confidence,
              sources: response.sources,
              data_caveats: response.data_caveats,
              provider_metadata: response.provider_metadata,
              token_input: response.token_input ?? undefined,
              token_output: response.token_output ?? undefined,
              estimated_cost_usd: response.estimated_cost_usd ?? undefined,
            };
            // Update session ID from backend response
            if (response.session_id && response.session_id !== sessionId) {
              setSessionId(response.session_id);
            }
          } catch (apiErr) {
            // API failed — fall back to local help responder
            console.warn("AI API failed, using local help:", apiErr);
            assistantMsg = generateLmviewHelpResponse(trimmed, context);
            assistantMsg.warnings = [
              ...(assistantMsg.warnings || []),
              `API unavailable — using local help mode: ${apiErr instanceof Error ? apiErr.message : "unknown error"}`,
            ];
          }
        }

        const nextMessages = [...baseMessages, assistantMsg];
        setMessages(nextMessages);
        persistSession(nextMessages, trimmed, sessionId);
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : "AI request failed";
        setError(errMsg);

        const errorMsg: AiMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `Error: ${errMsg}.`,
          provider: "error",
          warnings: [errMsg],
          created_at: new Date().toISOString(),
        };
        const nextMessages = [...baseMessages, errorMsg];
        setMessages(nextMessages);
        persistSession(nextMessages, trimmed, sessionId);
      } finally {
        setLoading(false);
      }
    },
    [
      isAuthenticated,
      loading,
      messages,
      mode,
      persistSession,
      sessionId,
    ],
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setError(null);
    setMode("ask");
  }, []);

  const loadSession = useCallback((session: LocalAiHelpSession) => {
    setSessionId(session.id);
    setMessages(session.messages);
    setMode(session.mode);
    setError(null);
  }, []);

  const deleteSession = useCallback(
    (targetSessionId: string) => {
      if (!user?.id) return;
      deleteLocalAiSession(user.id, targetSessionId);
      setSessions(loadLocalAiSessions(user.id));
      if (sessionId === targetSessionId) {
        clearChat();
      }
    },
    [clearChat, sessionId, user?.id],
  );

  return {
    sessionId,
    messages,
    sessions,
    mode,
    loading,
    error,
    sendMessage,
    clearChat,
    setMode,
    loadSession,
    deleteSession,
  };
}
