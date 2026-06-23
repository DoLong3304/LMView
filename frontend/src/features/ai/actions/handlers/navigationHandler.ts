import type { ActionHandler } from "./index";

/**
 * Zoom the chart in or out.
 * @param ctx.args.direction      "in" or "out"
 * @param ctx.args.anchor_ratio   0..1 — anchor point (0 left, 1 right)
 * @param ctx.args.steps          How many zoom levels (default 1)
 */
export const handleZoomChart: ActionHandler = ({ runtime, args }) => {
  if (!runtime.chartController) {
    return "error: chart controller not available";
  }
  const direction = String(args.direction || "in") === "out" ? "out" : "in";
  const anchorRatio = Number(args.anchor_ratio ?? 0.5);
  const steps = Math.max(1, Math.min(10, Number(args.steps ?? 1)));
  for (let i = 0; i < steps; i += 1) {
    runtime.chartController.zoomChart(direction, anchorRatio);
  }
  return `success: zoomed chart ${direction} x${steps}`;
};

/**
 * Scroll chart horizontally.
 * @param ctx.args.target  "start" | "end" | "left" | "right" | number
 * @param ctx.args.bars    integer count for left/right scroll
 */
export const handleScrollChart: ActionHandler = ({ runtime, args }) => {
  if (!runtime.chartController) {
    return "error: chart controller not available";
  }
  const rawTarget = args.target;
  let target: "start" | "end" | "left" | "right" | number;
  if (typeof rawTarget === "number") {
    target = rawTarget;
  } else if (rawTarget === "left" || rawTarget === "right") {
    const bars = Number(args.bars ?? 20);
    target = rawTarget === "left" ? -Math.abs(bars) : Math.abs(bars);
  } else {
    target = String(rawTarget || "end") === "start" ? "start" : "end";
  }
  runtime.chartController.scrollChart(target);
  return `success: scrolled chart ${String(target)}`;
};

/**
 * Reset the chart to the default zoom + scroll position.
 */
export const handleResetChartView: ActionHandler = ({ runtime }) => {
  if (!runtime.chartController) {
    return "error: chart controller not available";
  }
  // Scroll to end (live latest) + zoom to default
  runtime.chartController.scrollChart("end");
  return "success: reset chart view to default";
};

/**
 * Scroll chart to a specific timestamp.
 * @param ctx.args.time  Unix seconds (preferred) or milliseconds.
 */
export const handleScrollChartToTime: ActionHandler = ({ runtime, args }) => {
  if (!runtime.chartController) {
    return "error: chart controller not available";
  }
  const rawTime = Number(args.time);
  if (!Number.isFinite(rawTime)) {
    return "error: 'time' is required (unix seconds or ms)";
  }
  // Heuristic: ms > 10^12 → ms; otherwise seconds
  const timeSeconds = rawTime > 1e12 ? Math.floor(rawTime / 1000) : rawTime;
  window.dispatchEvent(
    new CustomEvent("lmview:scroll-chart-to-time", { detail: { time: timeSeconds } }),
  );
  return `success: scrolled chart to ${timeSeconds}`;
};
