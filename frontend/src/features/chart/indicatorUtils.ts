import type { Candle } from "@/types";

export interface DataPoint {
  time: number;
  value: number;
}

export interface BandData {
  middle: DataPoint[];
  upper: DataPoint[];
  lower: DataPoint[];
}

export interface MacdData {
  macd: DataPoint[];
  signal: DataPoint[];
  histogram: DataPoint[];
}

export interface StochasticData {
  k: DataPoint[];
  d: DataPoint[];
}

export interface IchimokuData {
  conversion: DataPoint[];
  base: DataPoint[];
  spanA: DataPoint[];
  spanB: DataPoint[];
  lagging: DataPoint[];
}

export function calcSMA(candles: Candle[], period: number): DataPoint[] {
  if (!candles || candles.length < period) return [];
  const out: DataPoint[] = [];
  for (let i = period - 1; i < candles.length; i++) {
    const avg =
      candles.slice(i - period + 1, i + 1).reduce((s, c) => s + c.close, 0) /
      period;
    out.push({ time: candles[i].time, value: +avg.toFixed(4) });
  }
  return out;
}

export function calcEMA(candles: Candle[], period: number): DataPoint[] {
  if (!candles || candles.length < period) return [];
  const k = 2 / (period + 1);
  const out: DataPoint[] = [];
  let ema = candles.slice(0, period).reduce((s, c) => s + c.close, 0) / period;
  out.push({ time: candles[period - 1].time, value: +ema.toFixed(4) });
  for (let i = period; i < candles.length; i++) {
    ema = candles[i].close * k + ema * (1 - k);
    out.push({ time: candles[i].time, value: +ema.toFixed(4) });
  }
  return out;
}

export function calcRSI(candles: Candle[], period: number): DataPoint[] {
  const out: DataPoint[] = [];
  if (candles.length < period + 1) return out;
  let gains = 0,
    losses = 0;
  for (let i = 1; i <= period; i++) {
    const diff = candles[i].close - candles[i - 1].close;
    if (diff > 0) gains += diff;
    else losses -= diff;
  }
  let avgGain = gains / period,
    avgLoss = losses / period;
  const rsi = (v: number) => (avgLoss === 0 ? 100 : 100 - 100 / (1 + v));
  out.push({
    time: candles[period].time,
    value: +rsi(avgGain / avgLoss).toFixed(2),
  });
  for (let i = period + 1; i < candles.length; i++) {
    const diff = candles[i].close - candles[i - 1].close;
    const g = diff > 0 ? diff : 0;
    const l = diff < 0 ? -diff : 0;
    avgGain = (avgGain * (period - 1) + g) / period;
    avgLoss = (avgLoss * (period - 1) + l) / period;
    out.push({
      time: candles[i].time,
      value: +rsi(avgGain / (avgLoss || 1e-10)).toFixed(2),
    });
  }
  return out;
}

export function calcMFI(candles: Candle[], period: number): DataPoint[] {
  const out: DataPoint[] = [];
  const typicals = candles.map((c) => ({
    time: c.time,
    tp: (c.high + c.low + c.close) / 3,
    vol: c.volume,
  }));
  for (let i = period; i < typicals.length; i++) {
    let posFlow = 0,
      negFlow = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const mf = typicals[j].tp * typicals[j].vol;
      if (typicals[j].tp >= typicals[j - 1].tp) posFlow += mf;
      else negFlow += mf;
    }
    const ratio = negFlow === 0 ? 100 : 100 - 100 / (1 + posFlow / negFlow);
    out.push({ time: typicals[i].time, value: +ratio.toFixed(2) });
  }
  return out;
}

export function calcBollingerBands(
  candles: Candle[],
  period: number,
  multiplier = 2,
): BandData {
  const middle = calcSMA(candles, period);
  const upper: DataPoint[] = [];
  const lower: DataPoint[] = [];
  if (!candles || candles.length < period) return { middle, upper, lower };

  for (let i = period - 1; i < candles.length; i++) {
    const window = candles.slice(i - period + 1, i + 1);
    const avg = window.reduce((sum, candle) => sum + candle.close, 0) / period;
    const variance = window.reduce((sum, candle) => sum + (candle.close - avg) ** 2, 0) / period;
    const deviation = Math.sqrt(variance) * multiplier;
    upper.push({ time: candles[i].time, value: +(avg + deviation).toFixed(4) });
    lower.push({ time: candles[i].time, value: +(avg - deviation).toFixed(4) });
  }

  return { middle, upper, lower };
}

