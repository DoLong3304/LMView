import { DATA_SOURCE } from "@/constants/env";
import { apiGet, buildQuery } from "@/services/apiClient";
import { isUnavailableApiPayload } from "@/services/apiMetadata";
import { makeClientCacheKey, withClientCache } from "@/services/clientCache";
import { getMockDataAdapter } from "@/services/dataSourceAdapter";
import type { MarketMetrics, MarketOverview, SectorPerformance, TopMover } from "@/types";

const MARKET_OVERVIEW_CACHE_MS = 30_000;
const TOP_MOVERS_CACHE_MS = 15_000;
const mockDataAdapter = getMockDataAdapter();

function normalizeMover(item: Partial<TopMover>): TopMover {
  return {
    symbol: item.symbol || "",
    name: item.name,
    price: Number(item.price || 0),
    change_24h_pct: Number(item.change_24h_pct || 0),
    change_7d_pct: item.change_7d_pct,
    change_30d_pct: item.change_30d_pct,
    volume_24h: Number(item.volume_24h || 0),
    market_cap: item.market_cap,
    rank: item.rank,
    exchange: item.exchange,
  };
}

export async function fetchMarketOverview(): Promise<MarketOverview | null> {
  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.fetchMarketOverview();
    return payload.data;
  }
  const payload = await withClientCache(
    "market-overview",
    MARKET_OVERVIEW_CACHE_MS,
    () => apiGet<MarketOverview | { market_summary: MarketMetrics }>("/market/overview"),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return null;
  // If response is wrapped with market_summary, wrap it
  if (payload && typeof payload === "object" && "market_summary" in payload && !("timestamp" in payload)) {
    const p = payload as { market_summary: MarketMetrics };
    return {
      timestamp: new Date().toISOString(),
      timeframe: "24h",
      market_summary: p.market_summary,
      top_gainers: [],
      top_losers: [],
      most_volatile: [],
      highest_volume: [],
      trending_news: [],
      sector_performance: {},
      heatmap_data: [],
      indicators_summary: {
        total_symbols: 0,
        avg_rsi: 50,
        overbought_count: 0,
        oversold_count: 0,
        bullish_macd_count: 0,
        bearish_macd_count: 0,
      },
      metadata: {
        source: "unknown",
        data_sources: [],
        is_placeholder: true,
        computed_at: new Date().toISOString(),
        gold_tables_healthy: false,
        warning: "Using legacy API format",
      },
    };
  }
  return payload as MarketOverview;
}

export async function fetchMarketMetrics(): Promise<MarketMetrics | null> {
  const overview = await fetchMarketOverview();
  return overview?.market_summary || null;
}

export async function fetchTopGainers(limit: number = 5): Promise<TopMover[]> {
  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.fetchTopGainers(limit);
    return payload.data;
  }
  const payload = await withClientCache(
    makeClientCacheKey(["market-gainers", limit]),
    TOP_MOVERS_CACHE_MS,
    () =>
      // P1 fix: dedicated endpoint /market/movers?category=gainer
      apiGet<{ category: string; data: TopMover[] }>(
        `/market/movers?${buildQuery({ category: "gainer", limit })}`,
      ),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  const data = Array.isArray(payload) ? payload : payload.data || [];
  return data.map(normalizeMover);
}

export async function fetchTopLosers(limit: number = 5): Promise<TopMover[]> {
  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.fetchTopLosers(limit);
    return payload.data;
  }
  const payload = await withClientCache(
    makeClientCacheKey(["market-losers", limit]),
    TOP_MOVERS_CACHE_MS,
    () =>
      // P1 fix: dedicated endpoint /market/movers?category=loser
      apiGet<{ category: string; data: TopMover[] }>(
        `/market/movers?${buildQuery({ category: "loser", limit })}`,
      ),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  const data = Array.isArray(payload) ? payload : payload.data || [];
  return data.map(normalizeMover);
}

