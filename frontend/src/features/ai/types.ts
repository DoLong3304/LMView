/**
 * AI chat types shared across AI feature components.
 */

export interface AiMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  is_mock?: boolean;
  provider?: string | null;
  model_name?: string | null;
  created_at?: string | null;
  warnings?: string[];
  suggested_actions?: string[] | null;
  tool_calls?: Array<{
    name: string;
    arguments?: Record<string, unknown>;
    reason?: string | null;
    requires_approval?: boolean;
  }> | null;
  chart_actions?: Array<{
    action_type: string;
    params: Record<string, unknown>;
    reason?: string | null;
    requires_approval: boolean;
  }> | null;
  /** Tour plan for Interact mode guided analysis */
  tour_plan?: TourPlan | null;
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
  /** News context summary */
  news_context?: import("@/services/aiService").NewsContextSummary | null;
}

/**
 * Tour step action for Interact mode guided analysis.
 */
export interface TourStepAction {
  action_type: string;
  params: Record<string, unknown>;
  explanation: string;
  target_selector?: string | null;
  requires_approval?: boolean;
}

/**
 * Tour plan for Interact mode guided analysis.
 */
export interface TourPlan {
  tour_id: string;
  title: string;
  steps: TourStepAction[];
  summary: string;
  chart_snapshot?: Record<string, unknown> | null;
}

/** Active tour execution state */
export interface TourExecutionState {
  plan: TourPlan;
  currentStep: number;
  active: boolean;
}

export interface AiChatState {
  sessionId: string | null;
  messages: AiMessage[];
  setMessages: React.Dispatch<React.SetStateAction<AiMessage[]>>;
  loading: boolean;
  error: string | null;
  /** Active tour execution, if any */
  activeTour: TourExecutionState | null;
}

export interface ChartContextForAi {
  symbol: string;
  exchange: string;
  timeframe: string;
  chart_type?: string;
  selected_indicators: string[];
  /** User locale for bi-lingual AI responses */
  language?: string;
  latest_candle?: {
    open_time?: number;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    volume?: number;
  } | null;
  /** Batch 4: last 20 candles as lightweight preview */
  recent_candles?: Array<{
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  /** Batch 4: actual indicator values from chart state */
  indicator_values?: Array<{
    name: string;
    value?: number | null;
    signal?: string | null;
    params: Record<string, unknown>;
  }>;
  frontend_context_version: string;
}

export type { AiMode, LocalAiHelpSession } from "@/types";
