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
export const _drawingHelpers = { clampPercent, parseDrawingDataPoints };
