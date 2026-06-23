import type { ActionHandler } from "./index";

/**
 * Start a user-paced LMView tour. The new Interact-mode tour planner
 * drives the action; this is kept for backwards-compat with the static
 * "lmview-overview" tour button in the debug window.
 */
export const handleStartTour: ActionHandler = ({ args }) => {
  const tourId = String(args.tour_id || "lmview-overview");
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("lmview:start-tour", { detail: { tour_id: tourId } }));
  }
  return `success: starting tour "${tourId}"`;
};

/**
 * Cancel the currently active tour.
 */
export const handleEndTour: ActionHandler = () => {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-cancel"));
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-complete"));
  }
  return "success: ended tour";
};
