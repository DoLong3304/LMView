import { DATA_SOURCE } from "@/constants/env";
import { TIMEFRAMES, normalizeTimeframe } from "@/constants/timeframes";
import { apiGet, buildQuery, getWsBaseUrl } from "@/services/apiClient";
import { makeClientCacheKey, withClientCache } from "@/services/clientCache";
import {
  generateMockCandles,
  generateMockOrderBook,
  generateMockTrades,
  generateMockTickers,
} from "@/data/mockDataGenerator";
import type { Candle, SymbolInfo, Ticker, Trade } from "@/types";

export { TIMEFRAMES };

const LIVE_TICK_CACHE_MS = 2_000;
const ORDER_BOOK_CACHE_MS = 1_000;
const CANDLE_LATEST_CACHE_MS = 3_000;
const CANDLE_HISTORY_CACHE_MS = 5 * 60_000;
const SYMBOLS_CACHE_MS = 10 * 60_000;

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

function getMockTickerPrice(symbol: string): number {
  return generateMockTickers().find((ticker) => ticker.symbol === symbol)?.price || 100;
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
        const raw = await apiGet<RawKline[]>(`/klines?${query}`);
        return raw.map(mapRawToCandle);
      },
      { persist: Boolean(endTime), staleOnError: true },
    );
  }

  return new Promise((resolve) => {
    setTimeout(() => resolve(generateMockCandles(symbol, interval, limit)), 300);
  });
}

export function subscribeCandle(
  symbol: string,
  timeframe: string,
  onCandle: (candle: Candle) => void,
  exchange: string = "binance",
): () => void {
  const interval = normalizeTimeframe(timeframe);

  if (DATA_SOURCE === "api") {
    const wsUrl = `${getWsBaseUrl()}/stream?${buildQuery({ symbol, interval, exchange })}`;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (e: MessageEvent) => {
      const k: RawKline = JSON.parse(e.data as string);
      onCandle(mapRawToCandle(k));
    };
    ws.onerror = (err) => console.error("[WS error]", err);
    return () => ws.close();
  }

  let lastCandle: Candle | null = null;
  const timer = setInterval(() => {
    const mockSeries = generateMockCandles(symbol, interval, 2);
    const latest = mockSeries[mockSeries.length - 1];
    if (!lastCandle || latest.time >= lastCandle.time) {
      lastCandle = latest;
      onCandle(latest);
    }
  }, 2000);

  return () => clearInterval(timer);
}

export type TimeframeCallback = (timeframe: string, candle: Candle) => void;

interface MultiTimeframeOptions {
  symbol: string;
  exchange?: string;
  onCandle: TimeframeCallback;
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
        if (kline) onCandle(normalizeTimeframe(tf), mapRawToCandle(kline));
      }
    };

    ws.onerror = onError || ((err) => console.error("[WS stream/all error]", err));
    return () => ws.close();
  }

  const tfKeys = Object.keys(TIMEFRAMES);
  const openCandles: Record<string, Candle> = {};
  const seedPrices: Record<string, number> = {
    BTCUSDT: 64000,
    ETHUSDT: 3400,
    BNBUSDT: 580,
    SOLUSDT: 165,
    XRPUSDT: 2.35,
    DOGEUSDT: 0.158,
    ADAUSDT: 0.72,
    AVAXUSDT: 35.2,
    DOTUSDT: 7.5,
    LINKUSDT: 18.5,
    MATICUSDT: 0.72,
    LTCUSDT: 95,
  };
  let price = seedPrices[symbol] || 100;
  const volatility = price * 0.008;

  const timer = setInterval(() => {
    const now = Math.floor(Date.now() / 1000);
    const tickPrice = price + (Math.random() - 0.5) * volatility;
    price = tickPrice;

    for (const tf of tfKeys) {
      const normalized = normalizeTimeframe(tf);
      const tfSeconds = TIMEFRAMES[normalized].seconds;
      const currentPeriod = Math.floor(now / tfSeconds) * tfSeconds;

      if (normalized === "1s") {
        const candle: Candle = {
          time: currentPeriod,
          open: +tickPrice.toFixed(2),
          high: +tickPrice.toFixed(2),
          low: +tickPrice.toFixed(2),
          close: +tickPrice.toFixed(2),
          volume: Math.round(Math.random() * 100),
        };
        onCandle(normalized, candle);
        continue;
      }

      const openCandle = openCandles[normalized];
      if (!openCandle || openCandle.time < currentPeriod) {
        if (openCandle) onCandle(normalized, { ...openCandle });
        openCandles[normalized] = {
          time: currentPeriod,
          open: +tickPrice.toFixed(2),
          high: +tickPrice.toFixed(2),
          low: +tickPrice.toFixed(2),
          close: +tickPrice.toFixed(2),
          volume: Math.round(Math.random() * 1000),
        };
        onCandle(normalized, { ...openCandles[normalized] });
      } else {
        openCandle.close = +tickPrice.toFixed(2);
        openCandle.high = Math.max(openCandle.high, tickPrice);
        openCandle.low = Math.min(openCandle.low, tickPrice);
        openCandle.volume += Math.round(Math.random() * 100);
        onCandle(normalized, { ...openCandle });
      }
    }
  }, 1000);

  return () => clearInterval(timer);
}

export async function fetchSymbols(): Promise<SymbolInfo[]> {
  if (DATA_SOURCE === "api") {
    return withClientCache(
      "symbols",
      SYMBOLS_CACHE_MS,
      () => apiGet<SymbolInfo[]>("/symbols"),
      { staleOnError: true },
    );
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
        const raw = await apiGet<RawKline[]>(`/klines/historical?${query}`);
        return raw.map(mapRawToCandle);
      },
      { staleOnError: true },
    );
  }

  const hourMs = 3600 * 1000;
  const count = Math.min(Math.floor((endMs - startMs) / hourMs), limit);
  return new Promise((resolve) => {
    setTimeout(
      () => resolve(generateMockCandles(symbol, normalizedInterval, Math.max(count, 10))),
      300,
    );
  });
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
      () => apiGet<RawOrderBookData>(`/orderbook/${encodeURIComponent(symbol)}`),
      { persist: false },
    );
  }
  return generateMockOrderBook(getMockTickerPrice(symbol));
}

export async function fetchTrades(symbol: string, limit: number = 50): Promise<Trade[]> {
  if (DATA_SOURCE === "api") {
    return withClientCache(
      makeClientCacheKey(["trades", symbol, limit]),
      LIVE_TICK_CACHE_MS,
      () => apiGet<Trade[]>(`/trades/${encodeURIComponent(symbol)}?${buildQuery({ limit })}`),
      { persist: false },
    );
  }
  return generateMockTrades(getMockTickerPrice(symbol), limit);
}

export async function fetchTicker(symbol: string): Promise<Ticker> {
  if (DATA_SOURCE === "api") {
    return withClientCache(
      makeClientCacheKey(["ticker", symbol]),
      LIVE_TICK_CACHE_MS,
      () => apiGet<Ticker>(`/ticker/${encodeURIComponent(symbol)}`),
      { persist: false },
    );
  }
  return generateMockTickers().find((ticker) => ticker.symbol === symbol) || { symbol, price: 0 };
}

export async function fetchTickers(): Promise<Ticker[]> {
  if (DATA_SOURCE === "api") {
    return withClientCache("tickers", LIVE_TICK_CACHE_MS, () => apiGet<Ticker[]>("/ticker"), {
      persist: false,
    });
  }
  return generateMockTickers();
}
