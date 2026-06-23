import type { ActionHandler } from "./index";

const ALLOWED_PANELS = new Set([
  "ai", "overview", "watchlist", "orderBook", "recentTrades", "marketsNews", "screener",
]);

const ALLOWED_PANEL_TABS = new Set(["watchlist", "orderBook", "recentTrades"]);

const ALLOWED_VIEWS = new Set(["charts", "marketsNews", "screener", "settings"]);

function openPanelTarget(runtime: ActionHandler extends never ? never : import("./index").ActionDispatchContext["runtime"], target: string) {
  if (typeof window === "undefined") return;
  // We dispatch a high-level event so the AppShell can route correctly
  // even when the right panel is in a collapsed state.
  window.dispatchEvent(new CustomEvent("lmview:open-panel", { detail: { target } }));
  runtime.setView?.("charts");
  runtime.setRightPanelOpen?.(true);
  if (target === "ai") {
    runtime.setRightPanelTopTab?.("aiHelper");
    return;
  }
  runtime.setRightPanelTopTab?.("overview");
  if (target === "watchlist" || target === "orderBook" || target === "recentTrades") {
    runtime.setRightPanelTab?.(target);
  }
}

function switchAppView(runtime: ActionHandler extends never ? never : import("./index").ActionDispatchContext["runtime"], view: string) {
  runtime.setView?.(view);
  if (view === "charts") {
    runtime.setRightPanelOpen?.(true);
    return;
  }
  if (view === "settings") {
    runtime.openSettings?.();
    return;
  }
  // NB: do NOT close the right panel when switching to markets/news.
  // The AI Helper lives inside the right panel; closing it would hide
  // the tour overlay mid-step. Leave the panel open so the user can
  // still see the step text and click Next/Finish.
}

export const handleOpenPanel: ActionHandler = ({ runtime, setHighlight, captureUiSnapshot, args }) => {
  const target = String(args.target || "overview");
  if (!ALLOWED_PANELS.has(target)) {
    return `error: unsupported panel "${target}". Allowed: ${[...ALLOWED_PANELS].join(", ")}`;
  }
  captureUiSnapshot();
  openPanelTarget(runtime, target);
  if (args.highlight !== false) {
    setHighlight({
      target: target === "ai" ? "ai" : "rightPanel",
      label: typeof args.label === "string" ? args.label : target,
      message: typeof args.message === "string" ? args.message : undefined,
      includeChat: target === "ai",
    });
  }
  return `success: opened ${target} panel`;
};

export const handleClosePanel: ActionHandler = ({ runtime, captureUiSnapshot }) => {
  captureUiSnapshot();
  runtime.setRightPanelOpen?.(false);
  return "success: closed right panel";
};

export const handleSwitchPanelTab: ActionHandler = ({ runtime, setHighlight, captureUiSnapshot, args }) => {
  const tab = String(args.tab || "watchlist");
  if (!ALLOWED_PANEL_TABS.has(tab)) {
    return `error: unsupported right-panel tab "${tab}". Allowed: ${[...ALLOWED_PANEL_TABS].join(", ")}`;
  }
  captureUiSnapshot();
  runtime.setView?.("charts");
  runtime.setRightPanelOpen?.(true);
  runtime.setRightPanelTopTab?.("overview");
  runtime.setRightPanelTab?.(tab);
  if (args.highlight !== false) {
    setHighlight({
      target: tab,
      label: typeof args.label === "string" ? args.label : tab,
    });
  }
  return `success: switched right panel to ${tab}`;
};

export const handleSwitchAppView: ActionHandler = ({ runtime, setHighlight, captureUiSnapshot, args }) => {
  const view = String(args.view || "charts");
  if (!ALLOWED_VIEWS.has(view)) {
    return `error: unsupported app view "${view}". Allowed: ${[...ALLOWED_VIEWS].join(", ")}`;
  }
  captureUiSnapshot();
  switchAppView(runtime, view);
  if (args.highlight !== false) {
    setHighlight({
      target: view,
      label: view,
    });
  }
  return `success: switched app view to ${view}`;
};

export const handleViewSection: ActionHandler = ({ showSection, setHighlight, args }) => {
  const target = String(args.target || "chart");
  showSection(target);
  setHighlight({ target, label: typeof args.label === "string" ? args.label : target });
  return `success: opened section ${target}`;
};

export const handleOpenSettings: ActionHandler = ({ runtime, setHighlight }) => {
  runtime.openSettings?.();
  setHighlight({ target: "settings", label: "Settings" });
  return "success: opened settings";
};

export const handleCloseSettings: ActionHandler = ({ runtime }) => {
  runtime.closeSettings?.();
  return "success: closed settings";
};
