// ─────────────────────────────────────────────────────────────────────────────
// Shared type definitions for the trading dashboard frontend
// ─────────────────────────────────────────────────────────────────────────────

/** OHLCV candlestick data point (time in seconds for lightweight-charts) */
export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/** Raw candle from API (time may be in ms before conversion) */
export interface RawCandle {
  openTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/** 24h ticker snapshot */
export interface Ticker {
  symbol: string;
  price: number;
  change24h?: number;
  bid?: number;
  ask?: number;
  volume?: number;
  event_time?: number;
  activity_score?: number;
}

/** Single order book price level */
export interface OrderBookEntry {
  price: number;
  amount: number;
  total: number;
}

/** Full order book snapshot */
export interface OrderBookData {
  bids: OrderBookEntry[];
  asks: OrderBookEntry[];
  spread: number;
  best_bid?: number;
  best_ask?: number;
}

/** Single trade */
export interface Trade {
  time: number;
  price: number;
  volume: number;
  side: "buy" | "sell";
}

/** News item */
export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  url: string;
  source: string;
  image_url?: string;
  published_at: string;
  sentiment_label: string;
  sentiment_score: number;
  symbols: string[];
}

export interface NewsArticle {
  id: string;
  source: string;
  title: string;
  summary: string;
  url: string;
  author?: string;
  published_at: number | string;
  image_url?: string;
  tags: string[];
  symbols: string[];
  sentiment_score: number;
  sentiment_label: string;
  language?: string;
  region?: string;
  symbolsMentioned?: string[];
}

export interface TrendingSymbol {
  symbol: string;
  mention_count: number;
  avg_sentiment: number;
}

export interface NewsFilters {
  limit?: number;
  hours?: number;
  source?: string;
  symbol?: string;
  query?: string;
}

export interface MarketMetrics {
  total_symbols: number;
  total_market_cap: number;
  total_volume_24h: number;
  btc_dominance: number;
  eth_dominance?: number;
  btc_price: number;
}

export interface TopMover {
  symbol: string;
  price: number;
  change_24h_pct: number;
  volume_24h: number;
  rank?: number;
}

/** Symbol info from /api/symbols */
export interface SymbolInfo {
  symbol: string;
  name?: string;
  type?: string;
}

/** Symbol metadata (icon, name, category) */
export interface SymbolMeta {
  symbol: string;
  icon: string;
  category: string;
  name: string;
  logoUrl?: string;
}

/** Watchlist item for sidebar */
export interface WatchlistItem {
  symbol: string;
  price: number;
  change: number;
  activityScore?: number;
  volume?: number;
  color: "green" | "red" | "gray";
}

/** Historical date range selection */
export interface HistoricalRange {
  startMs: number;
  endMs: number;
}

/** System health API response */
export interface HealthData {
  status: string;
  checks?: Record<string, string>;
  latency_ms?: Record<string, number>;
  uptime_sec?: number;
  checked_at?: string;
  total_latency_ms?: number;
  api_rtt_ms?: number;
}

/** Flexible per-indicator settings (SMA, EMA, RSI, MFI, Volume, etc.) */
export interface IndicatorSettings {
  visible: boolean;
  period?: number;
  color?: string;
  lineWidth?: number;
  type?: string;
  overbought?: number;
  oversold?: number;
  upColor?: string;
  downColor?: string;
  [key: string]: unknown;
}

/** Latest indicator snapshot from backend WebSocket stream. */
export interface IndicatorStreamSnapshot {
  symbol: string;
  exchange: string;
  interval: string;
  timestamp?: number | null;
  indicators: Record<string, number>;
}

/** Point on the chart canvas for drawing tools (pixel space - for rendering only) */
export interface DrawingPoint {
  x: number;
  y: number;
}

/** Data-space point (time in seconds, price in actual value) - SOURCE OF TRUTH */
export interface DataPoint {
  time: number;  // Unix timestamp in seconds (lightweight-charts convention)
  price: number; // Actual price value
}

/** Drawing object - uses data-space coordinates as source of truth */
export interface Drawing {
  id: string | number;
  tool: string;

  // Data-space coordinates (SOURCE OF TRUTH)
  dataPoints?: DataPoint[];

  // Legacy pixel-space (deprecated, only for backward compatibility)
  start?: DrawingPoint;
  end?: DrawingPoint;
  points?: DrawingPoint[];

  // Drawing properties
  settings?: Record<string, any>;
  text?: string;
  locked?: boolean;
  hidden?: boolean;
}

/** Crosshair tooltip data */
export interface TooltipData {
  visible: boolean;
  x: number;
  y: number;
  time?: number;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
}

/** User session */
export interface UserSession {
  email: string;
  name: string;
}

/** Auth operation result */
export interface AuthResult {
  success: boolean;
  error?: string;
}

/** Supported timeframe keys: lowercase for API calls, labels live in constants/timeframes.ts. */
export type TimeframeKey = "1s" | "1m" | "5m" | "15m" | "1h" | "4h" | "1d" | "1w";
export type Timeframe = TimeframeKey;

export type ChartType = "candles" | "line" | "area" | "bars";

export interface FeatureAvailability {
  available: boolean;
  reason?: string;
  requiresLogin?: boolean;
  requiresAdmin?: boolean;
}

export type SettingsTab =
  | "account"
  | "notifications"
  | "customization"
  | "aiHelper"
  | "about"
  | "debug"
  | "adminAccounts";

export type AiMode = "ask" | "interact";

export interface LocalAiHelpSession {
  id: string;
  userId: string;
  title: string;
  mode: AiMode;
  messages: Array<{
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    created_at?: string | null;
    warnings?: string[];
    token_input?: number | null;
    token_output?: number | null;
    estimated_cost_usd?: number | null;
  }>;
  message_count?: number;
  symbol?: string;
  timeframe?: string;
  exchange?: string;
  source?: "local" | "api";
  created_at: string;
  updated_at: string;
}

/** Watchlist filter mode */
export type WatchlistFilter = "all" | "starred";

/** Drawing tool types */
export type DrawingTool = "cursor" | "trendline" | "horizontal" | "circle" | "rectangle" | "triangle" | "text" | "ruler";

/** Command types for undo/redo system */
export type CommandType = 'add' | 'delete' | 'update' | 'move' | 'batch';

/** Command for undo/redo history */
export interface Command {
  type: CommandType;
  timestamp: number;
  drawingId?: string | number;
  drawingIds?: (string | number)[]; // For batch operations
  before?: Drawing | Drawing[]; // State before change
  after?: Drawing | Drawing[];  // State after change
  description?: string; // Human-readable description
}

/** History state for undo/redo */
export interface HistoryState {
  commands: Command[];
  currentIndex: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 0: Data freshness and metadata types (shared with backend contracts)
// ─────────────────────────────────────────────────────────────────────────────

/** Reusable freshness metadata for AI-critical data responses */
export interface DataFreshness {
  source: string;
  exchange?: string | null;
  event_time?: number | null;
  last_updated?: string | null;
  freshness_seconds?: number | null;
  is_stale: boolean;
  is_fallback: boolean;
  warnings: string[];
}

/** Extended data metadata for provenance */
export interface DataMetadata {
  data_type: string; // live, cached, computed, synthetic, placeholder
  source: string;
  exchange?: string | null;
  is_synthetic: boolean;
  is_true_data: boolean;
  freshness?: DataFreshness | null;
  persisted: boolean;
}

/** User session (backend auth response) */
export interface UserSession {
  id: string;
  email: string;
  display_name: string;
  role: string;
  preferred_language?: string | null;
  is_active: boolean;
  session_token?: string;
  expires_at?: string;
}
