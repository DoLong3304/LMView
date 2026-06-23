import type { ActionHandler } from "./index";

/**
 * Clear all AI-placed drawings from the chart.
 */
export const handleClearDrawings: ActionHandler = ({ runtime }) => {
  if (typeof window === "undefined") {
    return "error: window unavailable";
  }
  window.dispatchEvent(new CustomEvent("lmview:clear-ai-drawings"));
  runtime.clearDrawings?.();
  return "success: cleared AI drawings";
};

/**
 * Delete a single drawing by id.
 * @param ctx.args.drawing_id  Required.
 */
export const handleDeleteDrawing: ActionHandler = ({ args }) => {
  const id = String(args.drawing_id || args.id || "").trim();
  if (!id) {
    return "error: 'drawing_id' is required";
  }
  if (typeof window === "undefined") {
    return "error: window unavailable";
  }
  window.dispatchEvent(new CustomEvent("lmview:delete-drawing", { detail: { id } }));
  return `success: deleted drawing ${id}`;
};

/**
 * Update the color of an existing drawing.
 * @param ctx.args.drawing_id  Required.
 * @param ctx.args.color       Required (CSS color).
 */
export const handleSetDrawingColor: ActionHandler = ({ args }) => {
  const id = String(args.drawing_id || args.id || "").trim();
  const color = String(args.color || "").trim();
  if (!id || !color) {
    return "error: 'drawing_id' and 'color' are required";
  }
  if (typeof window === "undefined") {
    return "error: window unavailable";
  }
  window.dispatchEvent(new CustomEvent("lmview:set-drawing-color", { detail: { id, color } }));
  return `success: recoloured drawing ${id} to ${color}`;
};
