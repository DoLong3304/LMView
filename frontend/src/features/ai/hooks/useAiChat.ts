import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/features/auth/AuthContext";
import {
  deleteLocalAiSession,
  loadLocalAiSessions,
  upsertLocalAiSession,
} from "@/features/ai/localAiSessions";
import {
  AI_SESSION_SELECTED_EVENT,
  getActiveAiSessionId,
  setActiveAiSessionId,
} from "@/features/ai/aiSessionSelection";
import { generateLmviewHelpResponse } from "@/features/ai/localHelpResponder";
import {
  aiChat,
  aiGetSessionMessages,
  aiListSessions,
  shouldUseMockAi,
  type AIMessageResponse,
  type AISessionResponse,
} from "@/services/aiService";
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
  loadSession: (session: LocalAiHelpSession) => Promise<void>;
  deleteSession: (sessionId: string) => void;
}

function titleFromMessage(message: string): string {
  const trimmed = message.trim();
  if (trimmed.length <= 48) return trimmed || "LMView Help";
  return `${trimmed.slice(0, 45)}...`;
}

function isApiAi(isAuthenticated: boolean): boolean {
  return isAuthenticated && !shouldUseMockAi();
}

function apiSessionTitle(session: AISessionResponse): string {
  if (session.title) return session.title;
  const market = [session.symbol, session.timeframe?.toUpperCase()].filter(Boolean).join(" ");
  return market || "LMView AI session";
}

function mapApiSession(userId: string, session: AISessionResponse): LocalAiHelpSession {
  return {
    id: session.id,
    userId,
    title: apiSessionTitle(session),
    mode: session.mode === "interact" ? "interact" : "ask",
    messages: [],
    message_count: session.message_count,
    symbol: session.symbol ?? undefined,
    timeframe: session.timeframe ?? undefined,
    exchange: session.exchange ?? undefined,
    source: "api",
    created_at: session.created_at || new Date().toISOString(),
    updated_at: session.updated_at || session.created_at || new Date().toISOString(),
  };
}

function metadataNumber(metadata: Record<string, unknown>, key: string): number | undefined {
  const value = metadata[key];
  return typeof value === "number" ? value : undefined;
}

function mapApiMessage(message: AIMessageResponse): AiMessage {
  const metadata = message.metadata || {};
  return {
    id: message.id,
    role: message.role === "user" || message.role === "system" ? message.role : "assistant",
    content: message.content,
    provider: message.provider,
    model_name: message.model_name,
    is_mock: message.is_mock,
    created_at: message.created_at,
    confidence: metadataNumber(metadata, "confidence"),
    data_caveats: Array.isArray(metadata.data_caveats)
      ? metadata.data_caveats.filter((item): item is string => typeof item === "string")
      : undefined,
    provider_metadata:
      metadata.provider_routing && typeof metadata.provider_routing === "object"
        ? (metadata.provider_routing as Record<string, unknown>)
        : undefined,
    token_input: message.token_input ?? metadataNumber(metadata, "token_input"),
    token_output: message.token_output ?? metadataNumber(metadata, "token_output"),
    estimated_cost_usd: metadataNumber(metadata, "estimated_cost_usd"),
  };
}

