import type { ActionHandler } from "./index";

const ALLOWED_TOOLS = new Set([
  // Direct tools
  "cursor", "text", "ruler", "brush",
  // Lines
  "trendline", "ray", "extendedLine", "horizontalRay", "horizontal", "vertical", "arrow",
  // Shapes
  "rectangle", "circle", "triangle", "ellipse", "polygon",
  // Fibonacci
  "fibRetracement", "fibExtension", "fibChannel", "fibTimeZone", "fibWedge",
  // Channels
  "parallelChannel", "pitchfork", "schiffPitchfork", "modifiedPitchfork", "insidePitchfork",
  // Patterns
  "harmonicABCD", "xabcdPattern", "cypherPattern", "crabPattern", "batPattern", "butterflyPattern", "threeDrivesPattern",
  // Elliott
  "elliottWave", "elliottImpulseWave", "elliottCorrectiveWave",
  // Gann
  "gannBox", "gannFan", "gannSquare", "gannSquareFixed",
  // Positions
  "longPosition", "shortPosition", "forecast", "priceRange", "dateRange", "callout", "comment", "priceLabel", "ghost", "arrowMarker", "balloon", "signpost", "flag", "flagMark",
  // Measure
  "measure", "priceScale", "barsPattern", "ghostFeed", "replay",
]);

function clampPercent(value: unknown, fallback: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.min(100, n));
}

function parseDrawingDataPoints(points: unknown): Array<{ time: number; price: number }> | null {
  if (!Array.isArray(points)) return null;
  const parsed: Array<{ time: number; price: number }> = [];
  for (const point of points) {
    if (!point || typeof point !== "object") return null;
    const c = point as Record<string, unknown>;
    const time = Number(c.time);
    const price = Number(c.price);
    if (!Number.isFinite(time) || !Number.isFinite(price)) return null;
    parsed.push({ time, price });
  }
  if (!parsed.length) return null;
  return parsed;
}

/**
 * Select a drawing tool and optionally place a drawing on the chart.
 * @param ctx.args.tool     One of the supported tool IDs.
 * @param ctx.args.points   Optional list of {time, price} points.
 * @param ctx.args.text     Optional text label.
 * @param ctx.args.color    Optional color override.
 * @param ctx.args.lineWidth Optional line width override.
 * @param ctx.args.settings Optional settings object passed through.
 */