export function calcVWAP(candles: Candle[]): DataPoint[] {
  const out: DataPoint[] = [];
  let cumulativePv = 0;
  let cumulativeVolume = 0;

  for (const candle of candles) {
    const typical = (candle.high + candle.low + candle.close) / 3;
    cumulativePv += typical * candle.volume;
    cumulativeVolume += candle.volume;
    if (cumulativeVolume > 0) {
      out.push({ time: candle.time, value: +(cumulativePv / cumulativeVolume).toFixed(4) });
    }
  }

  return out;
}

export function calcVolumeMA(candles: Candle[], period: number): DataPoint[] {
  if (!candles || candles.length < period) return [];
  const out: DataPoint[] = [];

  for (let i = period - 1; i < candles.length; i++) {
    const avg =
      candles.slice(i - period + 1, i + 1).reduce((sum, candle) => sum + candle.volume, 0) /
      period;
    out.push({ time: candles[i].time, value: +avg.toFixed(4) });
  }

  return out;
}

function calcEMAFromPoints(points: DataPoint[], period: number): DataPoint[] {
  if (!points || points.length < period) return [];
  const k = 2 / (period + 1);
  const out: DataPoint[] = [];
  let ema = points.slice(0, period).reduce((sum, point) => sum + point.value, 0) / period;
  out.push({ time: points[period - 1].time, value: +ema.toFixed(4) });

  for (let i = period; i < points.length; i++) {
    ema = points[i].value * k + ema * (1 - k);
    out.push({ time: points[i].time, value: +ema.toFixed(4) });
  }

  return out;
}

export function calcMACD(
  candles: Candle[],
  fastPeriod = 12,
  slowPeriod = 26,
  signalPeriod = 9,
): MacdData {
  const fast = calcEMA(candles, fastPeriod);
  const slow = calcEMA(candles, slowPeriod);
  const fastByTime = new Map(fast.map((point) => [point.time, point.value]));
  const macd = slow
    .map((point) => {
      const fastValue = fastByTime.get(point.time);
      if (fastValue === undefined) return null;
      return { time: point.time, value: +(fastValue - point.value).toFixed(4) };
    })
    .filter((point): point is DataPoint => point !== null);
  const signal = calcEMAFromPoints(macd, signalPeriod);
  const signalByTime = new Map(signal.map((point) => [point.time, point.value]));
  const histogram = macd
    .map((point) => {
      const signalValue = signalByTime.get(point.time);
      if (signalValue === undefined) return null;
      return { time: point.time, value: +(point.value - signalValue).toFixed(4) };
    })
    .filter((point): point is DataPoint => point !== null);

  return { macd, signal, histogram };
}

export function calcStochastic(
  candles: Candle[],
  period = 14,
  signalPeriod = 3,
): StochasticData {
  const k: DataPoint[] = [];
  if (!candles || candles.length < period) return { k, d: [] };

  for (let i = period - 1; i < candles.length; i++) {
    const window = candles.slice(i - period + 1, i + 1);
    const highest = Math.max(...window.map((candle) => candle.high));
    const lowest = Math.min(...window.map((candle) => candle.low));
    const value = highest === lowest ? 50 : ((candles[i].close - lowest) / (highest - lowest)) * 100;
    k.push({ time: candles[i].time, value: +value.toFixed(2) });
  }

  const d: DataPoint[] = [];
  for (let i = signalPeriod - 1; i < k.length; i++) {
    const avg = k.slice(i - signalPeriod + 1, i + 1).reduce((sum, point) => sum + point.value, 0) / signalPeriod;
    d.push({ time: k[i].time, value: +avg.toFixed(2) });
  }

  return { k, d };
}

