import { normalizeTimeframe, TIMEFRAMES } from "@/constants/timeframes";
import type { Candle, Ticker, Trade, NewsItem, TopMover, MarketMetrics } from "@/types";

export function generateMockCandles(symbol: string, timeframeKey: string, count: number = 200): Candle[] {
  const normalizedTimeframe = normalizeTimeframe(timeframeKey);
  const tf = TIMEFRAMES[normalizedTimeframe];
  const now = Math.floor(Date.now() / 1000);
  const startTime = now - tf.seconds * count;

  const seedPrices: Record<string, number> = {
    BTCUSDT: 64000, ETHUSDT: 3400, BNBUSDT: 580, SOLUSDT: 165,
    XRPUSDT: 2.35, DOGEUSDT: 0.158, ADAUSDT: 0.72, AVAXUSDT: 35.2,
    DOTUSDT: 7.5, LINKUSDT: 18.5, MATICUSDT: 0.72, LTCUSDT: 95, default: 100,
  };

  let price = seedPrices[symbol] || seedPrices.default;
  const volatility = price * 0.008;
  const is1s = normalizedTimeframe === "1s";
  const candles: Candle[] = [];

  for (let i = 0; i < count; i++) {
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
  return candles;
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
  return [
    { symbol: "BTCUSDT", price: +(64444 + t * 100).toFixed(2), change24h: +(0.33 + t * 0.1).toFixed(2) },
    { symbol: "ETHUSDT", price: +(3400 + t * 15).toFixed(2), change24h: +(-0.53 + t * 0.1).toFixed(2) },
    { symbol: "BNBUSDT", price: +(580 + t * 2).toFixed(2), change24h: +(-0.27 + t * 0.1).toFixed(2) },
    { symbol: "SOLUSDT", price: +(165 + t * 0.5).toFixed(2), change24h: +(0.54 + t * 0.1).toFixed(2) },
    { symbol: "XRPUSDT", price: +(2.35 + t * 0.02).toFixed(4), change24h: +(-0.16 + t * 0.1).toFixed(2) },
    { symbol: "DOGEUSDT", price: +(0.158 + t * 0.002).toFixed(4), change24h: +(-0.6 + t * 0.1).toFixed(2) },
    { symbol: "ADAUSDT", price: +(0.72 + t * 0.01).toFixed(4), change24h: +(-0.83 + t * 0.1).toFixed(2) },
    { symbol: "AVAXUSDT", price: +(35.2 + t * 0.2).toFixed(2), change24h: +(0.33 + t * 0.1).toFixed(2) },
    { symbol: "DOTUSDT", price: +(7.5 + t * 0.08).toFixed(3), change24h: +(-0.21 + t * 0.1).toFixed(2) },
    { symbol: "LINKUSDT", price: +(18.5 + t * 0.12).toFixed(3), change24h: +(0.72 + t * 0.1).toFixed(2) },
    { symbol: "MATICUSDT", price: +(0.72 + t * 0.008).toFixed(4), change24h: +(-0.44 + t * 0.1).toFixed(2) },
    { symbol: "LTCUSDT", price: +(95 + t * 0.75).toFixed(2), change24h: +(0.18 + t * 0.1).toFixed(2) },
  ];
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
    total_market_cap: 2.4e12 + (Math.sin(t / 5000) * 1e10),
    total_volume_24h: 8e10 + (Math.cos(t / 5000) * 5e9),
    btc_dominance: +(52 + (Math.sin(t / 10000) * 0.5)).toFixed(2),
    eth_dominance: +(17 + (Math.cos(t / 10000) * 0.4)).toFixed(2),
    total_symbols: 1245,
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
