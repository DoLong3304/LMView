import type { Candle, ChartType } from "@/types";
import { toHeikinAshi } from "./transformers/heikinAshi";
import { toKagi } from "./transformers/kagi";
import { toLineBreak } from "./transformers/lineBreak";
import { toPointFigure } from "./transformers/pointFigure";
import { toRenko } from "./transformers/renko";

export interface LineSeriesPoint {
  time: number;
  value: number;
}

export interface ChartTypeSeriesData {
  candles: Candle[];
  line: LineSeriesPoint[];
  sourceCandles: Candle[];
  usedFallback: boolean;
}

interface SanitizeOptions {
  syntheticTimes?: boolean;
}

function finiteNumber(value: unknown): number | null {
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeChartTime(value: unknown): number | null {
  const numeric = finiteNumber(value);
  if (numeric === null || numeric <= 0) return null;
  return Math.floor(numeric > 1_000_000_000_000 ? numeric / 1000 : numeric);
}

export function sanitizeCandlesForChart(
  rows: Array<Partial<Candle>>,
  options: SanitizeOptions = {},
): Candle[] {
  const normalized: Candle[] = [];

  for (const row of rows) {
    const time = normalizeChartTime(row.time);
    const open = finiteNumber(row.open);
    const close = finiteNumber(row.close);
    const rawHigh = finiteNumber(row.high);
    const rawLow = finiteNumber(row.low);
    const volume = finiteNumber(row.volume) ?? 0;

    if (time === null || open === null || close === null) continue;

    const high = Math.max(rawHigh ?? open, rawLow ?? open, open, close);
    const low = Math.min(rawLow ?? open, rawHigh ?? open, open, close);

    normalized.push({
      time,
      open,
      high,
      low,
      close,
      volume: Math.max(0, volume),
    });
  }

  normalized.sort((a, b) => a.time - b.time);

  if (options.syntheticTimes) {
    let previousTime = Number.NEGATIVE_INFINITY;
    return normalized.map((candle) => {
      const time = candle.time <= previousTime ? previousTime + 1 : candle.time;
      previousTime = time;
      return time === candle.time ? candle : { ...candle, time };
    });
  }

  const byTime = new Map<number, Candle>();
  for (const candle of normalized) {
    byTime.set(candle.time, candle);
  }

  return Array.from(byTime.values()).sort((a, b) => a.time - b.time);
}

export function toCloseSeriesData(candles: Candle[]): LineSeriesPoint[] {
  return candles.map((candle) => ({
    time: candle.time,
    value: candle.close,
  }));
}

export function sanitizeLineSeriesData(
  rows: Array<Partial<LineSeriesPoint>>,
  options: SanitizeOptions = {},
): LineSeriesPoint[] {
  const normalized: LineSeriesPoint[] = [];

  for (const row of rows) {
    const time = normalizeChartTime(row.time);
    const value = finiteNumber(row.value);
    if (time === null || value === null) continue;
    normalized.push({ time, value });
  }

  normalized.sort((a, b) => a.time - b.time);

  if (options.syntheticTimes) {
    let previousTime = Number.NEGATIVE_INFINITY;
    return normalized.map((point) => {
      const time = point.time <= previousTime ? previousTime + 1 : point.time;
      previousTime = time;
      return time === point.time ? point : { ...point, time };
    });
  }

  const byTime = new Map<number, LineSeriesPoint>();
  for (const point of normalized) {
    byTime.set(point.time, point);
  }

  return Array.from(byTime.values()).sort((a, b) => a.time - b.time);
}

function candleFromSourceFallback(sourceCandles: Candle[]): ChartTypeSeriesData {
  return {
    candles: sourceCandles,
    line: toCloseSeriesData(sourceCandles),
    sourceCandles,
    usedFallback: true,
  };
}

export function buildChartTypeSeriesData(
  chartType: ChartType,
  rawCandles: Candle[],
): ChartTypeSeriesData {
  const sourceCandles = sanitizeCandlesForChart(rawCandles);
  const sourceLine = toCloseSeriesData(sourceCandles);

  if (sourceCandles.length === 0) {
    return { candles: [], line: [], sourceCandles: [], usedFallback: false };
  }

  if (chartType === "kagi") {
    const line = sanitizeLineSeriesData(
      toKagi(sourceCandles, { reversalPercent: 4, useClose: true }).map(
        (kagiLine) => ({
          time: kagiLine.time,
          value: kagiLine.price,
        }),
      ),
      { syntheticTimes: true },
    );

    return {
      candles: [],
      line: line.length >= 2 ? line : sourceLine,
      sourceCandles,
      usedFallback: line.length < 2,
    };
  }

  let transformedCandles: Candle[] = sourceCandles;

  if (chartType === "heikinAshi") {
    transformedCandles = sanitizeCandlesForChart(toHeikinAshi(sourceCandles));
  } else if (chartType === "renko") {
    transformedCandles = sanitizeCandlesForChart(
      toRenko(sourceCandles, {
        brickSize: "atr",
        atrPeriod: 14,
        wicks: true,
      }).map((brick) => ({
        time: brick.time,
        open: brick.open,
        high: brick.high,
        low: brick.low,
        close: brick.close,
        volume: 0,
      })),
      { syntheticTimes: true },
    );
  } else if (chartType === "lineBreak") {
    transformedCandles = sanitizeCandlesForChart(
      toLineBreak(sourceCandles, { lookback: 3 }).map((block) => ({
        time: block.time,
        open: block.open,
        high: block.high,
        low: block.low,
        close: block.close,
        volume: 0,
      })),
      { syntheticTimes: true },
    );
  } else if (chartType === "pointFigure") {
    transformedCandles = sanitizeCandlesForChart(
      toPointFigure(sourceCandles, {
        boxSize: "atr",
        atrPeriod: 14,
        reversalBoxes: 3,
      }),
      { syntheticTimes: true },
    );
  }

  if (
    (chartType === "renko" || chartType === "lineBreak" || chartType === "pointFigure")
    && transformedCandles.length < 2
  ) {
    return candleFromSourceFallback(sourceCandles);
  }

  return {
    candles: transformedCandles,
    line: toCloseSeriesData(transformedCandles),
    sourceCandles,
    usedFallback: false,
  };
}
