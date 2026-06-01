import { DATA_SOURCE } from "@/constants/env";
import { apiGet, buildQuery } from "@/services/apiClient";
import { isUnavailableApiPayload } from "@/services/apiMetadata";
import { makeClientCacheKey, withClientCache } from "@/services/clientCache";
import { getMockDataAdapter } from "@/services/dataSourceAdapter";
import type { MarketMetrics, TopMover } from "@/types";

const MARKET_OVERVIEW_CACHE_MS = 30_000;
const TOP_MOVERS_CACHE_MS = 15_000;
const mockDataAdapter = getMockDataAdapter();

function unwrapData<T>(payload: T | { data: T }): T {
  if (payload && typeof payload === "object" && "data" in payload) {
    return (payload as { data: T }).data;
  }
  return payload as T;
}

function normalizeMover(item: Partial<TopMover>): TopMover {
  return {
    symbol: item.symbol || "",
    price: Number(item.price || 0),
    change_24h_pct: Number(item.change_24h_pct || 0),
    volume_24h: Number(item.volume_24h || 0),
    rank: item.rank,
  };
}

export async function fetchMarketOverview(): Promise<MarketMetrics | null> {
  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.fetchMarketOverview();
    return payload.data;
  }
  const payload = await withClientCache(
    "market-overview",
    MARKET_OVERVIEW_CACHE_MS,
    () => apiGet<MarketMetrics | { data: MarketMetrics }>("/market/overview"),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return null;
  return unwrapData(payload);
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