export const handleDrawTool: ActionHandler = ({ runtime, args }) => {
  const tool = String(args.tool || "").trim();
  if (!tool) {
    return "error: missing required argument 'tool'";
  }
  if (!ALLOWED_TOOLS.has(tool) && tool !== "cursor") {
    return `error: unsupported drawing tool "${tool}"`;
  }
  if (!runtime.setDrawingTool) {
    return "error: drawing controller not available";
  }
  runtime.setDrawingTool(tool);

  const points = parseDrawingDataPoints(args.points);
  if (points && runtime.addDrawing) {
    const color = typeof args.color === "string" ? args.color : "#38bdf8";
    const lineWidth = Number(args.lineWidth ?? 2);
    const settings: Record<string, unknown> = { color, lineWidth };
    if (args.settings && typeof args.settings === "object") {
      Object.assign(settings, args.settings);
    }
    runtime.addDrawing({
      id: `ai-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      tool,
      dataPoints: points,
      text: typeof args.text === "string" ? args.text : undefined,
      settings,
    });
    // Reset to cursor so subsequent clicks don't draw more points.
    runtime.setDrawingTool("cursor");
    return `success: placed ${tool} with ${points.length} point(s)`;
  }
  return `success: selected ${tool} tool`;
};

/**
 * Place a text annotation at a chart point.
 * @param ctx.args.time  Unix seconds.
 * @param ctx.args.price Price level.
 * @param ctx.args.text  Annotation text.
 */
export const handleCreateAnnotation: ActionHandler = ({ runtime, args }) => {
  const time = Number(args.time);
  const price = Number(args.price);
  const text = String(args.text || "").trim();
  if (!Number.isFinite(time) || !Number.isFinite(price)) {
    return "error: annotation requires 'time' and 'price'";
  }
  if (!runtime.addDrawing) {
    return "error: drawing controller not available";
  }
  runtime.addDrawing({
    id: `ai-anno-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    tool: "text",
    dataPoints: [{ time, price }],
    text: text || "Note",
    settings: {
      color: typeof args.color === "string" ? args.color : "#fbbf24",
      fontSize: Number(args.fontSize ?? 13),
    },
  });
  return `success: created annotation "${text}"`;
};

// Silence the linter for the helper we export

/**
 * Draw a horizontal support / resistance line.
 * Auto-computes the price level from the recent chart candles when no
 * explicit `price` is given (uses the highest high of the last 20
 * candles as resistance, or the lowest low as support, based on the
 * label keyword).
 */
export const handleDrawHorizontalLine: ActionHandler = ({ runtime, args }) => {
  if (!runtime.addDrawing) {
    return "error: drawing controller not available";
  }
  const label = String(args.label || "Horizontal line");
  const color = typeof args.color === "string" ? args.color : "#f97316";
  // Get chart's latest candle from runtime context if available
  const latestCandle = (runtime as { getLatestCandle?: () => { time: number; high: number; low: number } | null }).getLatestCandle?.();
  let price = Number(args.price);
  if (!Number.isFinite(price) && latestCandle) {
    if (/support/i.test(label)) price = latestCandle.low;
    else if (/resistance|high|swing high/i.test(label)) price = latestCandle.high;
    else price = (latestCandle.high + latestCandle.low) / 2;
  }
  if (!Number.isFinite(price)) {
    return "error: cannot determine price level for horizontal line";
  }
  // Use 10 candles around current time as data points so the line spans
  // a reasonable region of the chart.
  const now = Math.floor(Date.now() / 1000);
  const points = [
    { time: now - 3600 * 5, price },
    { time: now, price },
  ];
  runtime.addDrawing({
    id: `ai-hl-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    tool: "horizontal",
    dataPoints: points,
    text: label,
    settings: { color, lineWidth: 2, lineStyle: 2 },
  });
  return `success: drew horizontal line at ${price.toFixed(2)} (${label})`;
};

/**
 * Place a Fibonacci retracement overlay.
 */
export const handleDrawFib: ActionHandler = ({ runtime, args: _args }) => {
  if (!runtime.addDrawing) {
    return "error: drawing controller not available";
  }
  const latestCandle = (runtime as { getLatestCandle?: () => { time: number; high: number; low: number } | null }).getLatestCandle?.();
  if (!latestCandle) {
    return "error: no chart data to compute Fibonacci levels";
  }
  const now = Math.floor(Date.now() / 1000);
  const range = latestCandle.high - latestCandle.low;
  const levels = [
    { price: latestCandle.high, label: "100%" },
    { price: latestCandle.high - range * 0.382, label: "61.8%" },
    { price: latestCandle.high - range * 0.5, label: "50%" },
    { price: latestCandle.high - range * 0.618, label: "38.2%" },
    { price: latestCandle.low, label: "0%" },
  ];
  for (const lvl of levels) {
    runtime.addDrawing({
      id: `ai-fib-${lvl.label}-${Math.random().toString(36).slice(2, 8)}`,
      tool: "horizontal",
      dataPoints: [{ time: now - 3600 * 5, price: lvl.price }, { time: now, price: lvl.price }],
      text: `Fib ${lvl.label}`,
      settings: { color: "#a78bfa", lineWidth: 1, lineStyle: 2 },
    });
  }
  return "success: drew Fibonacci retracement (38.2%, 50%, 61.8%)";
};

/**
 * Highlight a price/time box (rectangle).
 */
export const handleDrawRectangle: ActionHandler = ({ runtime, args }) => {
  if (!runtime.addDrawing) {
    return "error: drawing controller not available";
  }
  const now = Math.floor(Date.now() / 1000);
  const color = typeof args.color === "string" ? args.color : "#22c55e";
  const points = [
    { time: now - 3600 * 2, price: Number(args.priceTop ?? 100000) },
    { time: now, price: Number(args.priceBottom ?? 0) },
  ];
  if (!Number.isFinite(points[0].price) || !Number.isFinite(points[1].price)) {
    return "error: rectangle requires priceTop and priceBottom";
  }
  runtime.addDrawing({
    id: `ai-rect-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    tool: "rectangle",
    dataPoints: points,
    text: typeof args.label === "string" ? args.label : undefined,
    settings: { color, fillColor: `${color}33`, lineWidth: 2 },
  });
  return "success: drew rectangle";
};

// Silence the linter for the helper we export
export const _drawingHelpers = { clampPercent, parseDrawingDataPoints };
