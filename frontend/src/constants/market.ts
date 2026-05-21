export const FALLBACK_SYMBOLS = [
  "BTCUSDT",
  "ETHUSDT",
  "BNBUSDT",
  "SOLUSDT",
  "XRPUSDT",
  "DOGEUSDT",
  "ADAUSDT",
  "AVAXUSDT",
] as const;

export const NEWS_SOURCES = [
  "all",
  "CryptoPanic",
  "CoinDesk",
  "CoinTelegraph",
  "Decrypt",
  "The Block",
  "Bitcoin Magazine",
  "CryptoSlate",
  "BeInCrypto",
  "NewsBTC",
  "U.Today",
  "Bitcoinist",
  "CryptoNews",
] as const;

export const NEWS_SYMBOLS = [
  "all",
  "BTC",
  "ETH",
  "BNB",
  "SOL",
  "XRP",
  "ADA",
  "DOGE",
] as const;

export const MARKET_REFRESH_MS = 30_000;
export const NEWS_REFRESH_MS = 5 * 60 * 1000;
