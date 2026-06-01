/**
 * AI chat types shared across AI feature components.
 */

export interface AiMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  is_mock?: boolean;
  provider?: string | null;
  created_at?: string | null;
  warnings?: string[];
  suggested_actions?: string[] | null;
}

export interface AiChatState {
  sessionId: string | null;
  messages: AiMessage[];
  loading: boolean;
  error: string | null;
}

export interface ChartContextForAi {
  symbol: string;
  exchange: string;
  timeframe: string;
  chart_type?: string;
  selected_indicators: string[];
  latest_candle?: {
    open_time?: number;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    volume?: number;
  } | null;
  frontend_context_version: string;
}

export type { AiMode, LocalAiHelpSession } from "@/types";
