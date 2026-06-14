import { normalizeTimeframe, TIMEFRAMES } from "@/constants/timeframes";
import {
  generateMockCandles,
  generateMockGainers,
  generateMockHeatmapData,
  generateMockLosers,
  generateMockMarketOverviewPayload,
  generateMockNews,
  generateMockOrderBook,
  generateMockTickers,
  generateMockTrendingSymbols,
  generateMockTrades,
  normalizeMockCandles,
} from "@/data/mock/mockDataGenerator";
import { generateMockAiResponse } from "@/data/mock/mockAi";
import type {
  Candle,
  HeatmapItem,
  MarketOverview,
  NewsArticle,
  NewsFilters,
  SymbolInfo,
  Ticker,
  TopMover,
  Trade,
  TrendingSymbol,
  EnhancedWatchlistItem,
  WatchlistFilter,
} from "@/types";
import type { AiMessage, ChartContextForAi } from "@/features/ai/types";

export interface MockMetadata {
  data_type: "mock";
  is_mock: true;
  is_placeholder: false;
  source: "frontend_mock_adapter";
  generated_at: string;
}

export interface MockTradesResponse {
  symbol: string;
  trades: Trade[];
  metadata: MockMetadata;
}

export interface MockListResponse<T> {
  data: T[];
  metadata: MockMetadata;
}

export interface MockOrderBookResponse {
  symbol: string;
  bids: [number | string, number | string][];
  asks: [number | string, number | string][];
  spread?: number | string;
  best_bid?: number | string;
  best_ask?: number | string;
  metadata: MockMetadata;
}

export interface MockMarketOverviewResponse {
  data: MarketOverview;
  metadata: MockMetadata;
}

export interface MockNewsResponse {
  articles: NewsArticle[];
  metadata: MockMetadata;
}

export interface MockTrendingSymbolsResponse {
  trending_symbols: TrendingSymbol[];
  metadata: MockMetadata;
}

export interface DataSourceAdapter {
  fetchCandles: (symbol: string, timeframe: string, limit: number) => Promise<Candle[]>;
  subscribeCandle: (
    symbol: string,
    timeframe: string,
    onCandle: (candle: Candle) => void,
  ) => () => void;
  subscribeAllTimeframes: (
    symbol: string,
    onCandle: (timeframe: string, candle: Candle) => void,
  ) => () => void;
  fetchSymbols: () => Promise<SymbolInfo[]>;
  fetchHistoricalCandles: (
    symbol: string,
    startMs: number,
    endMs: number,
    limit: number,
    interval: string,
  ) => Promise<Candle[]>;
  fetchOrderBook: (symbol: string) => Promise<MockOrderBookResponse>;
  fetchTrades: (symbol: string, limit: number) => Promise<MockTradesResponse>;
  fetchTicker: (symbol: string) => Promise<{ ticker: Ticker; metadata: MockMetadata }>;
  fetchTickers: () => Promise<{ tickers: Ticker[]; metadata: MockMetadata }>;
  fetchMarketOverview: () => Promise<MockMarketOverviewResponse>;
  fetchTopGainers: (limit: number) => Promise<MockListResponse<TopMover>>;
  fetchTopLosers: (limit: number) => Promise<MockListResponse<TopMover>>;
  fetchHeatmapData: (limit: number) => Promise<MockListResponse<HeatmapItem>>;
  fetchLatestNews: (filters: NewsFilters) => Promise<MockNewsResponse>;
  searchNews: (filters: NewsFilters) => Promise<MockNewsResponse>;
  fetchTrendingSymbols: (limit: number) => Promise<MockTrendingSymbolsResponse>;
  fetchScreenerResults: (filter: import("@/types").WatchlistFilter) => Promise<{ data: import("@/types").EnhancedWatchlistItem[]; timestamp: string }>;
  fetchWatchlistWithIndicators: (symbols?: string[]) => Promise<{ data: import("@/types").EnhancedWatchlistItem[]; timestamp: string }>;
  generateAiResponse: (
    message: string,
    context?: ChartContextForAi | null,
  ) => AiMessage;
}

