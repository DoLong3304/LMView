import { DATA_SOURCE } from "@/constants/env";
import { TIMEFRAMES, normalizeTimeframe } from "@/constants/timeframes";
import { apiGet, buildQuery, getWsBaseUrl } from "@/services/apiClient";
import { isUnavailableApiPayload } from "@/services/apiMetadata";
import { makeClientCacheKey, withClientCache } from "@/services/clientCache";
import { getMockDataAdapter } from "@/services/dataSourceAdapter";
import type { Candle, IndicatorSeriesResponse, IndicatorStreamSnapshot, SymbolInfo, Ticker, Trade } from "@/types";

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
const INDICATOR_SERIES_CACHE_MS = 30_000;
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

const MAX_RECONNECT_DELAY_MS = 30_000;
const BASE_RECONNECT_DELAY_MS = 1_000;
// can be idle for hours and we want live prices the moment user comes back.

function createReconnectingWebSocket(
  url: string,
  handlers: {
    onOpen?: () => void;
    onMessage: (event: MessageEvent) => void;
    onError?: (event: Event) => void;
    onClose?: () => void;
  },
): { ws: WebSocket | null; cleanup: () => void } {
  let ws: WebSocket | null = null;
  let retries = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let watchdogTimer: ReturnType<typeof setInterval> | null = null;
  let manualClose = false;
  let lastMessageTs = 0;

  function connect() {
    ws = new WebSocket(url);

    ws.onopen = () => {
      retries = 0;
      lastMessageTs = Date.now();
      handlers.onOpen?.();

      // Watchdog: if no message for 45s while open, force-close so we
      // reconnect. Some proxies / browser idle paths kill the socket
      // silently — we'd see readyState=OPEN but never receive data.
      if (watchdogTimer) clearInterval(watchdogTimer);
      watchdogTimer = setInterval(() => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        if (Date.now() - lastMessageTs > 45_000) {
          console.warn('[WS] No data for 45s, forcing reconnect');
          try { ws.close(); } catch (_) { /* ignore */ }
        }
      }, 15_000);
    };

    ws.onmessage = (e) => {
      lastMessageTs = Date.now();
      handlers.onMessage(e);
    };

    ws.onerror = (event) => {
      handlers.onError?.(event);
    };

    ws.onclose = () => {
      if (watchdogTimer) { clearInterval(watchdogTimer); watchdogTimer = null; }
      handlers.onClose?.();
      if (!manualClose) {
        // Exponential backoff capped at 30s + jitter, never stop retrying.
        const expDelay = BASE_RECONNECT_DELAY_MS * Math.pow(2, retries);
        const delay = Math.min(expDelay, MAX_RECONNECT_DELAY_MS)
          + Math.floor(Math.random() * 1000);
        retries++;
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${retries})`);
        reconnectTimer = setTimeout(connect, delay);
      }
    };
  }

  connect();

  return {
    get ws() { return ws; },
    cleanup: () => {
      manualClose = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (watchdogTimer) clearInterval(watchdogTimer);
      ws?.close();
    },
  };
}

export type TimeframeCallback = (timeframe: string, candle: Candle) => void;

export interface StreamTickerPayload {
  price: number;
  eventTime: number;
  change24h: number;
  change_pct?: number;
  change_abs?: number;
  volume: number;
  quote_volume?: number;
  bid?: number;
  ask?: number;
  bid_qty?: number;
  ask_qty?: number;
  weighted_avg?: number;
  open_24h?: number;
  high_24h?: number;
  low_24h?: number;
  last_qty?: number;
  activity_score?: number;
}

interface MultiTimeframeOptions {
  symbol: string;
  exchange?: string;
  onCandle: TimeframeCallback;
  onTicker?: (ticker: StreamTickerPayload) => void;
  onError?: (error: Event) => void;
}

interface IndicatorStreamOptions {
  symbol: string;
  timeframe: string;
  exchange?: string;
  onIndicator: (snapshot: IndicatorStreamSnapshot) => void;
  onError?: (error: Event) => void;
}

/**
 * Parse a WebSocket message's `data` field which may be:
 * - string (text frame)
 * - Blob (binary frame from `send_bytes()`)
 * - ArrayBuffer
 *
 * The backend uses `send_bytes()` so browsers receive Blob by default.
 * `JSON.parse(blob)` throws — must convert Blob → string first.
 */
async function parseWsData<T = unknown>(data: MessageEvent["data"]): Promise<T> {
  if (typeof data === "string") return JSON.parse(data) as T;
  if (data instanceof Blob) {
    const text = await data.text();
    return JSON.parse(text) as T;
  }
  if (data instanceof ArrayBuffer) {
    const text = new TextDecoder().decode(new Uint8Array(data));
    return JSON.parse(text) as T;
  }
  return JSON.parse(String(data)) as T;
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

    const { cleanup } = createReconnectingWebSocket(wsUrl, {
      onMessage: async (e: MessageEvent) => {
        try {
          const k = await parseWsData<RawKline>(e.data);
          onCandle(mapRawToCandle(k));
        } catch (err) {
          console.error("[WS candle parse error]", err);
        }
      },
      onError: (err) => console.error("[WS candle error]", err),
    });

    return cleanup;
  }

  return mockDataAdapter.subscribeCandle(symbol, interval, onCandle);
}

export function subscribeAllTimeframes(options: MultiTimeframeOptions): () => void {
  const { symbol, exchange = "binance", onCandle, onTicker, onError } = options;

  if (DATA_SOURCE === "api") {
    const wsUrl = `${getWsBaseUrl()}/stream/all?${buildQuery({ symbol, exchange })}`;

    const { cleanup } = createReconnectingWebSocket(wsUrl, {
      onMessage: async (e: MessageEvent) => {
        let data: Record<string, RawKline | StreamTickerPayload | string | undefined>;
        try {
          data = await parseWsData<Record<string, any>>(e.data);
        } catch (err) {
          console.error("[WS stream/all parse error]", err);
          return;
        }
        const ticker = data._ticker as StreamTickerPayload | undefined;
        if (ticker?.price != null) {
          const price = Number(ticker.price);
          const change24h = Number(ticker.change24h) || 0;
          const volume = Number(ticker.volume) || 0;
          const activity_score = Number(ticker.activity_score) || 0;
          const eventTime = (ticker as any).event_time != null
            ? Number((ticker as any).event_time)
            : (ticker as any).eventTime ?? Date.now();
          updateLivePrice(symbol, price, change24h, volume, activity_score);
          onTicker?.({
            price,
            eventTime,
            change24h,
            volume,
            change_pct: Number(ticker.change_pct) || 0,
            change_abs: Number(ticker.change_abs) || 0,
            quote_volume: Number(ticker.quote_volume) || 0,
            bid: Number(ticker.bid) || 0,
            ask: Number(ticker.ask) || 0,
            bid_qty: Number(ticker.bid_qty) || 0,
            ask_qty: Number(ticker.ask_qty) || 0,
            weighted_avg: Number(ticker.weighted_avg) || 0,
            open_24h: Number(ticker.open_24h) || 0,
            high_24h: Number(ticker.high_24h) || 0,
            low_24h: Number(ticker.low_24h) || 0,
            last_qty: Number(ticker.last_qty) || 0,
            activity_score,
          });
        }
        for (const [tf, kline] of Object.entries(data)) {
          if (tf.startsWith("_")) continue;
          if (kline && typeof kline === "object") {
            onCandle(normalizeTimeframe(tf), mapRawToCandle(kline as RawKline));
          }
        }
      },
      onError: onError || ((err) => console.error("[WS stream/all error]", err)),
    });

    return cleanup;
  }

  return mockDataAdapter.subscribeAllTimeframes(symbol, onCandle);
}

export function subscribeIndicatorStream(options: IndicatorStreamOptions): () => void {
  const { symbol, timeframe, exchange = "binance", onIndicator, onError } = options;
  const interval = normalizeTimeframe(timeframe);

  if (DATA_SOURCE === "api") {
    const wsUrl = `${getWsBaseUrl()}/stream/indicators/${interval}?${buildQuery({ symbol, exchange })}`;

    const { cleanup } = createReconnectingWebSocket(wsUrl, {
      onMessage: async (e: MessageEvent) => {
        try {
          const payload = await parseWsData<IndicatorStreamSnapshot>(e.data);
          onIndicator(payload);
        } catch (err) {
          console.error("[WS indicators parse error]", err);
        }
      },
      onError: onError || ((err) => console.error("[WS indicators error]", err)),
    });

    return cleanup;
  }

  return () => {};
}

export async function fetchIndicatorSeries(
  symbol: string,
  timeframe: string = "1m",
  indicators: string[] = [],
  limit: number = 500,
  exchange: string = "binance",
): Promise<IndicatorSeriesResponse> {
  const interval = normalizeTimeframe(timeframe);
  const requested = indicators.filter(Boolean);

  if (DATA_SOURCE === "api") {
    const query = buildQuery({
      exchange,
      interval,
      indicators: requested.join(","),
      limit,
    });
    const cacheKey = makeClientCacheKey([
      "indicators",
      exchange,
      symbol,
      interval,
      requested.join(","),
      limit,
    ]);

    return withClientCache(
      cacheKey,
      INDICATOR_SERIES_CACHE_MS,
      async () => apiGet<IndicatorSeriesResponse>(
        `/indicators/${encodeURIComponent(symbol)}/series?${query}`,
      ),
      { persist: false, staleOnError: true },
    );
  }

  return {
    symbol,
    exchange,
    interval,
    requested,
    series: {},
    latest_values: {},
    source: "mock_mode_local_candles",
    sources: ["mock_candles"],
    candle_count: 0,
    required_candles: 0,
    warnings: [],
  };
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
