import { normalizeTimeframe, TIMEFRAMES } from "@/constants/timeframes";
import {
  generateMockCandles,
  generateMockGainers,
  generateMockLosers,
  generateMockMarketOverview,
  generateMockNews,
  generateMockOrderBook,
  generateMockTickers,
  generateMockTrades,
} from "@/data/mock/mockDataGenerator";
import { generateMockAiResponse } from "@/data/mock/mockAi";
import type {
  Candle,
  MarketMetrics,
  NewsArticle,
  NewsFilters,
  SymbolInfo,
  Ticker,
  TopMover,
  Trade,
  TrendingSymbol,
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
  data: MarketMetrics;
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
  fetchLatestNews: (filters: NewsFilters) => Promise<MockNewsResponse>;
  searchNews: (filters: NewsFilters) => Promise<MockNewsResponse>;
  fetchTrendingSymbols: (limit: number) => Promise<MockTrendingSymbolsResponse>;
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
    return generateMockCandles(symbol, normalizeTimeframe(timeframe), limit);
  },

  subscribeCandle(symbol, timeframe, onCandle) {
    const interval = normalizeTimeframe(timeframe);
    let lastCandle: Candle | null = null;
    const timer = window.setInterval(() => {
      const mockSeries = generateMockCandles(symbol, interval, 2);
      const latest = mockSeries[mockSeries.length - 1];
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

    const timer = window.setInterval(() => {
      const now = Math.floor(Date.now() / 1000);
      const tickPrice = price + (Math.random() - 0.5) * volatility;
      price = tickPrice;

      for (const tf of tfKeys) {
        const normalized = normalizeTimeframe(tf);
        const tfSeconds = TIMEFRAMES[normalized].seconds;
        const currentPeriod = Math.floor(now / tfSeconds) * tfSeconds;

        if (normalized === "1s") {
          onCandle(normalized, {
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

    return () => window.clearInterval(timer);
  },

  async fetchSymbols() {
    return mockSymbols();
  },

  async fetchHistoricalCandles(symbol, startMs, endMs, limit, interval) {
    const hourMs = 3600 * 1000;
    const count = Math.min(Math.floor((endMs - startMs) / hourMs), limit);
    return generateMockCandles(symbol, normalizeTimeframe(interval), Math.max(count, 10));
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
      data: generateMockMarketOverview(),
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
      trending_symbols: [
        { symbol: "BTC", mention_count: 42, avg_sentiment: 0.18 },
        { symbol: "ETH", mention_count: 35, avg_sentiment: 0.12 },
        { symbol: "SOL", mention_count: 28, avg_sentiment: 0.32 },
        { symbol: "BNB", mention_count: 20, avg_sentiment: 0.04 },
      ].slice(0, limit),
      metadata: metadata(),
    };
  },

  generateAiResponse(message, context) {
    return generateMockAiResponse(message, context);
  },
};
