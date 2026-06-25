/**
 * AI service — API calls for AI chat, sessions, and chart actions.
 *
 * Talks to /api/ai/* endpoints.
 * Real API helpers only. Mock and local help modes live at frontend service boundary.
 */

import { API_BASE_URL, DATA_SOURCE } from "@/constants/env";
import { getAuthHeaders } from "@/services/authService";
import { createApiError } from "@/utils/errors";

// ── Types ────────────────────────────────────────────────────────────────────

export interface AIChatRequest {
  session_id?: string | null;
  mode: "ask" | "interact";
  message: string;
  language?: string | null;
  chart_context?: Record<string, unknown> | null;
}

export interface AIChartAction {
  action_type: string;
  params: Record<string, unknown>;
  reason?: string | null;
  requires_approval: boolean;
}

export interface AIChatResponse {
  session_id: string;
  message_id: string;
  role: string;
  content: string;
  provider: string;
  model_name?: string | null;
  is_mock: boolean;
  created_at?: string | null;
  warnings: string[];
  suggested_actions?: string[] | null;
  tool_calls?: Array<{
    name: string;
    arguments?: Record<string, unknown>;
    reason?: string | null;
    requires_approval?: boolean;
  }> | null;
  chart_actions?: AIChartAction[] | null;
  grounded_context_used: boolean;
  /** Phase 1: response confidence level 0-1 */
  confidence?: number | null;
  /** Phase 1: RAG source citations */
  sources?: Array<{
    chunk_id?: string;
    title?: string;
    source?: string;
    score?: number;
    heading?: string;
  }> | null;
  /** Phase 1: data caveat warnings */
  data_caveats?: string[] | null;
  /** Phase 1: provider routing metadata */
  provider_metadata?: Record<string, unknown> | null;
  /** Token usage for cost tracking */
  token_input?: number | null;
  token_output?: number | null;
  estimated_cost_usd?: number | null;
  /** News context summary for display chips */
  news_context?: NewsContextSummary | null;
  /** Tour plan for Interact mode guided analysis */
  tour_plan?: {
    tour_id: string;
    title: string;
    steps: Array<{
      action_type: string;
      params: Record<string, unknown>;
      explanation: string;
      target_selector?: string | null;
      requires_approval?: boolean;
    }>;
    summary: string;
    chart_snapshot?: Record<string, unknown> | null;
  } | null;
}

/** Compact news context returned by AI chat */
export interface NewsContextSummary {
  symbol?: string | null;
  article_count: number;
  source_count: number;
  top_headlines: Array<{
    title: string;
    source: string;
    sentiment: string;
    sentiment_score: number;
    published_at?: string | null;
    symbols: string[];
  }>;
  sentiment_summary: {
    direction: string;
    avg_score: number;
    positive_count: number;
    neutral_count: number;
    negative_count: number;
    confidence: string;
    symbol_specific?: boolean;
  };
  freshness: {
    newest_age_hours?: number | null;
    oldest_age_hours?: number | null;
    newest_at?: string | null;
    is_stale: boolean;
  };
  risk_events: string[];
  caveats: string[];
  trending_symbols: Array<{
    symbol: string;
    mention_count: number;
    avg_sentiment: number;
  }>;
}

