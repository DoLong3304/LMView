import type { ActionHandler } from "./index";

/**
 * Clear AI highlights, action overlays, and tour annotations.
 */
export const handleClearAiAnnotations: ActionHandler = ({ setHighlight }) => {
  setHighlight(null);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("lmview:clear-ai-annotations"));
  }
  return "success: cleared AI annotations";
};

/**
 * Export current chart view. Frontend chart layer handles actual export.
 */
export const handleExportChart: ActionHandler = ({ args }) => {
  const format = String(args.format || "png");
  const filename = typeof args.filename === "string" ? args.filename : undefined;
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("lmview:export-chart", {
      detail: { format, filename },
    }));
  }
  return `success: requested chart export as ${format}`;
};
