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
  // Overall Market
  total_symbols: number;
  total_market_cap: number;
  total_volume_24h: number;
  btc_dominance: number;
  eth_dominance?: number;
  fear_greed_index?: number;

  // BTC Metrics
  btc_price: number;
  btc_change_24h?: number;
  btc_high_24h?: number;
  btc_low_24h?: number;

  // ETH Metrics
  eth_price?: number;
  eth_change_24h?: number;

  // Market Breadth
  advancing_count?: number;
  declining_count?: number;
  new_highs_24h?: number;
  new_lows_24h?: number;

  // Volume Metrics
  avg_volume_24h?: number;
  btc_volume_24h?: number;
  stablecoin_volume_24h?: number;
}

export interface TopMover {
  symbol: string;
  name?: string;
  price: number;
  change_24h_pct: number;
  change_7d_pct?: number;
  change_30d_pct?: number;
  volume_24h: number;
  market_cap?: number;
  rank?: number;
  exchange?: string;
}

export interface SectorPerformance {
  sector: string;
  name: string;
  change_24h_pct: number;
  change_7d_pct?: number;
  market_cap: number;
  top_coins: string[];
}

export interface MarketOverview {
  timestamp: string;
  timeframe: string;
  market_summary: MarketMetrics;
  top_gainers: TopMover[];
  top_losers: TopMover[];
  most_volatile: TopMover[];
  highest_volume: TopMover[];
  trending_news: TrendingSymbol[];
  sector_performance: Record<string, SectorPerformance>;
  heatmap_data: HeatmapItem[];
  indicators_summary: IndicatorsSummary;
  metadata: MarketOverviewMetadata;
}

export interface HeatmapItem {
  symbol: string;
  change_pct: number;
  price: number;
  volume_24h: number;
  market_cap: number;
  volatility?: number;
}

export interface IndicatorsSummary {
  total_symbols: number;
  avg_rsi: number;
  overbought_count: number;
  oversold_count: number;
  bullish_macd_count: number;
  bearish_macd_count: number;
}

export interface MarketOverviewMetadata {
  source: string;
  data_sources: string[];
  is_placeholder: boolean;
  computed_at: string;
  gold_tables_healthy: boolean;
  warning?: string | null;
}

export type MarketPeriod = "1h" | "24h" | "7d" | "30d";

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
  tool: DrawingTool | string;

  // Data-space coordinates (SOURCE OF TRUTH)
  dataPoints?: DataPoint[];

  // Legacy pixel-space (deprecated, only for backward compatibility)
  start?: DrawingPoint;
  end?: DrawingPoint;
  points?: DrawingPoint[];

  // Drawing properties
  settings?: DrawingSettings;
  text?: string;
  locked?: boolean;
  hidden?: boolean;
}

/** Drawing tool settings */
export interface DrawingSettings {
  color?: string;
  lineWidth?: number;
  lineStyle?: "solid" | "dashed" | "dotted";
  dashArray?: string;
  showLabel?: boolean;
  showPrices?: boolean;
  showTimes?: boolean;
  fill?: boolean;
  fillColor?: string;
  fillOpacity?: number;
  fontSize?: number;
  fontFamily?: string;
  textColor?: string;
  backgroundColor?: string;
  // Fibonacci specific
  levels?: number[];
  // Gann specific
  angles?: number[];
  showGrid?: boolean;
  showMidlines?: boolean;
  showArcs?: boolean;
  showFans?: boolean;
  // Elliott specific
  waveType?: "impulse" | "corrective" | string;
  waveLabels?: string[];
  fiboLevels?: number[];
  // Pitchfork specific
  showMedian?: boolean;
  showExtensions?: boolean;
  showChannels?: boolean;
  // Extended settings
  extendLeft?: boolean;
  extendRight?: boolean;
  bold?: boolean;
  italic?: boolean;
  alignment?: "left" | "center" | "right";
  [key: string]: unknown;
}

/** Fibonacci level definition */
export interface FibonacciLevel {
  level: number;        // e.g., 0.236, 0.382, 0.618
  color: string;
  lineWidth: number;
  style: "solid" | "dashed" | "dotted";
  label?: string;
  show?: boolean;
}

/** Default Fibonacci levels */
export const FIBONACCI_RETRACEMENT_LEVELS: FibonacciLevel[] = [
  { level: 0, label: "0%", color: "#787B86", lineWidth: 1, style: "solid" },
  { level: 0.236, label: "23.6%", color: "#787B86", lineWidth: 1, style: "dashed" },
  { level: 0.382, label: "38.2%", color: "#7E8A93", lineWidth: 1, style: "dashed" },
  { level: 0.5, label: "50%", color: "#9E8C6D", lineWidth: 1, style: "dashed" },
  { level: 0.618, label: "61.8%", color: "#E7863D", lineWidth: 2, style: "solid" },
  { level: 0.786, label: "78.6%", color: "#7E8A93", lineWidth: 1, style: "dashed" },
  { level: 1, label: "100%", color: "#787B86", lineWidth: 1, style: "solid" },
  { level: 1.272, label: "127.2%", color: "#3D793D", lineWidth: 1, style: "solid" },
  { level: 1.618, label: "161.8%", color: "#3D793D", lineWidth: 2, style: "solid" },
];