export interface AISessionResponse {
  id: string;
  user_id: string;
  title?: string | null;
  mode: string;
  symbol?: string | null;
  timeframe?: string | null;
  exchange?: string | null;
  status: string;
  message_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AIMessageResponse {
  id: string;
  session_id: string;
  role: string;
  content: string;
  provider?: string | null;
  model_name?: string | null;
  is_mock: boolean;
  token_input?: number | null;
  token_output?: number | null;
  latency_ms?: number | null;
  created_at?: string | null;
  metadata: Record<string, unknown>;
  /** Tour plan for Interact mode guided analysis */
  tour_plan?: {
    tour_id: string;
    title: string;
    steps: Array<{
      action_type: string;
      params: Record<string, unknown>;
      explanation: string;
      target_selector?: string | null;
      requires_approval?: boolean;
    }>;
    summary: string;
    chart_snapshot?: Record<string, unknown> | null;
  } | null;
}

export interface AIHealthResponse {
  auth_required: boolean;
  database_ready: boolean;
  mock_mode_available: boolean;
  chart_action_schema_version: string;
  supported_modes: string[];
  supported_action_types: string[];
  ai_mode?: string | null;
  provider_mode?: string | null;
  effective_provider?: string | null;
  available_api_models?: string[];
  local_available?: boolean;
  action_catalog_version?: string | null;
  rag_enabled?: boolean;
  real_llm_enabled?: boolean;
  available_providers?: string[] | null;
  pgvector_ready?: boolean;
  knowledge_source_count?: number;
}

export interface AiActionCatalog {
  version: string;
  functions: Array<{
    name: string;
    description: string;
    action_type?: string;
    parameters: Record<string, unknown>;
  }>;
}

export interface ChartContextDTO {
  symbol: string;
  exchange: string;
  timeframe: string;
  chart_type?: string;
  selected_indicators: string[];
  indicator_values: Array<{
    name: string;
    value?: number | null;
    signal?: string | null;
    params: Record<string, unknown>;
  }>;
  active_drawings: Array<Record<string, unknown>>;
  latest_candle?: {
    open_time?: number | null;
    open?: number | null;
    high?: number | null;
    low?: number | null;
    close?: number | null;
    volume?: number | null;
  } | null;
  frontend_context_version: string;
}

// ── API calls ────────────────────────────────────────────────────────────────

async function aiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
    ...(options.headers as Record<string, string> || {}),
  };

  const resp = await fetch(url, { ...options, headers });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw createApiError("ai", resp.status, errorData, { endpoint: path });
  }

  return resp.json();
}

export async function aiHealth(): Promise<AIHealthResponse> {
  return aiFetch<AIHealthResponse>("/ai/health");
}

