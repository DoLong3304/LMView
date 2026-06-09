import type { Candle } from "@/types";
import type { DetectedPattern, PatternType } from "@/types/patterns";

export class PatternDetector {
  private minConfidence = 60;

  detect(candles: Candle[], patternTypes: PatternType[]): DetectedPattern[] {
    const results: DetectedPattern[] = [];
    for (const patternType of patternTypes) {
      const detected = this.detectPattern(candles, patternType);
      if (detected) results.push(detected);
    }
    return results;
  }

  private detectPattern(candles: Candle[], type: PatternType): DetectedPattern | null {
    switch (type) {
      case "double_top": return this.detectDoubleTop(candles);
      case "double_bottom": return this.detectDoubleBottom(candles);
      case "ascending_triangle": return this.detectAscendingTriangle(candles);
      case "descending_triangle": return this.detectDescendingTriangle(candles);
      case "head_shoulders": return this.detectHeadShoulders(candles);
      default: return null;
    }
  }

  private detectDoubleTop(candles: Candle[]): DetectedPattern | null {
    if (candles.length < 40) return null;
    const highs = candles.map((c, i) => ({ i, price: c.high })).filter((h, i, arr) =>
      i > 0 && i < arr.length - 1 && h.price > arr[i - 1].price && h.price > arr[i + 1].price
    );
    for (let i = 0; i < highs.length - 1; i++) {
      for (let j = i + 1; j < highs.length; j++) {
        const diff = Math.abs(highs[i].price - highs[j].price) / highs[i].price;
        if (diff <= 0.03) {
          const trough = Math.min(...candles.slice(highs[i].i, highs[j].i + 1).map(c => c.low));
          const neckline = trough;
          const height = highs[i].price - neckline;
          return {
            id: `double_top_${highs[i].i}_${highs[j].i}`,
            type: "double_top",
            symbol: "",
            timeframe: "1h",
            confidence: Math.max(this.minConfidence, 100 - diff * 200),
            startTime: candles[highs[i].i].time,
            endTime: candles[highs[j].i].time,
            startPrice: highs[i].price,
            endPrice: highs[j].price,
            targetPrice: neckline - height,
            stopLoss: Math.max(highs[i].price, highs[j].i) * 1.02,
            bullish: false,
            detectedAt: Date.now(),
          };
        }
      }
    }
    return null;
  }

  private detectDoubleBottom(candles: Candle[]): DetectedPattern | null {
    if (candles.length < 40) return null;
    const lows = candles.map((c, i) => ({ i, price: c.low })).filter((l, i, arr) =>
      i > 0 && i < arr.length - 1 && l.price < arr[i - 1].price && l.price < arr[i + 1].price
    );
    for (let i = 0; i < lows.length - 1; i++) {
      for (let j = i + 1; j < lows.length; j++) {
        const diff = Math.abs(lows[i].price - lows[j].price) / lows[i].price;
        if (diff <= 0.03) {
          const peak = Math.max(...candles.slice(lows[i].i, lows[j].i + 1).map(c => c.high));
          const neckline = peak;
          const height = neckline - lows[i].price;
          return {
            id: `double_bottom_${lows[i].i}_${lows[j].i}`,
            type: "double_bottom",
            symbol: "",
            timeframe: "1h",
            confidence: Math.max(this.minConfidence, 100 - diff * 200),
            startTime: candles[lows[i].i].time,
            endTime: candles[lows[j].i].time,
            startPrice: lows[i].price,
            endPrice: lows[j].price,
            targetPrice: neckline + height,
            stopLoss: Math.min(lows[i].price, lows[j].price) * 0.98,
            bullish: true,
            detectedAt: Date.now(),
          };
        }
      }
    }
    return null;
  }

  private detectAscendingTriangle(candles: Candle[]): DetectedPattern | null {
    if (candles.length < 50) return null;
    const recent = candles.slice(-50);
    const highs = recent.map(c => c.high);
    const resistance = this.findHorizontalLevel(highs, 3, 0.01);
    if (!resistance) return null;
    const lows = recent.map(c => c.low);
    const rising = this.findRisingTrendline(lows);
    if (!rising) return null;
    return {
      id: `asc_tri_${Date.now()}`,
      type: "ascending_triangle",
      symbol: "",
      timeframe: "1h",
      confidence: 75,
      startTime: recent[0].time,
      endTime: recent[recent.length - 1].time,
      startPrice: rising.slope,
      endPrice: resistance,
      targetPrice: resistance + (resistance - rising.intercept),
      bullish: true,
      detectedAt: Date.now(),
    };
  }

