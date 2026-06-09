import type { Candle } from "@/types";

export interface VolumeProfileLevel {
  price: number;
  volume: number;
  buyVolume: number;
  sellVolume: number;
  percentage: number;
  poc: boolean;       // Point of Control
  vah: boolean;       // Value Area High
  val: boolean;       // Value Area Low
}

export interface VolumeProfileResult {
  levels: VolumeProfileLevel[];
  poc: number;
  vah: number;
  val: number;
  totalVolume: number;
}

export interface VolumeProfileConfig {
  bins: number;              // Number of price levels (24-100)
  valueAreaPercent: number;  // Typically 70%
}

/**
 * Calculate Volume Profile from candle data.
 * Distributes volume into price bins, finds POC/VAH/VAL.
 */
export function calculateVolumeProfile(
  candles: Candle[],
  config: VolumeProfileConfig = { bins: 24, valueAreaPercent: 70 },
): VolumeProfileResult {
  if (candles.length === 0) {
    return { levels: [], poc: 0, vah: 0, val: 0, totalVolume: 0 };
  }

  const prices = candles.flatMap((c) => [c.high, c.low]);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const range = maxPrice - minPrice;

  if (range === 0) {
    return { levels: [], poc: 0, vah: 0, val: 0, totalVolume: 0 };
  }

  const binSize = range / config.bins;

  // Initialize bins
  const bins: Map<number, VolumeProfileLevel> = new Map();
  for (let i = 0; i < config.bins; i++) {
    const price = minPrice + (i + 0.5) * binSize;
    bins.set(price, {
      price,
      volume: 0,
      buyVolume: 0,
      sellVolume: 0,
      percentage: 0,
      poc: false,
      vah: false,
      val: false,
    });
  }

  // Distribute volume into bins
  let totalVolume = 0;

  for (const candle of candles) {
    const isBullish = candle.close >= candle.open;
    const range = candle.high - candle.low || 1;
    const buyRatio = isBullish
      ? (candle.close - candle.low) / range
      : (candle.high - candle.close) / range;
    const sellRatio = 1 - buyRatio;

    const startBin = Math.max(0, Math.floor((Math.min(candle.open, candle.close) - minPrice) / binSize));
    const endBin = Math.min(config.bins - 1, Math.ceil((Math.max(candle.open, candle.close) - minPrice) / binSize));

    for (let i = startBin; i <= endBin; i++) {
      const price = minPrice + (i + 0.5) * binSize;
      const level = bins.get(price);
      if (level) {
        const portion = candle.volume / (endBin - startBin + 1);
        level.volume += portion;
        level.buyVolume += portion * buyRatio;
        level.sellVolume += portion * sellRatio;
        totalVolume += portion;
      }
    }
  }

  if (totalVolume === 0) {
    return { levels: [], poc: 0, vah: 0, val: 0, totalVolume: 0 };
  }

  // Sort by price, find POC
  const sortedByPrice = Array.from(bins.values()).sort((a, b) => a.price - b.price);
  const sortedByVolume = [...sortedByPrice].sort((a, b) => b.volume - a.volume);
  const poc = sortedByVolume[0]?.price || 0;

  // Calculate percentages
  for (const level of sortedByPrice) {
    level.percentage = (level.volume / totalVolume) * 100;
  }

  // Find Value Area (config.valueAreaPercent of total volume around POC)
  const targetVolume = totalVolume * (config.valueAreaPercent / 100);
  const pocIndex = sortedByPrice.findIndex((l) => l.price === poc);
  let vah = poc;
  let val = poc;
  let accumulated = sortedByPrice[pocIndex]?.volume || 0;
  let highIdx = pocIndex;
  let lowIdx = pocIndex;

  while (accumulated < targetVolume) {
    const aboveVolume = highIdx < sortedByPrice.length - 1 ? sortedByPrice[highIdx + 1].volume : 0;
    const belowVolume = lowIdx > 0 ? sortedByPrice[lowIdx - 1].volume : 0;

    if (aboveVolume >= belowVolume && highIdx < sortedByPrice.length - 1) {
      highIdx++;
      accumulated += sortedByPrice[highIdx].volume;
      vah = sortedByPrice[highIdx].price;
    } else if (lowIdx > 0) {
      lowIdx--;
      accumulated += sortedByPrice[lowIdx].volume;
      val = sortedByPrice[lowIdx].price;
    } else {
      break;
    }
  }

  // Mark POC/VAH/VAL
  for (const level of sortedByPrice) {
    level.poc = level.price === poc;
    level.vah = level.price === vah;
    level.val = level.price === val;
  }

  return {
    levels: sortedByPrice,
    poc,
    vah,
    val,
    totalVolume,
  };
}
