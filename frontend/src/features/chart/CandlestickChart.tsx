import React, { useEffect, useRef, useState, useCallback } from "react";
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
import { Settings, Download, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { normalizeTimeframe } from "@/constants/timeframes";
import { useI18n } from "@/i18n";
import { useChartZoom } from "@/hooks/useChartZoom";
import {
  fetchCandles,
  fetchHistoricalCandles,
  subscribeAllTimeframes,
  TIMEFRAMES as SERVICE_TIMEFRAMES,
} from "@/services/marketDataService";
import MarketSelector from "./MarketSelector";
import DateRangePicker from "./DateRangePicker";
import {
  getChartTheme,
  DEFAULT_INDICATOR_SETTINGS,
  localTickMarkFormatter,
  localTimeFormatter,
} from "./chartConstants";
import { calcSMA, calcEMA, calcRSI, calcMFI } from "./indicatorUtils";
import IndicatorPanel from "./IndicatorPanel";
import OHLCVBar from "./OHLCVBar";
import type { Candle, ChartType, IndicatorSettings, HistoricalRange, TimeframeKey } from "@/types";

interface CandlestickChartProps {
  defaultSymbol?: string;
  symbol?: string;
  timeframe?: TimeframeKey;
  symbols?: string[];
  children?: React.ReactNode | ((chartApi: any, candleSeries: any) => React.ReactNode);
  starredSymbols?: string[];
  onToggleStar?: (symbol: string) => void;
  onSymbolChange?: (symbol: string) => void;
  onCandlesChange?: (candles: Candle[]) => void;
  onTimeframeChange?: (timeframe: TimeframeKey) => void;
  themeMode?: "dark" | "light";
  chartType?: ChartType;
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
  timeframe: timeframeProp,
  symbols = [],
  children,
  starredSymbols = [],
  onToggleStar,
  onSymbolChange,
  onCandlesChange,
  onTimeframeChange,
  themeMode = "dark",
  chartType = "candles",
  isReplayActive = false,
}) => {
  const { t } = useI18n();
  const containerRef = useRef<HTMLDivElement>(null);
  const chartStageRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const candleRef = useRef<any>(null);
  const barRef = useRef<any>(null);
  const lineRef = useRef<any>(null);
  const areaRef = useRef<any>(null);
  const volumeRef = useRef<any>(null);
  const sma20Ref = useRef<any>(null);
  const sma50Ref = useRef<any>(null);
  const emaRef = useRef<any>(null);
  const rsiSeriesRef = useRef<any>(null);
  const mfiSeriesRef = useRef<any>(null);
  const candlesRef = useRef<Candle[]>([]);
  const themeRef = useRef(getChartTheme());
  const symbolRef = useRef(defaultSymbol);
  const timeframeRef = useRef(timeframeProp || "1m");
  const chartTypeRef = useRef<ChartType>(chartType);

  const [symbol, setSymbol] = useState(symbolProp || defaultSymbol);
  const [timeframe, setTimeframe] = useState(timeframeProp || "1m");

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

  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [showIndPanel, setShowIndPanel] = useState(false);
  const [indSettings, setIndSettings] = useState<Record<string, IndicatorSettings>>(() =>
    JSON.parse(JSON.stringify(DEFAULT_INDICATOR_SETTINGS)),
  );
  const [candles, setCandles] = useState<Candle[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [historicalRange, setHistoricalRange] = useState<HistoricalRange | null>(null);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [noData, setNoData] = useState(false);
  const isLoadingMoreRef = useRef(false);
  const earliestTimestampRef = useRef<number | null>(null);
  const noMoreDataRef = useRef(false);
  const scrollCooldownRef = useRef(0);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const historicalRequestIdRef = useRef(0);
  const seriesControllerRef = useRef<any>(null);

  // Initialize zoom control hook
  const { zoomIn, zoomOut, resetZoom, canZoomIn, canZoomOut } = useChartZoom({
    chartApi: chartRef.current,
    initialBarSpacing: 4,
    minBarSpacing: 2,
    maxBarSpacing: 30,
  });

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
    SHOW_SECONDS: true,       // All timeframes show seconds (consistent display)
  };

  const toCloseSeriesData = useCallback(
    (data: Candle[]) => data.map((c) => ({ time: c.time, value: c.close })),
    [],
  );

  const getActivePriceSeries = useCallback(() => {
    if (chartTypeRef.current === "bars") return barRef.current || candleRef.current;
    if (chartTypeRef.current === "line") return lineRef.current || candleRef.current;
    if (chartTypeRef.current === "area") return areaRef.current || candleRef.current;
    return candleRef.current;
  }, []);

  const setAllPriceSeriesData = useCallback(
    (data: Candle[]) => {
      candleRef.current?.setData(data);
      barRef.current?.setData(data);
      const closeData = toCloseSeriesData(data);
      lineRef.current?.setData(closeData);
      areaRef.current?.setData(closeData);
    },
    [toCloseSeriesData],
  );

  const updateAllPriceSeries = useCallback((candle: Candle) => {
    candleRef.current?.update(candle);
    barRef.current?.update(candle);
    const closePoint = { time: candle.time, value: candle.close };
    lineRef.current?.update(closePoint);
    areaRef.current?.update(closePoint);
  }, []);

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

      if (!Array.isArray(olderData) || olderData.length === 0) return data;

      const dedupedOlder = olderData.filter((c) => c.time < earliestTime);
      if (dedupedOlder.length === 0) return data;

      return [...dedupedOlder, ...data].sort((a, b) => a.time - b.time);
    },
    [getInitialVisibleBars, getTimeframeSeconds],
  );

  // Keep latest symbol/timeframe in refs so async scroll-load results can be
  // ignored when the user changes context mid-request.
  useEffect(() => {
    symbolRef.current = symbol;
    timeframeRef.current = normalizeTimeframe(timeframe);
  }, [symbol, timeframe]);

  const handleSymbolChange = useCallback(
    (s: string) => {
      setSymbol(s);
      if (onSymbolChange) onSymbolChange(s);
    },
    [onSymbolChange],
  );

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
    const chartTheme = getChartTheme();
    themeRef.current = chartTheme;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: chartTheme.background },
        textColor: chartTheme.textColor,
        fontFamily: "'Inter','Segoe UI',sans-serif",
        fontSize: 12,
      },
      localization: {
        locale: navigator.language || "en-US",
        timeFormatter: localTimeFormatter,
      },
      grid: {
        vertLines: { color: chartTheme.gridColor, style: LineStyle.Solid },
        horzLines: { color: chartTheme.gridColor, style: LineStyle.Solid },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: chartTheme.crosshair, labelBackgroundColor: chartTheme.crosshairLabelBg },
        horzLine: { color: chartTheme.crosshair, labelBackgroundColor: chartTheme.crosshairLabelBg },
      },
      rightPriceScale: {
        borderColor: chartTheme.borderColor,
        scaleMargins: { top: 0.05, bottom: 0.25 },
        minimumWidth: 80,
      },
      timeScale: {
        borderColor: chartTheme.borderColor,
        timeVisible: true,
        secondsVisible: false,
        barSpacing: 4,
        minBarSpacing: 2,
        rightOffset: 12,
        fixLeftEdge: false,
        fixRightEdge: false,
        lockVisibleTimeRangeOnResize: true,
        tickMarkFormatter: localTickMarkFormatter,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
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
      visible: chartType === "candles",
    });
    const bs = chart.addSeries(BarSeries, {
      upColor: chartTheme.upColor,
      downColor: chartTheme.downColor,
      thinBars: false,
      visible: chartType === "bars",
    });
    const ls = chart.addSeries(LineSeries, {
      color: chartTheme.textColor,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: true,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
      visible: chartType === "line",
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
    const ema = chart.addSeries(LineSeries, {
      color: chartTheme.ema,
      lineWidth: 2 as 1 | 2 | 3 | 4,
      priceLineVisible: false,
      lastValueVisible: true,
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
    emaRef.current = ema;
    rsiSeriesRef.current = rsiSeries;
    mfiSeriesRef.current = mfiSeries;
    chart.subscribeCrosshairMove((param: any) => {
      if (!param.time || (param.point && param.point.x < 0)) {
        setTooltip(null);
        return;
      }
      const c = param.seriesData.get(cs);
      const v = param.seriesData.get(vs);
      if (c) {
        const lbl = localTimeFormatter(param.time as number);
        setTooltip({ ...c, volume: v ? v.value : undefined, timeLabel: lbl });
      }
    });
    const ro = new ResizeObserver(() => {
      if (containerRef.current)
        chart.resize(
          containerRef.current.clientWidth,
          containerRef.current.clientHeight,
        );
    });
    ro.observe(containerRef.current);
    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const chartTheme = getChartTheme();
    themeRef.current = chartTheme;

    if (!chartRef.current) return;

    chartRef.current.applyOptions({
      layout: {
        background: { color: chartTheme.background },
        textColor: chartTheme.textColor,
      },
      grid: {
        vertLines: { color: chartTheme.gridColor, style: LineStyle.Solid },
        horzLines: { color: chartTheme.gridColor, style: LineStyle.Solid },
      },
      crosshair: {
        vertLine: {
          color: chartTheme.crosshair,
          labelBackgroundColor: chartTheme.crosshairLabelBg,
        },
        horzLine: {
          color: chartTheme.crosshair,
          labelBackgroundColor: chartTheme.crosshairLabelBg,
        },
      },
      rightPriceScale: {
        borderColor: chartTheme.borderColor,
      },
      timeScale: {
        borderColor: chartTheme.borderColor,
      },
    });

    candleRef.current?.applyOptions({
      upColor: chartTheme.upColor,
      downColor: chartTheme.downColor,
      borderUpColor: chartTheme.upColor,
      borderDownColor: chartTheme.downColor,
      wickUpColor: chartTheme.upColor,
      wickDownColor: chartTheme.downColor,
    });

    barRef.current?.applyOptions({
      upColor: chartTheme.upColor,
      downColor: chartTheme.downColor,
    });

    lineRef.current?.applyOptions({
      color: chartTheme.textColor,
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
  }, [themeMode]);

  useEffect(() => {
    chartTypeRef.current = chartType;
    candleRef.current?.applyOptions({ visible: chartType === "candles" });
    barRef.current?.applyOptions({ visible: chartType === "bars" });
    lineRef.current?.applyOptions({ visible: chartType === "line" });
    areaRef.current?.applyOptions({ visible: chartType === "area" });
  }, [chartType]);

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
      const newCandles = olderData.filter(c => c.time < earliestTime);
      if (newCandles.length === 0) {
        noMoreDataRef.current = true;
        isLoadingMoreRef.current = false;
        return;
      }
      const merged = [...newCandles, ...current];
      
      // Update refs BEFORE touching chart
      candlesRef.current = merged;
      earliestTimestampRef.current = merged[0].time;
      
      // Preserve visible range so chart doesn't jump
      const ts = chartRef.current ? chartRef.current.timeScale() : null;
      const visibleRange = ts ? ts.getVisibleLogicalRange() : null;

      // Apply to chart series
      setAllPriceSeriesData(merged);
      if (onCandlesChange) onCandlesChange(merged);

      // Restore visible range offset (older data shifts indices)
      if (ts && visibleRange) {
        const shift = newCandles.length;
        ts.setVisibleLogicalRange({
          from: visibleRange.from + shift,
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
      if (sma20Ref.current)
        sma20Ref.current.setData(calcSMA(merged, indSettings.sma20.period ?? 20));
      if (sma50Ref.current)
        sma50Ref.current.setData(calcSMA(merged, indSettings.sma50.period ?? 50));
      if (emaRef.current)
        emaRef.current.setData(calcEMA(merged, indSettings.ema.period ?? 20));
      if (rsiSeriesRef.current)
        rsiSeriesRef.current.setData(calcRSI(merged, indSettings.rsi.period ?? 14));
      if (mfiSeriesRef.current)
        mfiSeriesRef.current.setData(calcMFI(merged, indSettings.mfi.period ?? 14));

      // Update React state last (avoid triggering re-renders mid-update)
      setCandles(merged);
      scrollCooldownRef.current = Date.now();
      isLoadingMoreRef.current = false;
    } catch (error) {
      console.error('Failed to load more historical data:', error);
      isLoadingMoreRef.current = false;
    }
  }, [symbol, timeframe, historicalRange, indSettings, onCandlesChange, setAllPriceSeriesData]);

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
      setCandles(data);
      candlesRef.current = data;
      if (data.length > 0) {
        earliestTimestampRef.current = data[0].time;
        noMoreDataRef.current = false;
        scrollCooldownRef.current = 0;
      }
      if (onCandlesChange) onCandlesChange(data);
      setNoData(data.length === 0);
      setAllPriceSeriesData(data);
      const vs = volumeRef.current;
      if (vs)
        vs.setData(
          data.map((c) => ({
            time: c.time,
            value: c.volume,
            color: c.close >= c.open ? themeRef.current.volumeUp : themeRef.current.volumeDown,
          })),
        );
      if (sma20Ref.current)
        sma20Ref.current.setData(calcSMA(data, indSettings.sma20.period ?? 20));
      if (sma50Ref.current)
        sma50Ref.current.setData(calcSMA(data, indSettings.sma50.period ?? 50));
      if (emaRef.current)
        emaRef.current.setData(calcEMA(data, indSettings.ema.period ?? 20));
      if (rsiSeriesRef.current)
        rsiSeriesRef.current.setData(calcRSI(data, indSettings.rsi.period ?? 14));
      if (mfiSeriesRef.current)
        mfiSeriesRef.current.setData(calcMFI(data, indSettings.mfi.period ?? 14));
      setInitialVisibleRange(data);
      if (data.length > 0)
        setTooltip({ ...data[data.length - 1], timeLabel: "" });
    },
    [indSettings, onCandlesChange, setAllPriceSeriesData, setInitialVisibleRange],
  );

  // Historical mode handlers
  const handleHistoricalRange = useCallback(
    async (range: HistoricalRange) => {
      // Increment request ID to invalidate pending requests
      historicalRequestIdRef.current += 1;
      const currentRequestId = historicalRequestIdRef.current;

      // Auto-switch from 1s to 1m in historical mode
      let effectiveTimeframe = timeframe;
      if (timeframe === "1s") {
        effectiveTimeframe = "1m";
        setTimeframe("1m");
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
        const requestInterval = effectiveTimeframe.toLowerCase();

        // Fetch historical data
        let data = await fetchHistoricalCandles(
          requestSymbol,
          range.startMs,
          range.endMs,
          500,
          requestInterval,
        );

        // Check if this request is still valid (not superseded by newer request)
        if (currentRequestId !== historicalRequestIdRef.current) {
          return; // Newer request has been made, discard this result
        }

        // Check if user changed context mid-request
        if (symbolRef.current !== requestSymbol || timeframeRef.current !== requestInterval) {
          return;
        }

        // Check if user went back to live mode
        if (isLiveMode) {
          return;
        }

        data = await preloadInitialCandles({
          data,
          requestSymbol,
          requestInterval,
          isHistoricalMode: true,
        });

        // Final check before applying data
        if (currentRequestId !== historicalRequestIdRef.current || isLiveMode) {
          return;
        }

        applyDataToChart(data);
        setIsLoading(false);
      } catch (err) {
        // Only show error if this request is still current
        if (currentRequestId === historicalRequestIdRef.current) {
          setIsLoading(false);
          setFetchError(t("failedLoadCandles"));
          console.error("[Historical] Load error:", err);
        }
      }
    },
    [symbol, timeframe, isLiveMode, preloadInitialCandles, applyDataToChart, t],
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

    // Update secondsVisible based on UNIFIED config (all timeframes show seconds)
    if (chartRef.current) {
      chartRef.current
        .timeScale()
        .applyOptions({ secondsVisible: CHART_CONFIG.SHOW_SECONDS });
    }

    // Use unified settings for all timeframes (no is1s branching)
    const limit = CHART_CONFIG.VISIBLE_BARS;
    const maxBars = CHART_CONFIG.MAX_BARS_MEMORY;

    // Full load — fetches candles, rebuilds all series + indicators
    const loadData = async () => {
      setFetchError(null);
      try {
        const requestSymbol = symbol;
        const requestInterval = timeframe.toLowerCase();
        let data = await fetchCandles(requestSymbol, requestInterval, limit);
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
      } catch {
        if (cancelled) return;
        setIsLoading(false);
        setFetchError(t("failedLoadCandles"));
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
    loadData();

    // Subscribe to ALL timeframes simultaneously via a single WebSocket.
    // This ensures all timeframes update at the same time when price changes.
    //
    // Logic by timeframe:
    // - 1s  : Each tick = 1 candle (Open=High=Low=Close, no wicks)
    // - 1m+ : Backend aggregates ticks → update in-progress candle, close & start new on period change
    const unsub = subscribeAllTimeframes({
      symbol,
      onCandle: (tf, candle) => {
        // Only process the current timeframe
        if (tf !== timeframe.toLowerCase()) return;
        if (cancelled || !candleRef.current) return;
        const prev = candlesRef.current;
        if (prev.length === 0) return;

        const lastTime = prev[prev.length - 1].time;
        const is1s = tf === "1s";

        if (is1s) {
          // ── 1-second mode: each tick = new candle (Open=High=Low=Close) ──
          // Accept candles with time >= lastTime (same second updates, new second adds)
          if (candle.time < lastTime) return; // Only skip older candles

          if (candle.time === lastTime) {
            // Same second → update existing candle
            updateAllPriceSeries(candle);
            if (volumeRef.current) {
              volumeRef.current.update({
                time: candle.time,
                value: candle.volume,
                color: candle.close >= candle.open ? themeRef.current.volumeUp : themeRef.current.volumeDown,
              });
            }
            // Update in-place
            const next = [...prev.slice(0, -1), candle];
            candlesRef.current = next;
            setCandles(next);
            if (onCandlesChange) onCandlesChange(next);
          } else {
            // New second → add new candle
            updateAllPriceSeries(candle);
            if (volumeRef.current) {
              volumeRef.current.update({
                time: candle.time,
                value: candle.volume,
                color: candle.close >= candle.open ? themeRef.current.volumeUp : themeRef.current.volumeDown,
              });
            }
            const next = [...prev.slice(-(maxBars - 1)), candle];
            candlesRef.current = next;
            setCandles(next);
            if (onCandlesChange) onCandlesChange(next);
          }
          setTooltip((tip) =>
            tip ? { ...tip, ...candle, timeLabel: tip.timeLabel } : null,
          );
        } else {
          // ── 1m+ mode: update in-progress candle, new candle on period change ──
          // Backend sends candles with correct openTime (already aggregated)
          if (candle.time === lastTime) {
            // Same period → update latest candle
            updateAllPriceSeries(candle);
            if (volumeRef.current) {
              volumeRef.current.update({
                time: candle.time,
                value: candle.volume,
                color:
                  candle.close >= candle.open
                    ? themeRef.current.volumeUp
                    : themeRef.current.volumeDown,
              });
            }
            const next = [...prev];
            next[next.length - 1] = candle;
            candlesRef.current = next;
            setCandles(next);
            if (onCandlesChange) onCandlesChange(next);
            setTooltip((tip) =>
              tip ? { ...tip, ...candle, timeLabel: tip.timeLabel } : null,
            );
          } else if (candle.time > lastTime) {
            // New period → append new candle
            updateAllPriceSeries(candle);
            if (volumeRef.current) {
              volumeRef.current.update({
                time: candle.time,
                value: candle.volume,
                color:
                  candle.close >= candle.open
                    ? themeRef.current.volumeUp
                    : themeRef.current.volumeDown,
              });
            }
            const next = [...prev.slice(-(maxBars - 1)), candle];
            candlesRef.current = next;
            setCandles(next);
            if (onCandlesChange) onCandlesChange(next);
            setTooltip((tip) =>
              tip ? { ...tip, ...candle, timeLabel: tip.timeLabel } : null,
            );
          }
          // candle.time < lastTime → stale data, skip
        }
      },
    });

    // Store unsubscribe function in ref
    unsubscribeRef.current = unsub;

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
      pollIntervalRef.current = null;
      unsubscribeRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    symbol,
    timeframe,
    isLiveMode,
    retryCount,
    applyDataToChart,
    preloadInitialCandles,
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
      // Stop poll interval
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }
  }, [isReplayActive]);

  // Load historical data when date range is set
  // (Removed - now handled by handleHistoricalRange callback)

  // Refetch historical data when symbol/timeframe changes in historical mode
  useEffect(() => {
    if (!isLiveMode && historicalRange) {
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
    const cfgE = indSettings.ema;
    const cfgV = indSettings.volume;
    if (sma20Ref.current) {
      sma20Ref.current.applyOptions({
        visible: cfg20.visible,
        color: cfg20.color,
        lineWidth: cfg20.lineWidth,
      });
      sma20Ref.current.setData(calcSMA(candles, cfg20.period ?? 20));
    }
    if (sma50Ref.current) {
      sma50Ref.current.applyOptions({
        visible: cfg50.visible,
        color: cfg50.color,
        lineWidth: cfg50.lineWidth,
      });
      sma50Ref.current.setData(calcSMA(candles, cfg50.period ?? 50));
    }
    if (emaRef.current) {
      emaRef.current.applyOptions({
        visible: cfgE.visible,
        color: cfgE.color,
        lineWidth: cfgE.lineWidth,
      });
      emaRef.current.setData(calcEMA(candles, cfgE.period ?? 20));
    }
    if (volumeRef.current)
      volumeRef.current.applyOptions({ visible: cfgV.visible });
    // RSI / MFI on main chart oscillator scale
    const cfgR = indSettings.rsi;
    const cfgM = indSettings.mfi;
    if (rsiSeriesRef.current) {
      rsiSeriesRef.current.applyOptions({
        visible: cfgR.visible,
        color: cfgR.color,
        lineWidth: cfgR.lineWidth || 1.5,
      });
      rsiSeriesRef.current.setData(calcRSI(candles, cfgR.period ?? 14));
    }
    if (mfiSeriesRef.current) {
      mfiSeriesRef.current.applyOptions({
        visible: cfgM.visible,
        color: cfgM.color,
        lineWidth: cfgM.lineWidth || 1.5,
      });
      mfiSeriesRef.current.setData(calcMFI(candles, cfgM.period ?? 14));
    }
    // Show/hide the oscillator price scale when either is visible
    if (chartRef.current) {
      chartRef.current
        .priceScale("oscillator")
        .applyOptions({ visible: cfgR.visible || cfgM.visible });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indSettings, candles]);

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

  const handleResetView = useCallback(() => {
    resetZoom();
    setInitialVisibleRange(candlesRef.current);
    chartRef.current?.priceScale("right").applyOptions({ autoScale: true });
  }, [resetZoom, setInitialVisibleRange]);

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <MarketSelector
            symbols={symbols}
            selectedSymbol={symbol}
            onSelect={handleSymbolChange}
            starredSymbols={starredSymbols}
            onToggleStar={onToggleStar || (() => {})}
          />
          {lastCandle && (
            <div className="flex items-center gap-2">
              <span
                className={`text-base font-bold font-mono ${isUp ? "text-green-400" : "text-red-400"}`}
              >
                {lastCandle.close.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                })}
              </span>
              {pricePct && (
                <span
                  className={`text-xs px-1.5 py-0.5 rounded ${isUp ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}
                >
                  {isUp ? "+" : ""}
                  {pricePct}%
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Export button */}
          <button
            onClick={handleExportChart}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border border-gray-600 text-gray-400 hover:text-white hover:border-gray-400 transition-colors"
            title={t("exportAsPNG")}
          >
            <Download size={12} /> {t("exportChart")}
          </button>
          {/* Indicator panel toggle */}
          <div className="relative">
            <button
              onClick={() => setShowIndPanel((v) => !v)}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border transition-colors
                ${showIndPanel ? "bg-blue-600 border-blue-500 text-white" : "border-gray-600 text-gray-400 hover:text-white hover:border-gray-400"}`}
            >
              <Settings size={12} /> {t("indicators")}
            </button>
            {showIndPanel && (
              <div className="absolute right-0 top-full mt-1 z-[100]">
                <IndicatorPanel
                  indSettings={indSettings}
                  onChange={setIndSettings}
                />
              </div>
            )}
          </div>
          {/* Historical date-range picker */}
          <DateRangePicker
            active={!isLiveMode}
            onApply={handleHistoricalRange}
            onClear={handleBackToLive}
          />
          {/* Zoom controls */}
          <div className="flex items-center gap-1 border border-gray-600 rounded overflow-hidden">
            <button
              onClick={zoomIn}
              disabled={!canZoomIn}
              className={`px-2 py-1 text-xs font-medium transition-colors ${
                canZoomIn
                  ? "text-gray-400 hover:text-white hover:bg-gray-700"
                  : "text-gray-600 cursor-not-allowed"
              }`}
              title={t("zoomIn")}
            >
              <ZoomIn size={12} />
            </button>
            <button
              onClick={zoomOut}
              disabled={!canZoomOut}
              className={`px-2 py-1 text-xs font-medium border-l border-gray-600 transition-colors ${
                canZoomOut
                  ? "text-gray-400 hover:text-white hover:bg-gray-700"
                  : "text-gray-600 cursor-not-allowed"
              }`}
              title={t("zoomOut")}
            >
              <ZoomOut size={12} />
            </button>
            <button
              onClick={handleResetView}
              className="px-2 py-1 text-xs font-medium border-l border-gray-600 text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
              title={t("resetZoom")}
            >
              <Maximize2 size={12} />
            </button>
          </div>
        </div>
      </div>

      {/* Historical mode banner */}
      {!isLiveMode && historicalRange && (
        <div className="flex items-center justify-between px-3 py-1.5 bg-amber-900/40 border-b border-amber-700/50">
          <span className="text-xs text-amber-300">
            {new Date(historicalRange.startMs).toLocaleString()} &mdash;{" "}
            {new Date(historicalRange.endMs).toLocaleString()} ({timeframe})
          </span>
          <button
            onClick={handleBackToLive}
            className="text-xs text-amber-400 hover:text-white underline"
          >
            {t("live")}
          </button>
        </div>
      )}

      {/* Tab content — candlestick chart is always mounted to preserve the
           lightweight-charts instance; visibility is toggled via CSS. */}
      <div className="contents">
        {/* OHLCV bar */}
        <div className="px-3 py-1 bg-gray-900 border-b border-gray-800 min-h-[28px]">
          <OHLCVBar data={tooltip} />
        </div>
        {/* Chart canvas + overlay slot */}
        <div ref={chartStageRef} className="relative flex-1 min-h-0">
          <div ref={containerRef} className="w-full h-full" />
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-60 z-10">
              <span className="text-gray-400 text-sm animate-pulse">
                {t("loading")}
              </span>
            </div>
          )}
          {fetchError && !isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-60 z-10">
              <div className="text-center">
                <p className="text-red-400 text-sm mb-2">{fetchError}</p>
                <button
                  onClick={() => {
                    setFetchError(null);
                    setRetryCount((c) => c + 1);
                  }}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs transition-colors"
                >
                  {t("retry")}
                </button>
              </div>
            </div>
          )}
          {noData && !isLoading && !fetchError && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-40 z-10">
              <p className="text-gray-400 text-sm">
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
