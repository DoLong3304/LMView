/**
 * useChartIndicators — sync indicator data, live updates, S/R lines.
 */
import { useCallback } from "react";
import type { Candle, IndicatorSettings } from "@/types";
import {
  calcATR, calcBollingerBands, calcEMA, calcIchimoku, calcMACD, calcMFI,
  calcParabolicSAR, calcRSI, calcSMA, calcStochastic, calcSupertrend,
  calcVolumeMA, calcVWAP, calcSupportResistance,
} from "./indicatorUtils";

export interface IndicatorRefs {
  sma20Ref: any; sma50Ref: any; ema12Ref: any; ema26Ref: any;
  bbUpperRef: any; bbBasisRef: any; bbLowerRef: any;
  vwapRef: any; supertrendRef: any; psarRef: any; volumeMaRef: any;
  ichimokuConversionRef: any; ichimokuBaseRef: any;
  ichimokuSpanARef: any; ichimokuSpanBRef: any; ichimokuLaggingRef: any;
  rsiSeriesRef: any; mfiSeriesRef: any;
  macdLineRef: any; macdSignalRef: any; macdHistogramRef: any;
  stochasticKRef: any; stochasticDRef: any; atrRef: any;
  candleRef: any;
}

export function useChartIndicators(indSettings: Record<string, IndicatorSettings>, refs: IndicatorRefs) {
  const { candleRef } = refs;

  /** Sync all indicator data from a candle array */
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

    refs.sma20Ref.current?.setData(calcSMA(data, Number(cfg20.period ?? 20)));
    refs.sma50Ref.current?.setData(calcSMA(data, Number(cfg50.period ?? 50)));
    refs.ema12Ref.current?.setData(calcEMA(data, Number(cfgE12.period ?? 12)));
    refs.ema26Ref.current?.setData(calcEMA(data, Number(cfgE26.period ?? 26)));

    const bb = calcBollingerBands(data, Number(cfgBb.period ?? 20), Number(cfgBb.multiplier ?? 2));
    refs.bbUpperRef.current?.setData(bb.upper);
    refs.bbBasisRef.current?.setData(bb.middle);
    refs.bbLowerRef.current?.setData(bb.lower);

    refs.vwapRef.current?.setData(calcVWAP(data));
    refs.volumeMaRef.current?.setData(calcVolumeMA(data, Number(cfgVolumeMa.period ?? 20)));

    const macd = calcMACD(data, Number(cfgMacd.fastPeriod ?? 12), Number(cfgMacd.slowPeriod ?? 26), Number(cfgMacd.signalPeriod ?? 9));
    refs.macdLineRef.current?.setData(macd.macd);
    refs.macdSignalRef.current?.setData(macd.signal);
    refs.macdHistogramRef.current?.setData(macd.histogram);

    const stoch = calcStochastic(data, Number(cfgStochastic.period ?? 14), Number(cfgStochastic.signalPeriod ?? 3));
    refs.stochasticKRef.current?.setData(stoch.k);
    refs.stochasticDRef.current?.setData(stoch.d);

    refs.atrRef.current?.setData(calcATR(data, Number(cfgAtr.period ?? 14)));

    const ichimoku = calcIchimoku(data, Number(cfgIchimoku.conversionPeriod ?? 9), Number(cfgIchimoku.basePeriod ?? 26), Number(cfgIchimoku.spanPeriod ?? 52), Number(cfgIchimoku.displacement ?? 26));
    refs.ichimokuConversionRef.current?.setData(ichimoku.conversion);
    refs.ichimokuBaseRef.current?.setData(ichimoku.base);
    refs.ichimokuSpanARef.current?.setData(ichimoku.spanA);
    refs.ichimokuSpanBRef.current?.setData(ichimoku.spanB);
    refs.ichimokuLaggingRef.current?.setData(ichimoku.lagging);

    refs.supertrendRef.current?.setData(calcSupertrend(data, Number(cfgSupertrend.period ?? 10), Number(cfgSupertrend.multiplier ?? 3)));
    refs.psarRef.current?.setData(calcParabolicSAR(data, Number(cfgPsar.step ?? 0.02), Number(cfgPsar.maxStep ?? 0.2)));
    refs.rsiSeriesRef.current?.setData(calcRSI(data, Number(indSettings.rsi.period ?? 14)));
    refs.mfiSeriesRef.current?.setData(calcMFI(data, Number(indSettings.mfi.period ?? 14)));

    // S/R lines
    syncSRLines(data, candleRef.current, indSettings.support_resistance);
  }, [indSettings, refs, candleRef]);

  /** Compute required candle window for live updates */
  const getLiveIndicatorWindow = useCallback((_data: Candle[]) => {
    const visibleWindows = [
      indSettings.sma20.visible ? Number(indSettings.sma20.period ?? 20) : 0,
      indSettings.sma50.visible ? Number(indSettings.sma50.period ?? 50) : 0,
      indSettings.ema12.visible ? Number(indSettings.ema12.period ?? 12) : 0,
      indSettings.ema26.visible ? Number(indSettings.ema26.period ?? 26) : 0,
      indSettings.bb.visible ? Number(indSettings.bb.period ?? 20) : 0,
      indSettings.volumeMa.visible ? Number(indSettings.volumeMa.period ?? 20) : 0,
      indSettings.macd.visible ? Number(indSettings.macd.slowPeriod ?? 26) + Number(indSettings.macd.signalPeriod ?? 9) : 0,
      indSettings.stochastic.visible ? Number(indSettings.stochastic.period ?? 14) + Number(indSettings.stochastic.signalPeriod ?? 3) : 0,
      indSettings.atr.visible ? Number(indSettings.atr.period ?? 14) : 0,
      indSettings.ichimoku.visible ? Number(indSettings.ichimoku.spanPeriod ?? 52) + Number(indSettings.ichimoku.displacement ?? 26) : 0,
      indSettings.supertrend.visible ? Number(indSettings.supertrend.period ?? 10) : 0,
      indSettings.psar.visible ? 3 : 0,
      indSettings.rsi.visible ? Number(indSettings.rsi.period ?? 14) : 0,
      indSettings.mfi.visible ? Number(indSettings.mfi.period ?? 14) : 0,
      indSettings.support_resistance?.visible ? Number(indSettings.support_resistance.lookback ?? 50) : 0,
    ];
    return Math.max(...visibleWindows);
  }, [indSettings]);

  /** Live update last candle for each visible indicator */
  const updateLast = (series: any, points: Array<{ time: number; value: number }>) => {
    if (!series || !points?.length) return;
    const last = points[points.length - 1];
    if (last) series.update(last);
  };

  const liveUpdateIndicators = useCallback((windowed: Candle[]) => {
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
    const bb = calcBollingerBands(windowed, Number(cfgBb.period ?? 20), Number(cfgBb.multiplier ?? 2));
    const vwap = calcVWAP(windowed);
    const volumeMa = calcVolumeMA(windowed, Number(cfgVolumeMa.period ?? 20));
    const macd = calcMACD(windowed, Number(cfgMacd.fastPeriod ?? 12), Number(cfgMacd.slowPeriod ?? 26), Number(cfgMacd.signalPeriod ?? 9));
    const stoch = calcStochastic(windowed, Number(cfgStochastic.period ?? 14), Number(cfgStochastic.signalPeriod ?? 3));
    const atr = calcATR(windowed, Number(cfgAtr.period ?? 14));
    const ichimoku = calcIchimoku(windowed, Number(cfgIchimoku.conversionPeriod ?? 9), Number(cfgIchimoku.basePeriod ?? 26), Number(cfgIchimoku.spanPeriod ?? 52), Number(cfgIchimoku.displacement ?? 26));

    updateLast(refs.sma20Ref.current, sma20);
    updateLast(refs.sma50Ref.current, sma50);
    updateLast(refs.ema12Ref.current, ema12);
    updateLast(refs.ema26Ref.current, ema26);
    updateLast(refs.bbUpperRef.current, bb.upper);
    updateLast(refs.bbBasisRef.current, bb.middle);
    updateLast(refs.bbLowerRef.current, bb.lower);
    updateLast(refs.vwapRef.current, vwap);
    updateLast(refs.volumeMaRef.current, volumeMa);
    updateLast(refs.macdLineRef.current, macd.macd);
    updateLast(refs.macdSignalRef.current, macd.signal);
    updateLast(refs.macdHistogramRef.current, macd.histogram);
    updateLast(refs.stochasticKRef.current, stoch.k);
    updateLast(refs.stochasticDRef.current, stoch.d);
    updateLast(refs.atrRef.current, atr);
    updateLast(refs.ichimokuConversionRef.current, ichimoku.conversion);
    updateLast(refs.ichimokuBaseRef.current, ichimoku.base);
    updateLast(refs.ichimokuSpanARef.current, ichimoku.spanA);
    updateLast(refs.ichimokuSpanBRef.current, ichimoku.spanB);
    updateLast(refs.ichimokuLaggingRef.current, ichimoku.lagging);
    updateLast(refs.supertrendRef.current, calcSupertrend(windowed, Number(cfgSupertrend.period ?? 10), Number(cfgSupertrend.multiplier ?? 3)));
    updateLast(refs.psarRef.current, calcParabolicSAR(windowed, Number(cfgPsar.step ?? 0.02), Number(cfgPsar.maxStep ?? 0.2)));
    updateLast(refs.rsiSeriesRef.current, calcRSI(windowed, Number(indSettings.rsi.period ?? 14)));
    updateLast(refs.mfiSeriesRef.current, calcMFI(windowed, Number(indSettings.mfi.period ?? 14)));
  }, [indSettings, refs]);

  return { syncIndicatorData, getLiveIndicatorWindow, liveUpdateIndicators };
}

/** Internal helper: draw S/R price lines on candle series */
function syncSRLines(data: Candle[], candleSeries: any, srSettings: any, srLinesRef = { current: [] as any[] }) {
  for (const item of srLinesRef.current) {
    try { candleSeries?.removePriceLine(item.priceLine); } catch { }
  }
  srLinesRef.current = [];
  if (!srSettings?.visible || !candleSeries) return;

  const lookback = Number(srSettings.lookback ?? 50);
  const levels = calcSupportResistance(data, lookback);
  for (const level of levels) {
    const isSupport = level.type === "support";
    const priceLine = candleSeries.createPriceLine({
      price: level.price,
      color: isSupport ? srSettings.supportColor ?? "#22c55e" : srSettings.resistanceColor ?? "#ef4444",
      lineWidth: Number(srSettings.lineWidth ?? 1),
      lineStyle: 2,
      axisLabelVisible: true,
      title: level.label,
    });
    srLinesRef.current.push({ priceLine, label: level.label });
  }
}

export { syncSRLines };
