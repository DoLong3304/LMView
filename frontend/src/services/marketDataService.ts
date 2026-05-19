/**
 * marketDataService.ts
 *
 * Service layer for OHLCV market data.
 * All data access goes through this service — never fetch directly in components.
 *
 * OHLCV candle shape expected by lightweight-charts:
 *  { time: number (unix seconds), open, high, low, close, volume }
 */

import type { Candle, SymbolInfo, Ticker, Trade, NewsItem } from "../types";

// ─── Config ──────────────────────────────────────────────────────
const DATA_SOURCE = import.meta.env.VITE_DATA_SOURCE === "mock" ? "mock" : "api";

// Base URL of your backend REST/WebSocket endpoint.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

// ─── Timeframe helpers ────────────────────────────────────────────
export const TIMEFRAMES: Record<string, { label: string; seconds: number }> = {
  "1s": { label: "1s", seconds: 1 },
  "1m": { label: "1m", seconds: 60 },
  "5m": { label: "5m", seconds: 300 },
  "15m": { label: "15m", seconds: 900 },
  "1h": { label: "1H", seconds: 3600 },
  "4h": { label: "4H", seconds: 14400 },
  "1d": { label: "1D", seconds: 86400 },
  "1w": { label: "1W", seconds: 604800 },
};

// ─── WebSocket URL helper ─────────────────────────────────────────
function getWsBaseUrl(): string {
  if (API_BASE_URL.startsWith("http")) {
    return API_BASE_URL.replace(/^http/, "ws");
  }
  // Relative path — construct from current page origin
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${API_BASE_URL}`;
}

// ─── Raw API response shape ───────────────────────────────────────
interface RawKline {
  openTime: number;
  open: string | number;
  high: string | number;
  low: string | number;
  close: string | number;
  volume: string | number;
}

/** Convert raw kline from API to Candle for lightweight-charts */
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

import { generateMockCandles, generateMockOrderBook, generateMockTrades, generateMockTickers, generateMockNews } from "../mock/mockDataGenerator";

// ─── Public API ───────────────────────────────────────────────────

/**
 * Fetch historical OHLCV candles.
 *
 * @param symbol      e.g. 'BTCUSDT'
 * @param timeframe   key of TIMEFRAMES, e.g. '1h'
 * @param limit       number of candles
 * @param endTime     optional end timestamp in seconds (exclusive)
 * @param exchange    exchange name (default: 'binance')
 */
export async function fetchCandles(
  symbol: string,
  timeframe: string = "1h",
  limit: number = 200,
  endTime: number | null = null,
  exchange: string = "binance",
): Promise<Candle[]> {
  if (DATA_SOURCE === "api") {
    // Normalize interval to lowercase for backend API
    const interval = timeframe.toLowerCase();
    let url = `${API_BASE_URL}/klines?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&limit=${limit}&exchange=${encodeURIComponent(exchange)}`;
    if (endTime) {
      // Convert seconds to milliseconds for backend API
      url += `&endTime=${endTime * 1000}`;
    }
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error(`API error ${res.status}`);
    const raw: RawKline[] = await res.json();
    return raw.map(mapRawToCandle);
  }

  // Mock fallback (remove once API is ready)
  return new Promise((resolve) => {
    setTimeout(
      () => resolve(generateMockCandles(symbol, timeframe, limit)),
      300,
    );
  });
}

/**
 * Subscribe to real-time candle updates via WebSocket.
 *
 * @param symbol
 * @param timeframe
 * @param onCandle   called with latest candle
 * @param exchange   exchange name (default: 'binance')
 * @returns          unsubscribe function — call it on cleanup
 */
export function subscribeCandle(
  symbol: string,
  timeframe: string,
  onCandle: (candle: Candle) => void,
  exchange: string = "binance",
): () => void {
  if (DATA_SOURCE === "api") {
    // Normalize interval to lowercase for backend API
    const interval = timeframe.toLowerCase();
    const wsUrl = `${getWsBaseUrl()}/stream?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&exchange=${encodeURIComponent(exchange)}`;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (e: MessageEvent) => {
      const k: RawKline = JSON.parse(e.data as string);
      onCandle(mapRawToCandle(k));
    };
    ws.onerror = (err) => console.error("[WS error]", err);
    return () => ws.close();
  }

  // Mock: simulate a live tick every 2 seconds
  let lastCandle: Candle | null = null;
  const interval = setInterval(() => {
    const mockSeries = generateMockCandles(symbol, timeframe, 2);
    const latest = mockSeries[mockSeries.length - 1];
    if (!lastCandle || latest.time >= lastCandle.time) {
      lastCandle = latest;
      onCandle(latest);
    }
  }, 2000);

  return () => clearInterval(interval);
}

// ─── Multi-Timeframe Streaming ─────────────────────────────────────

export type TimeframeCallback = (timeframe: string, candle: Candle) => void;

interface MultiTimeframeOptions {
  symbol: string;
  exchange?: string;
  onCandle: TimeframeCallback;
  onError?: (error: Event) => void;
}

/**
 * Subscribe to ALL timeframes simultaneously via a single WebSocket.
 * This ensures all timeframes update at the same time when price changes.
 *
 * @param options  { symbol, exchange, onCandle, onError }
 * @returns        unsubscribe function
 */
export function subscribeAllTimeframes(
  options: MultiTimeframeOptions,
): () => void {
  const {
    symbol,
    exchange = "binance",
    onCandle,
    onError,
  } = options;

  if (DATA_SOURCE === "api") {
    const wsUrl = `${getWsBaseUrl()}/stream/all?symbol=${encodeURIComponent(symbol)}&exchange=${encodeURIComponent(exchange)}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (e: MessageEvent) => {
      // Message shape: { "1s": candle, "1m": candle, "5m": candle, ... }
      const data: Record<string, RawKline> = JSON.parse(e.data as string);
      for (const [tf, kline] of Object.entries(data)) {
        if (kline) {
          onCandle(tf, mapRawToCandle(kline));
        }
      }
    };

    if (onError) {
      ws.onerror = onError;
    } else {
      ws.onerror = (err) => console.error("[WS stream/all error]", err);
    }

    return () => ws.close();
  }

  // Mock fallback: simulate all timeframes updating simultaneously
  // Logic: Generate 1s ticks, aggregate into proper timeframe candles
  const tfKeys = Object.keys(TIMEFRAMES);

  // Track open candles for each timeframe (in-progress)
  const openCandles: Record<string, Candle> = {};

  // Seed price
  const seedPrices: Record<string, number> = {
    BTCUSDT: 64000, ETHUSDT: 3400, BNBUSDT: 580, SOLUSDT: 165,
    XRPUSDT: 2.35, DOGEUSDT: 0.158, ADAUSDT: 0.72, AVAXUSDT: 35.2,
    DOTUSDT: 7.5, LINKUSDT: 18.5, MATICUSDT: 0.72, LTCUSDT: 95,
  };
  let price = seedPrices[symbol] || 100;
  const volatility = price * 0.008;

  const interval = setInterval(() => {
    const now = Math.floor(Date.now() / 1000);

    // Generate 1s tick
    const tickPrice = price + (Math.random() - 0.5) * volatility;
    price = tickPrice;

    // Process each timeframe
    for (const tf of tfKeys) {
      const tfSeconds = TIMEFRAMES[tf]?.seconds || 60;
      const currentPeriod = Math.floor(now / tfSeconds) * tfSeconds;
      const is1s = tf === "1s";

      if (is1s) {
        // 1s: Each tick is a complete candle (Open=High=Low=Close)
        const candle: Candle = {
          time: currentPeriod,
          open: +tickPrice.toFixed(2),
          high: +tickPrice.toFixed(2),
          low: +tickPrice.toFixed(2),
          close: +tickPrice.toFixed(2),
          volume: Math.round(Math.random() * 100),
        };
        onCandle(tf, candle);
      } else {
        // 1m+: Accumulate ticks into current candle
        const openCandle = openCandles[tf];

        if (!openCandle || openCandle.time < currentPeriod) {
          // New candle period started - close old, start new
          if (openCandle) {
            onCandle(tf, { ...openCandle }); // Close previous candle
          }
          openCandles[tf] = {
            time: currentPeriod,
            open: +tickPrice.toFixed(2),
            high: +tickPrice.toFixed(2),
            low: +tickPrice.toFixed(2),
            close: +tickPrice.toFixed(2),
            volume: Math.round(Math.random() * 1000),
          };
          onCandle(tf, { ...openCandles[tf] });
        } else {
          // Update in-progress candle
          openCandle.close = +tickPrice.toFixed(2);
          openCandle.high = Math.max(openCandle.high, tickPrice);
          openCandle.low = Math.min(openCandle.low, tickPrice);
          openCandle.volume += Math.round(Math.random() * 100);
          onCandle(tf, { ...openCandle });
        }
      }
    }
  }, 1000); // 1 tick per second

  return () => clearInterval(interval);
}

