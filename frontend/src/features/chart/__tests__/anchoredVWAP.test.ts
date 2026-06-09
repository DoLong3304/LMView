import { describe, it, expect } from "vitest";
import { calculateAnchoredVWAP } from "../indicators/anchoredVWAP";
import type { Candle } from "@/types";

function makeCandle(time: number, o: number, h: number, l: number, c: number, v = 1000): Candle {
  return { time, open: o, high: h, low: l, close: c, volume: v };
}

describe("calculateAnchoredVWAP", () => {
  const candles: Candle[] = Array.from({ length: 50 }, (_, i) =>
    makeCandle(1700000000 + i * 3600, 100 + i * 0.5, 101 + i * 0.5, 99 + i * 0.5, 100.5 + i * 0.5, 1000),
  );

  it("returns empty for empty candles", () => {
    expect(calculateAnchoredVWAP([], { anchorType: "session", showBands: false, bandStdDev: 2, bandPeriod: 20 })).toHaveLength(0);
  });

  it("calculates VWAP from session start", () => {
    const result = calculateAnchoredVWAP(candles, { anchorType: "session", showBands: false, bandStdDev: 2, bandPeriod: 20 });
    expect(result.length).toBe(50);
    // VWAP should be within price range
    const minPrice = Math.min(...candles.map((c) => c.low));
    const maxPrice = Math.max(...candles.map((c) => c.high));
    for (const level of result) {
      expect(level.value).toBeGreaterThanOrEqual(minPrice);
      expect(level.value).toBeLessThanOrEqual(maxPrice);
    }
  });

  it("VWAP values are monotonically progressing with trend", () => {
    // Uptrending candles
    const upCandles: Candle[] = Array.from({ length: 30 }, (_, i) =>
      makeCandle(1700000000 + i * 3600, 100 + i, 101 + i, 99 + i, 100.5 + i, 1000),
    );
    const result = calculateAnchoredVWAP(upCandles, { anchorType: "session", showBands: false, bandStdDev: 2, bandPeriod: 10 });
    // VWAP should trend upward
    expect(result[result.length - 1].value).toBeGreaterThan(result[0].value);
  });

  it("includes bands when showBands=true", () => {
    const result = calculateAnchoredVWAP(candles, {
      anchorType: "session",
      showBands: true,
      bandStdDev: 2,
      bandPeriod: 10,
    });
    // First bandPeriod levels won't have bands
    const withBands = result.filter((l) => l.upperBand !== undefined);
    expect(withBands.length).toBeGreaterThan(0);

    for (const level of withBands) {
      expect(level.upperBand).toBeGreaterThan(level.value);
      expect(level.lowerBand).toBeLessThan(level.value);
    }
  });

  it("no bands when showBands=false", () => {
    const result = calculateAnchoredVWAP(candles, {
      anchorType: "session",
      showBands: false,
      bandStdDev: 2,
      bandPeriod: 10,
    });
    expect(result.every((l) => l.upperBand === undefined && l.lowerBand === undefined)).toBe(true);
  });

  it("custom anchor starts from specified time", () => {
    const midTime = candles[25].time;
    const result = calculateAnchoredVWAP(candles, {
      anchorType: "custom",
      customStartTime: midTime,
      showBands: false,
      bandStdDev: 2,
      bandPeriod: 10,
    });
    expect(result.length).toBeLessThanOrEqual(25);
    if (result.length > 0) {
      expect(result[0].time).toBeGreaterThanOrEqual(midTime);
    }
  });
});
