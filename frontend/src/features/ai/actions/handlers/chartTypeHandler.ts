import type { ActionHandler } from "./index";
import type { ChartType, TimeframeKey } from "@/types";

/**
 * Extended timeframe / chart-type lists. The base ``TimeframeKey`` type
 * in ``@/types`` is intentionally narrow (covers the main trading
 * timeframes) but the chart UI supports a broader set; we widen here so
 * the AI can request any of them.
 */
const ALLOWED_TIMEFRAMES: string[] = [
  "1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "3d", "1w", "1M",
];

const ALLOWED_CHART_TYPES: string[] = [
  "candles", "line", "area", "bars", "heikinAshi", "renko", "lineBreak", "kagi", "pointFigure", "hollowCandles", "baseline", "columns",
];

export const handleSetTimeframe: ActionHandler = ({ runtime, showSection, args }) => {
  const tf = String(args.timeframe || args.interval || "").toLowerCase();
  if (!ALLOWED_TIMEFRAMES.includes(tf)) {
    return `error: unsupported timeframe "${tf}". Allowed: ${ALLOWED_TIMEFRAMES.join(", ")}`;
  }
  if (!runtime.setTimeframe) {
    return "error: timeframe controller not available";
  }
  runtime.setTimeframe(tf as TimeframeKey);
  showSection("chartToolbar");
  return `success: switched timeframe to ${tf}`;
};

export const handleSetChartType: ActionHandler = ({ runtime, showSection, args }) => {
  const chartType = String(args.chart_type || args.type || "candles");
  if (!ALLOWED_CHART_TYPES.includes(chartType)) {
    return `error: unsupported chart type "${chartType}". Allowed: ${ALLOWED_CHART_TYPES.join(", ")}`;
  }
  if (!runtime.setChartType) {
    return "error: chart type controller not available";
  }
  runtime.setChartType(chartType as ChartType);
  showSection("chartToolbar");
  return `success: switched chart type to ${chartType}`;
};

export const handleSetSymbol: ActionHandler = ({ runtime, showSection, args }) => {
  const symbol = String(args.symbol || args.market || "BTCUSDT").toUpperCase();
  if (!/^[A-Z0-9]{2,20}USDT?$/.test(symbol)) {
    return `error: invalid symbol "${symbol}"`;
  }
  if (!runtime.setSymbol) {
    return "error: symbol controller not available";
  }
  runtime.setSymbol(symbol);
  showSection("chartToolbar");
  return `success: switched market to ${symbol}`;
};
