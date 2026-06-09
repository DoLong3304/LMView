import { DATA_SOURCE } from "@/constants/env";
import { apiGet, buildQuery } from "@/services/apiClient";
import { isUnavailableApiPayload } from "@/services/apiMetadata";
import { makeClientCacheKey, withClientCache } from "@/services/clientCache";
import { getMockDataAdapter } from "@/services/dataSourceAdapter";
import type { EnhancedWatchlistItem, WatchlistFilter, WatchlistSortKey } from "@/types";

const SCREENER_CACHE_MS = 15_000;
const WATCHLIST_CACHE_MS = 10_000;
const mockDataAdapter = getMockDataAdapter();

export interface ScreenerFilterParams {
  trend?: "bullish" | "bearish" | "neutral";
  rsiMin?: number;
  rsiMax?: number;
  priceMin?: number;
  priceMax?: number;
  volumeMin?: number;
  changeMin?: number;
  changeMax?: number;
  marketCapMin?: number;
  sortBy?: "volume_24h" | "change_24h" | "price" | "rsi" | "market_cap";
  sortDir?: "asc" | "desc";
  limit?: number;
}

export interface ScreenerResult {
  timestamp: string;
  filters: Record<string, any>;
  count: number;
  data: ScreenerSymbol[];
}

export interface ScreenerSymbol {
  symbol: string;
  exchange?: string;
  price: number;
  change_24h: number;
  change_7d?: number;
  volume_24h: number;
  market_cap?: number;
  rsi_14?: number;
  volatility_24h?: number;
  trend?: string;
  sma_20?: number;
  sma_50?: number;
  support?: number;
  resistance?: number;
}

export interface ScreenerPreset {
  id: string;
  name: string;
  description?: string;
  filters: ScreenerFilterParams;
}

export const SCREENER_PRESETS: ScreenerPreset[] = [
  {
    id: "oversold",
    name: "Oversold",
    description: "RSI below 30",
    filters: { rsiMin: 0, rsiMax: 30 },
  },
  {
    id: "overbought",
    name: "Overbought",
    description: "RSI above 70",
    filters: { rsiMin: 70, rsiMax: 100 },
  },
  {
    id: "highVolume",
    name: "High Volume",
    description: "Volume > 100M",
    filters: { volumeMin: 100_000_000 },
  },
  {
    id: "topGainers",
    name: "Top Gainers",
    description: "+5% or more 24h",
    filters: { changeMin: 5, changeMax: 100 },
  },
  {
    id: "topLosers",
    name: "Top Losers",
    description: "-5% or more 24h",
    filters: { changeMin: -100, changeMax: -5 },
  },
];

/** Convert internal WatchlistFilter to API params */
function filterToParams(filter: WatchlistFilter): ScreenerFilterParams {
  const params: ScreenerFilterParams = {};

  if (filter.trends?.length) {
    params.trend = filter.trends[0] as "bullish" | "bearish" | "neutral";
  }
  if (filter.rsiRange) {
    params.rsiMin = filter.rsiRange.min;
    params.rsiMax = filter.rsiRange.max;
  }
  if (filter.minPrice != null) params.priceMin = filter.minPrice;
  if (filter.maxPrice != null) params.priceMax = filter.maxPrice;
  if (filter.minVolume != null) params.volumeMin = filter.minVolume;
  if (filter.minMarketCap != null) params.marketCapMin = filter.minMarketCap;
  if (filter.changeRange) {
    params.changeMin = filter.changeRange.min;
    params.changeMax = filter.changeRange.max;
  }

  return params;
}

/** Convert ScreenerSymbol to EnhancedWatchlistItem */
function toWatchlistItem(s: ScreenerSymbol): EnhancedWatchlistItem {
  const change24h = s.change_24h ?? 0;
  const base = s.symbol.replace("USDT", "").replace("BTC", "").replace("ETH", "");
  return {
    symbol: s.symbol,
    name: base,
    rank: undefined,
    price: s.price ?? 0,
    change24h,
    change7d: s.change_7d,
    volume24h: s.volume_24h ?? 0,
    marketCap: s.market_cap,
    rsi14: s.rsi_14,
    rsiSignal: s.rsi_14
      ? s.rsi_14 > 70 ? "overbought" : s.rsi_14 < 30 ? "oversold" : "neutral"
      : undefined,
    trend: (s.trend as "bullish" | "bearish" | "neutral") ?? undefined,
    volatility24h: s.volatility_24h,
    change: change24h,
    color: change24h >= 0 ? "green" : "red",
  };
}

export async function fetchScreenerResults(
  filter: WatchlistFilter,
  sortBy: WatchlistSortKey = "volume24h",
  sortDir: "asc" | "desc" = "desc",
  limit: number = 50
): Promise<EnhancedWatchlistItem[]> {
  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.fetchScreenerResults(filter);
    return payload.data as EnhancedWatchlistItem[];
  }

  const params = filterToParams(filter);

  // Map sort key to API field
  const sortByMap: Record<string, string> = {
    volume24h: "volume_24h",
    change24h: "change_24h",
    change7d: "change_7d",
    price: "price",
    rsi14: "rsi",
    marketCap: "market_cap",
    volatility24h: "volatility",
    rank: "volume_24h",
    symbol: "symbol",
  };

  const query = buildQuery({
    trend: params.trend,
    rsi_min: params.rsiMin,
    rsi_max: params.rsiMax,
    price_min: params.priceMin,
    price_max: params.priceMax,
    volume_min: params.volumeMin,
    change_min: params.changeMin,
    change_max: params.changeMax,
    market_cap_min: params.marketCapMin,
    sort_by: sortByMap[sortBy] || "volume_24h",
    sort_dir: sortDir,
    limit,
  });

  const cacheKey = makeClientCacheKey(["screener", sortBy, sortDir, limit]);
  const payload = await withClientCache(
    cacheKey,
    SCREENER_CACHE_MS,
    () => apiGet<ScreenerResult>(`/screener/symbols?${query}`),
    { staleOnError: true },
  );

  if (isUnavailableApiPayload(payload)) return [];
  return (payload.data || []).map(toWatchlistItem);
}

export async function fetchWatchlistWithIndicators(
  symbols?: string[],
  includeIndicators: boolean = true
): Promise<EnhancedWatchlistItem[]> {
  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.fetchWatchlistWithIndicators(symbols);
    return payload.data as EnhancedWatchlistItem[];
  }

  const params = new URLSearchParams();
  if (symbols?.length) params.set("symbols", symbols.join(","));
  params.set("include_indicators", String(includeIndicators));

  const cacheKey = makeClientCacheKey([
    "watchlist-indicators",
    symbols?.join(",") || "all",
    includeIndicators,
  ]);
  const payload = await withClientCache(
    cacheKey,
    WATCHLIST_CACHE_MS,
    () => apiGet<{ count: number; data: ScreenerSymbol[] }>(`/screener/watchlist?${params}`),
    { staleOnError: true },
  );

  if (isUnavailableApiPayload(payload)) return [];
  return (payload.data || []).map(toWatchlistItem);
}

export async function fetchScreenerPresets(): Promise<ScreenerPreset[]> {
  if (DATA_SOURCE === "mock") {
    return SCREENER_PRESETS;
  }

  try {
    const payload = await apiGet<{ presets: ScreenerPreset[] }>("/screener/presets");
    return payload.presets || SCREENER_PRESETS;
  } catch {
    return SCREENER_PRESETS;
  }
}