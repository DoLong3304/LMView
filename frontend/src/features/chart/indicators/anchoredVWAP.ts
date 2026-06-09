import type { Candle } from "@/types";

export interface AnchoredVWAPConfig {
  anchorType: "session" | "week" | "month" | "custom";
  customStartTime?: number; // Unix timestamp
  showBands: boolean;
  bandStdDev: number; // Standard deviations for bands
  bandPeriod: number;
}

export interface VWAPLevel {
  time: number;
  value: number;
  upperBand?: number;
  lowerBand?: number;
}

/**
 * Calculate Anchored VWAP from candle data.
 * Supports session/week/month/custom anchor points with optional standard deviation bands.
 */
export function calculateAnchoredVWAP(
  candles: Candle[],
  config: AnchoredVWAPConfig,
): VWAPLevel[] {
  if (candles.length === 0) return [];

  let startIndex = 0;

  switch (config.anchorType) {
    case "week": {
      // Find start of current week (Monday)
      for (let i = 0; i < candles.length; i++) {
        const date = new Date(candles[i].time * 1000);
        if (date.getDay() === 1 && date.getHours() === 0) {
          startIndex = i;
          break;
        }
      }
      break;
    }
    case "month": {
      for (let i = 0; i < candles.length; i++) {
        const date = new Date(candles[i].time * 1000);
        if (date.getDate() === 1 && date.getHours() === 0) {
          startIndex = i;
          break;
        }
      }
      break;
    }
    case "custom": {
      const idx = candles.findIndex((c) => c.time >= (config.customStartTime || 0));
      if (idx !== -1) startIndex = idx;
      break;
    }
    // "session" = start from beginning
  }

  const vwapCandles = candles.slice(startIndex);
  const levels: VWAPLevel[] = [];
  let cumulativeTPV = 0;
  let cumulativeVolume = 0;
  const typicalPrices: number[] = [];

  for (let i = 0; i < vwapCandles.length; i++) {
    const candle = vwapCandles[i];
    const typicalPrice = (candle.high + candle.low + candle.close) / 3;
    cumulativeTPV += typicalPrice * candle.volume;
    cumulativeVolume += candle.volume;
    typicalPrices.push(typicalPrice);

    const vwap = cumulativeVolume > 0 ? cumulativeTPV / cumulativeVolume : typicalPrice;

    // Calculate bands
    let upperBand: number | undefined;
    let lowerBand: number | undefined;

    if (config.showBands && i >= config.bandPeriod) {
      const periodTPs = typicalPrices.slice(-config.bandPeriod);
      const mean = periodTPs.reduce((a, b) => a + b, 0) / periodTPs.length;
      const variance =
        periodTPs.reduce((sum, tp) => sum + (tp - mean) ** 2, 0) / periodTPs.length;
      const stdDev = Math.sqrt(variance);

      upperBand = vwap + stdDev * config.bandStdDev;
      lowerBand = vwap - stdDev * config.bandStdDev;
    }

    levels.push({
      time: candle.time,
      value: +vwap.toFixed(4),
      upperBand: upperBand ? +upperBand.toFixed(4) : undefined,
      lowerBand: lowerBand ? +lowerBand.toFixed(4) : undefined,
    });
  }

  return levels;
}
