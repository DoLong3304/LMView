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
import {
  aiChat,
  aiChatStream,
  aiGetSessionMessages,
  aiListSessions,
  getSelectedModel,
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
import { normalizeTourPlan } from "@/features/ai/types";
import type { AiMode, LocalAiHelpSession } from "@/types";

type AiToolCall = NonNullable<AiMessage["tool_calls"]>[number];
type AiChartActionMessage = NonNullable<AiMessage["chart_actions"]>[number];

const mockDataAdapter = getMockDataAdapter();

// ── Format version migration ───────────────────────────────────────────
// Sessions created before Phase B won't have response_sections/knowledge_chunks
// in message metadata. They're flushed once on first load after update.
const FORMAT_VERSION_KEY = "lmview_ai_format_v2_migrated";

async function flushOldApiSessions(_userId: string): Promise<void> {
  try {
    const migrated = localStorage.getItem(FORMAT_VERSION_KEY);
    if (migrated) return;
    const payload = await aiListSessions();
    for (const session of payload.sessions) {
      try {
        const msgPayload = await aiGetSessionMessages(session.id);
        const latestAssistant = [...msgPayload.messages]
          .reverse()
          .find((m) => m.role === "assistant");
        if (
          latestAssistant &&
          !(
            Array.isArray(
              (latestAssistant.metadata || {}).response_sections,
            ) ||
            Array.isArray(
              (latestAssistant.metadata || {}).knowledge_chunks,
            )
          )
        ) {
          // Old format — delete
          const { aiDeleteSession } = await import("@/services/aiService");
          await aiDeleteSession(session.id);
        }
      } catch {
        // Skip failures
      }
    }
    localStorage.setItem(FORMAT_VERSION_KEY, "1");
  } catch {
    // Skip on error
  }
}

interface UseAiChatReturn extends AiChatState {
  mode: AiMode;
  sessions: LocalAiHelpSession[];
  sendMessage: (message: string, context?: ChartContextForAi | null) => Promise<void>;
  clearChat: () => void;
  setMode: (mode: AiMode) => void;
  loadSession: (session: LocalAiHelpSession) => Promise<void>;
  deleteSession: (sessionId: string) => void;
  setActiveTour: (tour: TourExecutionState | null) => void;
  /** IDs of assistant messages produced in the current mount by sendMessage (not loaded history) */
  liveMessageIdsRef: React.MutableRefObject<Set<string>>;
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

function mapApiMessage(message: AIMessageResponse, sessionMode?: string): AiMessage {
  const metadata = message.metadata || {};
  const rawTourPlan = message.tour_plan as Record<string, unknown> | null | undefined;
  // Normalize to WalkthroughStep[] format
  const tourPlan = rawTourPlan ? normalizeTourPlan(rawTourPlan) : null;
  return {
    id: message.id,
    role: message.role === "user" || message.role === "system" ? message.role : "assistant",
    content: message.content,
    mode: sessionMode === "interact" ? "interact" : "ask",
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
    response_sections: Array.isArray(metadata.response_sections)
      ? metadata.response_sections.map((s: unknown) => ({
          title: String((s as Record<string, unknown>).title || ""),
          content: String((s as Record<string, unknown>).content || ""),
        }))
      : null,
    knowledge_chunks: Array.isArray(metadata.knowledge_chunks)
      ? metadata.knowledge_chunks.map((c: unknown) => ({
          text: String((c as Record<string, unknown>).text || ""),
          title: String((c as Record<string, unknown>).title || ""),
          source: String((c as Record<string, unknown>).source || ""),
          source_type: String((c as Record<string, unknown>).source_type || ""),
          credibility_level: String((c as Record<string, unknown>).credibility_level || ""),
          score: Number((c as Record<string, unknown>).score) || 0,
          heading: String((c as Record<string, unknown>).heading || ""),
        }))
      : null,
  };
}

interface LocalToolCallInput {
  text: string;
  mode: AiMode;
  /** Backend already returned a tour_plan — skip local interact tool calls for tours */
  alreadyHasTourPlan?: boolean;
}

function tourPlanFromDirectActions(response: import("@/services/aiService").AIChatResponse) {
  const actions = [
    ...(response.chart_actions || []).map((action) => ({
      type: action.action_type,
      params: action.params || {},
      requires_approval: action.requires_approval,
    })),
    ...(response.tool_calls || []).map((call) => ({
      type: call.name,
      params: call.arguments || {},
      requires_approval: call.requires_approval ?? false,
    })),
  ].filter((action) => action.type);

  if (actions.length === 0) return null;
  return {
    tour_id: `direct-actions-${response.message_id || Date.now()}`,
    title: "AI chart actions",
    summary: response.content || "AI chart actions completed.",
    steps: [
      {
        explanation: response.content || "Applying requested chart actions.",
        actions,
        keep_effects: true,
        chart_freeze: true,
      },
    ],
  };
}

function localInteractToolCalls(input: LocalToolCallInput): AiToolCall[] | undefined {
  const { text, mode, alreadyHasTourPlan } = input;
  if (mode !== "interact") return undefined;
  if (alreadyHasTourPlan) return undefined;
  // Tour queries are handled by the backend tour_planner, which
  // produces a `tour_plan` in the assistant message metadata. The
  // local fallback path can't synthesize a valid tour, so we skip
  // any tool call — the user will see a regular text response
  // instead of a half-running legacy tour.
  void text;
  return undefined;
}

export function useAiChat(): UseAiChatReturn {
  const { user, isAuthenticated } = useAuth();
  const isAdmin = user?.role === "admin";
  const abortRef = useRef<(() => void) | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [sessions, setSessions] = useState<LocalAiHelpSession[]>([]);
  // Ref tracking message IDs produced by a live `sendMessage` in this
  // browser session. Messages loaded from history (session reload,
  // session switch) are NOT in this set, so the panel can distinguish
  // a persisted `tour_plan` (don't auto-run) from a fresh response
  // (auto-run if Interact mode).
  const liveMessageIdsRef = useRef<Set<string>>(new Set());
  // The initial-load effect would re-fire if its `refreshApiSessions`
  // dep changes (it's a new ref each render because loadApiSession
  // deps include sessions). Guard with a ref so it only fires once
  // per hook lifetime, otherwise it would clear activeTour on every
  // session-list refresh and break the tour.
  const initialisedRef = useRef(false);
  // Reset ref when sessions are loaded so we don't auto-fire a tour
  // from a persisted message.
  const [_mode, _setMode] = useState<AiMode>("ask");
  // Persist mode across reloads
  useEffect(() => {
    const saved = localStorage.getItem('lmview_ai_mode') as AiMode | null;
    if (saved) _setMode(saved);
  }, []);
  const setMode = useCallback((newMode: AiMode) => {
    _setMode(newMode);
    localStorage.setItem('lmview_ai_mode', newMode);
  }, []);
  const mode = _mode;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTour, setActiveTour] = useState<TourExecutionState | null>(null);

  const loadApiSession = useCallback(
    async (targetSessionId: string) => {
      if (!user?.id) return;
      const payload = await aiGetSessionMessages(targetSessionId);
      const sessionMeta = sessions.find((s) => s.id === targetSessionId);
      const sessionMode = sessionMeta?.mode;
      const nextMessages = payload.messages.map((m) => mapApiMessage(m, sessionMode));
      setSessionId(targetSessionId);
      setMessages(nextMessages);
      setMode(sessionMeta?.mode === "interact" ? "interact" : "ask");
      setError(null);
      setActiveTour(null);
      setActiveAiSessionId(user.id, targetSessionId);
    },
    [sessions, setMode, user?.id],
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
      liveMessageIdsRef.current = new Set();
      return;
    }

    if (isApiAi(isAuthenticated)) {
      // Initial load: flush old session formats, then refresh + auto-load
      if (!initialisedRef.current) {
        initialisedRef.current = true;
        void flushOldApiSessions(user.id).finally(() =>
          refreshApiSessions(true),
        );
      }
      return;
    }

    const localSessions = loadLocalAiSessions(user.id);
    setSessions(localSessions);
    const storedSessionId = getActiveAiSessionId(user.id);
    const localSession =
      localSessions.find((session) => session.id === storedSessionId) || localSessions[0];
    if (localSession) {
      liveMessageIdsRef.current = new Set();
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
        liveMessageIdsRef.current = new Set();
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
        mode,
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
            mode,
            provider: "auth_gate",
            is_mock: false,
            created_at: new Date().toISOString(),
            warnings: ["Login required."],
          };
          setError("You must log in to use AI Helper.");
        } else if (shouldUseMockAi()) {
          assistantMsg = mockDataAdapter.generateAiResponse(trimmed, context);
          assistantMsg.mode = mode;
          assistantMsg.tool_calls = localInteractToolCalls({ text: trimmed, mode });
        } else {
          // Use batch responses for both Ask and Interact so formatted
          // metadata (response_sections, knowledge_chunks, tour_plan,
          // chart_actions, tool_calls) renders consistently. The streaming
          // endpoint is text-only and drops structured UI data.
          const useStructuredBatch = true;
          if (mode === "interact" || useStructuredBatch) {
            try {
              const detectedLang = (context as Record<string, unknown> | null)?.language as string | undefined;
              const { modelName, modelTier } = getSelectedModel();
              const response = await aiChat({
                session_id: sessionId,
                mode,
                message: trimmed,
                chart_context: context as Record<string, unknown> | null,
                language: detectedLang ?? undefined,
                model_name: modelName,
                model_tier: modelTier,
              });
              nextSessionId = response.session_id || sessionId;
              const tourPlan =
                normalizeTourPlan(response.tour_plan as Record<string, unknown> | null | undefined) ||
                (mode === "interact" ? normalizeTourPlan(tourPlanFromDirectActions(response)) : null);
              assistantMsg = {
                id: response.message_id || `api-${Date.now()}`,
                role: "assistant",
                mode,
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
                tour_plan: tourPlan,
                response_sections: response.response_sections ?? null,
                knowledge_chunks: response.knowledge_chunks ?? null,
              };
            } catch (apiErr) {
              // API failed — surface real error instead of fake local help
              throw apiErr;
            }
          } else {
            // Try streaming first, fall back to batch
            try {
            const detectedLang = (context as Record<string, unknown> | null)?.language as string | undefined;
            const { modelName, modelTier } = getSelectedModel();
            const chatStream = aiChatStream({
              session_id: sessionId,
              mode,
              message: trimmed,
              chart_context: context as Record<string, unknown> | null,
              language: detectedLang ?? undefined,
              model_name: modelName,
              model_tier: modelTier,
            });
            abortRef.current = chatStream.abort;
            const { stream } = chatStream;

            // Create streaming placeholder message
            const streamMsgId = `stream-${Date.now()}`;
            const streamAssistantMsg: AiMessage = {
              id: streamMsgId,
              role: "assistant",
              mode,
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
              const detectedLang = (context as Record<string, unknown> | null)?.language as string | undefined;
              const { modelName, modelTier } = getSelectedModel();
              const response = await aiChat({
                session_id: sessionId,
                mode,
                message: trimmed,
                chart_context: context as Record<string, unknown> | null,
                language: detectedLang ?? undefined,
                model_name: modelName,
                model_tier: modelTier,
              });
              nextSessionId = response.session_id || sessionId;
              assistantMsg = {
                id: response.message_id || `api-${Date.now()}`,
                role: "assistant",
                mode,
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
                tour_plan: normalizeTourPlan(response.tour_plan as Record<string, unknown> | null | undefined),
                response_sections: response.response_sections ?? null,
                knowledge_chunks: response.knowledge_chunks ?? null,
              };
            } catch (apiErr) {
              // API failed — surface real error instead of fake local help
              throw apiErr;            }
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
    setActiveTour(null);
    liveMessageIdsRef.current = new Set();
    if (user?.id) setActiveAiSessionId(user.id, null);
    // Fully tear down tour-related UI so we don't leave a stale
    // frozen chart, dim overlay, or highlight from a previous session.
    window.dispatchEvent(new CustomEvent("lmview:chart-freeze", { detail: { frozen: false } }));
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-end"));
    window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));
    // Restore the right panel to the AI Helper tab so the textarea is
    // visible. During the previous tour, open_panel steps may have
    // switched the right panel to "overview" / "orderBook" / etc.
    window.dispatchEvent(new CustomEvent("lmview:open-panel", { detail: { target: "ai" } }));
  }, [user?.id]);

  // Listen for explicit "new chat" requests (from the AI panel
  // + button, the Settings modal "New session" button, or the
  // escape-hatch buttons). Tears down the current session + tour
  // state so the next sendMessage starts a fresh conversation.
  useEffect(() => {
    const onClearChat = (_e: Event) => {
      clearChat();
    };
    window.addEventListener("lmview:ai-clear-chat", onClearChat);
    return () => window.removeEventListener("lmview:ai-clear-chat", onClearChat);
  }, [clearChat]);

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
      setActiveTour(null);
      if (user?.id) setActiveAiSessionId(user.id, session.id);
    },
    [loadApiSession, user?.id],
  );

  const deleteSession = useCallback(
    async (targetSessionId: string) => {
      if (!user?.id) return;
      // Try API delete first; fall back to local-only delete on failure.
      const session = sessions.find((s) => s.id === targetSessionId);
      const isApi = session?.source === "api";
      if (isApi) {
        try {
          const { aiDeleteSession } = await import("@/services/aiService");
          await aiDeleteSession(targetSessionId);
        } catch (err) {
          if (isAdmin || import.meta.env.DEV) {
            console.warn("[AI] Failed to delete API session:", err);
          }
          // Re-throw so the UI can show an error.
          throw err;
        }
      } else {
        deleteLocalAiSession(user.id, targetSessionId);
      }
      setSessions(
        isApi
          ? sessions.filter((s) => s.id !== targetSessionId)
          : loadLocalAiSessions(user.id),
      );
      if (sessionId === targetSessionId) {
        clearChat();
      }
    },
    [clearChat, isAdmin, sessionId, sessions, user?.id],
  );

  return {
    sessionId,
    messages,
    setMessages,
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
    liveMessageIdsRef,
  };
}
