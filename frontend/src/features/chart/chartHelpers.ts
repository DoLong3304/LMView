/**
 * Pure helper functions extracted from CandlestickChart.tsx
 */
import { ChartType, CHART_TYPES, TimeframeKey } from "@/types";
import { TIMEFRAME_KEYS } from "@/constants/timeframes";
import { getChartTheme } from "./chartConstants";
import type { ChartPreferenceSettings } from "@/services/settingsService";
import type { IndicatorSettings, IndicatorSeriesResponse } from "@/types";
import type { TranslationKey } from "@/i18n/translations";
import {
  Activity, AreaChart, BarChart3, CandlestickChart as CandleIcon,
  Grid3x3, Layers, LineChart, TrendingUp,
} from "lucide-react";
import { LineStyle, CrosshairMode } from "lightweight-charts";

export const HISTORICAL_FALLBACK_TIMEFRAME: TimeframeKey = "1m";
export const HISTORICAL_TIMEFRAME_KEYS = TIMEFRAME_KEYS.filter((key) => key !== "1s");

export const CHART_TYPE_ORDER: ChartType[] = CHART_TYPES.map((ct) => ct.id);

export const CANDLE_SERIES_CHART_TYPES = new Set<ChartType>(["candles", "heikinAshi", "renko", "lineBreak", "pointFigure"]);
export const LINE_SERIES_CHART_TYPES = new Set<ChartType>(["line", "kagi"]);

export function usesCandleSeries(type: ChartType): boolean { return CANDLE_SERIES_CHART_TYPES.has(type); }
export function usesTransformedCandleData(type: ChartType): boolean { return type !== "candles" && CANDLE_SERIES_CHART_TYPES.has(type); }
export function usesDerivedSeriesData(type: ChartType): boolean { return usesTransformedCandleData(type) || type === "kagi"; }
export function usesLineSeries(type: ChartType): boolean { return LINE_SERIES_CHART_TYPES.has(type); }

export const CHART_TYPE_ICONS: Record<ChartType, typeof CandleIcon> = {
  candles: CandleIcon, bars: BarChart3, line: LineChart, area: AreaChart,
  heikinAshi: Layers, renko: Grid3x3, lineBreak: TrendingUp, kagi: Activity, pointFigure: BarChart3,
};

export const CHART_TYPE_LABELS: Record<ChartType, TranslationKey> = {
  candles: "candlestick", bars: "bars", line: "line", area: "area",
  heikinAshi: "heikinAshi", renko: "renko", lineBreak: "lineBreak", kagi: "kagi", pointFigure: "pointFigure",
};

export const AI_INDICATOR_ALIASES: Record<string, string> = {
  sma: "sma20", sma20: "sma20", sma50: "sma50",
  ema: "ema12", ema12: "ema12", ema26: "ema26",
  rsi14: "rsi", bollinger: "bb", bollinger_bands: "bb",
  volume_ma: "volumeMa", parabolic_sar: "psar", atr14: "atr",
};

export const BACKEND_SERIES_INDICATORS = [
  "sma20", "sma50", "ema12", "ema26", "rsi", "macd", "bb",
  "volume", "volumeMa", "atr",
] as const;

export const INDICATOR_WARNING_MESSAGES: Record<string, TranslationKey> = {
  not_enough_candle_data: "indicatorNotEnoughData",
  indicator_data_unavailable: "indicatorDataUnavailable",
  backend_returned_empty_result: "indicatorBackendEmpty",
};

export function normalizeAiIndicatorKey(indicator: string): string {
  const key = indicator.trim().replace(/\s+/g, "_").toLowerCase();
  return AI_INDICATOR_ALIASES[key] || key;
}

export function activeBackendIndicators(settings: Record<string, IndicatorSettings>): string[] {
  return BACKEND_SERIES_INDICATORS.filter((i) => settings[i]?.visible);
}

export function warningMessageKey(warnings: string[] = []): TranslationKey | null {
  for (const w of ["not_enough_candle_data", "backend_returned_empty_result", "indicator_data_unavailable"]) {
    if (warnings.includes(w)) return INDICATOR_WARNING_MESSAGES[w];
  }
  return null;
}

export function resolveChartTheme(
  baseTheme: ReturnType<typeof getChartTheme>,
  preferences: ChartPreferenceSettings,
): ReturnType<typeof getChartTheme> {
  const withCandleColors = {
    ...baseTheme,
    upColor: preferences.candle_style.up_color,
    downColor: preferences.candle_style.down_color,
    volumeUp: `${preferences.candle_style.up_color}80`,
    volumeDown: `${preferences.candle_style.down_color}80`,
  };
  if (preferences.chart_theme_preset === "light") {
    return { ...withCandleColors, background: "#f8fafc", textColor: "#334155", gridColor: "#dbe4ee", borderColor: "#cbd5e1", crosshair: "#475569", crosshairLabelBg: "#e2e8f0" };
  }
  if (preferences.chart_theme_preset === "highContrast") {
    return { ...withCandleColors, background: "#050505", textColor: "#f8fafc", gridColor: "#3f3f46", borderColor: "#e4e4e7", crosshair: "#facc15", crosshairLabelBg: "#111111" };
  }
  return withCandleColors;
}

export function gridLineStyle(preferences: ChartPreferenceSettings): LineStyle {
  return preferences.grid_crosshair.grid_style === "dashed" ? LineStyle.Dashed : LineStyle.Solid;
}

export function crosshairMode(preferences: ChartPreferenceSettings): CrosshairMode {
  return preferences.grid_crosshair.crosshair_style === "magnet" ? CrosshairMode.Magnet : CrosshairMode.Normal;
}

export function hasSeriesData(payload: IndicatorSeriesResponse, indicator: string): boolean {
  const series = payload.series || {};
  if (indicator === "rsi") return Boolean(series.rsi?.length || series.rsi14?.length);
  if (indicator === "bb") return Boolean(series.bb_upper?.length || series.bb_middle?.length || series.bb_lower?.length);
  if (indicator === "volumeMa") return Boolean(series.volumeMa?.length || series.volume_sma20?.length);
  if (indicator === "atr") return Boolean(series.atr?.length || series.atr14?.length);
  return Boolean(series[indicator]?.length);
}