/** Default Gann angles */
export const GANN_ANGLES = [
  { name: "1x1", angle: 45, label: "1x1 (45°)" },
  { name: "1x2", angle: 26.565, label: "1x2 (26.565°)" },
  { name: "1x3", angle: 18.435, label: "1x3 (18.435°)" },
  { name: "1x4", angle: 14.036, label: "1x4 (14.036°)" },
  { name: "1x8", angle: 7.125, label: "1x8 (7.125°)" },
  { name: "2x1", angle: 63.75, label: "2x1 (63.75°)" },
  { name: "3x1", angle: 71.565, label: "3x1 (71.565°)" },
  { name: "4x1", angle: 75.964, label: "4x1 (75.964°)" },
  { name: "8x1", angle: 82.875, label: "8x1 (82.875°)" },
];

/** Drawing preset/template interface */
export interface DrawingPreset {
  id: string;
  name: string;
  description: string;
  drawings: Drawing[];
  category: "bullish" | "bearish" | "neutral";
  applicableTo: "crypto" | "forex" | "stocks" | "all";
}

/** Tool category grouping for toolbar */
export interface DrawingCategory {
  id: string;
  labelKey: string;  // Using string to avoid circular dependency with i18n
  tools: DrawingTool[];
  children?: DrawingTool[];
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

export type ChartType = "candles" | "line" | "area" | "bars" | "heikinAshi" | "renko" | "lineBreak" | "kagi" | "pointFigure";

/** Chart type config */
export interface ChartTypeConfig {
  id: ChartType;
  labelKey: string;
  description: string;
  requiresTransformation: boolean;
  hasSettings: boolean;
}

export const CHART_TYPES: ChartTypeConfig[] = [
  { id: "candles", labelKey: "candlestick", description: "Standard candlestick", requiresTransformation: false, hasSettings: false },
  { id: "bars", labelKey: "bars", description: "OHLC bars", requiresTransformation: false, hasSettings: false },
  { id: "line", labelKey: "line", description: "Close line", requiresTransformation: false, hasSettings: false },
  { id: "area", labelKey: "area", description: "Filled area", requiresTransformation: false, hasSettings: false },
  { id: "heikinAshi", labelKey: "heikinAshi", description: "Smoothed candles", requiresTransformation: true, hasSettings: false },
  { id: "renko", labelKey: "renko", description: "Brick-based", requiresTransformation: true, hasSettings: true },
  { id: "lineBreak", labelKey: "lineBreak", description: "Price blocks", requiresTransformation: true, hasSettings: true },
  { id: "kagi", labelKey: "kagi", description: "Trend-based lines", requiresTransformation: true, hasSettings: true },
  { id: "pointFigure", labelKey: "pointFigure", description: "Box reversal", requiresTransformation: true, hasSettings: false },
];

/** Chart type settings for advanced chart types */
export interface ChartTypeSettings {
  // Renko
  brickSizeType?: "fixed" | "atr";
  fixedBrickSize?: number;
  atrPeriod?: number;
  renkoWicks?: boolean;
  // Kagi
  reversalPercent?: number;
  kagiUseClose?: boolean;
  // Line Break
  lookback?: number;
}

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
export type WatchlistTabFilter = "all" | "starred";
export type DrawingToolCategory =
  | "lines"          // Trend lines, Horizontal, Vertical, Angle
  | "shapes"         // Rectangle, Triangle, Ellipse, Arrow, etc.
  | "fibonacci"      // Retracement, Extension, Arcs, Spiral, Channel
  | "gann"           // Box, Fan, Square
  | "elliott"        // Elliott Wave tools
  | "pitchfork"      // Pitchfork variants
  | "text"           // Text, Callout, Rectangle Text, Note
  | "measurement"    // Ruler, Crossline, DateRange, PriceRange
  | "channels"       // Parallel, Regression, Pitchfork
  | "patterns"       // Harmonic, XABCD
  | "utility";       // Cursor, Magnet, Lock, Hide, Eraser

/** Drawing tool types - comprehensive list matching TradingView */
export type DrawingTool =
  // Lines
  | "cursor"
  | "crosshair"
  | "trendline"
  | "ray"
  | "extendedLine"
  | "horizontalRay"
  | "horizontal"
  | "vertical"
  | "angleLine"
  | "disjointAngle"

  // Shapes
  | "rectangle"
  | "rotatedRectangle"
  | "triangle"
  | "ellipse"
  | "arrow"
  | "polyline"
  | "parallelChannel"
  | "priceRange"

  // Fibonacci
  | "fibRetracement"
  | "fibExtension"
  | "fibChannel"
  | "fibArcs"
  | "fibSpiral"
  | "fibTimeZone"

  // Gann
  | "gannBox"
  | "gannFan"
  | "gannSquare"
  | "gannLine"

