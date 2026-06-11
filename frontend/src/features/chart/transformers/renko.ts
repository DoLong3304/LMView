import type { Candle } from "@/types";

export interface RenkoBrick {
  time: number;
  open: number;
  close: number;
  high: number;
  low: number;
  direction: "up" | "down";
  bullish: boolean;
}

export interface RenkoConfig {
  brickSize: number | "atr";
  atrPeriod?: number;
  wicks?: boolean;
}

/** Calculate Average True Range */
function calculateATR(candles: Candle[], period: number): number {
  if (candles.length < 2) return 0;

  let sum = 0;
  const len = Math.min(period, candles.length - 1);

  for (let i = 1; i <= len; i++) {
    const high = candles[i].high;
    const low = candles[i].low;
    const prevClose = candles[i - 1].close;
    const tr = Math.max(high - low, Math.abs(high - prevClose), Math.abs(low - prevClose));
    sum += tr;
  }

  return sum / len;
}

/**
 * Transform standard candles to Renko bricks.
 * Supports fixed brick size or ATR-based.
 */
export function toRenko(candles: Candle[], config: RenkoConfig): RenkoBrick[] {
  if (candles.length < 2) return [];

  const brickSize =
    typeof config.brickSize === "number" ? config.brickSize : calculateATR(candles, config.atrPeriod || 14);

  if (brickSize <= 0) return [];

  const bricks: RenkoBrick[] = [];
  let direction: "up" | "down" = candles[0].close >= candles[0].open ? "up" : "down";
  let open = Math.floor(candles[0].close / brickSize) * brickSize;
  let close = open;
  let lastEmittedTime = Number.NEGATIVE_INFINITY;

  const nextTime = (baseTime: number): number => {
    lastEmittedTime = Math.max(baseTime, lastEmittedTime + 1);
    return lastEmittedTime;
  };

  for (const candle of candles) {
    const price = candle.close;

    if (direction === "up") {
      if (price >= close + brickSize) {
        const moves = Math.floor((price - close) / brickSize);
        for (let i = 0; i < moves; i++) {
          open = close;
          close = open + brickSize;
          direction = "up";
          bricks.push({
            time: nextTime(candle.time),
            open,
            close,
            high: close,
            low: open,
            direction: "up",
            bullish: true,
          });
        }
      } else if (price <= close - 2 * brickSize) {
        // Reversal: need 2 bricks minimum
        const moves = Math.floor((close - price) / brickSize);
        for (let i = 0; i < moves; i++) {
          open = close;
          close = open - brickSize;
          direction = "down";
          bricks.push({
            time: nextTime(candle.time),
            open,
            close,
            high: open,
            low: close,
            direction: "down",
            bullish: false,
          });
        }
      }
    } else {
      // direction === "down"
      if (price <= close - brickSize) {
        const moves = Math.floor((close - price) / brickSize);
        for (let i = 0; i < moves; i++) {
          open = close;
          close = open - brickSize;
          direction = "down";
          bricks.push({
            time: nextTime(candle.time),
            open,
            close,
            high: open,
            low: close,
            direction: "down",
            bullish: false,
          });
        }
      } else if (price >= close + 2 * brickSize) {
        // Reversal
        const moves = Math.floor((price - close) / brickSize);
        for (let i = 0; i < moves; i++) {
          open = close;
          close = open + brickSize;
          direction = "up";
          bricks.push({
            time: nextTime(candle.time),
            open,
            close,
            high: close,
            low: open,
            direction: "up",
            bullish: true,
          });
        }
      }
    }
  }

  return bricks;
}
