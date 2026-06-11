import type { Candle } from "@/types";

export interface KagiLine {
  time: number;
  price: number;
  type: "yang" | "yin"; // Bullish / Bearish
  reversal: boolean;
  linewidth?: number; // Thick for yang (rises above prev high), thin for yin
}

export interface KagiConfig {
  reversalPercent: number; // Typically 3-5%
  useClose: boolean; // Use close price only
}

/**
 * Transform standard candles to Kagi lines.
 * Uses reversal percentage to determine direction changes.
 */
export function toKagi(
  candles: Candle[],
  config: KagiConfig = { reversalPercent: 4, useClose: true },
): KagiLine[] {
  if (candles.length < 2) return [];

  const lines: KagiLine[] = [];
  const reversalAmount = config.reversalPercent / 100;

  let basePrice = config.useClose
    ? candles[0].close
    : (candles[0].high + candles[0].low) / 2;
  let currentType: "yang" | "yin" = candles[0].close >= candles[0].open ? "yang" : "yin";
  let currentHigh = basePrice;
  let currentLow = basePrice;
  let lastEmittedTime = Number.NEGATIVE_INFINITY;

  const nextTime = (baseTime: number): number => {
    lastEmittedTime = Math.max(baseTime, lastEmittedTime + 1);
    return lastEmittedTime;
  };

  lines.push({
    time: nextTime(candles[0].time),
    price: basePrice,
    type: currentType,
    reversal: false,
    linewidth: currentType === "yang" ? 3 : 1,
  });

  for (let i = 1; i < candles.length; i++) {
    const price = config.useClose
      ? candles[i].close
      : (candles[i].high + candles[i].low) / 2;

    if (currentType === "yang") {
      if (price > currentHigh) {
        // Continue up
        currentHigh = price;
        lines.push({
          time: nextTime(candles[i].time),
          price,
          type: "yang",
          reversal: false,
          linewidth: 3,
        });
      } else if (price < currentHigh * (1 - reversalAmount)) {
        // Reversal down
        currentType = "yin";
        currentLow = price;
        lines.push({
          time: nextTime(candles[i].time),
          price,
          type: "yin",
          reversal: true,
          linewidth: 1,
        });
      }
    } else {
      // currentType === "yin"
      if (price < currentLow) {
        // Continue down
        currentLow = price;
        lines.push({
          time: nextTime(candles[i].time),
          price,
          type: "yin",
          reversal: false,
          linewidth: 1,
        });
      } else if (price > currentLow * (1 + reversalAmount)) {
        // Reversal up
        currentType = "yang";
        currentHigh = price;
        lines.push({
          time: nextTime(candles[i].time),
          price,
          type: "yang",
          reversal: true,
          linewidth: 3,
        });
      }
    }
  }

  return lines;
}
