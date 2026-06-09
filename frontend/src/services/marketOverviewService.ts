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
    return payload.data as unknown as MarketOverview;
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
      apiGet<TopMover[] | { data?: TopMover[]; gainers?: TopMover[] }>(
        `/market/gainers?${buildQuery({ limit })}`,
      ),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  const items = Array.isArray(payload) ? payload : payload.gainers || payload.data || [];
  return items.map(normalizeMover);
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
      apiGet<TopMover[] | { data?: TopMover[]; losers?: TopMover[] }>(
        `/market/losers?${buildQuery({ limit })}`,
      ),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  const items = Array.isArray(payload) ? payload : payload.losers || payload.data || [];
  return items.map(normalizeMover);
}

export async function fetchSectorPerformance(): Promise<SectorPerformance[]> {
  const overview = await fetchMarketOverview();
  if (!overview?.sector_performance) return [];
  return Object.values(overview.sector_performance);
}

export async function fetchHeatmapData(limit: number = 50): Promise<import("@/types").HeatmapItem[]> {
  const payload = await withClientCache(
    makeClientCacheKey(["market-heatmap", limit]),
    MARKET_OVERVIEW_CACHE_MS,
    () => apiGet<{ data: import("@/types").HeatmapItem[] }>(`/market/heatmap?${buildQuery({ limit })}`),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  return payload.data || [];
}
