/**
 * AI service — API calls for AI chat, sessions, and chart actions.
 *
 * Talks to /api/ai/* endpoints.
 * Real API helpers only. Mock and local help modes live at frontend service boundary.
 */

import { API_BASE_URL, DATA_SOURCE } from "@/constants/env";
import { getAuthHeaders } from "@/services/authService";

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
    throw new Error(
      errorData.detail || `AI API error: ${resp.status}`
    );
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

// ── Mock fallback ────────────────────────────────────────────────────────────

export function shouldUseMockAi(): boolean {
  return DATA_SOURCE === "mock";
}