export async function aiChat(
  request: AIChatRequest,
): Promise<AIChatResponse> {
  return aiFetch<AIChatResponse>("/ai/chat", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function aiListSessions(): Promise<{
  sessions: AISessionResponse[];
}> {
  return aiFetch("/ai/sessions");
}

export async function aiCreateSession(params: {
  title?: string;
  mode?: "ask" | "interact";
  symbol?: string;
  timeframe?: string;
  exchange?: string;
}): Promise<AISessionResponse> {
  return aiFetch<AISessionResponse>("/ai/sessions", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function aiGetSessionMessages(
  sessionId: string,
): Promise<{ messages: AIMessageResponse[] }> {
  return aiFetch(`/ai/sessions/${sessionId}/messages`);
}

export async function aiDeleteSession(
  sessionId: string,
): Promise<{ deleted: boolean; session_id: string }> {
  return aiFetch(`/ai/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

/**
 * Persist a non-LLM message (e.g. tour recap) to the server so it
 * survives a page reload. Returns the stored message.
 */
export async function aiPersistSessionMessage(
  sessionId: string,
  params: { role: "assistant" | "user" | "system"; content: string; metadata?: Record<string, unknown> },
): Promise<{ message: AIMessageResponse }> {
  return aiFetch(`/ai/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function aiSubmitChartContext(
  context: ChartContextDTO,
): Promise<{ snapshot_id?: string; context: ChartContextDTO }> {
  return aiFetch("/ai/chart-context", {
    method: "POST",
    body: JSON.stringify(context),
  });
}

export async function aiValidateActions(
  actions: AIChartAction[],
): Promise<{
  valid: boolean;
  errors: string[];
  warnings: string[];
  validated_actions: AIChartAction[];
}> {
  return aiFetch("/ai/chart-actions/validate", {
    method: "POST",
    body: JSON.stringify({ actions }),
  });
}

export async function aiActionCatalog(): Promise<AiActionCatalog> {
  return aiFetch<AiActionCatalog>("/ai/actions/catalog");
}

// ── Streaming ───────────────────────────────────────────────────────────────

export interface AIChatStreamEvent {
  content?: string;
  error?: string;
  done?: boolean;
  event?: string;
  guard_warnings?: string[];
}

/**
 * Stream AI chat response token-by-token via SSE.
 *
 * Returns an object with:
 * - stream: AsyncGenerator yielding parsed AIChatStreamEvent objects
 * - abort: () => void to cancel the fetch
 */
export function aiChatStream(
  request: AIChatRequest,
): {
  stream: AsyncGenerator<AIChatStreamEvent, void, unknown>;
  abort: () => void;
} {
  const url = `${API_BASE_URL}/ai/chat/stream`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
  };

  const controller = new AbortController();

  const stream = async function* () {
    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    if (!resp.ok) {
      const errorData = await resp.json().catch(() => ({}));
      yield {
        error: `HTTP ${resp.status}: ${errorData?.detail || resp.statusText}`,
        done: true,
      };
      return;
    }

    const reader = resp.body?.getReader();
    if (!reader) {
      yield { error: "No response body", done: true };
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE data lines
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const parsed = JSON.parse(line.slice(6)) as AIChatStreamEvent;
            yield parsed;
            if (parsed.done) return;
          } catch {
            // Skip unparseable events
          }
        }
      }
    }

    // Process remaining buffer
    if (buffer.startsWith("data: ")) {
      try {
        const parsed = JSON.parse(buffer.slice(6)) as AIChatStreamEvent;
        yield parsed;
      } catch {
        // Skip
      }
    }
  }();

  return {
    stream,
    abort: () => controller.abort(),
  };
}

// ── Mock fallback ────────────────────────────────────────────────────────────

export function shouldUseMockAi(): boolean {
  return DATA_SOURCE === "mock";
}

// ── Message rating ───────────────────────────────────────────────────────────

export async function rateMessage(messageId: string, rating: 1 | -1): Promise<void> {
  const url = `${API_BASE_URL}/ai/messages/${messageId}/rate`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
  };
  await fetch(url, {
    method: "PATCH",
    headers,
    body: JSON.stringify({ rating }),
  });
}

// ── Tour persistence ─────────────────────────────────────────────────────────

/** Save a completed tour plan for replay */
export async function saveTourPlan(
  sessionId: string,
  plan: {
    tour_id: string;
    title: string;
    summary?: string;
    chart_snapshot?: Record<string, unknown> | null;
    steps: Array<unknown>;
  },
): Promise<{ plan_id: string; status: string }> {
  const url = `${API_BASE_URL}/ai/tours/save`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
  };
  const resp = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({ session_id: sessionId, ...plan }),
  });
  return resp.json();
}

/** Get tour history for a session */
export async function getTourHistory(sessionId: string): Promise<Array<{
  id: string;
  tour_id: string;
  title: string;
  summary?: string;
  status: string;
  created_at?: string;
  completed_at?: string;
}>> {
  const url = `${API_BASE_URL}/ai/tours/history/${sessionId}`;
  const headers: Record<string, string> = {
    ...getAuthHeaders(),
  };
  const resp = await fetch(url, { headers });
  return resp.json();
}

/** Get a full tour plan for replay */
export async function getTourPlan(planId: string): Promise<{
  id: string;
  tour_id: string;
  title: string;
  summary?: string;
  steps: Array<unknown>;
  chart_snapshot?: Record<string, unknown> | null;
  status: string;
  created_at?: string;
  completed_at?: string;
}> {
  const url = `${API_BASE_URL}/ai/tours/${planId}`;
  const headers: Record<string, string> = {
    ...getAuthHeaders(),
  };
  const resp = await fetch(url, { headers });
  return resp.json();
}