export function useAiChat(): UseAiChatReturn {
  const { user, isAuthenticated } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [sessions, setSessions] = useState<LocalAiHelpSession[]>([]);
  const [mode, setMode] = useState<AiMode>("ask");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadApiSession = useCallback(
    async (targetSessionId: string) => {
      if (!user?.id) return;
      const payload = await aiGetSessionMessages(targetSessionId);
      const nextMessages = payload.messages.map(mapApiMessage);
      setSessionId(targetSessionId);
      setMessages(nextMessages);
      setMode("ask");
      setError(null);
      setActiveAiSessionId(user.id, targetSessionId);
    },
    [user?.id],
  );

  const refreshApiSessions = useCallback(
    async (autoLoad: boolean) => {
      if (!user?.id) return;
      const payload = await aiListSessions();
      const nextSessions = payload.sessions.map((session) => mapApiSession(user.id, session));
      setSessions(nextSessions);

      if (!autoLoad) return;
      const storedSessionId = getActiveAiSessionId(user.id);
      const targetSession =
        nextSessions.find((session) => session.id === storedSessionId) || nextSessions[0];
      if (targetSession) {
        await loadApiSession(targetSession.id);
      } else {
        setSessionId(null);
        setMessages([]);
      }
    },
    [loadApiSession, user?.id],
  );

  useEffect(() => {
    if (!user?.id) {
      setSessions([]);
      setSessionId(null);
      setMessages([]);
      return;
    }

    if (isApiAi(isAuthenticated)) {
      void refreshApiSessions(true);
      return;
    }

    const localSessions = loadLocalAiSessions(user.id);
    setSessions(localSessions);
    const storedSessionId = getActiveAiSessionId(user.id);
    const localSession =
      localSessions.find((session) => session.id === storedSessionId) || localSessions[0];
    if (localSession) {
      setSessionId(localSession.id);
      setMessages(localSession.messages);
      setMode(localSession.mode);
    }
  }, [isAuthenticated, refreshApiSessions, user?.id]);

  useEffect(() => {
    const onSelected = (event: Event) => {
      const detail = (event as CustomEvent<{ userId?: string; sessionId?: string }>).detail;
      if (!detail?.sessionId || !detail.userId || detail.userId !== user?.id) return;
      if (isApiAi(isAuthenticated)) {
        void loadApiSession(detail.sessionId);
        return;
      }
      const localSession = loadLocalAiSessions(detail.userId).find(
        (session) => session.id === detail.sessionId,
      );
      if (localSession) {
        setSessionId(localSession.id);
        setMessages(localSession.messages);
        setMode(localSession.mode);
        setError(null);
      }
    };

    window.addEventListener(AI_SESSION_SELECTED_EVENT, onSelected);
    return () => window.removeEventListener(AI_SESSION_SELECTED_EVENT, onSelected);
  }, [isAuthenticated, loadApiSession, user?.id]);

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
      if (!isApiAi(isAuthenticated)) {
        setSessions(loadLocalAiSessions(user.id));
      }
      setSessionId(session.id);
      setActiveAiSessionId(user.id, session.id);
      return session.id;
    },
    [isAuthenticated, mode, user?.id],
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
        let nextSessionId = sessionId;

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
          try {
            const response = await aiChat({
              session_id: sessionId,
              mode: "ask",
              message: trimmed,
              chart_context: context as Record<string, unknown> | null,
            });
            nextSessionId = response.session_id || sessionId;
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
            if (nextSessionId && user?.id) {
              setSessionId(nextSessionId);
              setActiveAiSessionId(user.id, nextSessionId);
            }
          } catch (apiErr) {
            console.warn("AI API failed, using local help:", apiErr);
            assistantMsg = generateLmviewHelpResponse(trimmed, context);
            assistantMsg.warnings = [
              ...(assistantMsg.warnings || []),
              `API unavailable - using local help mode: ${
                apiErr instanceof Error ? apiErr.message : "unknown error"
              }`,
            ];
          }
        }

        const nextMessages = [...baseMessages, assistantMsg];
        setMessages(nextMessages);
        persistSession(nextMessages, trimmed, nextSessionId);
        if (isApiAi(isAuthenticated)) void refreshApiSessions(false);
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
      refreshApiSessions,
      sessionId,
      user?.id,
    ],
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setError(null);
    setMode("ask");
    if (user?.id) setActiveAiSessionId(user.id, null);
  }, [user?.id]);

  const loadSession = useCallback(
    async (session: LocalAiHelpSession) => {
      if (session.source === "api") {
        await loadApiSession(session.id);
        return;
      }
      setSessionId(session.id);
      setMessages(session.messages);
      setMode(session.mode);
      setError(null);
      if (user?.id) setActiveAiSessionId(user.id, session.id);
    },
    [loadApiSession, user?.id],
  );

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
