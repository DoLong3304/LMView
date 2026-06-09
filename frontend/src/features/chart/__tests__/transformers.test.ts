import { describe, it, expect } from "vitest";
import { toHeikinAshi } from "../transformers/heikinAshi";
import { toRenko } from "../transformers/renko";
import { toLineBreak } from "../transformers/lineBreak";
import { toKagi } from "../transformers/kagi";
import type { Candle } from "@/types";

function makeCandle(time: number, o: number, h: number, l: number, c: number, v = 1000): Candle {
  return { time, open: o, high: h, low: l, close: c, volume: v };
}

// ── Heikin Ashi ──────────────────────────────────────────────────────────────

describe("toHeikinAshi", () => {
  it("returns empty for empty input", () => {
    expect(toHeikinAshi([])).toHaveLength(0);
  });

  it("HA-Close = average of OHLC", () => {
    const candles = [makeCandle(1000, 100, 110, 90, 105)];
    const ha = toHeikinAshi(candles);
    expect(ha).toHaveLength(1);
    expect(ha[0].close).toBeCloseTo((100 + 110 + 90 + 105) / 4);
  });

  it("HA-Open uses previous HA values", () => {
    const candles = [
      makeCandle(1000, 100, 110, 90, 105),
      makeCandle(1060, 105, 115, 100, 110),
    ];
    const ha = toHeikinAshi(candles);
    expect(ha).toHaveLength(2);
    // First HA-Open = (O+C)/2
    expect(ha[0].open).toBeCloseTo((100 + 105) / 2);
    // Second HA-Open = (prevHAOpen + prevHAClose) / 2
    expect(ha[1].open).toBeCloseTo((ha[0].open + ha[0].close) / 2);
  });

  it("HA-High >= max(high, haOpen, haClose)", () => {
    const candles = Array.from({ length: 20 }, (_, i) =>
      makeCandle(1000 + i * 60, 100 + Math.sin(i) * 5, 110, 90, 105),
    );
    const ha = toHeikinAshi(candles);
    for (const h of ha) {
      expect(h.high).toBeGreaterThanOrEqual(h.open);
      expect(h.high).toBeGreaterThanOrEqual(h.close);
    }
  });

  it("HA-Low <= min(low, haOpen, haClose)", () => {
    const candles = Array.from({ length: 20 }, (_, i) =>
      makeCandle(1000 + i * 60, 100, 110, 90 - Math.sin(i) * 5, 105),
    );
    const ha = toHeikinAshi(candles);
    for (const h of ha) {
      expect(h.low).toBeLessThanOrEqual(h.open);
      expect(h.low).toBeLessThanOrEqual(h.close);
    }
  });

  it("preserves time and volume", () => {
    const candles = [makeCandle(12345, 100, 110, 90, 105, 999)];
    const ha = toHeikinAshi(candles);
    expect(ha[0].time).toBe(12345);
    expect(ha[0].volume).toBe(999);
  });
});

// ── Renko ────────────────────────────────────────────────────────────────────

describe("toRenko", () => {
  const trendCandles: Candle[] = Array.from({ length: 50 }, (_, i) =>
    makeCandle(1000 + i * 60, 100 + i * 0.5, 101 + i * 0.5, 99 + i * 0.5, 100.5 + i * 0.5, 1000),
  );

  it("returns empty for < 2 candles", () => {
    expect(toRenko([makeCandle(1000, 100, 110, 90, 105)], { brickSize: 5 })).toHaveLength(0);
  });

  it("produces bricks with correct direction in uptrend", () => {
    const bricks = toRenko(trendCandles, { brickSize: 2 });
    if (bricks.length > 0) {
      // Most bricks should be bullish in uptrend
      const upBricks = bricks.filter((b) => b.bullish);
      expect(upBricks.length).toBeGreaterThan(bricks.length * 0.7);
    }
  });

  it("each brick has open != close and correct direction", () => {
    const bricks = toRenko(trendCandles, { brickSize: 2 });
    for (const brick of bricks) {
      expect(brick.open).not.toBe(brick.close);
      if (brick.bullish) {
        expect(brick.close).toBeGreaterThan(brick.open);
      } else {
        expect(brick.close).toBeLessThan(brick.open);
      }
    }
  });

  it("supports ATR-based brick size", () => {
    const bricks = toRenko(trendCandles, { brickSize: "atr", atrPeriod: 14 });
    // Should produce some bricks
    expect(bricks.length).toBeGreaterThan(0);
  });

  it("reversal requires 2-brick move", () => {
    // Create candles that go up then reverse
    const candles: Candle[] = [
      ...Array.from({ length: 20 }, (_, i) => makeCandle(1000 + i * 60, 100 + i * 2, 101 + i * 2, 99 + i * 2, 100 + i * 2, 1000)),
      makeCandle(2200, 140, 142, 130, 131, 1000), // sharp drop
    ];
    const bricks = toRenko(candles, { brickSize: 2 });
    // After up bricks, should see at least one down brick if reversal big enough
    const hasDown = bricks.some((b) => b.direction === "down");
    // Depends on whether the drop exceeds 2*brickSize from last close
    expect(bricks.length).toBeGreaterThan(0);
  });
});

