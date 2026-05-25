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
    rsi: cssToken("--lm-indicator-rsi", "#06b6d4"),
    mfi: cssToken("--lm-indicator-mfi", "#ec4899"),
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
  rsi: cssToken("--lm-indicator-rsi", "#06b6d4"),
  mfi: cssToken("--lm-indicator-mfi", "#ec4899"),
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
  ema: { period: 20, color: THEME.ema, lineWidth: 1.5, visible: false, type: "EMA" },
  volume: { visible: true, upColor: THEME.volumeUp, downColor: THEME.volumeDown },
  rsi: { period: 14, overbought: 70, oversold: 30, color: THEME.rsi, visible: false },
  mfi: { period: 14, overbought: 80, oversold: 20, color: THEME.mfi, visible: false },
};
