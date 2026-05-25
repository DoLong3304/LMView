/**
 * symbolMetaService.ts
 *
 * Fetches symbol logos and full names from CoinGecko's free API,
 * with localStorage caching (24h TTL) and a bundled fallback map.
 */

import fallbackSymbolMeta, {
  DEFAULT_SYMBOL_ICON,
  type SymbolMetaEntry,
} from "@/data/fallbackSymbolMeta";

const CACHE_KEY = "symbol_meta_cache";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const CG_BASE = "https://api.coingecko.com/api/v3";

interface CoinGeckoMarketItem {
  id: string;
  symbol: string;
  name: string;
  image: string;
}

interface CachedMeta {
  timestamp: number;
  data: Record<string, StoredSymbolMetaEntry>;
}

type StoredSymbolMetaEntry = Omit<SymbolMetaEntry, "icon"> & {
  icon?: string;
  logoUrl?: string;
};

/**
 * Extract the base coin symbol from a Binance trading pair.
 * e.g. "BTCUSDT" → "BTC", "1INCHUSDT" → "1INCH"
 */
function extractBaseSymbol(pair: string): string {
  const normalizedPair = pair.toUpperCase().replace(/[^A-Z0-9]/g, "");
  const suffixes = ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"];
  for (const suffix of suffixes) {
    if (normalizedPair.endsWith(suffix) && normalizedPair.length > suffix.length) {
      return normalizedPair.slice(0, -suffix.length);
    }
  }
  return normalizedPair;
}

function normalizeEntry(entry: StoredSymbolMetaEntry): SymbolMetaEntry {
  const symbol = entry.symbol.toUpperCase();
  const icon = entry.icon || entry.logoUrl || DEFAULT_SYMBOL_ICON;
  return {
    ...entry,
    id: entry.id || symbol.toLowerCase(),
    name: entry.name || symbol,
    symbol,
    icon,
    logoUrl: entry.logoUrl || icon,
    category: entry.category || "crypto",
  };
}

function normalizeMetadataMap(
  data: Record<string, StoredSymbolMetaEntry>,
): Record<string, SymbolMetaEntry> {
  return Object.fromEntries(
    Object.entries(data).map(([key, entry]) => [key.toUpperCase(), normalizeEntry(entry)]),
  );
}

function createFallbackMeta(pair: string): SymbolMetaEntry {
  const base = extractBaseSymbol(pair);
  return {
    id: base.toLowerCase(),
    name: base,
    symbol: base,
    icon: DEFAULT_SYMBOL_ICON,
    logoUrl: DEFAULT_SYMBOL_ICON,
    category: "crypto",
  };
}

/**
 * Fetch top coins from CoinGecko /coins/markets endpoint.
 * Two pages of 250 = top 500 coins by market cap.
 */
async function fetchFromCoinGecko(): Promise<Record<string, SymbolMetaEntry>> {
  const result: Record<string, SymbolMetaEntry> = {};

  for (const page of [1, 2]) {
    const url = `${CG_BASE}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=${page}&sparkline=false`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`CoinGecko API error ${res.status}`);

    const items: CoinGeckoMarketItem[] = await res.json();
    for (const item of items) {
      const key = item.symbol.toUpperCase();
      result[key] = {
        id: item.id,
        name: item.name,
        symbol: key,
        icon: item.image || DEFAULT_SYMBOL_ICON,
        logoUrl: item.image,
        category: "crypto",
      };
    }
  }

  return result;
}

/**
 * Read cached metadata from localStorage.
 */
function readCache(): Record<string, SymbolMetaEntry> | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const cached: CachedMeta = JSON.parse(raw);
    if (Date.now() - cached.timestamp > CACHE_TTL_MS) return null;
    return normalizeMetadataMap(cached.data);
  } catch {
    return null;
  }
}

/**
 * Write metadata to localStorage cache.
 */
function writeCache(data: Record<string, SymbolMetaEntry>): void {
  try {
    const cached: CachedMeta = { timestamp: Date.now(), data };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cached));
  } catch {
    // Storage full or unavailable — silently ignore
  }
}

/**
 * Get symbol metadata, using cache → CoinGecko API → fallback.
 */
export async function getSymbolMetadata(): Promise<Record<string, SymbolMetaEntry>> {
  // 1. Check cache
  const cached = readCache();
  if (cached && Object.keys(cached).length > 50) return cached;

  // 2. Try CoinGecko API
  try {
    const fresh = await fetchFromCoinGecko();
    // Merge with fallback to ensure we have everything
    const merged = normalizeMetadataMap({ ...fallbackSymbolMeta, ...fresh });
    writeCache(merged);
    return merged;
  } catch {
    // 3. Fall back to bundled static data
    return normalizeMetadataMap({ ...fallbackSymbolMeta });
  }
}

/**
 * Look up metadata for a specific Binance trading pair.
 */
export function lookupSymbol(
  meta: Record<string, SymbolMetaEntry>,
  pair: string,
): SymbolMetaEntry {
  const base = extractBaseSymbol(pair);
  return meta[base] || fallbackSymbolMeta[base] || createFallbackMeta(pair);
}

export { DEFAULT_SYMBOL_ICON };
export type { SymbolMetaEntry };
