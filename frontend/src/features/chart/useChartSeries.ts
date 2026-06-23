/**
 * useChartSeries — creates chart instance and all 30+ indicator series.
 */
import { useEffect, useRef, type RefObject } from "react";
import {
  createChart,
  LineStyle,
  AreaSeries,
  BarSeries,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from "lightweight-charts";
import { getChartTheme } from "./chartConstants";
import { DEFAULT_CHART_PREFERENCES, type ChartPreferenceSettings } from "@/services/settingsService";
import {
  resolveChartTheme,
  gridLineStyle,
  crosshairMode,
  usesCandleSeries,
  usesLineSeries,
} from "./chartHelpers";
import type { ChartType, TimeframeKey } from "@/types";

export interface ChartSeriesRefs {
  chart: any;
  candleRef: any;
  barRef: any;
  lineRef: any;
  areaRef: any;
  volumeRef: any;
  sma20Ref: any;
  sma50Ref: any;
  ema12Ref: any;
  ema26Ref: any;
  bbUpperRef: any;
  bbBasisRef: any;
  bbLowerRef: any;
  vwapRef: any;
  supertrendRef: any;
  psarRef: any;
  volumeMaRef: any;
  macdLineRef: any;
  macdSignalRef: any;
  macdHistogramRef: any;
  stochasticKRef: any;
  stochasticDRef: any;
  atrRef: any;
  ichimokuConversionRef: any;
  ichimokuBaseRef: any;
  ichimokuSpanARef: any;
  ichimokuSpanBRef: any;
  ichimokuLaggingRef: any;
  rsiSeriesRef: any;
  mfiSeriesRef: any;
}

export function useChartSeries(
  containerRef: RefObject<HTMLDivElement>,
  chartStageRef: RefObject<HTMLDivElement>,
  chartType: ChartType,
  timeframe: TimeframeKey,
  chartPreferences: ChartPreferenceSettings | undefined,
  tickMarkFormatter: (time: number, tickMarkType: number, locale: string) => string,
  timeFormatter: (time: number) => string,
  getActivePriceSeriesRef: RefObject<() => any>,
  onTooltipRef: RefObject<(data: any) => void>,
): ChartSeriesRefs {
  const refs: ChartSeriesRefs = {
    chart: useRef(null), candleRef: useRef(null), barRef: useRef(null),
    lineRef: useRef(null), areaRef: useRef(null), volumeRef: useRef(null),
    sma20Ref: useRef(null), sma50Ref: useRef(null),
    ema12Ref: useRef(null), ema26Ref: useRef(null),
    bbUpperRef: useRef(null), bbBasisRef: useRef(null), bbLowerRef: useRef(null),
    vwapRef: useRef(null), supertrendRef: useRef(null), psarRef: useRef(null),
    volumeMaRef: useRef(null),
    macdLineRef: useRef(null), macdSignalRef: useRef(null), macdHistogramRef: useRef(null),
    stochasticKRef: useRef(null), stochasticDRef: useRef(null), atrRef: useRef(null),
    ichimokuConversionRef: useRef(null), ichimokuBaseRef: useRef(null),
    ichimokuSpanARef: useRef(null), ichimokuSpanBRef: useRef(null), ichimokuLaggingRef: useRef(null),
    rsiSeriesRef: useRef(null), mfiSeriesRef: useRef(null),
  };

  const themeRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const prefs = chartPreferences ?? DEFAULT_CHART_PREFERENCES;
    const chartTheme = resolveChartTheme(getChartTheme(), prefs);
    themeRef.current = chartTheme;
    const ls = gridLineStyle(prefs);

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: chartTheme.background },
        textColor: chartTheme.textColor,
        fontFamily: "'Inter','Segoe UI',sans-serif",
        fontSize: 11,
      },
      localization: { locale: navigator.language || "en-US", timeFormatter },
      grid: {
        vertLines: { color: prefs.grid_crosshair.grid_visible ? chartTheme.gridColor : "transparent", style: ls },
        horzLines: { color: prefs.grid_crosshair.grid_visible ? chartTheme.gridColor : "transparent", style: ls },
      },
      crosshair: {
        mode: crosshairMode(prefs),
        vertLine: { color: chartTheme.crosshair, labelBackgroundColor: chartTheme.crosshairLabelBg, style: LineStyle.Dashed },
        horzLine: { color: chartTheme.crosshair, labelBackgroundColor: chartTheme.crosshairLabelBg, style: LineStyle.Dashed },
      },
      rightPriceScale: {
        borderColor: chartTheme.borderColor,
        scaleMargins: { top: 0.05, bottom: 0.25 },
        entireTextOnly: true,
        visible: prefs.scale.price_labels_visible,
        mode: 0,
      },
      timeScale: {
        borderColor: chartTheme.borderColor,
        timeVisible: true,
        secondsVisible: prefs.scale.seconds_visible && timeframe === "1s",
        barSpacing: prefs.scale.bar_spacing,
        minBarSpacing: 2,
        rightOffset: 8,
        fixLeftEdge: false, fixRightEdge: false,
        lockVisibleTimeRangeOnResize: true,
        tickMarkFormatter,
        visible: prefs.scale.time_labels_visible,
      },
      handleScroll: { mouseWheel: false, pressedMouseMove: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: false, pinch: true },
    });

    const cs = chart.addSeries(CandlestickSeries, {
      upColor: chartTheme.upColor, downColor: chartTheme.downColor,
      borderUpColor: chartTheme.upColor, borderDownColor: chartTheme.downColor,
      wickUpColor: chartTheme.upColor, wickDownColor: chartTheme.downColor,
      borderVisible: prefs.candle_style.border_visible,
      wickVisible: prefs.candle_style.wick_visible && timeframe !== "1s",
      visible: usesCandleSeries(chartType),
    });
    const bs = chart.addSeries(BarSeries, {
      upColor: chartTheme.upColor, downColor: chartTheme.downColor, thinBars: false, visible: chartType === "bars",
    });
    const ls_series = chart.addSeries(LineSeries, {
      color: chartTheme.upColor, lineWidth: 2 as const, priceLineVisible: true,
      lastValueVisible: true, crosshairMarkerVisible: true, visible: usesLineSeries(chartType),
    });
    const ar = chart.addSeries(AreaSeries, {
      lineColor: chartTheme.upColor, topColor: `${chartTheme.upColor}50`, bottomColor: `${chartTheme.background}00`,
      lineWidth: 2 as const, priceLineVisible: true, lastValueVisible: true, crosshairMarkerVisible: true,
      visible: chartType === "area",
    });
    const vs = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "volume" });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    const s20 = chart.addSeries(LineSeries, { color: chartTheme.sma20, lineWidth: 1, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: false });
    const s50 = chart.addSeries(LineSeries, { color: chartTheme.sma50, lineWidth: 1, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: false });
    const e12 = chart.addSeries(LineSeries, { color: chartTheme.ema12, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: false, visible: false });
    const e26 = chart.addSeries(LineSeries, { color: chartTheme.ema26, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: false, visible: false });
    const bbUpper = chart.addSeries(LineSeries, { color: chartTheme.bb, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false });
    const bbBasis = chart.addSeries(LineSeries, { color: chartTheme.bbBasis, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false });
    const bbLower = chart.addSeries(LineSeries, { color: chartTheme.bb, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false });
    const vwapSeries = chart.addSeries(LineSeries, { color: chartTheme.vwap, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: false, visible: false });
    const supertrendSeries = chart.addSeries(LineSeries, { color: chartTheme.supertrend, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: false, visible: false });
    const psarSeries = chart.addSeries(LineSeries, { color: chartTheme.psar, lineWidth: 1, lineStyle: LineStyle.Dotted, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false });
    const volumeMaSeries = chart.addSeries(LineSeries, { color: chartTheme.volumeMa, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false, priceScaleId: "volume" });
    const iConv = chart.addSeries(LineSeries, { color: chartTheme.ichimokuConversion, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false });
    const iBase = chart.addSeries(LineSeries, { color: chartTheme.ichimokuBase, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false });
    const iSpanA = chart.addSeries(LineSeries, { color: chartTheme.ichimokuSpanA, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false });
    const iSpanB = chart.addSeries(LineSeries, { color: chartTheme.ichimokuSpanB, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false });
    const iLag = chart.addSeries(LineSeries, { color: chartTheme.bbBasis, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false });

    const rsiSeries = chart.addSeries(LineSeries, { color: chartTheme.rsi, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false, priceScaleId: "oscillator" });
    const macdL = chart.addSeries(LineSeries, { color: chartTheme.macd, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false, priceScaleId: "oscillator" });
    const macdS = chart.addSeries(LineSeries, { color: chartTheme.macdSignal, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false, priceScaleId: "oscillator" });
    const macdH = chart.addSeries(HistogramSeries, { color: chartTheme.macd, priceFormat: { type: "volume" }, priceScaleId: "oscillator", visible: false });
    const stochK = chart.addSeries(LineSeries, { color: chartTheme.stochastic, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false, priceScaleId: "oscillator" });
    const stochD = chart.addSeries(LineSeries, { color: chartTheme.stochasticSignal, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false, priceScaleId: "oscillator" });
    const atrS = chart.addSeries(LineSeries, { color: chartTheme.atr, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false, priceScaleId: "oscillator" });
    const mfiS = chart.addSeries(LineSeries, { color: chartTheme.mfi, lineWidth: 2 as const, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, visible: false, priceScaleId: "oscillator" });
    chart.priceScale("oscillator").applyOptions({ scaleMargins: { top: 0.75, bottom: 0 }, visible: false });

    // Assign refs
    refs.chart.current = chart;
    refs.candleRef.current = cs; refs.barRef.current = bs; refs.lineRef.current = ls_series; refs.areaRef.current = ar; refs.volumeRef.current = vs;
    refs.sma20Ref.current = s20; refs.sma50Ref.current = s50; refs.ema12Ref.current = e12; refs.ema26Ref.current = e26;
    refs.bbUpperRef.current = bbUpper; refs.bbBasisRef.current = bbBasis; refs.bbLowerRef.current = bbLower;
    refs.vwapRef.current = vwapSeries; refs.supertrendRef.current = supertrendSeries; refs.psarRef.current = psarSeries;
    refs.volumeMaRef.current = volumeMaSeries;
    refs.ichimokuConversionRef.current = iConv; refs.ichimokuBaseRef.current = iBase;
    refs.ichimokuSpanARef.current = iSpanA; refs.ichimokuSpanBRef.current = iSpanB; refs.ichimokuLaggingRef.current = iLag;
    refs.rsiSeriesRef.current = rsiSeries; refs.mfiSeriesRef.current = mfiS;
    refs.macdLineRef.current = macdL; refs.macdSignalRef.current = macdS; refs.macdHistogramRef.current = macdH;
    refs.stochasticKRef.current = stochK; refs.stochasticDRef.current = stochD; refs.atrRef.current = atrS;

    // Crosshair tooltip
    chart.subscribeCrosshairMove((param: any) => {
      if (!param.time || (param.point && param.point.x < 0)) {
        onTooltipRef.current(null);
        return;
      }
      const activeSeries = getActivePriceSeriesRef.current();
      const c = activeSeries ? param.seriesData.get(activeSeries) : param.seriesData.get(cs);
      const v = param.seriesData.get(vs);
      if (c) {
        const lbl = timeFormatter(param.time as number);
        if (typeof c.open === "number" && typeof c.high === "number" && typeof c.low === "number" && typeof c.close === "number") {
          onTooltipRef.current({ ...c, volume: v ? v.value : undefined, timeLabel: lbl });
          return;
        }
        if (typeof c.value === "number" && Number.isFinite(c.value)) {
          onTooltipRef.current({ open: c.value, high: c.value, low: c.value, close: c.value, volume: v ? v.value : undefined, timeLabel: lbl });
        }
      }
    });

    const scheduleChartResize = () => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const width = Math.floor(rect.width);
      const height = Math.floor(rect.height);
      if (width > 0 && height > 0) chart.resize(width, height);
    };

    const ro = new ResizeObserver(scheduleChartResize);
    ro.observe(containerRef.current);
    if (chartStageRef.current) ro.observe(chartStageRef.current);
    window.addEventListener("resize", scheduleChartResize);
    window.visualViewport?.addEventListener("resize", scheduleChartResize);
    scheduleChartResize();

    return () => {
      ro.disconnect();
      window.removeEventListener("resize", scheduleChartResize);
      window.visualViewport?.removeEventListener("resize", scheduleChartResize);
      chart.remove();
      refs.chart.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return refs;
}