/**
 * Fetch available trading symbols from your backend.
 */
export async function fetchSymbols(): Promise<SymbolInfo[]> {
  if (DATA_SOURCE === "api") {
    const res = await fetch(`${API_BASE_URL}/symbols`);
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  }

  return [
    { symbol: "BTCUSDT", name: "Bitcoin / USDT", type: "crypto" },
    { symbol: "ETHUSDT", name: "Ethereum / USDT", type: "crypto" },
    { symbol: "BNBUSDT", name: "BNB / USDT", type: "crypto" },
    { symbol: "SOLUSDT", name: "Solana / USDT", type: "crypto" },
    { symbol: "XRPUSDT", name: "XRP / USDT", type: "crypto" },
    { symbol: "DOGEUSDT", name: "Dogecoin / USDT", type: "crypto" },
    { symbol: "ADAUSDT", name: "Cardano / USDT", type: "crypto" },
    { symbol: "AVAXUSDT", name: "Avalanche / USDT", type: "crypto" },
    { symbol: "DOTUSDT", name: "Polkadot / USDT", type: "crypto" },
    { symbol: "LINKUSDT", name: "Chainlink / USDT", type: "crypto" },
    { symbol: "MATICUSDT", name: "Polygon / USDT", type: "crypto" },
    { symbol: "LTCUSDT", name: "Litecoin / USDT", type: "crypto" },
  ];
}