export async function fetchSectorPerformance(): Promise<SectorPerformance[]> {
  const overview = await fetchMarketOverview();
  if (!overview?.sector_performance) return [];
  return Object.values(overview.sector_performance);
}

export async function fetchHeatmapData(limit: number = 50): Promise<import("@/types").HeatmapItem[]> {
  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.fetchHeatmapData(limit);
    return payload.data;
  }

  const payload = await withClientCache(
    makeClientCacheKey(["market-heatmap", limit]),
    MARKET_OVERVIEW_CACHE_MS,
    () => apiGet<{ data: import("@/types").HeatmapItem[] }>(`/market/heatmap?${buildQuery({ limit })}`),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  return payload.data || [];
}

// ============================================================================
// Dedicated Gold table endpoints (Task 1, v0.24.4)
// ----------------------------------------------------------------------------
// These are thin wrappers that hit the dedicated endpoints added in
// backend/api/market_overview.py. Each one queries ONE gold table and
// returns a flat response with a `data` field, so the Frontend can
// render directly without parsing a giant /overview blob.
// ============================================================================

/** Top volatile symbols from gold_volatility_ranking. */
export async function fetchVolatilityRanking(limit: number = 20): Promise<import("@/types").TopMover[]> {
  const payload = await withClientCache(
    makeClientCacheKey(["market-volatility", limit]),
    TOP_MOVERS_CACHE_MS,
    () => apiGet<{ data: import("@/types").TopMover[] }>(`/market/volatility?${buildQuery({ limit })}`),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  return (payload.data || []).map(normalizeMover);
}

/** BTC/ETH dominance and market summary from gold_market_dominance. */
export async function fetchMarketDominance(): Promise<MarketMetrics | null> {
  const payload = await withClientCache(
    "market-dominance",
    MARKET_OVERVIEW_CACHE_MS,
    () => apiGet<{ data: MarketMetrics }>("/market/dominance"),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return null;
  return payload?.data || null;
}

/**
 * Sector performance from gold_sector_performance.
 * Returns a list (not dict) of {sector, change_pct, volume, symbol_count}.
 */
export async function fetchSectors(): Promise<SectorPerformance[]> {
  const payload = await withClientCache(
    "market-sectors",
    MARKET_OVERVIEW_CACHE_MS,
    () => apiGet<{ data: SectorPerformance[] }>("/market/sectors"),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  return payload?.data || [];
}

/**
 * News sentiment from gold_news_sentiment_daily.
 * Returns per-symbol article counts and bullish/bearish breakdown.
 */
export interface NewsSentimentItem {
  symbol: string;
  article_count: number;
  avg_sentiment: number;
  bullish_count: number;
  bearish_count: number;
}

export async function fetchNewsSentiment(
  days: number = 7,
  limit: number = 20,
): Promise<NewsSentimentItem[]> {
  const payload = await withClientCache(
    makeClientCacheKey(["market-news-sentiment", days, limit]),
    MARKET_OVERVIEW_CACHE_MS,
    () => apiGet<{ data: NewsSentimentItem[] }>(`/market/news-sentiment?${buildQuery({ days, limit })}`),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  return payload?.data || [];
}

/** Momentum / RSI / MACD summary from gold_momentum_indicators. */
export interface IndicatorsSummary {
  total_symbols: number;
  avg_rsi: number;
  overbought_count: number;
  oversold_count: number;
  bullish_macd_count: number;
  bearish_macd_count: number;
}

export async function fetchIndicators(): Promise<IndicatorsSummary | null> {
  const payload = await withClientCache(
    "market-indicators",
    MARKET_OVERVIEW_CACHE_MS,
    () => apiGet<{ data: IndicatorsSummary }>("/market/indicators"),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return null;
  return payload?.data || null;
}

// ============================================================================
// News ↔ Price Impact (Task 4, v0.24.5)
// ---------------------------------------------------------------------------
// Each row represents a news article × symbol with measured price impact
// at t+1h, t+4h and t+24h. Used to render a "News Impact" panel and to
// overlay markers on the candlestick chart. Sort order on the server is
// by ABS(impact_score) DESC, so the first N items are the most
// market-moving news in the window.
// ============================================================================

export interface NewsImpactItem {
  news_id: number;
  symbol: string;
  exchange: string;
  published_at: string;       // ISO-8601
  headline: string;
  url: string;
  source: string;
  sentiment: number | null;   // -1.0..+1.0
  price_at_news: number | null;
  price_1h_after: number | null;
  price_4h_after: number | null;
  price_24h_after: number | null;
  change_1h_pct: number | null;
  change_4h_pct: number | null;
  change_24h_pct: number | null;
  impact_score: number | null;
  computed_at: string;
}

export interface NewsImpactFilter {
  days?: number;            // 1..90, default 7
  limit?: number;           // 1..200, default 50
  symbol?: string;          // e.g. "BTCUSDT"
  minImpactPct?: number;    // 0..100, default 0
  exchange?: string;        // default "binance"
}

export async function fetchNewsPriceImpact(
  filter: NewsImpactFilter = {},
): Promise<NewsImpactItem[]> {
  const params = buildQuery({
    days: filter.days ?? 7,
    limit: filter.limit ?? 50,
    symbol: filter.symbol,
    min_impact_pct: filter.minImpactPct ?? 0,
    exchange: filter.exchange ?? "binance",
  });
  // Higher cache (5 min) — this is a slow-changing analytical view,
  // not a real-time panel. Stale-while-revalidate is fine.
  const payload = await withClientCache(
    `market-news-impact:${params}`,
    5 * 60_000,
    () => apiGet<{ data: NewsImpactItem[]; count: number }>(`/market/news-impact?${params}`),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  return payload?.data ?? [];
}

/** Convenience: highest-impact news for a single symbol (used by the
 * chart's "News" tab overlay). Defaults to 7d window, 20 items.
 */
export async function fetchNewsPriceImpactForSymbol(
  symbol: string,
  days: number = 7,
  limit: number = 20,
): Promise<NewsImpactItem[]> {
  return fetchNewsPriceImpact({ symbol, days, limit });
}

// ============================================================================
// Liquidity Heatmap (Task 5, v0.24.5)
// ---------------------------------------------------------------------------
// Returns a flat list of (timestamp_ms, price_bucket, quantity) rows
// per side (bid + ask). The client pivots this into a 2-D grid for
// rendering. Bucket index 0 = at mid-price; 1 = first level away;
// etc. Quantities are summed within each minute × bucket cell.
// ============================================================================

export interface HeatmapRow {
  0: number;   // timestamp_ms
  1: number;   // price_bucket
  2: number;   // quantity
}

export interface HeatmapData {
  bid: HeatmapRow[];
  ask: HeatmapRow[];
}

export interface HeatmapFilter {
  symbol: string;            // e.g. "BTCUSDT" (required)
  hours?: number;            // 1..24, default 4
  bucketCount?: number;      // 1..100, default 20
  exchange?: string;         // default "binance"
}

export interface HeatmapResponse {
  data: HeatmapData;
  matrix_shape: { time_buckets: number; price_buckets_per_side: number };
  filter: { symbol: string; hours: number; bucket_count: number; exchange: string };
}

export async function fetchLiquidityHeatmap(
  filter: HeatmapFilter,
): Promise<HeatmapResponse | null> {
  const params = buildQuery({
    symbol: filter.symbol,
    hours: filter.hours ?? 4,
    bucket_count: filter.bucketCount ?? 20,
    exchange: filter.exchange ?? "binance",
  });
  // 30s cache — heatmap is a live visualization but the underlying
  // bucket aggregation is minute-grained so further refreshes don't
  // add information.
  const payload = await withClientCache(
    `liquidity-heatmap:${params}`,
    30_000,
    () => apiGet<HeatmapResponse>(`/market/liquidity-heatmap?${params}`),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return null;
  return payload ?? null;
}
