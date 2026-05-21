import type { TimeframeKey } from "@/types";

export const TIMEFRAMES: Record<TimeframeKey, { label: string; seconds: number }> = {
  "1s": { label: "1s", seconds: 1 },
  "1m": { label: "1m", seconds: 60 },
  "5m": { label: "5m", seconds: 300 },
  "15m": { label: "15m", seconds: 900 },
  "1h": { label: "1H", seconds: 3600 },
  "4h": { label: "4H", seconds: 14400 },
  "1d": { label: "1D", seconds: 86400 },
  "1w": { label: "1W", seconds: 604800 },
};

export const TIMEFRAME_KEYS = Object.keys(TIMEFRAMES) as TimeframeKey[];

export function normalizeTimeframe(value: string): TimeframeKey {
  const key = value.toLowerCase() as TimeframeKey;
  return TIMEFRAMES[key] ? key : "1m";
}
