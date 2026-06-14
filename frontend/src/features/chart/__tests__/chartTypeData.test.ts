import { describe, expect, it } from "vitest";
import {
  buildChartTypeSeriesData,
  sanitizeCandlesForChart,
  sanitizeLineSeriesData,
} from "../chartTypeData";
import type { Candle, ChartType } from "@/types";

function makeCandle(
  time: number,
  open: number,
  high: number,
  low: number,
  close: number,
  volume = 100,
): Candle {
  return { time, open, high, low, close, volume };
}

function trendingCandles(): Candle[] {
  return Array.from({ length: 80 }, (_, index) => {
    const base = 100 + index * 0.8 + Math.sin(index / 3) * 2;
    return makeCandle(
      1_700_000_000 + index * 60,
      base,
      base + 2.5,
      base - 2.5,
      base + Math.sin(index / 2),
      1000 + index,
    );
  });
}

function expectStrictAscending(items: Array<{ time: number }>): void {
  for (let index = 1; index < items.length; index += 1) {
    expect(items[index].time).toBeGreaterThan(items[index - 1].time);
  }
}

function expectValidCandles(candles: Candle[]): void {
  expectStrictAscending(candles);
  for (const candle of candles) {
    expect(Number.isFinite(candle.time)).toBe(true);
    expect(Number.isFinite(candle.open)).toBe(true);
    expect(Number.isFinite(candle.high)).toBe(true);
    expect(Number.isFinite(candle.low)).toBe(true);
    expect(Number.isFinite(candle.close)).toBe(true);
    expect(Number.isFinite(candle.volume)).toBe(true);
    expect(candle.high).toBeGreaterThanOrEqual(candle.open);
    expect(candle.high).toBeGreaterThanOrEqual(candle.close);
    expect(candle.high).toBeGreaterThanOrEqual(candle.low);
    expect(candle.low).toBeLessThanOrEqual(candle.open);
    expect(candle.low).toBeLessThanOrEqual(candle.close);
    expect(candle.low).toBeLessThanOrEqual(candle.high);
  }
}

function expectValidLine(points: Array<{ time: number; value: number }>): void {
  expectStrictAscending(points);
  for (const point of points) {
    expect(Number.isFinite(point.time)).toBe(true);
    expect(Number.isFinite(point.value)).toBe(true);
  }
}

describe("chart type render data", () => {
  it("sanitizes raw candles before chart rendering", () => {
    const candles = sanitizeCandlesForChart([
      makeCandle(3000, 100, 90, 110, 105, -5),
      makeCandle(1000, 10, 12, 9, 11),
      makeCandle(1000, 20, 22, 18, 21),
      { time: 2000, open: Number.NaN, high: 1, low: 1, close: 1, volume: 1 },
      makeCandle(2_000_000_000_000, 30, 35, 28, 34),
    ]);

    expect(candles.map((candle) => candle.time)).toEqual([
      1000,
      3000,
      2_000_000_000,
    ]);
    expect(candles[0].open).toBe(20);
    expect(candles[1].volume).toBe(0);
    expectValidCandles(candles);
  });

  it("keeps synthetic line points strictly ascending for non-time-based charts", () => {
    const points = sanitizeLineSeriesData(
      [
        { time: 1000, value: 1 },
        { time: 1000, value: 2 },
        { time: 900, value: 3 },
        { time: 1100, value: Number.NaN },
      ],
      { syntheticTimes: true },
    );

    expect(points).toHaveLength(3);
    expectValidLine(points);
  });

  it.each<ChartType>([
    "candles",
    "bars",
    "line",
    "area",
    "heikinAshi",
    "renko",
    "lineBreak",
    "kagi",
    "pointFigure",
  ])("%s outputs data safe for its lightweight-charts series", (chartType) => {
    const renderData = buildChartTypeSeriesData(chartType, trendingCandles());

    if (chartType === "line" || chartType === "area" || chartType === "kagi") {
      expect(renderData.line.length).toBeGreaterThan(0);
      expectValidLine(renderData.line);
    } else {
      expect(renderData.candles.length).toBeGreaterThan(0);
      expectValidCandles(renderData.candles);
    }

    if (chartType === "kagi") {
      expect(renderData.candles).toHaveLength(0);
    }
  });

  it.each<ChartType>(["renko", "lineBreak", "kagi", "pointFigure"])(
    "%s falls back to source candles or closes when transformation is empty",
    (chartType) => {
      const flat = [
        makeCandle(1000, 100, 100, 100, 100),
        makeCandle(1060, 100, 100, 100, 100),
      ];
      const renderData = buildChartTypeSeriesData(chartType, flat);

      expect(renderData.usedFallback).toBe(true);
      if (chartType === "kagi") {
        expect(renderData.line).toHaveLength(2);
        expectValidLine(renderData.line);
      } else {
        expect(renderData.candles).toHaveLength(2);
        expectValidCandles(renderData.candles);
      }
    },
  );
});
