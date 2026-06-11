import type { Candle } from "@/types";

export interface PointFigureConfig {
  boxSize: number | "atr";
  atrPeriod?: number;
  reversalBoxes?: number;
}

function calculateATR(candles: Candle[], period: number): number {
  if (candles.length < 2) return 0;

  const len = Math.min(period, candles.length - 1);
  let sum = 0;

  for (let i = 1; i <= len; i += 1) {
    const high = candles[i].high;
    const low = candles[i].low;
    const prevClose = candles[i - 1].close;
    sum += Math.max(high - low, Math.abs(high - prevClose), Math.abs(low - prevClose));
  }

  return sum / len;
}

/**
 * Transform standard candles to Point & Figure style box columns.
 * The output stays candle-shaped so it can render on Lightweight Charts.
 */
export function toPointFigure(
  candles: Candle[],
  config: PointFigureConfig = { boxSize: "atr", atrPeriod: 14, reversalBoxes: 3 },
): Candle[] {
  if (candles.length < 2) return [];

  const atr = calculateATR(candles, config.atrPeriod ?? 14);
  const fallbackBox = Math.max(candles[0].close * 0.005, 0.000001);
  const boxSize = typeof config.boxSize === "number" ? config.boxSize : atr || fallbackBox;
  const reversalBoxes = Math.max(1, config.reversalBoxes ?? 3);
  if (boxSize <= 0) return [];

  const roundedStart = Math.round(candles[0].close / boxSize) * boxSize;
  let columnClose = roundedStart;
  let direction: "x" | "o" = candles[1].close >= candles[0].close ? "x" : "o";
  const result: Candle[] = [];
  let lastEmittedTime = Number.NEGATIVE_INFINITY;

  const nextTime = (baseTime: number): number => {
    lastEmittedTime = Math.max(baseTime, lastEmittedTime + 1);
    return lastEmittedTime;
  };

  for (let i = 1; i < candles.length; i += 1) {
    const candle = candles[i];
    const price = candle.close;

    if (direction === "x") {
      if (price >= columnClose + boxSize) {
        const boxes = Math.floor((price - columnClose) / boxSize);
        const nextClose = columnClose + boxes * boxSize;
        result.push({
          time: nextTime(candle.time),
          open: columnClose,
          high: nextClose,
          low: columnClose,
          close: nextClose,
          volume: 0,
        });
        columnClose = nextClose;
      } else if (price <= columnClose - reversalBoxes * boxSize) {
        const boxes = Math.floor((columnClose - price) / boxSize);
        const nextClose = columnClose - boxes * boxSize;
        result.push({
          time: nextTime(candle.time),
          open: columnClose,
          high: columnClose,
          low: nextClose,
          close: nextClose,
          volume: 0,
        });
        columnClose = nextClose;
        direction = "o";
      }
    } else if (price <= columnClose - boxSize) {
      const boxes = Math.floor((columnClose - price) / boxSize);
      const nextClose = columnClose - boxes * boxSize;
      result.push({
        time: nextTime(candle.time),
        open: columnClose,
        high: columnClose,
        low: nextClose,
        close: nextClose,
        volume: 0,
      });
      columnClose = nextClose;
    } else if (price >= columnClose + reversalBoxes * boxSize) {
      const boxes = Math.floor((price - columnClose) / boxSize);
      const nextClose = columnClose + boxes * boxSize;
      result.push({
        time: nextTime(candle.time),
        open: columnClose,
        high: nextClose,
        low: columnClose,
        close: nextClose,
        volume: 0,
      });
      columnClose = nextClose;
      direction = "x";
    }
  }

  return result;
}
