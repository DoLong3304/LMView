import type { ActionHandler, ActionDispatchContext } from "./index";

/**
 * Show a supported chart indicator.
 * @param ctx.args.indicator  e.g. "rsi", "macd", "bb", "sma20"
 * @param ctx.args.settings    optional settings override (e.g. period)
 */
export const handleAddIndicator: ActionHandler = ({ runtime, args }) => {
  const indicator = String(args.indicator || args.indicator_name || "").trim();
  if (!indicator) {
    return "error: missing required argument 'indicator'";
  }
  if (!runtime.chartController) {
    return "error: chart controller not available";
  }
  runtime.chartController.setIndicatorVisible(indicator, true);
  return `success: added indicator "${indicator}"`;
};

export const handleRemoveIndicator: ActionHandler = ({ runtime, args }) => {
  const indicator = String(args.indicator || args.indicator_name || "").trim();
  if (!indicator) {
    return "error: missing required argument 'indicator'";
  }
  if (!runtime.chartController) {
    return "error: chart controller not available";
  }
  runtime.chartController.setIndicatorVisible(indicator, false);
  return `success: removed indicator "${indicator}"`;
};

export const handleToggleIndicator: ActionHandler = ({ runtime, args }) => {
  const indicator = String(args.indicator || args.indicator_name || "").trim();
  if (!indicator) {
    return "error: missing required argument 'indicator'";
  }
  if (!runtime.chartController) {
    return "error: chart controller not available";
  }
  runtime.chartController.toggleIndicator(indicator);
  return `success: toggled indicator "${indicator}"`;
};

/**
 * Configure indicator parameters (period, color, etc.). The chart
 * controller accepts generic settings overrides via a custom event so we
 * don't need a dedicated controller method.
 */
export const handleConfigureIndicator: ActionHandler = ({ args }) => {
  const indicator = String(args.indicator || args.indicator_name || "").trim();
  if (!indicator) {
    return "error: missing required argument 'indicator'";
  }
  const settings = (args.settings && typeof args.settings === "object"
    ? (args.settings as Record<string, unknown>)
    : null);
  if (!settings) {
    return "error: missing required argument 'settings'";
  }
  window.dispatchEvent(
    new CustomEvent("lmview:indicator-configure", {
      detail: { indicator, settings },
    }),
  );
  return `success: configured indicator "${indicator}"`;
};

// Kept for backwards compat with old `manage_indicator` shape
export const handleManageIndicator: ActionHandler = (ctx: ActionDispatchContext) => {
  const action = String(ctx.args.action || "").toLowerCase();
  if (action === "add") return handleAddIndicator(ctx);
  if (action === "remove") return handleRemoveIndicator(ctx);
  if (action === "toggle") return handleToggleIndicator(ctx);
  return `error: unsupported manage_indicator action "${action}"`;
};
