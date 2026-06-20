import React, { startTransition, useCallback, useEffect, useRef, useState } from "react";
import {
  createChart,
  CrosshairMode,
  LineStyle,
  AreaSeries,
  BarSeries,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from "lightweight-charts";
import {
  Activity,
  AreaChart,
  BarChart3,
  CandlestickChart as CandleIcon,
  ChevronDown,
  Download,
  Grid3x3,
  Layers,
  LineChart,
  Maximize2,
  Minimize2,
  TrendingUp,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { normalizeTimeframe, TIMEFRAME_KEYS, TIMEFRAMES } from "@/constants/timeframes";
import { useI18n } from "@/i18n";
import { useChartZoom } from "@/hooks/useChartZoom";
import {
  fetchCandles,
  fetchIndicatorSeries,
  fetchHistoricalCandles,
  subscribeIndicatorStream,
  subscribeAllTimeframes,
  TIMEFRAMES as SERVICE_TIMEFRAMES,
} from "@/services/marketDataService";
import DateRangePicker from "./DateRangePicker";
import DropdownPortal from "@/components/ui/DropdownPortal";
import {
  getChartTheme,
  DEFAULT_INDICATOR_SETTINGS,
  localTickMarkFormatter,
  localTimeFormatter,
} from "./chartConstants";
import {
  calcATR,
  calcBollingerBands,
  calcEMA,
  calcIchimoku,
  calcMACD,
  calcMFI,
  calcParabolicSAR,
  calcRSI,
  calcSMA,
  calcStochastic,
  calcSupertrend,
  calcVolumeMA,
  calcVWAP,
} from "./indicatorUtils";
import {
  buildChartTypeSeriesData,
  sanitizeCandlesForChart,
} from "./chartTypeData";
import IndicatorPanel, { type IndicatorPanelStatus } from "./IndicatorPanel";
import MarketSelector from "./MarketSelector";
import OHLCVBar from "./OHLCVBar";
import type { AiChartActionController } from "@/features/ai/actions/AiActionProvider";
import { CHART_TYPES } from "@/types";
import { DEFAULT_CHART_PREFERENCES, type ChartPreferenceSettings } from "@/services/settingsService";
import { formatNormalizedError, normalizeError, sanitizeTechnicalDetails } from "@/utils/errors";
import type {
  Candle,
  ChartType,
  HistoricalRange,
  IndicatorSettings,
  IndicatorSeriesResponse,
  IndicatorStreamSnapshot,
  TimeframeKey,
  NewsArticle,
} from "@/types";
import type { TranslationKey } from "@/i18n/translations";

const HISTORICAL_FALLBACK_TIMEFRAME: TimeframeKey = "1m";
const HISTORICAL_TIMEFRAME_KEYS = TIMEFRAME_KEYS.filter((key) => key !== "1s");

const CHART_TYPE_ORDER: ChartType[] = CHART_TYPES.map((chartType) => chartType.id);
const CANDLE_SERIES_CHART_TYPES = new Set<ChartType>([
  "candles",
  "heikinAshi",
  "renko",
  "lineBreak",
  "pointFigure",
]);
const LINE_SERIES_CHART_TYPES = new Set<ChartType>(["line", "kagi"]);

function usesCandleSeries(type: ChartType): boolean {
  return CANDLE_SERIES_CHART_TYPES.has(type);
}

function usesTransformedCandleData(type: ChartType): boolean {
  return type !== "candles" && CANDLE_SERIES_CHART_TYPES.has(type);
}

function usesDerivedSeriesData(type: ChartType): boolean {
  return usesTransformedCandleData(type) || type === "kagi";
}

function usesLineSeries(type: ChartType): boolean {
  return LINE_SERIES_CHART_TYPES.has(type);
}

const CHART_TYPE_ICONS: Record<ChartType, typeof CandleIcon> = {
  candles: CandleIcon,
  bars: BarChart3,
  line: LineChart,
  area: AreaChart,
  heikinAshi: Layers,
  renko: Grid3x3,
  lineBreak: TrendingUp,
  kagi: Activity,
  pointFigure: BarChart3,
};

const CHART_TYPE_LABELS: Record<ChartType, TranslationKey> = {
  candles: "candlestick",
  bars: "bars",
  line: "line",
  area: "area",
  heikinAshi: "heikinAshi",
  renko: "renko",
  lineBreak: "lineBreak",
  kagi: "kagi",
  pointFigure: "pointFigure",
};

const AI_INDICATOR_ALIASES: Record<string, string> = {
  sma: "sma20",
  sma20: "sma20",
  sma50: "sma50",
  ema: "ema12",
  ema12: "ema12",
  ema26: "ema26",
  rsi14: "rsi",
  bollinger: "bb",
  bollinger_bands: "bb",
  volume_ma: "volumeMa",
  parabolic_sar: "psar",
  atr14: "atr",
};

const BACKEND_SERIES_INDICATORS = [
  "sma20",
  "sma50",
  "ema12",
  "ema26",
  "rsi",
  "macd",
  "bb",
  "volume",
  "volumeMa",
  "atr",
] as const;

const INDICATOR_WARNING_MESSAGES: Record<string, TranslationKey> = {
  not_enough_candle_data: "indicatorNotEnoughData",
  indicator_data_unavailable: "indicatorDataUnavailable",
  backend_returned_empty_result: "indicatorBackendEmpty",
};

function normalizeAiIndicatorKey(indicator: string): string {
  const key = indicator.trim().replace(/\s+/g, "_").toLowerCase();
  return AI_INDICATOR_ALIASES[key] || key;
}

function activeBackendIndicators(settings: Record<string, IndicatorSettings>): string[] {
  return BACKEND_SERIES_INDICATORS.filter((indicator) => settings[indicator]?.visible);
}

function warningMessageKey(warnings: string[] = []): TranslationKey | null {
  for (const warning of ["not_enough_candle_data", "backend_returned_empty_result", "indicator_data_unavailable"]) {
    if (warnings.includes(warning)) return INDICATOR_WARNING_MESSAGES[warning];
  }
  return null;
}

function resolveChartTheme(
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
    return {
      ...withCandleColors,
      background: "#f8fafc",
      textColor: "#334155",
      gridColor: "#dbe4ee",
      borderColor: "#cbd5e1",
      crosshair: "#475569",
      crosshairLabelBg: "#e2e8f0",
    };
  }

  if (preferences.chart_theme_preset === "highContrast") {
    return {
      ...withCandleColors,
      background: "#050505",
      textColor: "#f8fafc",
      gridColor: "#3f3f46",
      borderColor: "#e4e4e7",
      crosshair: "#facc15",
      crosshairLabelBg: "#111111",
    };
  }

  return withCandleColors;
}

function gridLineStyle(preferences: ChartPreferenceSettings): LineStyle {
  return preferences.grid_crosshair.grid_style === "dashed"
    ? LineStyle.Dashed
    : LineStyle.Solid;
}

function crosshairMode(preferences: ChartPreferenceSettings): CrosshairMode {
  return preferences.grid_crosshair.crosshair_style === "magnet"
    ? CrosshairMode.Magnet
    : CrosshairMode.Normal;
}

function hasSeriesData(payload: IndicatorSeriesResponse, indicator: string): boolean {
  const series = payload.series || {};
  if (indicator === "rsi") return Boolean(series.rsi?.length || series.rsi14?.length);
  if (indicator === "bb") return Boolean(series.bb_upper?.length || series.bb_middle?.length || series.bb_lower?.length);
  if (indicator === "volumeMa") return Boolean(series.volumeMa?.length || series.volume_sma20?.length);
  if (indicator === "atr") return Boolean(series.atr?.length || series.atr14?.length);
  return Boolean(series[indicator]?.length);
}

interface CandlestickChartProps {
  defaultSymbol?: string;
  symbol?: string;
  symbols?: string[];
  starredSymbols?: string[];
  timeframe?: TimeframeKey;
  children?: React.ReactNode | ((chartApi: any, candleSeries: any) => React.ReactNode);
  onCandlesChange?: (candles: Candle[]) => void;
  onSymbolChange?: (symbol: string) => void;
  onToggleStar?: (symbol: string) => void;
  onTimeframeChange?: (timeframe: TimeframeKey) => void;
  themeMode?: "dark" | "light";
  chartType?: ChartType;
  chartPreferences?: ChartPreferenceSettings;
  onChartTypeChange?: (type: ChartType) => void;
  newsItems?: NewsArticle[];
  showNewsMarkers?: boolean;
  onAiActionControllerReady?: (controller: AiChartActionController | null) => void;
  // Replay mode props
  isReplayActive?: boolean;
}

interface TooltipData {
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  timeLabel: string;
}

const CandlestickChart: React.FC<CandlestickChartProps> = ({
  defaultSymbol = "BTCUSDT",
  symbol: symbolProp,
  symbols = [],
  starredSymbols = [],
  timeframe: timeframeProp,
  children,
  onCandlesChange,
  onSymbolChange,
  onToggleStar,
  onTimeframeChange,
  themeMode = "dark",
  chartType = "candles",
  chartPreferences = DEFAULT_CHART_PREFERENCES,
  onChartTypeChange,
  newsItems = [],
  showNewsMarkers = true,
  onAiActionControllerReady,
  isReplayActive = false,
}) => {
  const { t } = useI18n();
  const rootRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartStageRef = useRef<HTMLDivElement>(null);
  const timeframeButtonRef = useRef<HTMLButtonElement>(null);
  const indicatorButtonRef = useRef<HTMLButtonElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const candleRef = useRef<any>(null);
  const barRef = useRef<any>(null);
  const lineRef = useRef<any>(null);
  const areaRef = useRef<any>(null);
  const volumeRef = useRef<any>(null);
  const sma20Ref = useRef<any>(null);
  const sma50Ref = useRef<any>(null);
  const ema12Ref = useRef<any>(null);
  const ema26Ref = useRef<any>(null);
  const bbUpperRef = useRef<any>(null);
  const bbBasisRef = useRef<any>(null);
  const bbLowerRef = useRef<any>(null);
  const vwapRef = useRef<any>(null);
  const volumeMaRef = useRef<any>(null);
  const macdLineRef = useRef<any>(null);
  const macdSignalRef = useRef<any>(null);
  const macdHistogramRef = useRef<any>(null);
  const stochasticKRef = useRef<any>(null);
  const stochasticDRef = useRef<any>(null);
  const atrRef = useRef<any>(null);
  const ichimokuConversionRef = useRef<any>(null);
  const ichimokuBaseRef = useRef<any>(null);
  const ichimokuSpanARef = useRef<any>(null);
  const ichimokuSpanBRef = useRef<any>(null);
  const ichimokuLaggingRef = useRef<any>(null);
  const supertrendRef = useRef<any>(null);
  const psarRef = useRef<any>(null);
  const rsiSeriesRef = useRef<any>(null);
  const mfiSeriesRef = useRef<any>(null);
  const candlesRef = useRef<Candle[]>([]);
  const renderedPriceDataLengthRef = useRef(0);
  const themeRef = useRef(getChartTheme());
  const symbolRef = useRef(defaultSymbol);
  const timeframeRef = useRef(timeframeProp || "1m");
  const chartTypeRef = useRef<ChartType>(chartType);
  const lastClosedCandleRef = useRef<Candle | null>(null);

  const [symbol, setSymbol] = useState(symbolProp || defaultSymbol);
  const [timeframe, setTimeframe] = useState(timeframeProp || "1m");
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [showIndPanel, setShowIndPanel] = useState(false);
  const [isTimeframeMenuOpen, setIsTimeframeMenuOpen] = useState(false);
  const [indSettings, setIndSettings] = useState<Record<string, IndicatorSettings>>(() =>
    JSON.parse(JSON.stringify(DEFAULT_INDICATOR_SETTINGS)),
  );
  const [candles, setCandles] = useState<Candle[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [indicatorStatus, setIndicatorStatus] = useState<IndicatorPanelStatus>({});

  useEffect(() => {
    if (!onAiActionControllerReady) return;
    const controller: AiChartActionController = {
      setIndicatorVisible: (indicator, visible) => {
        const key = normalizeAiIndicatorKey(indicator);
        setIndSettings((prev) => {
          if (!prev[key]) return prev;
          return { ...prev, [key]: { ...prev[key], visible } };
        });
      },
      toggleIndicator: (indicator) => {
        const key = normalizeAiIndicatorKey(indicator);
        setIndSettings((prev) => {
          if (!prev[key]) return prev;
          return { ...prev, [key]: { ...prev[key], visible: !prev[key].visible } };
        });
      },
      zoomChart: (direction, anchorRatio = 0.5) => {
        const timeScale = chartRef.current?.timeScale();
        const range = timeScale?.getVisibleLogicalRange();
        if (!timeScale || !range) return;
        const anchor = range.from + (range.to - range.from) * Math.max(0, Math.min(1, anchorRatio));
        const factor = direction === "in" ? 0.8 : 1.25;
        timeScale.setVisibleLogicalRange({
          from: anchor - (anchor - range.from) * factor,
          to: anchor + (range.to - anchor) * factor,
        });
      },
      scrollChart: (target) => {
        const timeScale = chartRef.current?.timeScale();
        const range = timeScale?.getVisibleLogicalRange();
        if (!timeScale || !range) return;
        const width = range.to - range.from;
        if (target === "start") {
          timeScale.setVisibleLogicalRange({ from: 0, to: width });
          return;
        }
        if (target === "end") {
          const end = Math.max(width, candlesRef.current.length - 1);
          timeScale.setVisibleLogicalRange({ from: end - width, to: end });
          return;
        }
        const shift = typeof target === "number" ? target : 0;
        timeScale.setVisibleLogicalRange({ from: range.from + shift, to: range.to + shift });
      },
      rangeToChartRegion: (args) => {
        const current = candlesRef.current;
        const container = containerRef.current;
        if (!current.length || !container) return null;
        const fromIndex = Number(args.from_index);
        const toIndex = Number(args.to_index);
        if (Number.isFinite(fromIndex) && Number.isFinite(toIndex)) {
          const start = Math.max(0, Math.min(current.length - 1, Math.min(fromIndex, toIndex)));
          const end = Math.max(0, Math.min(current.length - 1, Math.max(fromIndex, toIndex)));
          const leftPct = (start / current.length) * 100;
          const widthPct = Math.max(3, ((end - start + 1) / current.length) * 100);
          return { leftPct, topPct: 12, widthPct, heightPct: 68 };
        }
        const startRaw = Number(args.start_time);
        const endRaw = Number(args.end_time);
        const timeScale = chartRef.current?.timeScale() as any;
        if (Number.isFinite(startRaw) && Number.isFinite(endRaw) && timeScale?.timeToCoordinate) {
          const toSeconds = (value: number) => value > 1_000_000_000_000 ? Math.floor(value / 1000) : value;
          const x1 = timeScale.timeToCoordinate(toSeconds(startRaw));
          const x2 = timeScale.timeToCoordinate(toSeconds(endRaw));
          if (typeof x1 === "number" && typeof x2 === "number") {
            const left = Math.max(0, Math.min(x1, x2));
            const right = Math.min(container.clientWidth, Math.max(x1, x2));
            return {
              leftPct: (left / container.clientWidth) * 100,
              topPct: 12,
              widthPct: Math.max(3, ((right - left) / container.clientWidth) * 100),
              heightPct: 68,
            };
          }
        }
        return null;
      },
    };
    onAiActionControllerReady(controller);
    return () => onAiActionControllerReady(null);
  }, [onAiActionControllerReady]);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [historicalRange, setHistoricalRange] = useState<HistoricalRange | null>(null);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [noData, setNoData] = useState(false);
  const isLoadingMoreRef = useRef(false);
  const earliestTimestampRef = useRef<number | null>(null);
  const noMoreDataRef = useRef(false);
  const scrollCooldownRef = useRef(0);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const indicatorUnsubscribeRef = useRef<(() => void) | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const historicalRequestIdRef = useRef(0);
  const seriesControllerRef = useRef<any>(null);

  // Initialize zoom control hook
  const { zoomIn, zoomOut, canZoomIn, canZoomOut } = useChartZoom({
    chartApi: chartRef.current,
    initialBarSpacing: 4,
    minBarSpacing: 2,
    maxBarSpacing: 30,
  });

  const resizeChartToContainer = useCallback(() => {
    if (!containerRef.current || !chartRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const stageRect = chartStageRef.current?.getBoundingClientRect();
    const width = Math.floor(containerRect.width || stageRect?.width || 0);
    const height = Math.floor(containerRect.height || stageRect?.height || 0);
    if (width <= 0 || height <= 0) return;

    chartRef.current.resize(width, height);
  }, []);

  const scheduleChartResize = useCallback(() => {
    requestAnimationFrame(resizeChartToContainer);
    window.setTimeout(resizeChartToContainer, 120);
  }, [resizeChartToContainer]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === rootRef.current);
      scheduleChartResize();
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, [scheduleChartResize]);

  const getTimeframeSeconds = useCallback((tf: string) => {
    return SERVICE_TIMEFRAMES[normalizeTimeframe(tf)].seconds;
  }, []);

  const getInitialVisibleBars = useCallback(
    () => {
      // TradingView-style: show consistent number of bars regardless of timeframe
      // This keeps candle density uniform across all timeframes
      // Increased to 150 for thinner candles across all timeframes
      return 150;
    },
    [],
  );

  // ─── UNIFIED CHART CONFIG (all timeframes use identical settings) ───
  const CHART_CONFIG = {
    VISIBLE_BARS: 150,        // All timeframes show 150 bars
    MAX_BARS_MEMORY: 10000,   // All timeframes keep 10000 bars in memory
  };

  const getActivePriceSeries = useCallback(() => {
    if (chartTypeRef.current === "bars") return barRef.current || candleRef.current;
    if (usesLineSeries(chartTypeRef.current)) return lineRef.current || candleRef.current;
    if (chartTypeRef.current === "area") return areaRef.current || candleRef.current;
    return candleRef.current;
  }, []);

  const setAllPriceSeriesData = useCallback(
    (data: Candle[]) => {
      const chart = chartRef.current;
      const timeScale = chart?.timeScale();
      const previousRange = timeScale?.getVisibleLogicalRange() || null;
      const previousLength = renderedPriceDataLengthRef.current;
      const seriesData = buildChartTypeSeriesData(chartType, data);
      const nextLength = Math.max(
        seriesData.candles.length,
        seriesData.line.length,
      );

      if (chartType === "kagi") {
        candleRef.current?.setData([]);
        barRef.current?.setData([]);
        lineRef.current?.setData(seriesData.line);
        areaRef.current?.setData([]);
      } else {
        candleRef.current?.setData(seriesData.candles);
        barRef.current?.setData(seriesData.candles);
        lineRef.current?.setData(seriesData.line);
        areaRef.current?.setData(seriesData.line);
      }

      renderedPriceDataLengthRef.current = nextLength;

      if (!timeScale || !previousRange || nextLength < 2) return;

      window.requestAnimationFrame(() => {
        const width = Math.max(5, previousRange.to - previousRange.from);
        const maxTo = nextLength - 1 + 0.5;
        const wasNearRight =
          previousLength <= 0 || previousRange.to >= previousLength - 3;
        const desiredTo = wasNearRight
          ? maxTo
          : Math.min(previousRange.to, maxTo);
        const from = Math.max(-0.5, desiredTo - width);
        const to = Math.min(maxTo, from + width);
        if (to > from) timeScale.setVisibleLogicalRange({ from, to });
      });
    },
    [chartType],
  );

  const updateAllPriceSeries = useCallback((candle: Candle) => {
    const chartCandle = sanitizeCandlesForChart([candle])[0];
    if (!chartCandle) return;

    if (usesDerivedSeriesData(chartTypeRef.current)) {
      const current = candlesRef.current;
      const last = current[current.length - 1];
      const next = !last
        ? [chartCandle]
        : chartCandle.time === last.time
          ? [...current.slice(0, -1), chartCandle]
          : chartCandle.time > last.time
            ? [...current.slice(-(CHART_CONFIG.MAX_BARS_MEMORY - 1)), chartCandle]
            : current;

      if (next !== current) {
        setAllPriceSeriesData(next);
      }
      return;
    }

    candleRef.current?.update(chartCandle);
    barRef.current?.update(chartCandle);
    const closePoint = { time: chartCandle.time, value: chartCandle.close };
    lineRef.current?.update(closePoint);
    areaRef.current?.update(closePoint);
  }, [setAllPriceSeriesData]);

  const commitCandlesState = useCallback(
    (next: Candle[]) => {
      startTransition(() => {
        setCandles(next);
        if (onCandlesChange) onCandlesChange(next);
      });
    },
    [onCandlesChange],
  );

  const setInitialVisibleRange = useCallback(
    (data: Candle[]) => {
      if (!chartRef.current || !Array.isArray(data) || data.length === 0) return;
      const bars = getInitialVisibleBars();
      const to = data.length - 1 + 0.5;
      const from = Math.max(0, data.length - bars) - 0.5;

      // Set visible range WITHOUT changing barSpacing
      // This preserves zoom level when switching timeframes
      chartRef.current.timeScale().setVisibleLogicalRange({ from, to });
    },
    [getInitialVisibleBars],
  );

  const preloadInitialCandles = useCallback(
    async ({ data, requestSymbol, requestInterval, isHistoricalMode = false }: { data: Candle[]; requestSymbol: string; requestInterval: string; isHistoricalMode?: boolean }) => {
      if (!Array.isArray(data) || data.length === 0) return data;

      const requiredBars = getInitialVisibleBars();
      if (data.length >= requiredBars) return data;

      const earliestTime = data[0].time;
      const missingBars = requiredBars - data.length;
      const fetchLimit = Math.min(Math.max(missingBars + 20, requiredBars), 500);
      let olderData = [];

      try {
        if (isHistoricalMode) {
          const seconds = getTimeframeSeconds(requestInterval);
          const backfillEndMs = earliestTime * 1000;
          const backfillStartMs = Math.max(
            0,
            backfillEndMs - seconds * 1000 * fetchLimit,
          );
          olderData = await fetchHistoricalCandles(
            requestSymbol,
            backfillStartMs,
            backfillEndMs,
            fetchLimit,
            requestInterval,
          );
        } else {
          olderData = await fetchCandles(
            requestSymbol,
            requestInterval,
            fetchLimit,
            earliestTime,
          );
        }
      } catch {
        return data;
      }

      olderData = sanitizeCandlesForChart(olderData);
      if (!Array.isArray(olderData) || olderData.length === 0) return data;

      const dedupedOlder = olderData.filter((c) => c.time < earliestTime);
      if (dedupedOlder.length === 0) return data;

      return sanitizeCandlesForChart([...dedupedOlder, ...data]);
    },
    [getInitialVisibleBars, getTimeframeSeconds],
  );

  // Keep latest symbol/timeframe in refs so async scroll-load results can be
  // ignored when the user changes context mid-request.
  useEffect(() => {
    symbolRef.current = symbol;
    timeframeRef.current = normalizeTimeframe(timeframe);
  }, [symbol, timeframe]);

  const handleTimeframeSelect = useCallback((nextTimeframe: TimeframeKey) => {
    setTimeframe(!isLiveMode && nextTimeframe === "1s" ? HISTORICAL_FALLBACK_TIMEFRAME : nextTimeframe);
    setIsTimeframeMenuOpen(false);
  }, [isLiveMode]);

  const handleSymbolChange = useCallback((nextSymbol: string) => {
    setSymbol(nextSymbol);
    onSymbolChange?.(nextSymbol);
  }, [onSymbolChange]);

  const handleToggleSymbolStar = useCallback((nextSymbol: string) => {
    onToggleStar?.(nextSymbol);
  }, [onToggleStar]);

  // Sync symbol from external prop
  useEffect(() => {
    if (symbolProp && symbolProp !== symbol) setSymbol(symbolProp);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbolProp]);

  // Sync timeframe from external prop (App.tsx controls it)
  useEffect(() => {
    if (timeframeProp && timeframeProp !== timeframe) {
      setTimeframe(timeframeProp);
    }
  }, [timeframeProp]);

  // Notify parent when timeframe changes (from internal setTimeframe)
  useEffect(() => {
    if (onTimeframeChange) {
      onTimeframeChange(timeframe);
    }
  }, [timeframe, onTimeframeChange]);

  // Init chart once
  useEffect(() => {
    if (!containerRef.current) return;
    const preferences = chartPreferences ?? DEFAULT_CHART_PREFERENCES;
    const chartTheme = resolveChartTheme(getChartTheme(), preferences);
    const lineStyle = gridLineStyle(preferences);
    themeRef.current = chartTheme;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: chartTheme.background },
        textColor: chartTheme.textColor,
        fontFamily: "'Inter','Segoe UI',sans-serif",
        fontSize: 11,
      },
      localization: {
        locale: navigator.language || "en-US",
        timeFormatter: localTimeFormatter,
      },
      grid: {
        vertLines: {
          color: preferences.grid_crosshair.grid_visible ? chartTheme.gridColor : "transparent",
          style: lineStyle,
        },
        horzLines: {
          color: preferences.grid_crosshair.grid_visible ? chartTheme.gridColor : "transparent",
          style: lineStyle,
        },
      },
      crosshair: {
        mode: crosshairMode(preferences),
        vertLine: {
          color: chartTheme.crosshair,
          labelBackgroundColor: chartTheme.crosshairLabelBg,
          style: LineStyle.Dashed,
        },
        horzLine: {
          color: chartTheme.crosshair,
          labelBackgroundColor: chartTheme.crosshairLabelBg,
          style: LineStyle.Dashed,
        },
      },
      rightPriceScale: {
        borderColor: chartTheme.borderColor,
        scaleMargins: { top: 0.05, bottom: 0.25 },
        entireTextOnly: true,
        visible: preferences.scale.price_labels_visible,
        mode: 0,
      },
      timeScale: {
        borderColor: chartTheme.borderColor,
        timeVisible: true,
        secondsVisible: preferences.scale.seconds_visible && timeframe === "1s",
        barSpacing: preferences.scale.bar_spacing,
        minBarSpacing: 2,
        rightOffset: 8,
        fixLeftEdge: false,
        fixRightEdge: false,
        lockVisibleTimeRangeOnResize: true,
        tickMarkFormatter: localTickMarkFormatter,
        visible: preferences.scale.time_labels_visible,
      },
      handleScroll: { mouseWheel: false, pressedMouseMove: true },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: false,
        pinch: true,
      },
    });
    const cs = chart.addSeries(CandlestickSeries, {
      upColor: chartTheme.upColor,
      downColor: chartTheme.downColor,
      borderUpColor: chartTheme.upColor,
      borderDownColor: chartTheme.downColor,
      wickUpColor: chartTheme.upColor,
      wickDownColor: chartTheme.downColor,
      borderVisible: preferences.candle_style.border_visible,
      wickVisible: preferences.candle_style.wick_visible && timeframe !== "1s",
      visible: usesCandleSeries(chartType),
    });
    const bs = chart.addSeries(BarSeries, {
      upColor: chartTheme.upColor,
      downColor: chartTheme.downColor,
      thinBars: false,
      visible: chartType === "bars",
    });
    const ls = chart.addSeries(LineSeries, {
      color: chartTheme.upColor,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: true,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
      visible: usesLineSeries(chartType),
    });
    const ar = chart.addSeries(AreaSeries, {
      lineColor: chartTheme.upColor,
      topColor: `${chartTheme.upColor}50`,
      bottomColor: `${chartTheme.background}00`,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: true,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
      visible: chartType === "area",
    });
    const vs = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart
      .priceScale("volume")
      .applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    const s20 = chart.addSeries(LineSeries, {
      color: chartTheme.sma20,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
    });
    const s50 = chart.addSeries(LineSeries, {
      color: chartTheme.sma50,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
    });
    const ema12 = chart.addSeries(LineSeries, {
      color: chartTheme.ema12,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const ema26 = chart.addSeries(LineSeries, {
      color: chartTheme.ema26,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const bbUpper = chart.addSeries(LineSeries, {
      color: chartTheme.bb,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const bbBasis = chart.addSeries(LineSeries, {
      color: chartTheme.bbBasis,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const bbLower = chart.addSeries(LineSeries, {
      color: chartTheme.bb,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const vwapSeries = chart.addSeries(LineSeries, {
      color: chartTheme.vwap,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const supertrendSeries = chart.addSeries(LineSeries, {
      color: chartTheme.supertrend,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const psarSeries = chart.addSeries(LineSeries, {
      color: chartTheme.psar,
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const volumeMaSeries = chart.addSeries(LineSeries, {
      color: chartTheme.volumeMa,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
      priceScaleId: "volume",
    });
    const ichimokuConversion = chart.addSeries(LineSeries, {
      color: chartTheme.ichimokuConversion,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const ichimokuBase = chart.addSeries(LineSeries, {
      color: chartTheme.ichimokuBase,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const ichimokuSpanA = chart.addSeries(LineSeries, {
      color: chartTheme.ichimokuSpanA,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const ichimokuSpanB = chart.addSeries(LineSeries, {
      color: chartTheme.ichimokuSpanB,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
    });
    const ichimokuLagging = chart.addSeries(LineSeries, {
      color: chartTheme.bbBasis,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
    });
    // RSI & MFI on a separate left-side oscillator scale (bottom 20%)
    const rsiSeries = chart.addSeries(LineSeries, {
      color: chartTheme.rsi,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
      priceScaleId: "oscillator",
    });
    const macdLine = chart.addSeries(LineSeries, {
      color: chartTheme.macd,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
      priceScaleId: "oscillator",
    });
    const macdSignal = chart.addSeries(LineSeries, {
      color: chartTheme.macdSignal,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
      priceScaleId: "oscillator",
    });
    const macdHistogram = chart.addSeries(HistogramSeries, {
      color: chartTheme.macd,
      priceFormat: { type: "volume" },
      priceScaleId: "oscillator",
      visible: false,
    });
    const stochasticK = chart.addSeries(LineSeries, {
      color: chartTheme.stochastic,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
      priceScaleId: "oscillator",
    });
    const stochasticD = chart.addSeries(LineSeries, {
      color: chartTheme.stochasticSignal,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
      priceScaleId: "oscillator",
    });
    const atrSeries = chart.addSeries(LineSeries, {
      color: chartTheme.atr,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
      priceScaleId: "oscillator",
    });
    const mfiSeries = chart.addSeries(LineSeries, {
      color: chartTheme.mfi,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      visible: false,
      priceScaleId: "oscillator",
    });
    chart.priceScale("oscillator").applyOptions({
      scaleMargins: { top: 0.75, bottom: 0 },
      visible: false,
    });
    chartRef.current = chart;
    candleRef.current = cs;
    barRef.current = bs;
    lineRef.current = ls;
    areaRef.current = ar;
    volumeRef.current = vs;
    sma20Ref.current = s20;
    sma50Ref.current = s50;
    ema12Ref.current = ema12;
    ema26Ref.current = ema26;
    bbUpperRef.current = bbUpper;
    bbBasisRef.current = bbBasis;
    bbLowerRef.current = bbLower;
    vwapRef.current = vwapSeries;
    supertrendRef.current = supertrendSeries;
    psarRef.current = psarSeries;
    volumeMaRef.current = volumeMaSeries;
    macdLineRef.current = macdLine;
    macdSignalRef.current = macdSignal;
    macdHistogramRef.current = macdHistogram;
    stochasticKRef.current = stochasticK;
    stochasticDRef.current = stochasticD;
    atrRef.current = atrSeries;
    ichimokuConversionRef.current = ichimokuConversion;
    ichimokuBaseRef.current = ichimokuBase;
    ichimokuSpanARef.current = ichimokuSpanA;
    ichimokuSpanBRef.current = ichimokuSpanB;
    ichimokuLaggingRef.current = ichimokuLagging;
    rsiSeriesRef.current = rsiSeries;
    mfiSeriesRef.current = mfiSeries;
    chart.subscribeCrosshairMove((param: any) => {
      if (!param.time || (param.point && param.point.x < 0)) {
        setTooltip(null);
        return;
      }
      const activeSeries = getActivePriceSeries();
      const c = activeSeries ? param.seriesData.get(activeSeries) : param.seriesData.get(cs);
      const v = param.seriesData.get(vs);
      if (c) {
        const lbl = localTimeFormatter(param.time as number);
        if (
          typeof c.open === "number"
          && typeof c.high === "number"
          && typeof c.low === "number"
          && typeof c.close === "number"
        ) {
          setTooltip({ ...c, volume: v ? v.value : undefined, timeLabel: lbl });
          return;
        }

        if (typeof c.value === "number" && Number.isFinite(c.value)) {
          setTooltip({
            open: c.value,
            high: c.value,
            low: c.value,
            close: c.value,
            volume: v ? v.value : undefined,
            timeLabel: lbl,
          });
        }
      }
    });
    const ro = new ResizeObserver(scheduleChartResize);
    ro.observe(containerRef.current);
    if (chartStageRef.current) {
      ro.observe(chartStageRef.current);
    }
    window.addEventListener("resize", scheduleChartResize);
    window.visualViewport?.addEventListener("resize", scheduleChartResize);
    scheduleChartResize();
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", scheduleChartResize);
      window.visualViewport?.removeEventListener("resize", scheduleChartResize);
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const preferences = chartPreferences ?? DEFAULT_CHART_PREFERENCES;
    const chartTheme = resolveChartTheme(getChartTheme(), preferences);
    const lineStyle = gridLineStyle(preferences);
    themeRef.current = chartTheme;

    if (!chartRef.current) return;

    chartRef.current.applyOptions({
      layout: {
        background: { color: chartTheme.background },
        textColor: chartTheme.textColor,
      },
      grid: {
        vertLines: {
          color: preferences.grid_crosshair.grid_visible ? chartTheme.gridColor : "transparent",
          style: lineStyle,
        },
        horzLines: {
          color: preferences.grid_crosshair.grid_visible ? chartTheme.gridColor : "transparent",
          style: lineStyle,
        },
      },
      crosshair: {
        mode: crosshairMode(preferences),
        vertLine: {
          color: chartTheme.crosshair,
          labelBackgroundColor: chartTheme.crosshairLabelBg,
          style: lineStyle,
        },
        horzLine: {
          color: chartTheme.crosshair,
          labelBackgroundColor: chartTheme.crosshairLabelBg,
          style: lineStyle,
        },
      },
      rightPriceScale: {
        borderColor: chartTheme.borderColor,
        visible: preferences.scale.price_labels_visible,
      },
      timeScale: {
        borderColor: chartTheme.borderColor,
        secondsVisible: preferences.scale.seconds_visible && timeframe === "1s",
        barSpacing: preferences.scale.bar_spacing,
        visible: preferences.scale.time_labels_visible,
      },
    });

    candleRef.current?.applyOptions({
      upColor: chartTheme.upColor,
      downColor: chartTheme.downColor,
      borderUpColor: chartTheme.upColor,
      borderDownColor: chartTheme.downColor,
      wickUpColor: chartTheme.upColor,
      wickDownColor: chartTheme.downColor,
      borderVisible: preferences.candle_style.border_visible,
      wickVisible: preferences.candle_style.wick_visible && timeframe !== "1s",
    });

    barRef.current?.applyOptions({
      upColor: chartTheme.upColor,
      downColor: chartTheme.downColor,
    });

    lineRef.current?.applyOptions({
      color: chartTheme.upColor,
    });

    areaRef.current?.applyOptions({
      lineColor: chartTheme.upColor,
      topColor: `${chartTheme.upColor}50`,
      bottomColor: `${chartTheme.background}00`,
    });

    volumeRef.current?.setData(
      candlesRef.current.map((c) => ({
        time: c.time,
        value: c.volume,
        color: c.close >= c.open ? chartTheme.volumeUp : chartTheme.volumeDown,
      })),
    );
  }, [timeframe, themeMode, chartPreferences]);

  useEffect(() => {
    chartTypeRef.current = chartType;
    candleRef.current?.applyOptions({ visible: usesCandleSeries(chartType) });
    barRef.current?.applyOptions({ visible: chartType === "bars" });
    lineRef.current?.applyOptions({ visible: usesLineSeries(chartType) });
    areaRef.current?.applyOptions({ visible: chartType === "area" });
    setAllPriceSeriesData(candlesRef.current);
  }, [chartType, setAllPriceSeriesData]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const handleWheel = (event: WheelEvent) => {
      if (!chartRef.current) return;
      const timeScale = chartRef.current.timeScale();
      const range = timeScale.getVisibleLogicalRange();
      if (!range) return;

      event.preventDefault();
      event.stopPropagation();

      if (!event.ctrlKey) {
        const rawDelta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
        if (!rawDelta) return;
        const shift = Math.max(-80, Math.min(80, rawDelta / 12));
        timeScale.setVisibleLogicalRange({ from: range.from + shift, to: range.to + shift });
        return;
      }

      const rect = container.getBoundingClientRect();
      const anchorRatio = rect.width > 0
        ? Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))
        : 0.5;
      const anchor = range.from + (range.to - range.from) * anchorRatio;
      const zoomDelta = event.deltaY || event.deltaX;
      const factor = zoomDelta < 0 ? 0.8 : 1.25;
      timeScale.setVisibleLogicalRange({
        from: anchor - (anchor - range.from) * factor,
        to: anchor + (range.to - anchor) * factor,
      });
    };
    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => container.removeEventListener("wheel", handleWheel);
  }, []);

  const syncIndicatorData = useCallback((data: Candle[]) => {
    const cfg20 = indSettings.sma20;
    const cfg50 = indSettings.sma50;
    const cfgE12 = indSettings.ema12;
    const cfgE26 = indSettings.ema26;
    const cfgBb = indSettings.bb;
    const cfgVolumeMa = indSettings.volumeMa;
    const cfgMacd = indSettings.macd;
    const cfgStochastic = indSettings.stochastic;
    const cfgAtr = indSettings.atr;
    const cfgIchimoku = indSettings.ichimoku;
    const cfgSupertrend = indSettings.supertrend;
    const cfgPsar = indSettings.psar;

    sma20Ref.current?.setData(calcSMA(data, Number(cfg20.period ?? 20)));
    sma50Ref.current?.setData(calcSMA(data, Number(cfg50.period ?? 50)));
    ema12Ref.current?.setData(calcEMA(data, Number(cfgE12.period ?? 12)));
    ema26Ref.current?.setData(calcEMA(data, Number(cfgE26.period ?? 26)));

    const bb = calcBollingerBands(
      data,
      Number(cfgBb.period ?? 20),
      Number(cfgBb.multiplier ?? 2),
    );
    bbUpperRef.current?.setData(bb.upper);
    bbBasisRef.current?.setData(bb.middle);
    bbLowerRef.current?.setData(bb.lower);

    vwapRef.current?.setData(calcVWAP(data));
    volumeMaRef.current?.setData(calcVolumeMA(data, Number(cfgVolumeMa.period ?? 20)));

    const macd = calcMACD(
      data,
      Number(cfgMacd.fastPeriod ?? 12),
      Number(cfgMacd.slowPeriod ?? 26),
      Number(cfgMacd.signalPeriod ?? 9),
    );
    macdLineRef.current?.setData(macd.macd);
    macdSignalRef.current?.setData(macd.signal);
    macdHistogramRef.current?.setData(
      macd.histogram.map((point) => ({
        ...point,
        color: point.value >= 0 ? themeRef.current.volumeUp : themeRef.current.volumeDown,
      })),
    );

    const stochastic = calcStochastic(
      data,
      Number(cfgStochastic.period ?? 14),
      Number(cfgStochastic.signalPeriod ?? 3),
    );
    stochasticKRef.current?.setData(stochastic.k);
    stochasticDRef.current?.setData(stochastic.d);
    atrRef.current?.setData(calcATR(data, Number(cfgAtr.period ?? 14)));

    const ichimoku = calcIchimoku(
      data,
      Number(cfgIchimoku.conversionPeriod ?? 9),
      Number(cfgIchimoku.basePeriod ?? 26),
      Number(cfgIchimoku.spanPeriod ?? 52),
      Number(cfgIchimoku.displacement ?? 26),
    );
    ichimokuConversionRef.current?.setData(ichimoku.conversion);
    ichimokuBaseRef.current?.setData(ichimoku.base);
    ichimokuSpanARef.current?.setData(ichimoku.spanA);
    ichimokuSpanBRef.current?.setData(ichimoku.spanB);
    ichimokuLaggingRef.current?.setData(ichimoku.lagging);

    supertrendRef.current?.setData(
      calcSupertrend(
        data,
        Number(cfgSupertrend.period ?? 10),
        Number(cfgSupertrend.multiplier ?? 3),
      ),
    );
    psarRef.current?.setData(
      calcParabolicSAR(
        data,
        Number(cfgPsar.step ?? 0.02),
        Number(cfgPsar.maxStep ?? 0.2),
      ),
    );

    rsiSeriesRef.current?.setData(calcRSI(data, Number(indSettings.rsi.period ?? 14)));
    mfiSeriesRef.current?.setData(calcMFI(data, Number(indSettings.mfi.period ?? 14)));
  }, [indSettings]);

  const getLiveIndicatorWindow = useCallback(
    (data: Candle[]) => {
      const visibleWindows = [
        indSettings.sma20.visible ? Number(indSettings.sma20.period ?? 20) : 0,
        indSettings.sma50.visible ? Number(indSettings.sma50.period ?? 50) : 0,
        indSettings.ema12.visible ? Number(indSettings.ema12.period ?? 12) : 0,
        indSettings.ema26.visible ? Number(indSettings.ema26.period ?? 26) : 0,
        indSettings.bb.visible ? Number(indSettings.bb.period ?? 20) : 0,
        indSettings.volumeMa.visible ? Number(indSettings.volumeMa.period ?? 20) : 0,
        indSettings.macd.visible
          ? Number(indSettings.macd.slowPeriod ?? 26) + Number(indSettings.macd.signalPeriod ?? 9)
          : 0,
        indSettings.stochastic.visible ? Number(indSettings.stochastic.period ?? 14) : 0,
        indSettings.atr.visible ? Number(indSettings.atr.period ?? 14) : 0,
        indSettings.ichimoku.visible
          ? Number(indSettings.ichimoku.spanPeriod ?? 52) + Number(indSettings.ichimoku.displacement ?? 26)
          : 0,
        indSettings.supertrend.visible ? Number(indSettings.supertrend.period ?? 10) * 4 : 0,
        indSettings.psar.visible ? 100 : 0,
        indSettings.rsi.visible ? Number(indSettings.rsi.period ?? 14) : 0,
        indSettings.mfi.visible ? Number(indSettings.mfi.period ?? 14) : 0,
        indSettings.vwap.visible ? 300 : 0,
      ];
      const maxWindow = Math.max(120, ...visibleWindows) + 32;
      return data.slice(-maxWindow);
    },
    [indSettings],
  );

  const syncLatestIndicatorData = useCallback(
    (data: Candle[]) => {
      if (data.length === 0) return;

      const windowed = getLiveIndicatorWindow(data);
      const cfg20 = indSettings.sma20;
      const cfg50 = indSettings.sma50;
      const cfgE12 = indSettings.ema12;
      const cfgE26 = indSettings.ema26;
      const cfgBb = indSettings.bb;
      const cfgVolumeMa = indSettings.volumeMa;
      const cfgMacd = indSettings.macd;
      const cfgStochastic = indSettings.stochastic;
      const cfgAtr = indSettings.atr;
      const cfgIchimoku = indSettings.ichimoku;
      const cfgSupertrend = indSettings.supertrend;
      const cfgPsar = indSettings.psar;

      const sma20 = calcSMA(windowed, Number(cfg20.period ?? 20));
      const sma50 = calcSMA(windowed, Number(cfg50.period ?? 50));
      const ema12 = calcEMA(windowed, Number(cfgE12.period ?? 12));
      const ema26 = calcEMA(windowed, Number(cfgE26.period ?? 26));
      const bb = calcBollingerBands(
        windowed,
        Number(cfgBb.period ?? 20),
        Number(cfgBb.multiplier ?? 2),
      );
      const vwap = calcVWAP(windowed);
      const volumeMa = calcVolumeMA(windowed, Number(cfgVolumeMa.period ?? 20));
      const macd = calcMACD(
        windowed,
        Number(cfgMacd.fastPeriod ?? 12),
        Number(cfgMacd.slowPeriod ?? 26),
        Number(cfgMacd.signalPeriod ?? 9),
      );
      const stochastic = calcStochastic(
        windowed,
        Number(cfgStochastic.period ?? 14),
        Number(cfgStochastic.signalPeriod ?? 3),
      );
      const atr = calcATR(windowed, Number(cfgAtr.period ?? 14));
      const ichimoku = calcIchimoku(
        windowed,
        Number(cfgIchimoku.conversionPeriod ?? 9),
        Number(cfgIchimoku.basePeriod ?? 26),
        Number(cfgIchimoku.spanPeriod ?? 52),
        Number(cfgIchimoku.displacement ?? 26),
      );
      const supertrend = calcSupertrend(
        windowed,
        Number(cfgSupertrend.period ?? 10),
        Number(cfgSupertrend.multiplier ?? 3),
      );
      const psar = calcParabolicSAR(
        windowed,
        Number(cfgPsar.step ?? 0.02),
        Number(cfgPsar.maxStep ?? 0.2),
      );
      const rsi = calcRSI(windowed, Number(indSettings.rsi.period ?? 14));
      const mfi = calcMFI(windowed, Number(indSettings.mfi.period ?? 14));

      const updateLast = (series: any, points: Array<{ time: number; value: number }>) => {
        const point = points[points.length - 1];
        if (series && point) series.update(point);
      };

      updateLast(sma20Ref.current, sma20);
      updateLast(sma50Ref.current, sma50);
      updateLast(ema12Ref.current, ema12);
      updateLast(ema26Ref.current, ema26);
      updateLast(bbUpperRef.current, bb.upper);
      updateLast(bbBasisRef.current, bb.middle);
      updateLast(bbLowerRef.current, bb.lower);
      updateLast(vwapRef.current, vwap);
      updateLast(volumeMaRef.current, volumeMa);
      updateLast(macdLineRef.current, macd.macd);
      updateLast(macdSignalRef.current, macd.signal);
      const macdLast = macd.histogram[macd.histogram.length - 1];
      if (macdHistogramRef.current && macdLast) {
        macdHistogramRef.current.update({
          ...macdLast,
          color: macdLast.value >= 0 ? themeRef.current.volumeUp : themeRef.current.volumeDown,
        });
      }
      updateLast(stochasticKRef.current, stochastic.k);
      updateLast(stochasticDRef.current, stochastic.d);
      updateLast(atrRef.current, atr);
      updateLast(ichimokuConversionRef.current, ichimoku.conversion);
      updateLast(ichimokuBaseRef.current, ichimoku.base);
      updateLast(ichimokuSpanARef.current, ichimoku.spanA);
      updateLast(ichimokuSpanBRef.current, ichimoku.spanB);
      const laggingLast = ichimoku.lagging[ichimoku.lagging.length - 1];
      if (ichimokuLaggingRef.current && laggingLast) {
        ichimokuLaggingRef.current.update(laggingLast);
      }
      updateLast(supertrendRef.current, supertrend);
      updateLast(psarRef.current, psar);
      updateLast(rsiSeriesRef.current, rsi);
      updateLast(mfiSeriesRef.current, mfi);
    },
    [getLiveIndicatorWindow, indSettings],
  );

  const formingCandleRef = useRef<Candle | null>(null);

  const applyStreamedIndicatorSnapshot = useCallback(
    (snapshot: IndicatorStreamSnapshot) => {
      if (!snapshot?.timestamp) return;
      const time = Math.floor(snapshot.timestamp / 1000);
      const values = snapshot.indicators || {};

      const updateLine = (series: any, key: string) => {
        const value = values[key];
        if (series && typeof value === "number") {
          series.update({ time, value });
        }
      };

      updateLine(sma20Ref.current, "sma20");
      updateLine(sma50Ref.current, "sma50");
      updateLine(ema12Ref.current, "ema12");
      updateLine(ema26Ref.current, "ema26");
      updateLine(bbUpperRef.current, "bb_upper");
      updateLine(bbBasisRef.current, "bb_middle");
      updateLine(bbLowerRef.current, "bb_lower");
      updateLine(volumeMaRef.current, "volume_sma20");
      updateLine(macdLineRef.current, "macd");
      updateLine(macdSignalRef.current, "macd_signal");
      updateLine(atrRef.current, "atr14");
      updateLine(rsiSeriesRef.current, "rsi14");

      const histogram = values.macd_histogram;
      if (macdHistogramRef.current && typeof histogram === "number") {
        macdHistogramRef.current.update({
          time,
          value: histogram,
          color: histogram >= 0 ? themeRef.current.volumeUp : themeRef.current.volumeDown,
        });
      }
    },
    [],
  );

  const applyFetchedIndicatorSeries = useCallback((payload: IndicatorSeriesResponse) => {
    const readPoints = (primary: string, fallback?: string) => {
      const rows = payload.series?.[primary]?.length
        ? payload.series[primary]
        : fallback
          ? payload.series?.[fallback] ?? []
          : [];
      return rows.map((point) => ({
        time: Math.floor(point.timestamp / 1000),
        value: point.value,
      }));
    };

    sma20Ref.current?.setData(readPoints("sma20"));
    sma50Ref.current?.setData(readPoints("sma50"));
    ema12Ref.current?.setData(readPoints("ema12"));
    ema26Ref.current?.setData(readPoints("ema26"));
    bbUpperRef.current?.setData(readPoints("bb_upper"));
    bbBasisRef.current?.setData(readPoints("bb_middle"));
    bbLowerRef.current?.setData(readPoints("bb_lower"));
    volumeMaRef.current?.setData(readPoints("volumeMa", "volume_sma20"));
    macdLineRef.current?.setData(readPoints("macd"));
    macdSignalRef.current?.setData(readPoints("macd_signal"));
    macdHistogramRef.current?.setData(
      readPoints("macd_histogram").map((point) => ({
        ...point,
        color: point.value >= 0 ? themeRef.current.volumeUp : themeRef.current.volumeDown,
      })),
    );
    atrRef.current?.setData(readPoints("atr", "atr14"));
    rsiSeriesRef.current?.setData(readPoints("rsi", "rsi14"));
  }, []);

  const activeIndicatorSignature = activeBackendIndicators(indSettings).join(",");

  useEffect(() => {
    const activeIndicators = activeIndicatorSignature
      .split(",")
      .filter(Boolean);
    if (activeIndicators.length === 0) {
      setIndicatorStatus({});
      return;
    }

    let cancelled = false;
    setIndicatorStatus({ loading: true, messageKey: null });

    const limit = Math.min(1000, Math.max(500, candlesRef.current.length || 0));
    fetchIndicatorSeries(symbol, timeframe, activeIndicators, limit)
      .then((payload) => {
        if (cancelled) return;
        if (payload.source !== "mock_mode_local_candles") {
          applyFetchedIndicatorSeries(payload);
        }

        const messageFromWarning = warningMessageKey(payload.warnings);
        const hasAnyActiveData = activeIndicators.some((indicator) => hasSeriesData(payload, indicator));
        setIndicatorStatus({
          loading: false,
          messageKey: messageFromWarning || (!hasAnyActiveData && payload.source !== "mock_mode_local_candles" ? "indicatorBackendEmpty" : null),
        });
      })
      .catch(() => {
        if (cancelled) return;
        setIndicatorStatus({ loading: false, messageKey: "indicatorDataUnavailable" });
      });

    return () => {
      cancelled = true;
    };
  }, [
    activeIndicatorSignature,
    applyFetchedIndicatorSeries,
    symbol,
    timeframe,
  ]);

  // Helper: load more historical data when scrolling left
  const loadMoreHistoricalData = useCallback(async () => {
    if (isLoadingMoreRef.current || noMoreDataRef.current || !candleRef.current || historicalRange) return;
    // Cooldown: prevent rapid-fire loads
    if (Date.now() - scrollCooldownRef.current < 500) return;
    const current = candlesRef.current;
    if (current.length === 0) return;

    const earliestTime = current[0].time;
    const requestSymbol = symbol;
    const requestInterval = timeframe.toLowerCase();
    
    isLoadingMoreRef.current = true;
    try {
      const limit = 500;
      const olderData = await fetchCandles(requestSymbol, requestInterval, limit, earliestTime);

      // User changed symbol/timeframe while request was in flight.
      if (
        symbolRef.current !== requestSymbol
        || timeframeRef.current !== requestInterval
      ) {
        isLoadingMoreRef.current = false;
        return;
      }
      
      if (olderData.length === 0) {
        noMoreDataRef.current = true;
        isLoadingMoreRef.current = false;
        return;
      }

      // Filter out duplicates and merge
      const newCandles = sanitizeCandlesForChart(olderData).filter(c => c.time < earliestTime);
      if (newCandles.length === 0) {
        noMoreDataRef.current = true;
        isLoadingMoreRef.current = false;
        return;
      }
      const merged = sanitizeCandlesForChart([...newCandles, ...current]);
      
      // Update refs BEFORE touching chart
      candlesRef.current = merged;
      earliestTimestampRef.current = merged[0].time;
      
      // Preserve visible range so chart doesn't jump
      const ts = chartRef.current ? chartRef.current.timeScale() : null;
      const visibleRange = ts ? ts.getVisibleLogicalRange() : null;

      // Apply to chart series
      setAllPriceSeriesData(merged);

      // Keep from at left edge, shift only to to preserve scroll position
      if (ts && visibleRange) {
        const shift = newCandles.length;
        ts.setVisibleLogicalRange({
          from: visibleRange.from,
          to: visibleRange.to + shift,
        });
      }
      
      // Update volume + indicators
      const vs = volumeRef.current;
      if (vs) {
        vs.setData(
          merged.map((c) => ({
            time: c.time,
            value: c.volume,
            color: c.close >= c.open ? themeRef.current.volumeUp : themeRef.current.volumeDown,
          })),
        );
      }
      syncIndicatorData(merged);

      // Update React state last (avoid triggering re-renders mid-update)
      commitCandlesState(merged);
      scrollCooldownRef.current = Date.now();
      isLoadingMoreRef.current = false;
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error("[Chart] Historical pagination error:", sanitizeTechnicalDetails(error));
      }
      isLoadingMoreRef.current = false;
    }
  }, [symbol, timeframe, historicalRange, commitCandlesState, setAllPriceSeriesData, syncIndicatorData]);

  // Subscribe to scroll/zoom events to load more historical data
  useEffect(() => {
    if (!chartRef.current || historicalRange) return;
    
    const timeScale = chartRef.current.timeScale();
    const handleVisibleRangeChange = () => {
      const logicalRange = timeScale.getVisibleLogicalRange();
      if (!logicalRange) return;
      
      // If user scrolls close to the left edge, load more data
      if (logicalRange.from < 20) {
        loadMoreHistoricalData();
      }
    };
    
    timeScale.subscribeVisibleLogicalRangeChange(handleVisibleRangeChange);
    
    return () => {
      timeScale.unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange);
    };
  }, [loadMoreHistoricalData, historicalRange]);

  // Helper: push OHLCV data into chart series + indicators
  const applyDataToChart = useCallback(
    (data: Candle[]) => {
      if (!candleRef.current) return;
      const chartCandles = sanitizeCandlesForChart(data);
      candlesRef.current = chartCandles;
      if (chartCandles.length > 0) {
        earliestTimestampRef.current = chartCandles[0].time;
        noMoreDataRef.current = false;
        scrollCooldownRef.current = 0;
        lastClosedCandleRef.current = chartCandles[chartCandles.length - 1];
      }
      setNoData(chartCandles.length === 0);
      setAllPriceSeriesData(chartCandles);
      const vs = volumeRef.current;
      if (vs)
        vs.setData(
          chartCandles.map((c) => ({
            time: c.time,
            value: c.volume,
            color: c.close >= c.open ? themeRef.current.volumeUp : themeRef.current.volumeDown,
          })),
        );
      syncIndicatorData(chartCandles);
      setInitialVisibleRange(chartCandles);
      if (chartCandles.length > 0)
        setTooltip({ ...chartCandles[chartCandles.length - 1], timeLabel: "" });
      commitCandlesState(chartCandles);
    },
    [commitCandlesState, setAllPriceSeriesData, setInitialVisibleRange, syncIndicatorData],
  );

  // Historical mode handlers
  const handleHistoricalRange = useCallback(
    async (range: HistoricalRange) => {
      // Increment request ID to invalidate pending requests
      historicalRequestIdRef.current += 1;
      const currentRequestId = historicalRequestIdRef.current;

      const requestedTimeframe = normalizeTimeframe(timeframe);
      const effectiveTimeframe = requestedTimeframe === "1s"
        ? HISTORICAL_FALLBACK_TIMEFRAME
        : requestedTimeframe;

      if (requestedTimeframe !== effectiveTimeframe) {
        timeframeRef.current = effectiveTimeframe;
        setTimeframe(effectiveTimeframe);
        onTimeframeChange?.(effectiveTimeframe);
      }

      setHistoricalRange(range);
      setIsLiveMode(false);
      setIsLoading(true);
      setFetchError(null);

      // Unsubscribe WebSocket
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }

      // Stop poll interval
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }

      try {
        const requestSymbol = symbol;
        const requestInterval = effectiveTimeframe;

        // Fetch historical data
        let data = sanitizeCandlesForChart(await fetchHistoricalCandles(
          requestSymbol,
          range.startMs,
          range.endMs,
          500,
          requestInterval,
        ));

        // Check if this request is still valid (not superseded by newer request)
        if (currentRequestId !== historicalRequestIdRef.current) {
          return; // Newer request has been made, discard this result
        }

        // Check if user changed context mid-request
        const currentInterval = normalizeTimeframe(timeframeRef.current);
        if (symbolRef.current !== requestSymbol || currentInterval !== requestInterval) {
          return;
        }

        data = await preloadInitialCandles({
          data,
          requestSymbol,
          requestInterval,
          isHistoricalMode: true,
        });

        // Final check before applying data
        if (currentRequestId !== historicalRequestIdRef.current) {
          return;
        }

        applyDataToChart(data);
        setIsLoading(false);
      } catch (err) {
        // Only show error if this request is still current
        if (currentRequestId === historicalRequestIdRef.current) {
          setIsLoading(false);
          setFetchError(formatNormalizedError(normalizeError(err, { area: "chart", fallbackMessage: t("failedLoadCandles") }), false));
          if (import.meta.env.DEV) {
            console.error("[Chart] Historical range error:", sanitizeTechnicalDetails(err));
          }
        }
      }
    },
    [symbol, timeframe, onTimeframeChange, preloadInitialCandles, applyDataToChart, t],
  );

  const handleBackToLive = useCallback(() => {
    // Invalidate any pending historical requests
    historicalRequestIdRef.current += 1;

    setHistoricalRange(null);
    setIsLiveMode(true);
    setFetchError(null);
    // The live mode useEffect will trigger and reconnect WebSocket + poll
  }, []);

  // Load data when symbol or timeframe changes (live mode) + auto-refresh
  useEffect(() => {
    if (!candleRef.current || !isLiveMode) return;
    let cancelled = false;

    const preferences = chartPreferences ?? DEFAULT_CHART_PREFERENCES;
    if (chartRef.current) {
      chartRef.current
        .timeScale()
        .applyOptions({
          secondsVisible: preferences.scale.seconds_visible && timeframe === "1s",
        });
    }

    // Use unified settings for all timeframes (no is1s branching)
    const limit = CHART_CONFIG.VISIBLE_BARS;

    // Full load — fetches candles, rebuilds all series + indicators
    const loadData = async () => {
      setFetchError(null);
      try {
        const requestSymbol = symbol;
        const requestInterval = timeframe.toLowerCase();
        let data = sanitizeCandlesForChart(await fetchCandles(requestSymbol, requestInterval, limit));
        if (cancelled) return;

        data = await preloadInitialCandles({
          data,
          requestSymbol,
          requestInterval,
          isHistoricalMode: false,
        });
        if (cancelled) return;

        applyDataToChart(data);
        setIsLoading(false);
      } catch (err) {
        if (cancelled) return;
        setIsLoading(false);
        setFetchError(formatNormalizedError(normalizeError(err, { area: "chart", fallbackMessage: t("failedLoadCandles") }), false));
      }
    };

    // ⚠️ CRITICAL: Block WebSocket subscription when replay mode is active
    // to prevent live fetches or WebSocket updates from interfering with playback.
    if (isReplayActive) {
      return () => {
        cancelled = true;
      };
    }

    setIsLoading(true);
    setFetchError(null);
    setNoData(false);
    formingCandleRef.current = null;
    loadData();

    const unsub = subscribeAllTimeframes({
      symbol,
      onTicker: (ticker) => {
        if (cancelled) return;
        const price = ticker.price;
        const eventTimeMs = ticker.eventTime;
        if (!Number.isFinite(price) || price <= 0 || !candleRef.current) return;
        const timeframeSec = getTimeframeSeconds(timeframeRef.current);
        if (!timeframeSec) return;

        const bucketTime = Math.floor(eventTimeMs / 1000 / timeframeSec) * timeframeSec;
        const lastClosed = lastClosedCandleRef.current;
        const forming = formingCandleRef.current;

        let nextCandle: Candle;

        if (forming && forming.time === bucketTime) {
          nextCandle = {
            time: bucketTime,
            open: forming.open,
            high: Math.max(forming.high, price),
            low: Math.min(forming.low, price),
            close: price,
            volume: forming.volume || 0,
          };
          formingCandleRef.current = nextCandle;
        } else if (forming && forming.time < bucketTime) {
          lastClosedCandleRef.current = forming;
          const open = forming.close;
          nextCandle = {
            time: bucketTime,
            open,
            high: Math.max(open, price),
            low: Math.min(open, price),
            close: price,
            volume: 0,
          };
          formingCandleRef.current = nextCandle;
        } else if (!forming && lastClosed) {
          const open = lastClosed.close;
          nextCandle = {
            time: bucketTime,
            open,
            high: Math.max(open, price),
            low: Math.min(open, price),
            close: price,
            volume: 0,
          };
          formingCandleRef.current = nextCandle;
        } else {
          return;
        }

        updateAllPriceSeries(nextCandle);
        if (volumeRef.current) {
          volumeRef.current.update({
            time: nextCandle.time,
            value: nextCandle.volume || 0,
            color: nextCandle.close >= nextCandle.open ? themeRef.current.volumeUp : themeRef.current.volumeDown,
          });
        }
        const closed = candlesRef.current.filter((c) => c.time < bucketTime);
        const updatedCandles = [...closed, nextCandle];
        candlesRef.current = updatedCandles;
        syncLatestIndicatorData(updatedCandles);
        commitCandlesState(updatedCandles);
        setTooltip((tip) =>
          tip ? { ...tip, ...nextCandle, timeLabel: tip.timeLabel || "" } : null,
        );
      },
      onCandle: (tf, candle) => {
        if (tf !== timeframe.toLowerCase()) return;
        if (cancelled || !candleRef.current) return;
        const official = sanitizeCandlesForChart([candle])[0];
        if (!official) return;
        const forming = formingCandleRef.current;
        if (!forming) return;
        if (official.time !== forming.time) return;

        const merged = {
          ...forming,
          high: Math.max(official.high, forming.high),
          low: Math.min(official.low, forming.low),
          volume: official.volume || forming.volume || 0,
        };
        formingCandleRef.current = merged;
        updateAllPriceSeries(merged);
        if (volumeRef.current) {
          volumeRef.current.update({
            time: merged.time,
            value: merged.volume || 0,
            color: merged.close >= merged.open ? themeRef.current.volumeUp : themeRef.current.volumeDown,
          });
        }
        const closed = candlesRef.current.filter((c) => c.time < merged.time);
        const updatedCandles = [...closed, merged];
        candlesRef.current = updatedCandles;
        syncLatestIndicatorData(updatedCandles);
        commitCandlesState(updatedCandles);
      },
    });

    const indicatorUnsub = subscribeIndicatorStream({
      symbol,
      timeframe,
      onIndicator: (snapshot) => {
        if (cancelled) return;
        if (normalizeTimeframe(snapshot.interval) !== normalizeTimeframe(timeframe)) return;
        applyStreamedIndicatorSnapshot(snapshot);
      },
    });

    // Store unsubscribe function in ref
    unsubscribeRef.current = unsub;
    indicatorUnsubscribeRef.current = indicatorUnsub;

    // OPTIMIZATION: Disable aggressive polling. WebSocket is now responsive (0.05s).
    // Only poll as fallback if WebSocket connection fails (passive recovery).
    // Previous: 1.5-3s polling added latency. Now: WebSocket primary, poll backup.
    // Fallback poll will be triggered by connection monitoring in future release.
    const pollId = null;
    pollIntervalRef.current = pollId;

    return () => {
      cancelled = true;
      if (pollId) clearInterval(pollId);
      if (unsub) unsub();
      if (indicatorUnsub) indicatorUnsub();
      pollIntervalRef.current = null;
      unsubscribeRef.current = null;
      indicatorUnsubscribeRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    symbol,
    timeframe,
    isLiveMode,
    retryCount,
    applyDataToChart,
    applyStreamedIndicatorSnapshot,
    commitCandlesState,
    preloadInitialCandles,
    syncLatestIndicatorData,
    updateAllPriceSeries,
    isReplayActive, // ⚠️ Re-run when replay mode changes to block/unblock WebSocket
  ]);

  // ⚠️ CRITICAL: Cleanup WebSocket immediately when entering replay mode
  useEffect(() => {
    if (isReplayActive) {
      // Unsubscribe WebSocket
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      if (indicatorUnsubscribeRef.current) {
        indicatorUnsubscribeRef.current();
        indicatorUnsubscribeRef.current = null;
      }
      // Stop poll interval
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }
  }, [isReplayActive]);

  useEffect(() => {
    if (!showNewsMarkers) {
      candleRef.current?.setMarkers?.([]);
      return;
    }
    if (!candleRef.current || !newsItems?.length) return;

    const markers = newsItems
      .filter((article) => {
        const symbols = article.symbolsMentioned || article.symbols || [];
        return symbols.some((s) => symbol.includes(s));
      })
      .map((article) => {
        const sentiment = (article.sentiment_label || "neutral").toLowerCase();
        const color = sentiment === "bullish" ? "#22c55e" : sentiment === "bearish" ? "#ef4444" : "#94a3b8";
        const ts = typeof article.published_at === "string" ? Date.parse(article.published_at) : article.published_at;
        return {
          time: Math.floor(ts / 1000),
          position: "aboveBar",
          color,
          shape: "circle",
          text: "N",
        } as any;
      })
      .sort((a, b) => Number(a.time) - Number(b.time));

    candleRef.current?.setMarkers?.(markers);
    return () => {
      candleRef.current?.setMarkers?.([]);
    };
  }, [newsItems, showNewsMarkers, symbol]);

  // Load historical data when date range is set
  // (Removed - now handled by handleHistoricalRange callback)

  // Refetch historical data when symbol/timeframe changes in historical mode
  useEffect(() => {
    if (!isLiveMode && historicalRange) {
      if (normalizeTimeframe(timeframe) === "1s") {
        timeframeRef.current = HISTORICAL_FALLBACK_TIMEFRAME;
        setTimeframe(HISTORICAL_FALLBACK_TIMEFRAME);
        onTimeframeChange?.(HISTORICAL_FALLBACK_TIMEFRAME);
        return;
      }
      handleHistoricalRange(historicalRange);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, timeframe]);

  chartTypeRef.current = chartType;

  if (!seriesControllerRef.current) {
    seriesControllerRef.current = {
      setData: (data: Candle[]) => setAllPriceSeriesData(data),
      update: (candle: Candle) => updateAllPriceSeries(candle),
      priceToCoordinate: (price: number) => {
        const activeSeries = getActivePriceSeries();
        return activeSeries?.priceToCoordinate(price) ?? null;
      },
      coordinateToPrice: (coordinate: number) => {
        const activeSeries = getActivePriceSeries();
        return activeSeries?.coordinateToPrice(coordinate) ?? null;
      },
    };
  }

  // Apply indicator settings (visibility, color, period, lineWidth)
  useEffect(() => {
    if (candles.length === 0) return;
    const cfg20 = indSettings.sma20;
    const cfg50 = indSettings.sma50;
    const cfgE12 = indSettings.ema12;
    const cfgE26 = indSettings.ema26;
    const cfgBb = indSettings.bb;
    const cfgVwap = indSettings.vwap;
    const cfgVolume = indSettings.volume;
    const cfgVolumeMa = indSettings.volumeMa;
    const cfgR = indSettings.rsi;
    const cfgM = indSettings.mfi;
    const cfgMacd = indSettings.macd;
    const cfgStochastic = indSettings.stochastic;
    const cfgAtr = indSettings.atr;
    const cfgIchimoku = indSettings.ichimoku;
    const cfgSupertrend = indSettings.supertrend;
    const cfgPsar = indSettings.psar;

    if (sma20Ref.current) {
      sma20Ref.current.applyOptions({
        visible: cfg20.visible,
        color: cfg20.color,
        lineWidth: cfg20.lineWidth,
      });
    }
    if (sma50Ref.current) {
      sma50Ref.current.applyOptions({
        visible: cfg50.visible,
        color: cfg50.color,
        lineWidth: cfg50.lineWidth,
      });
    }
    if (ema12Ref.current) {
      ema12Ref.current.applyOptions({
        visible: cfgE12.visible,
        color: cfgE12.color,
        lineWidth: cfgE12.lineWidth,
      });
    }
    if (ema26Ref.current) {
      ema26Ref.current.applyOptions({
        visible: cfgE26.visible,
        color: cfgE26.color,
        lineWidth: cfgE26.lineWidth,
      });
    }
    bbUpperRef.current?.applyOptions({
      visible: cfgBb.visible,
      color: cfgBb.color,
      lineWidth: cfgBb.lineWidth,
    });
    bbBasisRef.current?.applyOptions({
      visible: cfgBb.visible,
      color: cfgBb.basisColor,
      lineWidth: cfgBb.lineWidth,
    });
    bbLowerRef.current?.applyOptions({
      visible: cfgBb.visible,
      color: cfgBb.color,
      lineWidth: cfgBb.lineWidth,
    });
    vwapRef.current?.applyOptions({
      visible: cfgVwap.visible,
      color: cfgVwap.color,
      lineWidth: cfgVwap.lineWidth,
    });
    supertrendRef.current?.applyOptions({
      visible: cfgSupertrend.visible,
      color: cfgSupertrend.color,
      lineWidth: cfgSupertrend.lineWidth,
    });
    psarRef.current?.applyOptions({
      visible: cfgPsar.visible,
      color: cfgPsar.color,
      lineWidth: cfgPsar.lineWidth,
      lineStyle: LineStyle.Dotted,
    });
    volumeRef.current?.applyOptions({ visible: cfgVolume.visible });
    volumeMaRef.current?.applyOptions({
      visible: cfgVolumeMa.visible,
      color: cfgVolumeMa.color,
      lineWidth: cfgVolumeMa.lineWidth,
    });
    macdLineRef.current?.applyOptions({
      visible: cfgMacd.visible,
      color: cfgMacd.color,
      lineWidth: cfgMacd.lineWidth,
    });
    macdSignalRef.current?.applyOptions({
      visible: cfgMacd.visible,
      color: cfgMacd.signalColor,
      lineWidth: cfgMacd.lineWidth,
    });
    macdHistogramRef.current?.applyOptions({ visible: cfgMacd.visible });
    stochasticKRef.current?.applyOptions({
      visible: cfgStochastic.visible,
      color: cfgStochastic.color,
      lineWidth: cfgStochastic.lineWidth,
    });
    stochasticDRef.current?.applyOptions({
      visible: cfgStochastic.visible,
      color: cfgStochastic.signalColor,
      lineWidth: cfgStochastic.lineWidth,
    });
    atrRef.current?.applyOptions({
      visible: cfgAtr.visible,
      color: cfgAtr.color,
      lineWidth: cfgAtr.lineWidth,
    });
    ichimokuConversionRef.current?.applyOptions({
      visible: cfgIchimoku.visible,
      color: cfgIchimoku.color,
      lineWidth: cfgIchimoku.lineWidth,
    });
    ichimokuBaseRef.current?.applyOptions({
      visible: cfgIchimoku.visible,
      color: cfgIchimoku.baseColor,
      lineWidth: cfgIchimoku.lineWidth,
    });
    ichimokuSpanARef.current?.applyOptions({
      visible: cfgIchimoku.visible,
      color: cfgIchimoku.spanAColor,
      lineWidth: cfgIchimoku.lineWidth,
    });
    ichimokuSpanBRef.current?.applyOptions({
      visible: cfgIchimoku.visible,
      color: cfgIchimoku.spanBColor,
      lineWidth: cfgIchimoku.lineWidth,
    });
    ichimokuLaggingRef.current?.applyOptions({
      visible: cfgIchimoku.visible,
      color: cfgIchimoku.color,
      lineWidth: cfgIchimoku.lineWidth,
    });
    if (rsiSeriesRef.current) {
      rsiSeriesRef.current.applyOptions({
        visible: cfgR.visible,
        color: cfgR.color,
        lineWidth: cfgR.lineWidth || 1.5,
      });
    }
    if (mfiSeriesRef.current) {
      mfiSeriesRef.current.applyOptions({
        visible: cfgM.visible,
        color: cfgM.color,
        lineWidth: cfgM.lineWidth || 1.5,
      });
    }
    syncIndicatorData(candles);

    if (chartRef.current) {
      const oscillatorVisible = Boolean(
        cfgR.visible ||
        cfgM.visible ||
        cfgMacd.visible ||
        cfgStochastic.visible ||
        cfgAtr.visible,
      );
      chartRef.current
        .priceScale("oscillator")
        .applyOptions({ visible: oscillatorVisible });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indSettings, syncIndicatorData]);

  const lastCandle = candles[candles.length - 1];
  const firstCandle = candles[0];
  const priceDiff =
    lastCandle && firstCandle ? lastCandle.close - firstCandle.open : 0;
  const pricePct = firstCandle
    ? ((priceDiff / firstCandle.open) * 100).toFixed(2)
    : null;
  const isUp = priceDiff >= 0;

  const handleExportChart = useCallback(async () => {
    const stage = chartStageRef.current;
    if (!stage) return;

    const stageRect = stage.getBoundingClientRect();
    if (stageRect.width <= 0 || stageRect.height <= 0) return;

    const headerHeight = 72;
    const scale = Math.min(window.devicePixelRatio || 1, 2);
    const exportCanvas = document.createElement("canvas");
    exportCanvas.width = Math.round(stageRect.width * scale);
    exportCanvas.height = Math.round((stageRect.height + headerHeight) * scale);

    const ctx = exportCanvas.getContext("2d");
    if (!ctx) return;

    const chartTheme = themeRef.current;
    ctx.scale(scale, scale);
    ctx.fillStyle = chartTheme.background;
    ctx.fillRect(0, 0, stageRect.width, stageRect.height + headerHeight);

    ctx.fillStyle = chartTheme.textColor;
    ctx.font = "600 18px Inter, Segoe UI, sans-serif";
    ctx.fillText(`${symbol} ${timeframe.toUpperCase()} ${chartType.toUpperCase()}`, 16, 26);

    const latest = candlesRef.current[candlesRef.current.length - 1];
    if (latest) {
      const directionColor = latest.close >= latest.open ? chartTheme.upColor : chartTheme.downColor;
      ctx.font = "12px Inter, Segoe UI, sans-serif";
      ctx.fillStyle = directionColor;
      ctx.fillText(`O ${latest.open}  H ${latest.high}  L ${latest.low}  C ${latest.close}`, 16, 48);
      ctx.fillStyle = chartTheme.textColor;
      ctx.fillText(`Vol ${latest.volume.toLocaleString()}  ${new Date(latest.time * 1000).toLocaleString()}`, 16, 64);
    }

    const stageOffsetY = headerHeight;
    const canvases = Array.from(stage.querySelectorAll("canvas"));
    canvases.forEach((canvas) => {
      const rect = canvas.getBoundingClientRect();
      const dx = rect.left - stageRect.left;
      const dy = rect.top - stageRect.top + stageOffsetY;
      ctx.drawImage(canvas, dx, dy, rect.width, rect.height);
    });

    const overlaySvgs = Array.from(stage.querySelectorAll("svg")).filter((svg) => {
      const rect = svg.getBoundingClientRect();
      return rect.width >= stageRect.width * 0.9 && rect.height >= stageRect.height * 0.9;
    });

    for (const svg of overlaySvgs) {
      const rect = svg.getBoundingClientRect();
      const clone = svg.cloneNode(true) as SVGSVGElement;
      clone.setAttribute("width", String(rect.width));
      clone.setAttribute("height", String(rect.height));
      clone.setAttribute("viewBox", `0 0 ${rect.width} ${rect.height}`);

      const svgMarkup = new XMLSerializer().serializeToString(clone);
      const blob = new Blob([svgMarkup], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);

      try {
        const image = new Image();
        const loaded = new Promise<void>((resolve, reject) => {
          image.onload = () => resolve();
          image.onerror = () => reject(new Error("Failed to load drawing overlay"));
        });
        image.src = url;
        await loaded;
        ctx.drawImage(
          image,
          rect.left - stageRect.left,
          rect.top - stageRect.top + stageOffsetY,
          rect.width,
          rect.height,
        );
      } finally {
        URL.revokeObjectURL(url);
      }
    }

    const link = document.createElement("a");
    link.download = `${symbol}_${timeframe}_chart.png`;
    link.href = exportCanvas.toDataURL("image/png");
    link.click();
  }, [chartType, symbol, timeframe]);

  const handleToggleFullscreen = useCallback(() => {
    const root = rootRef.current;
    if (!root) return;

    if (document.fullscreenElement === root) {
      void document.exitFullscreen();
      return;
    }

    void root.requestFullscreen();
  }, []);

  const selectedTimeframeLabel = TIMEFRAMES[normalizeTimeframe(timeframe)].label;
  const marketSelectorSymbols =
    symbols.length > 0 ? Array.from(new Set([symbol, ...symbols])) : [symbol];
  const toolbarGroupClass = "lm-toolbar-group flex h-8 flex-shrink-0 items-center gap-1 rounded-md border p-0.5";
  const toolbarButtonBase = "lm-toolbar-button flex h-7 flex-shrink-0 items-center justify-center whitespace-nowrap rounded px-2 text-xs font-semibold transition-colors";
  const toolbarIconButtonBase = "lm-toolbar-button flex h-7 w-7 flex-shrink-0 items-center justify-center rounded transition-colors";
  const chartTypeButtonBase = "lm-toolbar-button flex h-7 w-8 flex-shrink-0 items-center justify-center rounded text-xs font-semibold transition-colors";
  const toolbarIdleClass = "";
  const toolbarActiveClass = "is-active shadow-sm shadow-blue-950/20";

  return (
    <div
      ref={rootRef}
      className={`flex min-h-0 w-full flex-col overflow-hidden bg-[var(--lm-bg-primary)] ${
        isFullscreen ? "h-dvh rounded-none" : "h-full rounded-lg"
      }`}
    >
      <div data-ai-section="chart-toolbar" className="lm-toolbar-surface flex-none border-b">
        <div className="overflow-x-auto overflow-y-visible">
          <div className="flex min-h-11 w-max min-w-full items-center gap-2 px-2 py-1.5 sm:px-3">
            <div className="flex min-w-0 flex-shrink-0 items-center gap-2">
              <MarketSelector
                symbols={marketSelectorSymbols}
                selectedSymbol={symbol}
                onSelect={handleSymbolChange}
                starredSymbols={starredSymbols}
                onToggleStar={handleToggleSymbolStar}
              />

              {lastCandle && (
                <div className="flex h-8 min-w-0 flex-shrink-0 items-center gap-2 whitespace-nowrap">
                  <span
                    className={`font-mono text-sm font-bold ${isUp ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
                  >
                    {lastCandle.close.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </span>
                  {pricePct && (
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs font-semibold ${
                        isUp
                          ? "bg-green-100 text-green-700 dark:bg-green-900/70 dark:text-green-300"
                          : "bg-red-100 text-red-700 dark:bg-red-900/70 dark:text-red-300"
                      }`}
                    >
                      {isUp ? "+" : ""}
                      {pricePct}%
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="ml-auto flex min-w-0 flex-shrink-0 items-center justify-end gap-1.5">
              <div className="relative flex-shrink-0">
                <button
                  ref={timeframeButtonRef}
                  type="button"
                  onClick={() => setIsTimeframeMenuOpen((open) => !open)}
                  className={`${toolbarButtonBase} min-w-14 gap-1 border border-[var(--lm-border)] px-2.5 ${
                    isTimeframeMenuOpen
                      ? "border-blue-500 bg-blue-600 text-white shadow-sm shadow-blue-950/20"
                      : "lm-toolbar-button bg-[var(--lm-bg-secondary)] text-[var(--lm-text-secondary)] hover:border-[var(--lm-blue-border)]"
                  }`}
                >
                  <span className="min-w-6 text-left">{selectedTimeframeLabel}</span>
                  <ChevronDown
                    size={12}
                    className={`transition-transform ${isTimeframeMenuOpen ? "rotate-180" : ""}`}
                  />
                </button>
                <DropdownPortal
                  anchorRef={timeframeButtonRef}
                  className="lm-menu-surface overflow-hidden rounded border shadow-2xl"
                  maxWidth={112}
                  minWidth={96}
                  onClose={() => setIsTimeframeMenuOpen(false)}
                  open={isTimeframeMenuOpen}
                  width={112}
                >
                    {(isLiveMode ? TIMEFRAME_KEYS : HISTORICAL_TIMEFRAME_KEYS).map((key) => {
                      const active = normalizeTimeframe(timeframe) === key;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => handleTimeframeSelect(key)}
                          className={`w-full px-3 py-2 text-left text-xs font-medium transition-colors ${
                            active
                              ? "bg-blue-600 text-white"
                              : "text-[var(--lm-text-secondary)] hover:bg-[var(--lm-blue-soft)] hover:text-[var(--lm-blue)]"
                          }`}
                        >
                          {TIMEFRAMES[key].label}
                        </button>
                      );
                    })}
                </DropdownPortal>
              </div>

              <div className={`${toolbarGroupClass} overflow-x-auto overscroll-x-contain`}>
                <div className="relative">
                  <button
                    ref={indicatorButtonRef}
                    onClick={() => setShowIndPanel((v) => !v)}
                    className={`${toolbarButtonBase} gap-1.5 ${
                      showIndPanel ? toolbarActiveClass : toolbarIdleClass
                    }`}
                    title={t("technicalIndicators")}
                  >
                    <Activity size={13} /> {t("indicators")}
                  </button>
                  <DropdownPortal
                    anchorRef={indicatorButtonRef}
                    className="max-w-[calc(100vw-1rem)]"
                    maxWidth={320}
                    minWidth={280}
                    onClose={() => setShowIndPanel(false)}
                    open={showIndPanel}
                    width={320}
                  >
                      <IndicatorPanel
                        indSettings={indSettings}
                        onChange={setIndSettings}
                        status={indicatorStatus}
                      />
                  </DropdownPortal>
                </div>

                <DateRangePicker
                  active={!isLiveMode}
                  onApply={handleHistoricalRange}
                  onClear={handleBackToLive}
                />

                <button
                  onClick={handleExportChart}
                  className={`${toolbarButtonBase} gap-1.5 ${toolbarIdleClass}`}
                  title={t("exportAsPNG")}
                >
                  <Download size={12} />
                  <span className="hidden sm:inline">{t("exportChart")}</span>
                </button>
              </div>

              <div className={`${toolbarGroupClass} max-w-[18rem] overflow-x-auto overscroll-x-contain`} aria-label={t("chartTypeSettings")}>
                {CHART_TYPE_ORDER.map((type) => {
                  const Icon = CHART_TYPE_ICONS[type];
                  const label = t(CHART_TYPE_LABELS[type]);
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => onChartTypeChange?.(type)}
                      className={`${chartTypeButtonBase} ${
                        chartType === type ? toolbarActiveClass : toolbarIdleClass
                      }`}
                      aria-pressed={chartType === type}
                      title={label}
                    >
                      <Icon size={14} />
                      <span className="sr-only">{label}</span>
                    </button>
                  );
                })}
              </div>

              <div className={toolbarGroupClass}>
                <button
                  onClick={zoomIn}
                  disabled={!canZoomIn}
                  className={`${toolbarIconButtonBase} ${
                    canZoomIn
                      ? toolbarIdleClass
                      : "is-disabled cursor-not-allowed"
                  }`}
                  title={t("zoomIn")}
                >
                  <ZoomIn size={12} />
                </button>
                <button
                  onClick={zoomOut}
                  disabled={!canZoomOut}
                  className={`${toolbarIconButtonBase} ${
                    canZoomOut
                      ? toolbarIdleClass
                      : "is-disabled cursor-not-allowed"
                  }`}
                  title={t("zoomOut")}
                >
                  <ZoomOut size={12} />
                </button>
                <button
                  onClick={handleToggleFullscreen}
                  className={`${toolbarIconButtonBase} ${toolbarIdleClass}`}
                  title={isFullscreen ? t("exitFullscreen") : t("fullscreen")}
                >
                  {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Historical mode banner */}
      {!isLiveMode && historicalRange && (
        <div className="flex flex-none items-center justify-between px-3 py-1.5 bg-amber-900/40 border-b border-amber-700/50">
          <span className="text-xs text-amber-300">
            {new Date(historicalRange.startMs).toLocaleString()} &mdash;{" "}
            {new Date(historicalRange.endMs).toLocaleString()} ({normalizeTimeframe(timeframe) === "1s" ? HISTORICAL_FALLBACK_TIMEFRAME : timeframe})
          </span>
          <button
            onClick={handleBackToLive}
            className="text-xs text-amber-600 underline hover:text-amber-500 dark:text-amber-400 dark:hover:text-white"
          >
            {t("live")}
          </button>
        </div>
      )}

      {/* Tab content — candlestick chart is always mounted to preserve the
           lightweight-charts instance; visibility is toggled via CSS. */}
      <div className="flex min-h-0 flex-1 flex-col">
        {/* OHLCV bar */}
        <div className="min-h-[28px] flex-none border-b border-[var(--lm-border)] bg-[var(--lm-bg-primary)] px-3 py-1">
          <OHLCVBar data={tooltip} />
        </div>
        {/* Chart canvas + overlay slot */}
        <div ref={chartStageRef} data-ai-section="chart-canvas" className="relative min-h-0 flex-1 overflow-hidden">
          <div ref={containerRef} className="w-full h-full" />
          {isLoading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-[var(--lm-bg-primary)]/60">
              <span className="animate-pulse text-sm text-[var(--lm-text-secondary)]">
                {t("loading")}
              </span>
            </div>
          )}
          {fetchError && !isLoading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-[var(--lm-bg-primary)]/60">
              <div className="text-center">
                <p className="text-red-400 text-sm mb-2">{fetchError}</p>
                <button
                  onClick={() => {
                    setFetchError(null);
                    setRetryCount((c) => c + 1);
                  }}
                  className="rounded bg-blue-600 px-3 py-1 text-xs text-white transition-colors hover:bg-blue-700"
                >
                  {t("retry")}
                </button>
              </div>
            </div>
          )}
          {noData && !isLoading && !fetchError && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-[var(--lm-bg-primary)]/40">
              <p className="text-sm text-[var(--lm-text-secondary)]">
                {t("noDataAvailable")} {symbol} @ {timeframe}
              </p>
            </div>
          )}
          {typeof children === 'function'
            ? children(chartRef.current, seriesControllerRef.current)
            : children}
        </div>
      </div>

    </div>
  );
};

export default CandlestickChart;
