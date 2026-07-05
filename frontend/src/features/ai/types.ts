/**
 * AI chat types shared across AI feature components.
 */

export interface AiMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  /** Mode that was active when this message was created */
  mode?: "ask" | "interact";
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
  /** Phase B: structured response sections for expandable rendering */
  response_sections?: Array<{ title: string; content: string }> | null;
  /** Phase B: full KB chunk data for expandable knowledge cards */
  knowledge_chunks?: Array<{
    text: string;
    title: string;
    source: string;
    source_type?: string;
    credibility_level?: string;
    score: number;
    heading?: string;
  }> | null;
}

/**
 * Tour step action for Interact mode guided analysis.
 * Legacy single-action format.
 */
export interface TourStepAction {
  action_type: string;
  params: Record<string, unknown>;
  explanation: string;
  target_selector?: string | null;
  requires_approval?: boolean;
}

/**
 * Phase E: Multi-action guided action within a walkthrough step.
 */
export interface GuidedAction {
  type: string;
  params: Record<string, unknown>;
  requires_approval?: boolean;
}

/**
 * Phase E: Walkthrough step with multiple simultaneous actions.
 */
export interface WalkthroughStep {
  explanation: string;
  actions: GuidedAction[];
  keep_effects?: boolean;
  chart_freeze?: boolean;
}

/**
 * Tour plan for Interact mode guided analysis.
 */
export interface TourPlan {
  tour_id: string;
  title: string;
  steps: TourStepAction[] | WalkthroughStep[];
  summary: string;
  chart_snapshot?: Record<string, unknown> | null;
}

/**
 * Normalize tour plan steps to WalkthroughStep[] format.
 * Handles both legacy (TourStepAction) and new (WalkthroughStep) formats.
 */
export function normalizeTourSteps(steps: TourStepAction[] | WalkthroughStep[]): WalkthroughStep[] {
  if (!steps || steps.length === 0) return [];
  // Check if first step uses new format (has `actions` array with `type`)
  const first = steps[0] as unknown as Record<string, unknown>;
  if (first.actions && Array.isArray(first.actions)) {
    // Already new format
    return steps as WalkthroughStep[];
  }
  // Legacy format — convert
  return (steps as TourStepAction[]).map((s: TourStepAction) => ({
    explanation: s.explanation,
    keep_effects: true,
    chart_freeze: true,
    actions: [{
      type: s.action_type,
      params: s.params || {},
      requires_approval: s.requires_approval ?? false,
    }],
  }));
}

/**
 * Normalize a tour_plan from API response to consistent format.
 */
export function normalizeTourPlan(plan: Record<string, unknown> | null | undefined): TourPlan | null {
  if (!plan) return null;
  const steps = plan.steps as TourStepAction[] | WalkthroughStep[] | undefined;
  if (!steps) return plan as unknown as TourPlan;
  return {
    ...plan,
    steps: normalizeTourSteps(steps),
  } as TourPlan;
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
  /** User's IANA timezone for temporal reasoning (e.g., "Asia/Ho_Chi_Minh") */
  user_timezone?: string;
  frontend_context_version: string;
}

export type { AiMode, LocalAiHelpSession } from "@/types";
