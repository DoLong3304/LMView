import { DATA_SOURCE } from "@/constants/env";
import { TIMEFRAMES, normalizeTimeframe } from "@/constants/timeframes";
import { apiGet, buildQuery, getWsBaseUrl } from "@/services/apiClient";
import { isUnavailableApiPayload } from "@/services/apiMetadata";
import { makeClientCacheKey, withClientCache } from "@/services/clientCache";
import { getMockDataAdapter } from "@/services/dataSourceAdapter";
import type { Candle, IndicatorStreamSnapshot, SymbolInfo, Ticker, Trade } from "@/types";

export { TIMEFRAMES };

// ── Shared real-time price map ────────────────────────────────────────────────
// Single source of truth for live prices across all UI components.
// Updated by subscribeAllTimeframes. Consumers read from here instead of
// polling /ticker every 5 seconds.
//
// Shape: { "BTCUSDT": { price, change24h, volume, activity_score } }
// Updated every 50ms via WebSocket trade stream.
const _livePriceMap: Record<string, {
  price: number;
  change24h: number;
  volume: number;
  activity_score: number;
  ts: number;
}> = {};

/**
 * Get all live prices. Callers should not mutate the returned object.
 */
export function getLivePrices(): Record<string, {
  price: number;
  change24h: number;
  volume: number;
  activity_score: number;
  ts: number;
}> {
  return _livePriceMap;
}

/**
 * Get live price for a single symbol. Returns undefined if not yet received.
 */
export function getLivePrice(symbol: string): {
  price: number;
  change24h: number;
  volume: number;
  activity_score: number;
  ts: number;
} | undefined {
  return _livePriceMap[symbol];
}

/**
 * Update live price for a symbol. Called internally by subscribeAllTimeframes.
 * Exported so App.tsx can read from the map instead of polling /ticker.
 */
export function updateLivePrice(
  symbol: string,
  price: number,
  change24h: number,
  volume: number,
  activity_score: number,
): void {
  _livePriceMap[symbol] = { price, change24h, volume, activity_score, ts: Date.now() };
}

const LIVE_TICK_CACHE_MS = 2_000;
const ORDER_BOOK_CACHE_MS = 1_000;
const CANDLE_LATEST_CACHE_MS = 3_000;
const CANDLE_HISTORY_CACHE_MS = 5 * 60_000;
const SYMBOLS_CACHE_MS = 10 * 60_000;
const mockDataAdapter = getMockDataAdapter();

interface RawKline {
  openTime: number;
  open: string | number;
  high: string | number;
  low: string | number;
  close: string | number;
  volume: string | number;
}

function mapRawToCandle(k: RawKline): Candle {
  return {
    time: Math.floor(k.openTime / 1000),
    open: parseFloat(String(k.open)),
    high: parseFloat(String(k.high)),
    low: parseFloat(String(k.low)),
    close: parseFloat(String(k.close)),
    volume: parseFloat(String(k.volume)),
  };
}

export async function fetchCandles(
  symbol: string,
  timeframe: string = "1h",
  limit: number = 200,
  endTime: number | null = null,
  exchange: string = "binance",
): Promise<Candle[]> {
  const interval = normalizeTimeframe(timeframe);

  if (DATA_SOURCE === "api") {
    const query = buildQuery({
      symbol,
      interval,
      limit,
      exchange,
      endTime: endTime ? endTime * 1000 : null,
    });
    const cacheKey = makeClientCacheKey([
      "klines",
      exchange,
      symbol,
      interval,
      limit,
      endTime ?? "latest",
    ]);

    return withClientCache(
      cacheKey,
      endTime ? CANDLE_HISTORY_CACHE_MS : CANDLE_LATEST_CACHE_MS,
      async () => {
        const raw = await apiGet<RawKline[] | { data?: RawKline[] }>(`/klines?${query}`);
        if (isUnavailableApiPayload(raw)) return [];
        const rows = Array.isArray(raw) ? raw : raw.data ?? [];
        return rows.map(mapRawToCandle);
      },
      { persist: Boolean(endTime), staleOnError: true },
    );
  }

  return mockDataAdapter.fetchCandles(symbol, interval, limit);
}

export function subscribeCandle(
  symbol: string,
  timeframe: string,
  onCandle: (candle: Candle) => void,
  exchange: string = "binance",
): () => void {
  const interval = normalizeTimeframe(timeframe);

  if (DATA_SOURCE === "api") {
    const wsUrl = `${getWsBaseUrl()}/stream/${interval}?${buildQuery({ symbol, exchange })}`;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (e: MessageEvent) => {
      const k: RawKline = JSON.parse(e.data as string);
      onCandle(mapRawToCandle(k));
    };
    ws.onerror = (err) => console.error("[WS error]", err);
    return () => ws.close();
  }

  return mockDataAdapter.subscribeCandle(symbol, interval, onCandle);
}

export type TimeframeCallback = (timeframe: string, candle: Candle) => void;

interface MultiTimeframeOptions {
  symbol: string;
  exchange?: string;
  onCandle: TimeframeCallback;
  onError?: (error: Event) => void;
}

interface IndicatorStreamOptions {
  symbol: string;
  timeframe: string;
  exchange?: string;
  onIndicator: (snapshot: IndicatorStreamSnapshot) => void;
  onError?: (error: Event) => void;
}

