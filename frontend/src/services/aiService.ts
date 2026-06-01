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
  chart_actions?: AIChartAction[] | null;
  grounded_context_used: boolean;
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

// ── Mock fallback ────────────────────────────────────────────────────────────

export function shouldUseMockAi(): boolean {
  return DATA_SOURCE === "mock";
}
