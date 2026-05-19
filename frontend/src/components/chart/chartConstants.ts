import type { LucideIcon } from "lucide-react";
import { BarChart3, BookOpen, ArrowLeftRight, Newspaper } from "lucide-react";
import type { IndicatorSettings } from "../../types";
import { tradingTheme } from "../../styles/tradingTheme";

// Pure Black Theme — dùng tradingTheme tokens
export const THEME = {
  // Background
  background: tradingTheme.bgPrimary,           // #000000
  textColor: tradingTheme.priceScaleText,       // #b0b0b0
  gridColor: tradingTheme.gridColor,            // #1a1a1a
  borderColor: tradingTheme.borderColor,        // #222222

  // Candle colors — bright on black
  upColor: tradingTheme.candleUpColor,          // #00c853
  downColor: tradingTheme.candleDownColor,      // #ff1744

  // Crosshair
  crosshair: tradingTheme.crosshair,            // #555555

  // Volume
  volumeUp: tradingTheme.volumeUp,              // rgba(0, 200, 83, 0.5)
  volumeDown: tradingTheme.volumeDown,          // rgba(255, 23, 68, 0.5)

  // Indicators — giữ nguyên màu để phân biệt
  sma20: "#fbbf24",    // Yellow — vẫn dễ nhìn trên nền đen
  sma50: "#f97316",    // Orange
  ema: "#8b5cf6",      // Purple
  rsi: "#06b6d4",      // Cyan
  mfi: "#ec4899",      // Pink
} as const;

export const TIMEFRAMES = ["1s", "1m", "5m", "15m", "1H", "4H", "1D", "1W"] as const;

/**
 * Custom tick-mark formatter for lightweight-charts time scale.
 */
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

/**
 * Crosshair / tooltip time formatter.
 */
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

// Real-time polling interval (ms)
export const REALTIME_POLL_MS = 2000;

export const CHART_TABS = ["chart", "orderBook", "recentTrades", "marketNews"] as const;
export type ChartTab = (typeof CHART_TABS)[number];

export const TAB_ICONS: Record<ChartTab, LucideIcon> = {
  chart: BarChart3,
  orderBook: BookOpen,
  recentTrades: ArrowLeftRight,
  marketNews: Newspaper,
};

export const DEFAULT_INDICATOR_SETTINGS: Record<string, IndicatorSettings> = {
  sma20: { period: 20, color: THEME.sma20, lineWidth: 1, visible: true, type: "SMA" },
  sma50: { period: 50, color: THEME.sma50, lineWidth: 1, visible: true, type: "SMA" },
  ema: { period: 20, color: THEME.ema, lineWidth: 1.5, visible: false, type: "EMA" },
  volume: { visible: true, upColor: THEME.volumeUp, downColor: THEME.volumeDown },
  rsi: { period: 14, overbought: 70, oversold: 30, color: THEME.rsi, visible: false },
  mfi: { period: 14, overbought: 80, oversold: 20, color: THEME.mfi, visible: false },
};