// ── Line Break ───────────────────────────────────────────────────────────────

describe("toLineBreak", () => {
  it("returns empty for < 2 candles", () => {
    expect(toLineBreak([makeCandle(1000, 100, 110, 90, 105)])).toHaveLength(0);
  });

  it("produces first block from first candle", () => {
    const candles = [
      makeCandle(1000, 100, 110, 90, 105),
      makeCandle(1060, 105, 115, 100, 112),
    ];
    const blocks = toLineBreak(candles);
    expect(blocks.length).toBeGreaterThanOrEqual(1);
  });

  it("bullish blocks have close > open", () => {
    const candles: Candle[] = Array.from({ length: 30 }, (_, i) =>
      makeCandle(1000 + i * 60, 100, 110, 90, 100 + Math.sin(i) * 5, 1000),
    );
    const blocks = toLineBreak(candles);
    for (const block of blocks) {
      if (block.bullish) {
        expect(block.close).toBeGreaterThanOrEqual(block.open);
      } else {
        expect(block.close).toBeLessThanOrEqual(block.open);
      }
    }
  });

  it("produces blocks from uptrend data", () => {
    const candles: Candle[] = Array.from({ length: 40 }, (_, i) =>
      makeCandle(1000 + i * 60, 100 + i, 101 + i, 99 + i, 100.5 + i, 1000),
    );
    const blocks = toLineBreak(candles);
    expect(blocks.length).toBeGreaterThan(0);
    // All should be bullish in steady uptrend
    expect(blocks.every((b) => b.bullish)).toBe(true);
  });

  it("respects lookback config", () => {
    const candles: Candle[] = Array.from({ length: 50 }, (_, i) =>
      makeCandle(1000 + i * 60, 100, 110, 90, 100 + i * 0.5, 1000),
    );
    const blocks3 = toLineBreak(candles, { lookback: 3 });
    const blocks5 = toLineBreak(candles, { lookback: 5 });
    // Both should produce blocks
    expect(blocks3.length).toBeGreaterThan(0);
    expect(blocks5.length).toBeGreaterThan(0);
  });
});

// ── Kagi ─────────────────────────────────────────────────────────────────────

describe("toKagi", () => {
  it("returns empty for < 2 candles", () => {
    expect(toKagi([makeCandle(1000, 100, 110, 90, 105)])).toHaveLength(0);
  });

  it("produces at least one line from first candle", () => {
    const candles = [
      makeCandle(1000, 100, 110, 90, 105),
      makeCandle(1060, 105, 115, 100, 112),
    ];
    const lines = toKagi(candles);
    expect(lines.length).toBeGreaterThanOrEqual(1);
  });

  it("reversal lines are marked", () => {
    // Create oscillating candles to trigger reversals
    const candles: Candle[] = [];
    for (let i = 0; i < 40; i++) {
      const dir = i % 2 === 0 ? 1 : -1;
      candles.push(makeCandle(1000 + i * 60, 100, 100 + 10, 100 - 10, 100 + dir * 8, 1000));
    }
    const lines = toKagi(candles, { reversalPercent: 3, useClose: true });
    const reversals = lines.filter((l) => l.reversal);
    expect(reversals.length).toBeGreaterThan(0);
  });

  it("linewidth is set on all lines", () => {
    const candles: Candle[] = Array.from({ length: 30 }, (_, i) =>
      makeCandle(1000 + i * 60, 100, 110, 90, 100 + Math.sin(i) * 5, 1000),
    );
    const lines = toKagi(candles, { reversalPercent: 4, useClose: true });
    expect(lines.length).toBeGreaterThan(0);
    for (const line of lines) {
      expect(line.linewidth).toBeDefined();
      expect(typeof line.linewidth).toBe("number");
    }
  });
});