export function calcATR(candles: Candle[], period = 14): DataPoint[] {
  if (!candles || candles.length < period + 1) return [];
  const trueRanges: DataPoint[] = [];

  for (let i = 1; i < candles.length; i++) {
    const candle = candles[i];
    const previous = candles[i - 1];
    const trueRange = Math.max(
      candle.high - candle.low,
      Math.abs(candle.high - previous.close),
      Math.abs(candle.low - previous.close),
    );
    trueRanges.push({ time: candle.time, value: trueRange });
  }

  const out: DataPoint[] = [];
  let atr = trueRanges.slice(0, period).reduce((sum, point) => sum + point.value, 0) / period;
  out.push({ time: trueRanges[period - 1].time, value: +atr.toFixed(4) });

  for (let i = period; i < trueRanges.length; i++) {
    atr = (atr * (period - 1) + trueRanges[i].value) / period;
    out.push({ time: trueRanges[i].time, value: +atr.toFixed(4) });
  }

  return out;
}

function midpoint(candles: Candle[], index: number, period: number): DataPoint | null {
  if (index < period - 1) return null;
  const window = candles.slice(index - period + 1, index + 1);
  const highest = Math.max(...window.map((candle) => candle.high));
  const lowest = Math.min(...window.map((candle) => candle.low));
  return { time: candles[index].time, value: +(((highest + lowest) / 2).toFixed(4)) };
}

export function calcIchimoku(
  candles: Candle[],
  conversionPeriod = 9,
  basePeriod = 26,
  spanPeriod = 52,
  displacement = 26,
): IchimokuData {
  const conversion: DataPoint[] = [];
  const base: DataPoint[] = [];
  const spanA: DataPoint[] = [];
  const spanB: DataPoint[] = [];
  const lagging: DataPoint[] = [];
  const conversionByTime = new Map<number, number>();
  const baseByTime = new Map<number, number>();

  candles.forEach((_, index) => {
    const conversionPoint = midpoint(candles, index, conversionPeriod);
    const basePoint = midpoint(candles, index, basePeriod);
    const spanBPoint = midpoint(candles, index, spanPeriod);

    if (conversionPoint) {
      conversion.push(conversionPoint);
      conversionByTime.set(conversionPoint.time, conversionPoint.value);
    }
    if (basePoint) {
      base.push(basePoint);
      baseByTime.set(basePoint.time, basePoint.value);
    }
    if (spanBPoint) spanB.push(spanBPoint);

    const conversionValue = conversionByTime.get(candles[index].time);
    const baseValue = baseByTime.get(candles[index].time);
    if (conversionValue !== undefined && baseValue !== undefined) {
      spanA.push({
        time: candles[index].time,
        value: +(((conversionValue + baseValue) / 2).toFixed(4)),
      });
    }

    if (index >= displacement) {
      lagging.push({ time: candles[index - displacement].time, value: candles[index].close });
    }
  });

  return { conversion, base, spanA, spanB, lagging };
}

export function calcSupertrend(
  candles: Candle[],
  period = 10,
  multiplier = 3,
): DataPoint[] {
  const atr = calcATR(candles, period);
  const atrByTime = new Map(atr.map((point) => [point.time, point.value]));
  const out: DataPoint[] = [];
  let finalUpper = 0;
  let finalLower = 0;
  let inUptrend = true;

  for (let i = 1; i < candles.length; i++) {
    const atrValue = atrByTime.get(candles[i].time);
    if (atrValue === undefined) continue;

    const hl2 = (candles[i].high + candles[i].low) / 2;
    const basicUpper = hl2 + multiplier * atrValue;
    const basicLower = hl2 - multiplier * atrValue;
    const previousClose = candles[i - 1].close;

    finalUpper = out.length === 0 || basicUpper < finalUpper || previousClose > finalUpper ? basicUpper : finalUpper;
    finalLower = out.length === 0 || basicLower > finalLower || previousClose < finalLower ? basicLower : finalLower;

    if (candles[i].close > finalUpper) inUptrend = true;
    else if (candles[i].close < finalLower) inUptrend = false;

    out.push({
      time: candles[i].time,
      value: +(inUptrend ? finalLower : finalUpper).toFixed(4),
    });
  }

  return out;
}

