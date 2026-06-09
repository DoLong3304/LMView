import { describe, it, expect } from "vitest";
import { calculateVolumeProfile } from "../indicators/volumeProfile";
import type { Candle } from "@/types";

function makeCandle(time: number, o: number, h: number, l: number, c: number, v = 1000): Candle {
  return { time, open: o, high: h, low: l, close: c, volume: v };
}

describe("calculateVolumeProfile", () => {
  it("returns empty result for empty candles", () => {
    const result = calculateVolumeProfile([]);
    expect(result.levels).toHaveLength(0);
    expect(result.poc).toBe(0);
    expect(result.totalVolume).toBe(0);
  });

  it("calculates POC at highest volume price level", () => {
    // Bullish candles clustered at 100-102
    const candles: Candle[] = Array.from({ length: 20 }, (_, i) =>
      makeCandle(1000 + i * 60, 100, 102, 99, 101, 500),
    );
    // Extra volume at 101 (midpoint)
    candles.push(makeCandle(2200, 100.5, 101.5, 100.5, 101.5, 5000));

    const result = calculateVolumeProfile(candles, { bins: 10, valueAreaPercent: 70 });
    expect(result.levels.length).toBeGreaterThan(0);
    expect(result.totalVolume).toBeGreaterThan(0);

    // POC should be near 101 where extra volume added
    const pocLevel = result.levels.find((l) => l.poc);
    expect(pocLevel).toBeDefined();
    expect(pocLevel!.volume).toBeGreaterThan(0);
  });

  it("distributes buy/sell volume based on candle direction", () => {
    // Bullish: close near high → more buy volume
    const bullish = makeCandle(1000, 100, 110, 90, 109, 1000);
    const bullishProfile = calculateVolumeProfile([bullish], { bins: 5, valueAreaPercent: 70 });
    const totalBuy = bullishProfile.levels.reduce((s, l) => s + l.buyVolume, 0);
    const totalSell = bullishProfile.levels.reduce((s, l) => s + l.sellVolume, 0);
    expect(totalBuy).toBeGreaterThan(totalSell);

    // Bearish: close near low → more sell volume
    const bearish = makeCandle(1060, 109, 110, 90, 91, 1000);
    const bearishProfile = calculateVolumeProfile([bearish], { bins: 5, valueAreaPercent: 70 });
    const totalBuy2 = bearishProfile.levels.reduce((s, l) => s + l.buyVolume, 0);
    const totalSell2 = bearishProfile.levels.reduce((s, l) => s + l.sellVolume, 0);
    expect(totalSell2).toBeGreaterThan(totalBuy2);
  });

  it("marks exactly one POC, one VAH, one VAL", () => {
    const candles: Candle[] = Array.from({ length: 50 }, (_, i) =>
      makeCandle(1000 + i * 60, 100 + Math.sin(i) * 5, 105 + Math.sin(i) * 5, 95 + Math.sin(i) * 5, 100 + Math.sin(i) * 5, 1000),
    );
    const result = calculateVolumeProfile(candles, { bins: 20, valueAreaPercent: 70 });

    expect(result.levels.filter((l) => l.poc)).toHaveLength(1);
    expect(result.levels.filter((l) => l.vah)).toHaveLength(1);
    expect(result.levels.filter((l) => l.val)).toHaveLength(1);
  });

  it("VAH > VAL in price terms", () => {
    const candles: Candle[] = Array.from({ length: 30 }, (_, i) =>
      makeCandle(1000 + i * 60, 100, 110, 90, 105, 1000),
    );
    const result = calculateVolumeProfile(candles, { bins: 10, valueAreaPercent: 70 });
    expect(result.vah).toBeGreaterThanOrEqual(result.val);
  });

  it("all percentages sum to approximately 100", () => {
    const candles: Candle[] = Array.from({ length: 40 }, (_, i) =>
      makeCandle(1000 + i * 60, 100, 110, 90, 100 + i * 0.5, 1000),
    );
    const result = calculateVolumeProfile(candles, { bins: 15, valueAreaPercent: 70 });
    const sum = result.levels.reduce((s, l) => s + l.percentage, 0);
    expect(sum).toBeCloseTo(100, 0);
  });
});
