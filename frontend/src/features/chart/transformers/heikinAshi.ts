import type { Candle } from "@/types";

/**
 * Heikin Ashi transformer.
 * Smooths price data using averaged OHLC values.
 * HA-Close = (Open + High + Low + Close) / 4
 * HA-Open = previous HA-Open + previous HA-Close) / 2
 */
export function toHeikinAshi(candles: Candle[]): Candle[] {
  if (candles.length === 0) return [];

  const result: Candle[] = [];

  for (let i = 0; i < candles.length; i++) {
    const c = candles[i];
    const haClose = (c.open + c.high + c.low + c.close) / 4;

    let haOpen: number;
    if (i === 0) {
      haOpen = (c.open + c.close) / 2;
    } else {
      haOpen = (result[i - 1].open + result[i - 1].close) / 2;
    }

    const haHigh = Math.max(c.high, haOpen, haClose);
    const haLow = Math.min(c.low, haOpen, haClose);

    result.push({
      time: c.time,
      open: haOpen,
      high: haHigh,
      low: haLow,
      close: haClose,
      volume: c.volume,
    });
  }

  return result;
}
