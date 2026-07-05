import type { ActionHandler } from "./index";

/**
 * Dim the UI except the target section. Chat stays unhighlighted unless
 * include_chat is true. Used for the "look here" visual cue in Interact
 * mode tours.
 */
export const handleHighlightSection: ActionHandler = ({ showSection, setHighlight, args }) => {
  const target = String(args.target || "chart");
  showSection(target);
  setHighlight({
    target,
    label: typeof args.label === "string" ? args.label : undefined,
    message: typeof args.message === "string" ? args.message : undefined,
    includeChat: args.include_chat === true || target === "ai",
  });
  return `success: highlighted section "${target}"`;
};

/**
 * Highlight a rectangular area inside the chart by percentages.
 */
export const handleHighlightChartArea: ActionHandler = ({ showSection, setHighlight, args }) => {
  showSection("chart");
  setHighlight({
    target: "chartCanvas",
    label: typeof args.label === "string" ? args.label : "Chart area",
    message: typeof args.message === "string" ? args.message : undefined,
    region: {
      leftPct: clampPercent(args.left_pct, 20),
      topPct: clampPercent(args.top_pct, 20),
      widthPct: clampPercent(args.width_pct, 40),
      heightPct: clampPercent(args.height_pct, 30),
    },
  });
  return "success: highlighted chart area";
};

/**
 * Highlight candles by index range or by time range.
 */
export const handleHighlightCandles: ActionHandler = ({ showSection, setHighlight, runtime, args }) => {
  showSection("chart");
  const region = runtime.chartController?.rangeToChartRegion(args) || {
    leftPct: 25,
    topPct: 18,
    widthPct: 35,
    heightPct: 58,
  };
  setHighlight({
    target: "chartCanvas",
    label: typeof args.label === "string" ? args.label : "Candles",
    message: typeof args.message === "string" ? args.message : undefined,
    region,
  });
  return "success: highlighted candle range";
};

/**
 * Highlight a chart zone based on analysis context (breakout, divergence, etc.).
 * Uses zone_type + candle_count to estimate the chart region from the latest
 * candles. The frontend maps this to actual coordinates — the AI doesn't need
 * exact candle indices.
 */
export const handleHighlightContextualZone: ActionHandler = ({ showSection, setHighlight, args }) => {
  showSection("chart");
  const zoneType = String(args.zone_type || "recent_action");
  const candleCount = Number(args.candle_count) || 5;
  const direction = String(args.direction || "neutral");

  // Map zone_type + direction to label/color hints
  const zoneMeta: Record<string, { label: string; color: string }> = {
    breakout: { label: "🚀 Breakout zone", color: "#22c55e" },
    breakdown: { label: "⬇ Breakdown zone", color: "#ef4444" },
    support_test: { label: "🛡 Support test", color: "#22c55e" },
    resistance_test: { label: "🧱 Resistance test", color: "#ef4444" },
    bullish_divergence: { label: "📈 Bullish divergence", color: "#22c55e" },
    bearish_divergence: { label: "📉 Bearish divergence", color: "#ef4444" },
    consolidation: { label: "🔲 Consolidation", color: "#facc15" },
    reversal_candles: { label: "🔄 Reversal setup", color: "#a78bfa" },
    volume_spike: { label: "📊 Volume spike", color: "#60a5fa" },
    trend_push: { label: "📈 Trend push", color: "#34d399" },
    accumulation: { label: "📥 Accumulation", color: "#22c55e" },
    distribution: { label: "📤 Distribution", color: "#ef4444" },
    recent_action: { label: "📌 Recent action", color: "#60a5fa" },
  };
  const meta = zoneMeta[zoneType] || { label: "📍 Analysis zone", color: "#60a5fa" };

  // Estimate region from candle_count relative to latest candles
  // The chart has ~30-50 visible candles; candle_count maps to a percentage width
  const visibleCandleEstimate = 40;
  const estimatedWidthPct = Math.min(90, Math.max(10, (candleCount / visibleCandleEstimate) * 100));
  const estimatedLeftPct = Math.max(0, 95 - estimatedWidthPct);  // anchor to right side (latest candles)

  const label = typeof args.label === "string" ? args.label : meta.label;
  const message = typeof args.message === "string"
    ? args.message
    : `Analyzing ${zoneType.replace(/_/g, " ")} zone — ${direction} bias`;

  setHighlight({
    target: "chartCanvas",
    label,
    message,
    region: {
      leftPct: estimatedLeftPct,
      topPct: 15,
      widthPct: estimatedWidthPct,
      heightPct: 65,
    },
  });
  return `success: highlighted contextual zone "${zoneType}" (${candleCount} candles, ${direction})`;
};

/**
 * Generic highlight dispatcher. Accepts any of:
 *  - { type: "section", target, label, message, include_chat }
 *  - { type: "chart_area", left_pct, top_pct, width_pct, height_pct, ... }
 *  - { type: "candles", from_index, to_index, start_time, end_time, ... }
 */
export const handleHighlight: ActionHandler = (ctx) => {
  const args = ctx.args;
  const type = String(args.type || args.kind || "section");
  if (type === "section") return handleHighlightSection(ctx);
  if (type === "chart_area") return handleHighlightChartArea(ctx);
  if (type === "candles" || type === "range") return handleHighlightCandles(ctx);
  // Default: treat as a section highlight for backward compat
  return handleHighlightSection(ctx);
};

function clampPercent(value: unknown, fallback: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.min(100, n));
}
