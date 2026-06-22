import { useCallback, useEffect, useRef, useState } from "react";
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
  aiChatStream,
  aiGetSessionMessages,
  aiListSessions,
  shouldUseMockAi,
  type AIMessageResponse,
  type AISessionResponse,
} from "@/services/aiService";
import { getMockDataAdapter } from "@/services/dataSourceAdapter";
import { getRoleAwareErrorMessage, sanitizeTechnicalDetails } from "@/utils/errors";
import type {
  AiChatState,
  AiMessage,
  ChartContextForAi,
  TourExecutionState,
} from "@/features/ai/types";
import type { AiMode, LocalAiHelpSession } from "@/types";

type AiToolCall = NonNullable<AiMessage["tool_calls"]>[number];
type AiChartActionMessage = NonNullable<AiMessage["chart_actions"]>[number];

const mockDataAdapter = getMockDataAdapter();

interface UseAiChatReturn extends AiChatState {
  mode: AiMode;
  sessions: LocalAiHelpSession[];
  sendMessage: (message: string, context?: ChartContextForAi | null) => Promise<void>;
  clearChat: () => void;
  setMode: (mode: AiMode) => void;
  loadSession: (session: LocalAiHelpSession) => Promise<void>;
  deleteSession: (sessionId: string) => void;
  setActiveTour: (tour: TourExecutionState | null) => void;
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
  const tourPlan = message.tour_plan ? {
    tour_id: message.tour_plan.tour_id,
    title: message.tour_plan.title,
    steps: message.tour_plan.steps.map((s: Record<string, unknown>) => ({
      action_type: String(s.action_type || ""),
      params: (s.params as Record<string, unknown>) || {},
      explanation: String(s.explanation || ""),
      target_selector: s.target_selector != null ? String(s.target_selector) : undefined,
      requires_approval: Boolean(s.requires_approval),
    })),
    summary: message.tour_plan.summary,
    chart_snapshot: message.tour_plan.chart_snapshot as Record<string, unknown> | null | undefined,
  } : null;
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
    tool_calls: Array.isArray(metadata.tool_calls)
      ? metadata.tool_calls.filter((item): item is AiToolCall =>
          Boolean(item) && typeof item === "object" && typeof (item as { name?: unknown }).name === "string",
        )
      : undefined,
    chart_actions: Array.isArray(metadata.chart_actions)
      ? metadata.chart_actions.filter((item): item is AiChartActionMessage =>
          Boolean(item) && typeof item === "object" && typeof (item as { action_type?: unknown }).action_type === "string",
        )
      : undefined,
    token_input: message.token_input ?? metadataNumber(metadata, "token_input"),
    token_output: message.token_output ?? metadataNumber(metadata, "token_output"),
    estimated_cost_usd: metadataNumber(metadata, "estimated_cost_usd"),
    tour_plan: tourPlan,
  };
}

function localInteractToolCalls(message: string, mode: AiMode): AiToolCall[] | undefined {
  if (mode !== "interact") return undefined;
  const text = message.toLowerCase();
  if (/\b(tour|guide|tutorial|demo|learn how|how to use|show me around)\b/.test(text)) {
    return [{
      name: "start_tour",
      arguments: { tour_id: "lmview-overview" },
      reason: "User asked to learn LMView interactively.",
      requires_approval: false,
    }];
  }
  return undefined;
}