export function subscribeAllTimeframes(options: MultiTimeframeOptions): () => void {
  const { symbol, exchange = "binance", onCandle, onError } = options;

  if (DATA_SOURCE === "api") {
    const wsUrl = `${getWsBaseUrl()}/stream/all?${buildQuery({ symbol, exchange })}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (e: MessageEvent) => {
      const data: Record<string, RawKline> = JSON.parse(e.data as string);
      for (const [tf, kline] of Object.entries(data)) {
        if (kline) {
          onCandle(normalizeTimeframe(tf), mapRawToCandle(kline));
          // Also update shared live price map so App.tsx/toolbar read from here
          // instead of polling /ticker every 5s. This is the single source of truth.
          updateLivePrice(symbol, Number(kline.close), 0, Number(kline.volume) || 0, 0);
        }
      }
    };

    ws.onerror = onError || ((err) => console.error("[WS stream/all error]", err));
    return () => ws.close();
  }

  return mockDataAdapter.subscribeAllTimeframes(symbol, onCandle);
}

export function subscribeIndicatorStream(options: IndicatorStreamOptions): () => void {
  const {
    symbol,
    timeframe,
    exchange = "binance",
    onIndicator,
    onError,
  } = options;
  const interval = normalizeTimeframe(timeframe);

  if (DATA_SOURCE === "api") {
    const wsUrl = `${getWsBaseUrl()}/stream/indicators/${interval}?${buildQuery({ symbol, exchange })}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (e: MessageEvent) => {
      const payload: IndicatorStreamSnapshot = JSON.parse(e.data as string);
      onIndicator(payload);
    };

    ws.onerror = onError || ((err) => console.error("[WS indicators error]", err));
    return () => ws.close();
  }

  return () => {};
}

export async function fetchSymbols(): Promise<SymbolInfo[]> {
  if (DATA_SOURCE === "api") {
    return withClientCache(
      "symbols",
      SYMBOLS_CACHE_MS,
      async () => {
        const data = await apiGet<SymbolInfo[] | { data?: SymbolInfo[] }>("/symbols");
        if (isUnavailableApiPayload(data)) return [];
        return Array.isArray(data) ? data : data.data ?? [];
      },
      { staleOnError: true },
    );
  }

  return mockDataAdapter.fetchSymbols();
}

export async function fetchHistoricalCandles(
  symbol: string,
  startMs: number,
  endMs: number,
  limit: number = 500,
  interval: string = "1h",
): Promise<Candle[]> {
  const normalizedInterval = normalizeTimeframe(interval);

  if (DATA_SOURCE === "api") {
    const query = buildQuery({
      symbol,
      interval: normalizedInterval,
      startTime: startMs,
      endTime: endMs,
      limit,
    });
    return withClientCache(
      makeClientCacheKey(["klines-historical", symbol, normalizedInterval, startMs, endMs, limit]),
      CANDLE_HISTORY_CACHE_MS,
      async () => {
        const raw = await apiGet<RawKline[] | { data?: RawKline[] }>(`/klines/historical?${query}`);
        if (isUnavailableApiPayload(raw)) return [];
        const rows = Array.isArray(raw) ? raw : raw.data ?? [];
        return rows.map(mapRawToCandle);
      },
      { staleOnError: true },
    );
  }

  return mockDataAdapter.fetchHistoricalCandles(
    symbol,
    startMs,
    endMs,
    limit,
    normalizedInterval,
  );
}

export interface RawOrderBookData {
  bids: [number | string, number | string][];
  asks: [number | string, number | string][];
  spread?: number | string;
  best_bid?: number | string;
  best_ask?: number | string;
}

export async function fetchOrderBook(symbol: string): Promise<RawOrderBookData> {
  if (DATA_SOURCE === "api") {
    return withClientCache(
      makeClientCacheKey(["orderbook", symbol]),
      ORDER_BOOK_CACHE_MS,
      async () => {
        const data = await apiGet<RawOrderBookData>(`/orderbook/${encodeURIComponent(symbol)}`);
        return isUnavailableApiPayload(data)
          ? { bids: [], asks: [], spread: 0, best_bid: 0, best_ask: 0 }
          : data;
      },
      { persist: false },
    );
  }
  const payload = await mockDataAdapter.fetchOrderBook(symbol);
  const { metadata: _metadata, symbol: _symbol, ...orderBook } = payload;
  return orderBook;
}

export async function fetchTrades(symbol: string, limit: number = 50): Promise<Trade[]> {
  if (DATA_SOURCE === "api") {
    return withClientCache(
      makeClientCacheKey(["trades", symbol, limit]),
      LIVE_TICK_CACHE_MS,
      async () => {
        const data = await apiGet<Trade[] | { trades?: Trade[] }>(
          `/trades/${encodeURIComponent(symbol)}?${buildQuery({ limit })}`,
        );
        if (isUnavailableApiPayload(data)) return [];
        return Array.isArray(data) ? data : data.trades ?? [];
      },
      { persist: false },
    );
  }
  const payload = await mockDataAdapter.fetchTrades(symbol, limit);
  return payload.trades;
}

export async function fetchTicker(symbol: string): Promise<Ticker> {
  if (DATA_SOURCE === "api") {
    return withClientCache(
      makeClientCacheKey(["ticker", symbol]),
      LIVE_TICK_CACHE_MS,
      async () => {
        const data = await apiGet<Ticker>(`/ticker/${encodeURIComponent(symbol)}`);
        return isUnavailableApiPayload(data) ? { symbol, price: 0 } : data;
      },
      { persist: false },
    );
  }
  const payload = await mockDataAdapter.fetchTicker(symbol);
  return payload.ticker;
}

export async function fetchTickers(): Promise<Ticker[]> {
  if (DATA_SOURCE === "api") {
    return withClientCache(
      "tickers",
      LIVE_TICK_CACHE_MS,
      async () => {
        const data = await apiGet<Ticker[]>("/ticker");
        return isUnavailableApiPayload(data) ? [] : data;
      },
      {
        persist: false,
      },
    );
  }
  const payload = await mockDataAdapter.fetchTickers();
  return payload.tickers;
}
