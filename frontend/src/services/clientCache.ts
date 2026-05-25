interface ClientCacheRecord<T> {
  createdAt: number;
  expiresAt: number;
  value: T;
}

interface ClientCacheOptions {
  persist?: boolean;
  staleOnError?: boolean;
}

const CACHE_PREFIX = "lmview_client_cache:";
const memoryCache = new Map<string, ClientCacheRecord<unknown>>();

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function storageKey(key: string): string {
  return `${CACHE_PREFIX}${key}`;
}

function readRecord<T>(key: string): ClientCacheRecord<T> | null {
  const memoryRecord = memoryCache.get(key) as ClientCacheRecord<T> | undefined;
  if (memoryRecord) return memoryRecord;

  if (!canUseStorage()) return null;

  try {
    const raw = window.localStorage.getItem(storageKey(key));
    if (!raw) return null;
    const record = JSON.parse(raw) as ClientCacheRecord<T>;
    memoryCache.set(key, record);
    return record;
  } catch {
    return null;
  }
}

export function getClientCacheValue<T>(key: string, allowExpired = false): T | null {
  const record = readRecord<T>(key);
  if (!record) return null;

  if (!allowExpired && record.expiresAt <= Date.now()) {
    memoryCache.delete(key);
    if (canUseStorage()) {
      try {
        window.localStorage.removeItem(storageKey(key));
      } catch {
        // Ignore storage cleanup failures.
      }
    }
    return null;
  }

  return record.value;
}

export function setClientCacheValue<T>(
  key: string,
  value: T,
  ttlMs: number,
  persist = true,
): void {
  if (ttlMs <= 0) return;

  const record: ClientCacheRecord<T> = {
    createdAt: Date.now(),
    expiresAt: Date.now() + ttlMs,
    value,
  };

  memoryCache.set(key, record);

  if (!persist || !canUseStorage()) return;

  try {
    window.localStorage.setItem(storageKey(key), JSON.stringify(record));
  } catch {
    // Storage may be unavailable or full; memory cache still covers this tab.
  }
}

export async function withClientCache<T>(
  key: string,
  ttlMs: number,
  loader: () => Promise<T>,
  options: ClientCacheOptions = {},
): Promise<T> {
  const cached = getClientCacheValue<T>(key);
  if (cached !== null) return cached;

  try {
    const value = await loader();
    setClientCacheValue(key, value, ttlMs, options.persist ?? true);
    return value;
  } catch (error) {
    if (options.staleOnError) {
      const stale = getClientCacheValue<T>(key, true);
      if (stale !== null) return stale;
    }
    throw error;
  }
}

export function makeClientCacheKey(parts: Array<string | number | boolean | null | undefined>): string {
  return parts
    .filter((part) => part !== undefined && part !== null && part !== "")
    .map((part) => encodeURIComponent(String(part)))
    .join(":");
}