function metadata(): MockMetadata {
  return {
    data_type: "mock",
    is_mock: true,
    is_placeholder: false,
    source: "frontend_mock_adapter",
    generated_at: new Date().toISOString(),
  };
}

function getMockTickerPrice(symbol: string): number {
  return generateMockTickers().find((ticker) => ticker.symbol === symbol)?.price || 100;
}

function mockSymbols(): SymbolInfo[] {
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

function normalizeMockNews(filters: NewsFilters): NewsArticle[] {
  return generateMockNews(
    filters.limit || 20,
    filters.symbol === "all" ? undefined : filters.symbol,
  ).map((item) => ({
    ...item,
    author: undefined,
    published_at: Date.parse(item.published_at),
    tags: ["mock"],
    language: "en",
    region: "global",
  }));
}

export const mockDataAdapter: DataSourceAdapter = {
  async fetchCandles(symbol, timeframe, limit) {
    return normalizeMockCandles(generateMockCandles(symbol, normalizeTimeframe(timeframe), limit));
  },

  subscribeCandle(symbol, timeframe, onCandle) {
    const interval = normalizeTimeframe(timeframe);
    let lastCandle: Candle | null = null;
    const timer = window.setInterval(() => {
      const mockSeries = normalizeMockCandles(generateMockCandles(symbol, interval, 2));
      const latest = mockSeries[mockSeries.length - 1];
      if (!latest) return;
      if (!lastCandle || latest.time >= lastCandle.time) {
        lastCandle = latest;
        onCandle(latest);
      }
    }, 2000);

    return () => window.clearInterval(timer);
  },

  subscribeAllTimeframes(symbol, onCandle) {
    const tfKeys = Object.keys(TIMEFRAMES);
    const openCandles: Record<string, Candle> = {};
    let price = getMockTickerPrice(symbol);
    const volatility = price * 0.008;
    const emitCandle = (timeframe: string, candle: Candle) => {
      const normalized = normalizeMockCandles([candle])[0];
      if (normalized) onCandle(timeframe, normalized);
    };

    const timer = window.setInterval(() => {
      const now = Math.floor(Date.now() / 1000);
      const tickPrice = price + (Math.random() - 0.5) * volatility;
      price = tickPrice;

      for (const tf of tfKeys) {
        const normalized = normalizeTimeframe(tf);
        const tfSeconds = TIMEFRAMES[normalized].seconds;
        const currentPeriod = Math.floor(now / tfSeconds) * tfSeconds;

        if (normalized === "1s") {
          emitCandle(normalized, {
            time: currentPeriod,
            open: +tickPrice.toFixed(2),
            high: +tickPrice.toFixed(2),
            low: +tickPrice.toFixed(2),
            close: +tickPrice.toFixed(2),
            volume: Math.round(Math.random() * 100),
          });
          continue;
        }

        const openCandle = openCandles[normalized];
        if (!openCandle || openCandle.time < currentPeriod) {
          if (openCandle) emitCandle(normalized, { ...openCandle });
          openCandles[normalized] = {
            time: currentPeriod,
            open: +tickPrice.toFixed(2),
            high: +tickPrice.toFixed(2),
            low: +tickPrice.toFixed(2),
            close: +tickPrice.toFixed(2),
            volume: Math.round(Math.random() * 1000),
          };
          emitCandle(normalized, { ...openCandles[normalized] });
        } else {
          openCandle.close = +tickPrice.toFixed(2);
          openCandle.high = Math.max(openCandle.high, tickPrice);
          openCandle.low = Math.min(openCandle.low, tickPrice);
          openCandle.volume += Math.round(Math.random() * 100);
          emitCandle(normalized, { ...openCandle });
        }
      }
    }, 1000);

    return () => window.clearInterval(timer);
  },

  async fetchSymbols() {
    return mockSymbols();
  },

  async fetchHistoricalCandles(symbol, startMs, endMs, limit, interval) {
    const hourMs = 3600 * 1000;
    const count = Math.min(Math.floor((endMs - startMs) / hourMs), limit);
    return normalizeMockCandles(
      generateMockCandles(symbol, normalizeTimeframe(interval), Math.max(count, 10)),
    );
  },

  async fetchOrderBook(symbol) {
    return {
      symbol,
      ...generateMockOrderBook(getMockTickerPrice(symbol)),
      metadata: metadata(),
    };
  },

  async fetchTrades(symbol, limit) {
    return {
      symbol,
      trades: generateMockTrades(getMockTickerPrice(symbol), limit),
      metadata: metadata(),
    };
  },

  async fetchTicker(symbol) {
    return {
      ticker: generateMockTickers().find((ticker) => ticker.symbol === symbol) || {
        symbol,
        price: 0,
      },
      metadata: metadata(),
    };
  },

  async fetchTickers() {
    return {
      tickers: generateMockTickers(),
      metadata: metadata(),
    };
  },

  async fetchMarketOverview() {
    return {
      data: generateMockMarketOverviewPayload(),
      metadata: metadata(),
    };
  },

  async fetchTopGainers(limit) {
    return {
      data: generateMockGainers().slice(0, limit),
      metadata: metadata(),
    };
  },

  async fetchTopLosers(limit) {
    return {
      data: generateMockLosers().slice(0, limit),
      metadata: metadata(),
    };
  },

  async fetchHeatmapData(limit) {
    return {
      data: generateMockHeatmapData(limit),
      metadata: metadata(),
    };
  },

  async fetchLatestNews(filters) {
    return {
      articles: normalizeMockNews(filters),
      metadata: metadata(),
    };
  },

  async searchNews(filters) {
    const q = filters.query?.toLowerCase() || "";
    const articles = normalizeMockNews(filters).filter((item) =>
      `${item.title} ${item.summary}`.toLowerCase().includes(q),
    );
    return {
      articles,
      metadata: metadata(),
    };
  },

  async fetchTrendingSymbols(limit) {
    return {
      trending_symbols: generateMockTrendingSymbols(limit),
      metadata: metadata(),
    };
  },

  async fetchScreenerResults(_filter: WatchlistFilter): Promise<{ data: EnhancedWatchlistItem[]; timestamp: string }> {
    const tickers = generateMockTickers();
    const items: EnhancedWatchlistItem[] = tickers.map((t, idx) => {
      const change24h = t.change24h ?? 0;
      const base = t.symbol.replace("USDT", "").replace("BTC", "");
      return {
        symbol: t.symbol,
        name: base,
        rank: idx + 1,
        price: t.price ?? 0,
        change24h,
        change7d: (Math.random() - 0.3) * 20,
        volume24h: t.volume ?? 0,
        marketCap: (t.price ?? 0) * (t.volume ?? 0) * 0.01,
        rsi14: 30 + Math.random() * 40,
        rsiSignal: "neutral" as const,
        trend: change24h > 2 ? "bullish" : change24h < -2 ? "bearish" : "neutral" as const,
        volatility24h: Math.random() * 10,
        change: change24h,
        color: (change24h >= 0 ? "green" : "red") as "green" | "red",
      };
    });
    return { data: items, timestamp: new Date().toISOString() };
  },

  async fetchWatchlistWithIndicators(_symbols?: string[]): Promise<{ data: EnhancedWatchlistItem[]; timestamp: string }> {
    const tickers = generateMockTickers();
    const items: EnhancedWatchlistItem[] = tickers.map((t, idx) => {
      const change24h = t.change24h ?? 0;
      const base = t.symbol.replace("USDT", "").replace("BTC", "");
      return {
        symbol: t.symbol,
        name: base,
        rank: idx + 1,
        price: t.price ?? 0,
        change24h,
        change7d: (Math.random() - 0.3) * 20,
        volume24h: t.volume ?? 0,
        marketCap: (t.price ?? 0) * (t.volume ?? 0) * 0.01,
        rsi14: 30 + Math.random() * 40,
        rsiSignal: "neutral" as const,
        trend: change24h > 2 ? "bullish" : change24h < -2 ? "bearish" : "neutral" as const,
        volatility24h: Math.random() * 10,
        change: change24h,
        color: (change24h >= 0 ? "green" : "red") as "green" | "red",
      };
    });
    return { data: items, timestamp: new Date().toISOString() };
  },

  generateAiResponse(message, context) {
    return generateMockAiResponse(message, context);
  },
};
