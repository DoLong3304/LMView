import type { Candle } from "@/types";

export interface LineBreakBlock {
  time: number;
  open: number;
  close: number;
  high: number;
  low: number;
  bullish: boolean;
}

export interface LineBreakConfig {
  lookback: number; // Number of lines to consider (typically 3)
}

/**
 * Transform standard candles to Line Break blocks.
 * Uses a configurable lookback period (default 3 = Three-Line Break).
 */
export function toLineBreak(
  candles: Candle[],
  config: LineBreakConfig = { lookback: 3 },
): LineBreakBlock[] {
  if (candles.length < 2) return [];

  const blocks: LineBreakBlock[] = [];
  const lookback = config.lookback;

  for (let i = 0; i < candles.length; i++) {
    const candle = candles[i];
    if (blocks.length === 0) {
      const bullish = candle.close >= candle.open;
      blocks.push({
        time: candle.time,
        open: candle.open,
        close: candle.close,
        high: candle.high,
        low: candle.low,
        bullish,
      });
      continue;
    }

    const lastBlock = blocks[blocks.length - 1];
    const prevClose = lastBlock.close;
    const lookbackClose = getNthLastClose(blocks, lookback);

    if (candle.close > Math.max(prevClose, lookbackClose)) {
      // New bullish block
      blocks.push({
        time: candle.time,
        open: prevClose,
        close: candle.close,
        high: candle.high,
        low: candle.low,
        bullish: true,
      });
    } else if (candle.close < Math.min(prevClose, lookbackClose)) {
      // New bearish block
      blocks.push({
        time: candle.time,
        open: prevClose,
        close: candle.close,
        high: candle.high,
        low: candle.low,
        bullish: false,
      });
    }
    // Otherwise: no new block, price within range
  }

  return blocks;
}

function getNthLastClose(blocks: LineBreakBlock[], n: number): number {
  const idx = Math.max(0, blocks.length - n);
  return blocks[idx].close;
}