export function calcParabolicSAR(
  candles: Candle[],
  step = 0.02,
  maxStep = 0.2,
): DataPoint[] {
  if (!candles || candles.length < 2) return [];
  const out: DataPoint[] = [];
  let rising = candles[1].close >= candles[0].close;
  let acceleration = step;
  let extremePoint = rising ? candles[0].high : candles[0].low;
  let sar = rising ? candles[0].low : candles[0].high;

  for (let i = 1; i < candles.length; i++) {
    sar = sar + acceleration * (extremePoint - sar);

    if (rising) {
      sar = Math.min(sar, candles[i - 1].low, candles[Math.max(0, i - 2)].low);
      if (candles[i].low < sar) {
        rising = false;
        sar = extremePoint;
        extremePoint = candles[i].low;
        acceleration = step;
      } else if (candles[i].high > extremePoint) {
        extremePoint = candles[i].high;
        acceleration = Math.min(acceleration + step, maxStep);
      }
    } else {
      sar = Math.max(sar, candles[i - 1].high, candles[Math.max(0, i - 2)].high);
      if (candles[i].high > sar) {
        rising = true;
        sar = extremePoint;
        extremePoint = candles[i].high;
        acceleration = step;
      } else if (candles[i].low < extremePoint) {
        extremePoint = candles[i].low;
        acceleration = Math.min(acceleration + step, maxStep);
      }
    }

    out.push({ time: candles[i].time, value: +sar.toFixed(4) });
  }

  return out;
}

// ── Support & Resistance ─────────────────────────────────────────────────────

export interface SRLevel {
  price: number;
  type: "support" | "resistance";
  label: string;
}

export function calcSupportResistance(candles: Candle[], lookback: number = 50): SRLevel[] {
  if (candles.length < 3) return [];

  const recent = candles.slice(-lookback);
  const swingLows: number[] = [];
  const swingHighs: number[] = [];

  // Detect swing points via 3-candle pivot
  for (let i = 1; i < recent.length - 1; i++) {
    const prev = recent[i - 1];
    const curr = recent[i];
    const nxt = recent[i + 1];

    if (curr.low < prev.low && curr.low < nxt.low) {
      swingLows.push(curr.low);
    }
    if (curr.high > prev.high && curr.high > nxt.high) {
      swingHighs.push(curr.high);
    }
  }

  // Add absolute extremes
  swingLows.push(Math.min(...recent.map(c => c.low)));
  swingHighs.push(Math.max(...recent.map(c => c.high)));

  // Deduplicate nearby levels (within 0.5%)
  function dedupe(arr: number[], tol: number = 0.005): number[] {
    if (!arr.length) return [];
    const sorted = [...new Set(arr)].sort((a, b) => a - b);
    const result: number[] = [sorted[0]];
    for (let i = 1; i < sorted.length; i++) {
      if (Math.abs(sorted[i] - result[result.length - 1]) / result[result.length - 1] > tol) {
        result.push(sorted[i]);
      }
    }
    return result;
  }

  const supports = dedupe(swingLows);
  const resistances = dedupe(swingHighs);

  const currentPrice = recent[recent.length - 1].close;

  const levels: SRLevel[] = [];
  // Supports below current price (most relevant)
  for (const s of supports) {
    if (s < currentPrice) {
      levels.push({ price: s, type: "support", label: `S ${s.toFixed(2)}` });
    }
  }
  // Resistances above current price
  for (const r of resistances) {
    if (r > currentPrice) {
      levels.push({ price: r, type: "resistance", label: `R ${r.toFixed(2)}` });
    }
  }

  // Sort: closest to current price first
  levels.sort((a, b) => Math.abs(a.price - currentPrice) - Math.abs(b.price - currentPrice));

  // Keep top 6 (3 support, 3 resistance)
  const supportsOut = levels.filter(l => l.type === "support").slice(0, 3);
  const resistancesOut = levels.filter(l => l.type === "resistance").slice(0, 3);

  return [...supportsOut, ...resistancesOut];
}
