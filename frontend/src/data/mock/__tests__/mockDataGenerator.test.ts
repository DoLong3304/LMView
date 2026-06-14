import { describe, expect, it } from "vitest";
import { generateMockCandles, normalizeMockCandles } from "@/data/mock/mockDataGenerator";

function expectValidCandles(candles: ReturnType<typeof generateMockCandles>) {
  expect(candles.length).toBeGreaterThan(0);
  let previousTime = 0;
  const times = new Set<number>();

  for (const candle of candles) {
    expect(Number.isFinite(candle.time)).toBe(true);
    expect(candle.time).toBeLessThan(1_000_000_000_000);
    expect(candle.time).toBeGreaterThan(previousTime);
    expect(times.has(candle.time)).toBe(false);
    times.add(candle.time);
    previousTime = candle.time;

    for (const value of [candle.open, candle.high, candle.low, candle.close, candle.volume]) {
      expect(Number.isFinite(value)).toBe(true);
    }

    expect(candle.high).toBeGreaterThanOrEqual(candle.open);
    expect(candle.high).toBeGreaterThanOrEqual(candle.close);
    expect(candle.high).toBeGreaterThanOrEqual(candle.low);
    expect(candle.low).toBeLessThanOrEqual(candle.open);
    expect(candle.low).toBeLessThanOrEqual(candle.close);
    expect(candle.low).toBeLessThanOrEqual(candle.high);
  }
}

describe("mock candle data", () => {
  it.each(["1m", "5m", "1h", "1d"])(
    "generates valid BTCUSDT candles for %s",
    (timeframe) => {
      expectValidCandles(generateMockCandles("BTCUSDT", timeframe, 200));
    },
  );

  it("normalizes API-shaped millisecond candles to chart seconds", () => {
    const candles = normalizeMockCandles([
      { openTime: 1_700_000_000_000, open: "10", high: "12", low: "9", close: "11", volume: "100" },
      { openTime: 1_700_000_060_000, o: 11, h: 13, l: 10, c: 12, v: 120 },
      { openTime: 1_700_000_060_000, o: 12, h: 14, l: 11, c: 13, v: 140 },
    ]);

    expect(candles).toHaveLength(2);
    expect(candles[0].time).toBe(1_700_000_000);
    expect(candles[1]).toMatchObject({
      time: 1_700_000_060,
      open: 12,
      high: 14,
      low: 11,
      close: 13,
      volume: 140,
    });
  });
});
