import { normalizeTimeframe, TIMEFRAMES } from "@/constants/timeframes";
import type {
  Candle,
  HeatmapItem,
  MarketMetrics,
  MarketOverview,
  SectorPerformance,
  Ticker,
  Trade,
  TrendingSymbol,
  TopMover,
  NewsItem,
} from "@/types";

type MockCandleLike = Partial<Candle> & {
  openTime?: number | string;
  timestamp?: number | string;
  t?: number | string;
  o?: number | string;
  h?: number | string;
  l?: number | string;
  c?: number | string;
  v?: number | string;
};

function finiteNumber(value: unknown): number | null {
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeMockCandleTime(value: unknown): number | null {
  const numeric = finiteNumber(value);
  if (numeric === null || numeric <= 0) return null;
  return Math.floor(numeric > 1_000_000_000_000 ? numeric / 1000 : numeric);
}

export function normalizeMockCandles(rows: MockCandleLike[]): Candle[] {
  const byTime = new Map<number, Candle>();

  for (const row of rows) {
    const time = normalizeMockCandleTime(row.time ?? row.openTime ?? row.timestamp ?? row.t);
    const open = finiteNumber(row.open ?? row.o);
    const close = finiteNumber(row.close ?? row.c);
    const rawHigh = finiteNumber(row.high ?? row.h);
    const rawLow = finiteNumber(row.low ?? row.l);
    const volume = finiteNumber(row.volume ?? row.v) ?? 0;

    if (time === null || open === null || close === null) continue;

    const high = Math.max(rawHigh ?? open, open, close, rawLow ?? open);
    const low = Math.min(rawLow ?? open, open, close, rawHigh ?? open);
    const candle: Candle = {
      time,
      open,
      high,
      low,
      close,
      volume: Math.max(0, volume),
    };

    if (
      candle.high >= candle.open &&
      candle.high >= candle.close &&
      candle.high >= candle.low &&
      candle.low <= candle.open &&
      candle.low <= candle.close &&
      candle.low <= candle.high
    ) {
      byTime.set(time, candle);
    }
  }

  return Array.from(byTime.values()).sort((a, b) => a.time - b.time);
}

export function generateMockCandles(symbol: string, timeframeKey: string, count: number = 200): Candle[] {
  const normalizedTimeframe = normalizeTimeframe(timeframeKey);
  const tf = TIMEFRAMES[normalizedTimeframe];
  const safeCount = Math.max(1, Math.floor(count));
  const now = Math.floor(Date.now() / 1000);
  const alignedNow = Math.floor(now / tf.seconds) * tf.seconds;
  const startTime = alignedNow - tf.seconds * safeCount;

  const seedPrices: Record<string, number> = {
    BTCUSDT: 64000, ETHUSDT: 3400, BNBUSDT: 580, SOLUSDT: 165,
    XRPUSDT: 2.35, DOGEUSDT: 0.158, ADAUSDT: 0.72, AVAXUSDT: 35.2,
    DOTUSDT: 7.5, LINKUSDT: 18.5, MATICUSDT: 0.72, LTCUSDT: 95, default: 100,
  };

  let price = seedPrices[symbol] || seedPrices.default;
  const volatility = price * 0.008;
  const is1s = normalizedTimeframe === "1s";
  const candles: Candle[] = [];

  for (let i = 0; i < safeCount; i++) {
    const time = startTime + i * tf.seconds;
    const open = price;
    const change = (Math.random() - 0.49) * volatility * 2;
    const close = Math.max(open + change, 1);
    let high: number, low: number;
    if (is1s) {
      high = close; low = close;
    } else {
      const wick = Math.random() * volatility;
      high = Math.max(open, close) + wick;
      low = Math.max(Math.min(open, close) - wick, 1);
    }
    const volume = Math.round(price * (0.5 + Math.random()) * 10);
    candles.push({
      time, open: +open.toFixed(2), high: +high.toFixed(2), low: +low.toFixed(2), close: +close.toFixed(2), volume,
    });
    price = close;
  }
  return normalizeMockCandles(candles);
}

export function generateMockOrderBook(basePrice: number, depth: number = 20) {
  const asks: [number, number][] = [];
  const bids: [number, number][] = [];
  let seed = Math.floor(basePrice * 100 + Date.now() / 2000);
  function rand(): number {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  }
  for (let i = 0; i < depth; i++) {
    const askP = +(basePrice * (1 + (i + 1) * 0.0005 + rand() * 0.0003)).toFixed(2);
    const bidP = +(basePrice * (1 - (i + 1) * 0.0005 - rand() * 0.0003)).toFixed(2);
    asks.push([askP, +(rand() * 5 + 0.1).toFixed(4)]);
    bids.push([bidP, +(rand() * 5 + 0.1).toFixed(4)]);
  }
  asks.sort((a, b) => a[0] - b[0]);
  bids.sort((a, b) => b[0] - a[0]);
  return {
    bids, asks,
    spread: +(asks[0][0] - bids[0][0]).toFixed(2),
    best_bid: bids[0][0], best_ask: asks[0][0],
  };
}

export function generateMockTrades(basePrice: number, count: number = 50): Trade[] {
  const trades: Trade[] = [];
  let seed = Math.floor(basePrice * 37 + Date.now() / 2000);
  function rand(): number {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  }
  const now = Math.floor(Date.now() / 1000);
  let price = basePrice;
  for (let i = 0; i < count; i++) {
    const side: "buy" | "sell" = rand() > 0.5 ? "buy" : "sell";
    price = Math.max(price + (rand() - 0.5) * basePrice * 0.002, 1);
    trades.push({
      time: (now - (count - i) * (Math.floor(rand() * 30) + 5)) * 1000,
      price: +price.toFixed(2),
      volume: +(rand() * 3 + 0.001).toFixed(4),
      side,
    });
  }
  return trades.reverse();
}

export function generateMockTickers(): Ticker[] {
  const t = Math.sin(Date.now() / 3000);
  const rows: Array<Ticker & { baseVolume: number }> = [
    { symbol: "BTCUSDT", price: +(64444 + t * 100).toFixed(2), change24h: +(0.33 + t * 0.1).toFixed(2), baseVolume: 32000000000 },
    { symbol: "ETHUSDT", price: +(3400 + t * 15).toFixed(2), change24h: +(-0.53 + t * 0.1).toFixed(2), baseVolume: 18000000000 },
    { symbol: "BNBUSDT", price: +(580 + t * 2).toFixed(2), change24h: +(-0.27 + t * 0.1).toFixed(2), baseVolume: 1400000000 },
    { symbol: "SOLUSDT", price: +(165 + t * 0.5).toFixed(2), change24h: +(0.54 + t * 0.1).toFixed(2), baseVolume: 3400000000 },
    { symbol: "XRPUSDT", price: +(2.35 + t * 0.02).toFixed(4), change24h: +(-0.16 + t * 0.1).toFixed(2), baseVolume: 2200000000 },
    { symbol: "DOGEUSDT", price: +(0.158 + t * 0.002).toFixed(4), change24h: +(-0.6 + t * 0.1).toFixed(2), baseVolume: 950000000 },
    { symbol: "ADAUSDT", price: +(0.72 + t * 0.01).toFixed(4), change24h: +(-0.83 + t * 0.1).toFixed(2), baseVolume: 780000000 },
    { symbol: "AVAXUSDT", price: +(35.2 + t * 0.2).toFixed(2), change24h: +(0.33 + t * 0.1).toFixed(2), baseVolume: 640000000 },
    { symbol: "DOTUSDT", price: +(7.5 + t * 0.08).toFixed(3), change24h: +(-0.21 + t * 0.1).toFixed(2), baseVolume: 420000000 },
    { symbol: "LINKUSDT", price: +(18.5 + t * 0.12).toFixed(3), change24h: +(0.72 + t * 0.1).toFixed(2), baseVolume: 690000000 },
    { symbol: "MATICUSDT", price: +(0.72 + t * 0.008).toFixed(4), change24h: +(-0.44 + t * 0.1).toFixed(2), baseVolume: 310000000 },
    { symbol: "LTCUSDT", price: +(95 + t * 0.75).toFixed(2), change24h: +(0.18 + t * 0.1).toFixed(2), baseVolume: 510000000 },
  ];

  return rows.map(({ baseVolume, ...ticker }, index) => {
    const volumeWave = 1 + Math.sin(Date.now() / 4000 + index) * 0.08;
    const volume = Math.round(baseVolume * volumeWave);
    return {
      ...ticker,
      volume,
      activity_score: Math.round(volume * (1 + Math.abs(ticker.change24h || 0) / 100)),
    };
  });
}

export function generateMockNews(limit: number = 10, symbol?: string): NewsItem[] {
  const t = Date.now();
  return Array.from({ length: limit }).map((_, i) => ({
    id: `mock-news-${i}-${t}`,
    title: symbol ? `Mock News ${i + 1} for ${symbol}: Market shifts` : `Mock News ${i + 1}: Market shows interesting movements`,
    summary: "This is a dynamically generated mock news summary to simulate real-time feed updates.",
    url: "#",
    source: "MockSource",
    published_at: new Date(t - i * 3600000).toISOString(),
    sentiment_label: i % 3 === 0 ? "Bullish" : i % 3 === 1 ? "Bearish" : "Neutral",
    sentiment_score: i % 3 === 0 ? 0.8 : i % 3 === 1 ? -0.7 : 0,
    symbols: symbol ? [symbol] : ["BTCUSDT", "ETHUSDT"],
  }));
}

export function generateMockMarketOverview(): MarketMetrics {
  const t = Date.now();
  return {
    btc_price: +(64000 + (Math.sin(t / 5000) * 500)).toFixed(2),
    btc_change_24h: +(0.8 + Math.sin(t / 6000) * 1.2).toFixed(2),
    btc_high_24h: +(65000 + Math.sin(t / 7000) * 450).toFixed(2),
    btc_low_24h: +(63000 + Math.cos(t / 7000) * 350).toFixed(2),
    eth_price: +(3400 + Math.cos(t / 5000) * 45).toFixed(2),
    eth_change_24h: +(-0.3 + Math.cos(t / 6000) * 1.1).toFixed(2),
    total_market_cap: 2.4e12 + (Math.sin(t / 5000) * 1e10),
    total_volume_24h: 8e10 + (Math.cos(t / 5000) * 5e9),
    btc_dominance: +(52 + (Math.sin(t / 10000) * 0.5)).toFixed(2),
    eth_dominance: +(17 + (Math.cos(t / 10000) * 0.4)).toFixed(2),
    fear_greed_index: Math.round(58 + Math.sin(t / 9000) * 12),
    advancing_count: 738,
    declining_count: 507,
    new_highs_24h: 46,
    new_lows_24h: 28,
    avg_volume_24h: 64200000,
    btc_volume_24h: 32000000000,
    stablecoin_volume_24h: 52000000000,
    total_symbols: 1245,
  };
}

export function generateMockHeatmapData(limit: number = 50): HeatmapItem[] {
  const tickers = generateMockTickers();
  const extras = ["UNIUSDT", "ATOMUSDT", "NEARUSDT", "AAVEUSDT", "OPUSDT", "ARBUSDT", "FILUSDT", "APTUSDT"];
  const rows = [
    ...tickers.map((ticker) => ticker.symbol),
    ...extras,
  ];

  return rows.slice(0, limit).map((symbol, index) => {
    const ticker = tickers.find((item) => item.symbol === symbol);
    const price = ticker?.price ?? +(2 + index * 1.7 + Math.random() * 8).toFixed(3);
    const change = ticker?.change24h ?? +((Math.sin(Date.now() / 5000 + index) * 7)).toFixed(2);
    const volume = ticker?.volume ?? Math.round(180000000 + index * 26000000);
    return {
      symbol,
      price,
      change_pct: change,
      volume_24h: volume,
      market_cap: Math.round(price * volume * (8 + index * 0.6)),
      volatility: +(Math.abs(change) * 0.8 + 1.5).toFixed(2),
    };
  });
}

export function generateMockSectorPerformance(): Record<string, SectorPerformance> {
  return {
    majors: {
      sector: "majors",
      name: "Major Assets",
      change_24h_pct: 0.84,
      change_7d_pct: 3.12,
      market_cap: 1.7e12,
      top_coins: ["BTC", "ETH", "BNB"],
    },
    layer1: {
      sector: "layer1",
      name: "Layer 1",
      change_24h_pct: 2.36,
      change_7d_pct: 6.48,
      market_cap: 420e9,
      top_coins: ["SOL", "AVAX", "ADA"],
    },
    defi: {
      sector: "defi",
      name: "DeFi",
      change_24h_pct: -0.92,
      change_7d_pct: 1.74,
      market_cap: 88e9,
      top_coins: ["UNI", "AAVE", "LINK"],
    },
    memes: {
      sector: "memes",
      name: "Meme Coins",
      change_24h_pct: -1.48,
      change_7d_pct: 9.05,
      market_cap: 62e9,
      top_coins: ["DOGE", "PEPE", "SHIB"],
    },
  };
}

export function generateMockTrendingSymbols(limit: number = 10): TrendingSymbol[] {
  return [
    { symbol: "BTC", mention_count: 42, avg_sentiment: 0.18 },
    { symbol: "ETH", mention_count: 35, avg_sentiment: 0.12 },
    { symbol: "SOL", mention_count: 28, avg_sentiment: 0.32 },
    { symbol: "BNB", mention_count: 20, avg_sentiment: 0.04 },
    { symbol: "AVAX", mention_count: 18, avg_sentiment: 0.21 },
    { symbol: "DOGE", mention_count: 16, avg_sentiment: -0.08 },
  ].slice(0, limit);
}

export function generateMockMarketOverviewPayload(): MarketOverview {
  const marketSummary = generateMockMarketOverview();
  const gainers = generateMockGainers();
  const losers = generateMockLosers();
  const heatmapData = generateMockHeatmapData(20);

  return {
    timestamp: new Date().toISOString(),
    timeframe: "24h",
    market_summary: marketSummary,
    top_gainers: gainers,
    top_losers: losers,
    most_volatile: [...gainers, ...losers]
      .sort((a, b) => Math.abs(b.change_24h_pct) - Math.abs(a.change_24h_pct))
      .slice(0, 8),
    highest_volume: heatmapData
      .map((item) => ({
        symbol: item.symbol,
        price: item.price,
        change_24h_pct: item.change_pct,
        volume_24h: item.volume_24h,
        market_cap: item.market_cap,
      }))
      .sort((a, b) => b.volume_24h - a.volume_24h)
      .slice(0, 8),
    trending_news: generateMockTrendingSymbols(6),
    sector_performance: generateMockSectorPerformance(),
    heatmap_data: heatmapData,
    indicators_summary: {
      total_symbols: marketSummary.total_symbols,
      avg_rsi: 54.8,
      overbought_count: 82,
      oversold_count: 41,
      bullish_macd_count: 694,
      bearish_macd_count: 551,
    },
    metadata: {
      source: "frontend_mock_adapter",
      data_sources: ["mockDataGenerator"],
      is_placeholder: false,
      computed_at: new Date().toISOString(),
      gold_tables_healthy: true,
      warning: null,
    },
  };
}

export function generateMockGainers(): TopMover[] {
  return [
    { symbol: "PEPEUSDT", price: 0.000012, volume_24h: 120000000, change_24h_pct: +(15.4 + Math.random() * 2).toFixed(2) },
    { symbol: "SOLUSDT", price: 165, volume_24h: 95000000, change_24h_pct: +(8.2 + Math.random() * 1).toFixed(2) },
    { symbol: "DOGEUSDT", price: 0.158, volume_24h: 78000000, change_24h_pct: +(6.5 + Math.random() * 1).toFixed(2) },
    { symbol: "AVAXUSDT", price: 35.2, volume_24h: 62000000, change_24h_pct: +(5.1 + Math.random() * 1).toFixed(2) },
    { symbol: "LINKUSDT", price: 18.5, volume_24h: 51000000, change_24h_pct: +(4.8 + Math.random() * 1).toFixed(2) },
  ];
}

export function generateMockLosers(): TopMover[] {
  return [
    { symbol: "ADAUSDT", price: 0.72, volume_24h: 50000000, change_24h_pct: +(-6.2 - Math.random() * 2).toFixed(2) },
    { symbol: "XRPUSDT", price: 2.35, volume_24h: 47000000, change_24h_pct: +(-4.5 - Math.random() * 1).toFixed(2) },
    { symbol: "DOTUSDT", price: 7.5, volume_24h: 36000000, change_24h_pct: +(-3.8 - Math.random() * 1).toFixed(2) },
    { symbol: "MATICUSDT", price: 0.72, volume_24h: 32000000, change_24h_pct: +(-2.9 - Math.random() * 1).toFixed(2) },
    { symbol: "LTCUSDT", price: 95, volume_24h: 29000000, change_24h_pct: +(-2.1 - Math.random() * 1).toFixed(2) },
  ];
}