  private detectDescendingTriangle(candles: Candle[]): DetectedPattern | null {
    if (candles.length < 50) return null;
    const recent = candles.slice(-50);
    const lows = recent.map(c => c.low);
    const support = this.findHorizontalLevel(lows, 3, 0.01);
    if (!support) return null;
    const highs = recent.map(c => c.high);
    const falling = this.findFallingTrendline(highs);
    if (!falling) return null;
    return {
      id: `desc_tri_${Date.now()}`,
      type: "descending_triangle",
      symbol: "",
      timeframe: "1h",
      confidence: 75,
      startTime: recent[0].time,
      endTime: recent[recent.length - 1].time,
      startPrice: falling.intercept,
      endPrice: support,
      targetPrice: support - (falling.intercept - support),
      bullish: false,
      detectedAt: Date.now(),
    };
  }

  private detectHeadShoulders(candles: Candle[]): DetectedPattern | null {
    if (candles.length < 60) return null;
    const highs = candles.map((c, i) => ({ i, price: c.high })).filter((h, i, arr) =>
      i > 0 && i < arr.length - 1 && h.price > arr[i - 1].price && h.price > arr[i + 1].price
    );
    if (highs.length < 3) return null;
    for (let l = 0; l < highs.length - 2; l++) {
      const left = highs[l];
      const head = highs[l + 1];
      const right = highs[l + 2];
      if (head.price > left.price && head.price > right.price) {
        const diffL = Math.abs(left.price - right.price) / left.price;
        const heightL = head.price - Math.min(left.price, right.price);
        if (diffL <= 0.05 && heightL > 0) {
          return {
            id: `hs_${left.i}_${head.i}_${right.i}`,
            type: "head_shoulders",
            symbol: "",
            timeframe: "1h",
            confidence: 70,
            startTime: candles[left.i].time,
            endTime: candles[right.i].time,
            startPrice: left.price,
            endPrice: right.price,
            targetPrice: Math.min(left.price, right.price) - heightL,
            stopLoss: head.price * 1.02,
            bullish: false,
            detectedAt: Date.now(),
          };
        }
      }
    }
    return null;
  }

  private findHorizontalLevel(prices: number[], minTouches: number, tolerance: number): number | null {
    const groups: Map<number, number> = new Map();
    for (const price of prices) {
      const rounded = Math.round(price / (price * tolerance)) * (price * tolerance);
      groups.set(rounded, (groups.get(rounded) || 0) + 1);
    }
    for (const [level, touches] of groups) {
      if (touches >= minTouches) return level;
    }
    return null;
  }

  private findRisingTrendline(prices: number[]): { slope: number; intercept: number } | null {
    if (prices.length < 5) return null;
    const n = prices.length;
    const xs = prices.map((_, i) => i);
    const sumX = xs.reduce((a, b) => a + b, 0);
    const sumY = prices.reduce((a, b) => a + b, 0);
    const sumXY = xs.reduce((acc, x, i) => acc + x * prices[i], 0);
    const sumX2 = xs.reduce((acc, x) => acc + x * x, 0);
    const denom = n * sumX2 - sumX * sumX;
    if (Math.abs(denom) < 0.001) return null;
    const slope = (n * sumXY - sumX * sumY) / denom;
    const intercept = (sumY - slope * sumX) / n;
    return slope > 0 ? { slope, intercept } : null;
  }

  private findFallingTrendline(prices: number[]): { slope: number; intercept: number } | null {
    if (prices.length < 5) return null;
    const n = prices.length;
    const xs = prices.map((_, i) => i);
    const sumX = xs.reduce((a, b) => a + b, 0);
    const sumY = prices.reduce((a, b) => a + b, 0);
    const sumXY = xs.reduce((acc, x, i) => acc + x * prices[i], 0);
    const sumX2 = xs.reduce((acc, x) => acc + x * x, 0);
    const denom = n * sumX2 - sumX * sumX;
    if (Math.abs(denom) < 0.001) return null;
    const slope = (n * sumXY - sumX * sumY) / denom;
    const intercept = (sumY - slope * sumX) / n;
    return slope < 0 ? { slope, intercept } : null;
  }
}

export const patternDetector = new PatternDetector();