export function useAiChat(): UseAiChatReturn {
  const { user, isAuthenticated } = useAuth();
  const isAdmin = user?.role === "admin";
  const abortRef = useRef<(() => void) | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [sessions, setSessions] = useState<LocalAiHelpSession[]>([]);
  const [mode, setMode] = useState<AiMode>("ask");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTour, setActiveTour] = useState<TourExecutionState | null>(null);

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

  // Abort streaming on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

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

      // Abort previous stream if any
      abortRef.current?.();

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
        } else if (shouldUseMockAi()) {
          assistantMsg = mockDataAdapter.generateAiResponse(trimmed, context);
          assistantMsg.tool_calls = localInteractToolCalls(trimmed, mode);
        } else {
          // Try streaming first, fall back to batch
          try {
            const chatStream = aiChatStream({
              session_id: sessionId,
              mode,
              message: trimmed,
              chart_context: context as Record<string, unknown> | null,
            });
            abortRef.current = chatStream.abort;
            const { stream } = chatStream;

            // Create streaming placeholder message
            const streamMsgId = `stream-${Date.now()}`;
            const streamAssistantMsg: AiMessage = {
              id: streamMsgId,
              role: "assistant",
              content: "",
              is_mock: false,
              provider: "streaming",
              created_at: new Date().toISOString(),
            };

            // Add placeholder so user sees immediate response
            const msgsWithPlaceholder = [...baseMessages, streamAssistantMsg];
            setMessages(msgsWithPlaceholder);

            let fullContent = "";
            let streamDone = false;

            for await (const event of stream) {
              if (event.done) {
                streamDone = true;
                // Update with final content
                const finalContent = event.content || fullContent;
                streamAssistantMsg.content = finalContent;
                streamAssistantMsg.provider = "api";
                if (event.guard_warnings) {
                  streamAssistantMsg.warnings = event.guard_warnings;
                }
                // Use session ID from the first response metadata if available
                nextSessionId = sessionId;
                break;
              }
              if (event.content) {
                fullContent += event.content;
                // Update progressively — use functional state update
                streamAssistantMsg.content = fullContent;
                setMessages([...msgsWithPlaceholder.slice(0, -1), { ...streamAssistantMsg }]);
              }
              if (event.error) {
                streamDone = true;
                streamAssistantMsg.content = `Error: ${event.error}`;
                streamAssistantMsg.warnings = [event.error];
                setMessages([...msgsWithPlaceholder.slice(0, -1), { ...streamAssistantMsg }]);
                break;
              }
            }

            if (!streamDone) {
              // Stream ended without done event — use accumulated
              streamAssistantMsg.content = fullContent || "Response incomplete.";
            }

            assistantMsg = streamAssistantMsg;
          } catch (streamErr) {
            // Streaming failed — try batch API
            if (isAdmin || import.meta.env.DEV) {
              console.warn("[AI] Stream failed, falling back to batch:", sanitizeTechnicalDetails(streamErr));
            }
            try {
              const response = await aiChat({
                session_id: sessionId,
                mode,
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
                tool_calls: response.tool_calls,
                chart_actions: response.chart_actions,
                confidence: response.confidence,
                sources: response.sources,
                data_caveats: response.data_caveats,
                provider_metadata: response.provider_metadata,
                token_input: response.token_input ?? undefined,
                token_output: response.token_output ?? undefined,
                estimated_cost_usd: response.estimated_cost_usd ?? undefined,
                news_context: response.news_context ?? undefined,
                tour_plan: response.tour_plan ? {
                  tour_id: response.tour_plan.tour_id,
                  title: response.tour_plan.title,
                  steps: response.tour_plan.steps.map((s: Record<string, unknown>) => ({
                    action_type: String(s.action_type || ""),
                    params: (s.params as Record<string, unknown>) || {},
                    explanation: String(s.explanation || ""),
                    target_selector: s.target_selector != null ? String(s.target_selector) : undefined,
                    requires_approval: Boolean(s.requires_approval),
                  })),
                  summary: response.tour_plan.summary,
                  chart_snapshot: response.tour_plan.chart_snapshot as Record<string, unknown> | null | undefined,
                } : null,
              };
            } catch (apiErr) {
              if (isAdmin || import.meta.env.DEV) {
                console.warn("[AI] API failed, using local help:", sanitizeTechnicalDetails(apiErr));
              }
              assistantMsg = generateLmviewHelpResponse(trimmed, context);
              assistantMsg.tool_calls = localInteractToolCalls(trimmed, mode);
              assistantMsg.warnings = [
                ...(assistantMsg.warnings || []),
                isAdmin
                  ? `API unavailable - using local help mode: ${getRoleAwareErrorMessage(apiErr, { isAdmin: true, area: "ai" })}`
                  : "AI service is unavailable, so local help mode answered instead.",
              ];
            }
          }
        }

        const nextMessages = [...baseMessages, assistantMsg];
        setMessages(nextMessages);
        persistSession(nextMessages, trimmed, nextSessionId);
        if (isApiAi(isAuthenticated)) void refreshApiSessions(false);
      } catch (err) {
        const errMsg = getRoleAwareErrorMessage(err, {
          isAdmin,
          area: "ai",
          fallback: "AI Helper could not complete that request. Please try again.",
        });
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
        abortRef.current = null;
        setLoading(false);
      }
    },
    [
      isAuthenticated,
      isAdmin,
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
    activeTour,
    sendMessage,
    clearChat,
    setMode,
    loadSession,
    deleteSession,
    setActiveTour,
  };
}