  // Elliott Wave
  | "elliottWave"
  | "harmonicABCD"
  | "xabcdPattern"

  // Pitchfork
  | "pitchfork"
  | "schiffPitchfork"
  | "modifiedPitchfork"
  | "insidePitchfork"

  // Text & Notes
  | "text"
  | "callout"
  | "note"
  | "balloon"
  | "anchoredText"

  // Measurement
  | "ruler"
  | "crossline"
  | "dateRange"
  | "priceRangeTool"
  | "riskReward"

  // Position & Forecast
  | "longPosition"
  | "shortPosition"
  | "forecast"

  // Utility
  | "magnet"
  | "lock"
  | "hide"
  | "eraser"
  | "clearAll";

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
// Phase E: Enhanced Watchlist & Screener
// ─────────────────────────────────────────────────────────────────────────────

/** Enhanced watchlist item with full technical data */
export interface EnhancedWatchlistItem {
  // Basic Info
  symbol: string;
  name?: string;
  rank?: number;

  // Price Data
  price: number;
  change24h: number;
  change7d?: number;
  change30d?: number;
  high24h?: number;
  low24h?: number;

  // Volume
  volume24h: number;
  volumeChange24h?: number;

  // Market Data
  marketCap?: number;
  marketCapRank?: number;

  // Technical Indicators
  rsi14?: number;
  rsiSignal?: "overbought" | "oversold" | "neutral";
  trend?: "bullish" | "bearish" | "neutral";
  sma20?: number;
  sma50?: number;
  ema20?: number;
  support?: number;
  resistance?: number;

  // Volatility
  volatility24h?: number;
  atr14?: number;

  // Classification
  category?: string;
  tags?: string[];
  isNewListing?: boolean;
  isActive?: boolean;

  // Legacy compatibility
  change: number;  // alias for change24h
  activityScore?: number;
  color: "green" | "red" | "gray";
}

export interface WatchlistColumn {
  id: string;
  labelKey: string;
  key: keyof EnhancedWatchlistItem;
  align: "left" | "right" | "center";
  width?: number;
  sortable: boolean;
  format?: "price" | "percent" | "volume" | "marketCap" | "number";
}

export const WATCHLIST_COLUMNS: WatchlistColumn[] = [
  { id: "rank", labelKey: "#", key: "rank", align: "center", width: 40, sortable: true },
  { id: "name", labelKey: "name", key: "symbol", align: "left", width: 120, sortable: true },
  { id: "price", labelKey: "price", key: "price", align: "right", width: 100, sortable: true, format: "price" },
  { id: "change24h", labelKey: "24h", key: "change24h", align: "right", width: 80, sortable: true, format: "percent" },
  { id: "change7d", labelKey: "7d", key: "change7d", align: "right", width: 80, sortable: true, format: "percent" },
  { id: "volume24h", labelKey: "24hVol", key: "volume24h", align: "right", width: 100, sortable: true, format: "volume" },
  { id: "marketCap", labelKey: "marketCap", key: "marketCap", align: "right", width: 100, sortable: true, format: "marketCap" },
  { id: "rsi14", labelKey: "RSI(14)", key: "rsi14", align: "right", width: 60, sortable: true },
  { id: "trend", labelKey: "trend", key: "trend", align: "center", width: 80, sortable: false },
  { id: "volatility", labelKey: "volatility", key: "volatility24h", align: "right", width: 80, sortable: true, format: "percent" },
];

export type WatchlistSortKey = "rank" | "symbol" | "price" | "change24h" | "change7d" | "volume24h" | "marketCap" | "rsi14" | "volatility24h";
export type WatchlistSortDir = "asc" | "desc";

export interface WatchlistFilter {
  categories?: string[];
  minVolume?: number;
  minPrice?: number;
  maxPrice?: number;
  minMarketCap?: number;
  rsiRange?: { min: number; max: number };
  changeRange?: { min: number; max: number };
  trends?: ("bullish" | "bearish" | "neutral")[];
  tags?: string[];
  isNewListing?: boolean;
  isActive?: boolean;
}

/** Screener filter presets */
export interface ScreenerPreset {
  id: string;
  name: string;
  description?: string;
  filters: WatchlistFilter;
}

export const SCREENER_PRESETS: ScreenerPreset[] = [
  {
    id: "oversold",
    name: "Oversold",
    description: "RSI below 30",
    filters: { rsiRange: { min: 0, max: 30 } },
  },
  {
    id: "overbought",
    name: "Overbought",
    description: "RSI above 70",
    filters: { rsiRange: { min: 70, max: 100 } },
  },
  {
    id: "highVolume",
    name: "High Volume",
    description: "Volume spike 24h",
    filters: { volumeChange24h: 100 } as any,
  },
  {
    id: "topGainers",
    name: "Top Gainers",
    description: "Top performers 24h",
    filters: { changeRange: { min: 5, max: 100 } },
  },
  {
    id: "topLosers",
    name: "Top Losers",
    description: "Worst performers 24h",
    filters: { changeRange: { min: -100, max: -5 } },
  },
];

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