// ─── Historical Candles ────────────────────────────────────────────

/**
 * Fetch historical candles for a specific date range.
 */
export async function fetchHistoricalCandles(
  symbol: string,
  startMs: number,
  endMs: number,
  limit: number = 500,
  interval: string = "1h",
): Promise<Candle[]> {
  if (DATA_SOURCE === "api") {
    // Normalize interval to lowercase for backend API
    const normalizedInterval = interval.toLowerCase();
    const params = new URLSearchParams({
      symbol,
      interval: normalizedInterval,
      startTime: String(startMs),
      endTime: String(endMs),
      limit: String(limit),
    });
    const res = await fetch(`${API_BASE_URL}/klines/historical?${params}`);
    if (!res.ok) throw new Error(`API error ${res.status}`);
    const raw: RawKline[] = await res.json();
    return raw.map(mapRawToCandle);
  }

  // Mock: generate hourly candles for the date range
  const hourMs = 3600 * 1000;
  const count = Math.min(Math.floor((endMs - startMs) / hourMs), limit);
  return new Promise((resolve) => {
    setTimeout(
      () =>
        resolve(generateMockCandles(symbol, interval, Math.max(count, 10))),
      300,
    );
  });
}

// ─── Order Book ───────────────────────────────────────────────────

/**
 * Fetch order book for a symbol.
 * Backend returns { bids: [[price, qty], ...], asks: [[price, qty], ...], spread, best_bid, best_ask }
 */
export async function fetchOrderBook(symbol: string) {
  if (DATA_SOURCE === "api") {
    const res = await fetch(
      `${API_BASE_URL}/orderbook/${encodeURIComponent(symbol)}`,
    );
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  }
  return generateMockOrderBook(symbol === "BTCUSDT" ? 64000 : 100);
}

// ─── Recent Trades ────────────────────────────────────────────────

/**
 * Fetch recent trades / price ticks.
 * Backend returns [{ time (ms), price, volume, side }]
 */
export async function fetchTrades(
  symbol: string,
  limit: number = 50,
): Promise<Trade[]> {
  if (DATA_SOURCE === "api") {
    const res = await fetch(
      `${API_BASE_URL}/trades/${encodeURIComponent(symbol)}?limit=${limit}`,
    );
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  }
  return generateMockTrades(symbol === "BTCUSDT" ? 64000 : 100, limit);
}

// ─── Tickers ──────────────────────────────────────────────────────

/**
 * Fetch a single live ticker by symbol.
 */
export async function fetchTicker(symbol: string): Promise<Ticker> {
  if (DATA_SOURCE === "api") {
    const res = await fetch(
      `${API_BASE_URL}/ticker/${encodeURIComponent(symbol)}`,
    );
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  }
  return { symbol, price: 0 };
}

/**
 * Fetch all live tickers.
 */
export async function fetchTickers(): Promise<Ticker[]> {
  if (DATA_SOURCE === "api") {
    const res = await fetch(`${API_BASE_URL}/ticker`);
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  }
  // Mock fallback
  return generateMockTickers();
}

// ─── News ─────────────────────────────────────────────────────────

/**
 * Fetch latest news for a symbol.
 */
export async function fetchNews(symbol: string, limit: number = 10): Promise<NewsItem[]> {
  if (DATA_SOURCE === "api") {
    try {
      const res = await fetch(`${API_BASE_URL}/news/${encodeURIComponent(symbol)}?limit=${limit}`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      return res.json();
    } catch (e) {
      console.warn("Failed to fetch news from API, falling back to mock", e);
      return generateMockNews(limit, symbol);
    }
  }

  return generateMockNews(limit, symbol);
}
