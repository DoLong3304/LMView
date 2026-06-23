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
