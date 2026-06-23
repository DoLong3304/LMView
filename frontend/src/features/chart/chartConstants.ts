import { TIMEFRAME_KEYS } from "@/constants/timeframes";
import type { IndicatorSettings } from "@/types";

function cssToken(name: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function getChartTheme() {
  return {
    background: cssToken("--lm-bg-primary", "#000000"),
    textColor: cssToken("--lm-text-secondary", "#b0b0b0"),
    gridColor: cssToken("--lm-grid", "#1a1a1a"),
    borderColor: cssToken("--lm-border", "#222222"),
    upColor: cssToken("--lm-green", "#00c853"),
    downColor: cssToken("--lm-red", "#ff1744"),
    crosshair: cssToken("--lm-crosshair", "#555555"),
    crosshairLabelBg: cssToken("--lm-bg-elevated", "#1a1a1a"),
    volumeUp: cssToken("--lm-volume-up", "rgba(0, 200, 83, 0.5)"),
    volumeDown: cssToken("--lm-volume-down", "rgba(255, 23, 68, 0.5)"),
    sma20: cssToken("--lm-indicator-sma20", "#fbbf24"),
    sma50: cssToken("--lm-indicator-sma50", "#f97316"),
    ema: cssToken("--lm-indicator-ema", "#8b5cf6"),
    ema12: cssToken("--lm-indicator-ema12", "#a78bfa"),
    ema26: cssToken("--lm-indicator-ema26", "#c084fc"),
    rsi: cssToken("--lm-indicator-rsi", "#06b6d4"),
    mfi: cssToken("--lm-indicator-mfi", "#ec4899"),
    bb: cssToken("--lm-indicator-bb", "#38bdf8"),
    bbBasis: cssToken("--lm-indicator-bb-basis", "#94a3b8"),
    vwap: cssToken("--lm-indicator-vwap", "#14b8a6"),
    volumeMa: cssToken("--lm-indicator-volume-ma", "#f59e0b"),
    macd: cssToken("--lm-indicator-macd", "#60a5fa"),
    macdSignal: cssToken("--lm-indicator-macd-signal", "#f97316"),
    stochastic: cssToken("--lm-indicator-stochastic", "#22c55e"),
    stochasticSignal: cssToken("--lm-indicator-stochastic-signal", "#facc15"),
    atr: cssToken("--lm-indicator-atr", "#fb7185"),
    ichimokuConversion: cssToken("--lm-indicator-ichimoku-conversion", "#60a5fa"),
    ichimokuBase: cssToken("--lm-indicator-ichimoku-base", "#f43f5e"),
    ichimokuSpanA: cssToken("--lm-indicator-ichimoku-span-a", "#22c55e"),
    ichimokuSpanB: cssToken("--lm-indicator-ichimoku-span-b", "#f97316"),
    supertrend: cssToken("--lm-indicator-supertrend", "#10b981"),
    psar: cssToken("--lm-indicator-psar", "#f472b6"),
  } as const;
}

export const THEME = {
  background: cssToken("--lm-bg-primary", "#000000"),
  textColor: cssToken("--lm-text-secondary", "#b0b0b0"),
  gridColor: cssToken("--lm-grid", "#1a1a1a"),
  borderColor: cssToken("--lm-border", "#222222"),
  upColor: cssToken("--lm-green", "#00c853"),
  downColor: cssToken("--lm-red", "#ff1744"),
  crosshair: cssToken("--lm-crosshair", "#555555"),
  crosshairLabelBg: cssToken("--lm-bg-elevated", "#1a1a1a"),
  volumeUp: cssToken("--lm-volume-up", "rgba(0, 200, 83, 0.5)"),
  volumeDown: cssToken("--lm-volume-down", "rgba(255, 23, 68, 0.5)"),
  sma20: cssToken("--lm-indicator-sma20", "#fbbf24"),
  sma50: cssToken("--lm-indicator-sma50", "#f97316"),
  ema: cssToken("--lm-indicator-ema", "#8b5cf6"),
  ema12: cssToken("--lm-indicator-ema12", "#a78bfa"),
  ema26: cssToken("--lm-indicator-ema26", "#c084fc"),
  rsi: cssToken("--lm-indicator-rsi", "#06b6d4"),
  mfi: cssToken("--lm-indicator-mfi", "#ec4899"),
  bb: cssToken("--lm-indicator-bb", "#38bdf8"),
  bbBasis: cssToken("--lm-indicator-bb-basis", "#94a3b8"),
  vwap: cssToken("--lm-indicator-vwap", "#14b8a6"),
  volumeMa: cssToken("--lm-indicator-volume-ma", "#f59e0b"),
  macd: cssToken("--lm-indicator-macd", "#60a5fa"),
  macdSignal: cssToken("--lm-indicator-macd-signal", "#f97316"),
  stochastic: cssToken("--lm-indicator-stochastic", "#22c55e"),
  stochasticSignal: cssToken("--lm-indicator-stochastic-signal", "#facc15"),
  atr: cssToken("--lm-indicator-atr", "#fb7185"),
  ichimokuConversion: cssToken("--lm-indicator-ichimoku-conversion", "#60a5fa"),
  ichimokuBase: cssToken("--lm-indicator-ichimoku-base", "#f43f5e"),
  ichimokuSpanA: cssToken("--lm-indicator-ichimoku-span-a", "#22c55e"),
  ichimokuSpanB: cssToken("--lm-indicator-ichimoku-span-b", "#f97316"),
  supertrend: cssToken("--lm-indicator-supertrend", "#10b981"),
  psar: cssToken("--lm-indicator-psar", "#f472b6"),
} as const;

export const TIMEFRAMES = TIMEFRAME_KEYS;

export function localTickMarkFormatter(
  time: number,
  tickMarkType: number,
  locale: string,
): string {
  const d = new Date(time * 1000);
  switch (tickMarkType) {
    case 0:
      return d.toLocaleDateString(locale, { year: "numeric" });
    case 1:
      return d.toLocaleDateString(locale, { month: "short", year: "numeric" });
    case 2:
      return d.toLocaleDateString(locale, { month: "short", day: "numeric" });
    case 3:
      return d.toLocaleTimeString(locale, {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    case 4:
      return d.toLocaleTimeString(locale, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
    default:
      return d.toLocaleDateString(locale);
  }
}

export function localTimeFormatter(time: number): string {
  const d = new Date(time * 1000);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export const REALTIME_POLL_MS = 2000;

export const DEFAULT_INDICATOR_SETTINGS: Record<string, IndicatorSettings> = {
  sma20: { period: 20, color: THEME.sma20, lineWidth: 1, visible: true, type: "SMA" },
  sma50: { period: 50, color: THEME.sma50, lineWidth: 1, visible: true, type: "SMA" },
  ema12: { period: 12, color: THEME.ema12, lineWidth: 1.5, visible: false, type: "EMA" },
  ema26: { period: 26, color: THEME.ema26, lineWidth: 1.5, visible: false, type: "EMA" },
  bb: { period: 20, multiplier: 2, color: THEME.bb, basisColor: THEME.bbBasis, lineWidth: 1, visible: false, type: "BB" },
  vwap: { color: THEME.vwap, lineWidth: 1.5, visible: false, type: "VWAP" },
  supertrend: { period: 10, multiplier: 3, color: THEME.supertrend, lineWidth: 1.5, visible: false, type: "Supertrend" },
  psar: { step: 0.02, maxStep: 0.2, color: THEME.psar, lineWidth: 1, visible: false, type: "PSAR" },
  ichimoku: {
    conversionPeriod: 9,
    basePeriod: 26,
    spanPeriod: 52,
    displacement: 26,
    color: THEME.ichimokuConversion,
    baseColor: THEME.ichimokuBase,
    spanAColor: THEME.ichimokuSpanA,
    spanBColor: THEME.ichimokuSpanB,
    lineWidth: 1,
    visible: false,
    type: "Ichimoku",
  },
  volume: { visible: true, upColor: THEME.volumeUp, downColor: THEME.volumeDown },
  volumeMa: { period: 20, color: THEME.volumeMa, lineWidth: 1, visible: false, type: "Volume MA" },
  rsi: { period: 14, overbought: 70, oversold: 30, color: THEME.rsi, visible: false },
  mfi: { period: 14, overbought: 80, oversold: 20, color: THEME.mfi, visible: false },
  macd: {
    fastPeriod: 12,
    slowPeriod: 26,
    signalPeriod: 9,
    color: THEME.macd,
    signalColor: THEME.macdSignal,
    lineWidth: 1.5,
    visible: false,
    type: "MACD",
  },
  stochastic: {
    period: 14,
    signalPeriod: 3,
    overbought: 80,
    oversold: 20,
    color: THEME.stochastic,
    signalColor: THEME.stochasticSignal,
    lineWidth: 1.5,
    visible: false,
    type: "Stochastic",
  },
  atr: { period: 14, color: THEME.atr, lineWidth: 1.5, visible: false, type: "ATR" },
  support_resistance: {
    lookback: 50,
    resistanceColor: THEME.sma20,
    supportColor: THEME.volumeMa,
    lineWidth: 1,
    visible: false,
    type: "S/R",
  },
};
