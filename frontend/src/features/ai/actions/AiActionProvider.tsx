import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Move, Play, X } from "lucide-react";
import { INDICATORS } from "@/features/chart/IndicatorPanel";
import { TOOL_GROUPS } from "@/features/drawing/components/DrawingToolbar";
import { useI18n } from "@/i18n";
import { fetchHistoricalCandles } from "@/services/marketDataService";
import { CHART_TYPES } from "@/types";
import { sanitizeTechnicalDetails } from "@/utils/errors";
import { getActionHandler } from "@/features/ai/actions/handlers";
import type { ChartType, Drawing, IndicatorSettings, TimeframeKey } from "@/types";

type AppView = "charts" | "marketsNews" | "screener";
type RightPanelTopTab = "overview" | "aiHelper";
type RightPanelTab = "watchlist" | "orderBook" | "recentTrades";
type PanelTarget = "ai" | "overview" | RightPanelTab;

export interface AiActionCall {
  name: string;
  arguments?: Record<string, unknown>;
  reason?: string | null;
  requires_approval?: boolean;
}

export interface AiActionDefinition {
  name: string;
  description: string;
  parameters: {
    type: "object";
    properties: Record<string, AiActionParameter>;
    required?: string[];
  };
}

interface AiActionParameter {
  type: "string" | "number" | "integer" | "boolean" | "array" | "object";
  enum?: string[];
  default?: unknown;
  description?: string;
}

export interface AiChartActionController {
  setIndicatorVisible: (indicator: string, visible: boolean) => void;
  toggleIndicator: (indicator: string) => void;
  zoomChart: (direction: "in" | "out", anchorRatio?: number) => void;
  scrollChart: (target: "start" | "end" | "left" | "right" | number) => void;
  rangeToChartRegion: (args: Record<string, unknown>) => ChartRegion | null;
}

interface AiActionRuntime {
  setDrawingTool?: (tool: string) => void;
  addDrawing?: (drawing: Drawing) => void;
  clearDrawings?: () => void;
  setTimeframe?: (timeframe: TimeframeKey) => void;
  setSymbol?: (symbol: string) => void;
  setChartType?: (chartType: ChartType) => void;
  setView?: (view: AppView) => void;
  setRightPanelOpen?: (open: boolean) => void;
  setRightPanelTopTab?: (tab: RightPanelTopTab) => void;
  setRightPanelTab?: (tab: RightPanelTab) => void;
  openSettings?: () => void;
  closeSettings?: () => void;
  currentView?: AppView;
  rightPanelOpen?: boolean;
  rightPanelTopTab?: RightPanelTopTab;
  rightPanelTab?: RightPanelTab;
  currentTimeframe?: TimeframeKey;
  selectedSymbol?: string;
  chartType?: ChartType;
  chartController?: AiChartActionController | null;
}

interface UiSnapshot {
  currentView?: AppView;
  rightPanelOpen?: boolean;
  rightPanelTopTab?: RightPanelTopTab;
  rightPanelTab?: RightPanelTab;
}

interface ChartRegion {
  leftPct: number;
  topPct: number;
  widthPct: number;
  heightPct: number;
}

interface HighlightState {
  target: string;
  label?: string;
  message?: string;
  includeChat?: boolean;
  region?: ChartRegion;
}

interface AiActionContextValue {
  definitions: AiActionDefinition[];
  executeAction: (call: AiActionCall) => Promise<{ ok: boolean; detail: string }>;
  openDebugWindow: () => void;
  setRuntime: (runtime: Partial<AiActionRuntime>) => void;
  actionLog: Array<{ call: AiActionCall; at: number; detail: string }>;
  clearActionLog: () => void;
}

const AiActionContext = createContext<AiActionContextValue | null>(null);

const SECTION_SELECTORS: Record<string, string> = {
  app: "[data-ai-section='app-shell']",
  header: "[data-ai-section='header']",
  chart: "[data-ai-section='chart']",
  chartToolbar: "[data-ai-section='chart-toolbar']",
  chartCanvas: "[data-ai-section='chart-canvas']",
  ai: "[data-ai-section='ai-panel']",
  rightPanel: "[data-ai-section='right-panel']",
  rightPanelOverview: "[data-ai-section='right-panel-overview']",
  watchlist: "[data-ai-section='right-panel']",
  watchlistList: "[data-ai-section='watchlist-list']",
  orderBook: "[data-ai-section='order-book-panel']",
  recentTrades: "[data-ai-section='recent-trades-panel']",
  drawingTools: "[data-ai-section='drawing-toolbar']",
  marketsNews: "[data-ai-section='markets-news-page']",
  screener: "[data-ai-section='screener-page']",
  settings: "[data-ai-section='settings-modal']",
  account: "[data-ai-section='header']",
};

const TIMEFRAMES: TimeframeKey[] = ["1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"];
const HISTORICAL_TIMEFRAMES: TimeframeKey[] = TIMEFRAMES.filter((item) => item !== "1s");
const PANEL_TARGETS: PanelTarget[] = ["ai", "overview", "watchlist", "orderBook", "recentTrades"];
const APP_VIEWS: AppView[] = ["charts", "marketsNews", "screener"];

function drawingTools(): string[] {
  return TOOL_GROUPS.flatMap((group) => group.tools.map((tool) => tool.id));
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, value));
}

function openPanelTarget(runtime: AiActionRuntime, target: PanelTarget): void {
  runtime.setView?.("charts");
  runtime.setRightPanelOpen?.(true);

  if (target === "ai") {
    runtime.setRightPanelTopTab?.("aiHelper");
    window.dispatchEvent(new CustomEvent("lmview:right-panel-top-tab", { detail: { tab: "aiHelper" } }));
    return;
  }

  runtime.setRightPanelTopTab?.("overview");
  window.dispatchEvent(new CustomEvent("lmview:right-panel-top-tab", { detail: { tab: "overview" } }));

  if (target !== "overview") {
    runtime.setRightPanelTab?.(target);
    window.dispatchEvent(new CustomEvent("lmview:right-panel-tab", { detail: { tab: target } }));
  }
}

function switchAppView(runtime: AiActionRuntime, view: AppView): void {
  runtime.setView?.(view);
  // NB: do NOT auto-close the right panel here. The AI Helper lives
  // inside the right panel, so closing it mid-tour would hide the
  // overlay itself. The user (or the next step) can open/close the
  // panel explicitly if needed.
}

function actionDefinitions(): AiActionDefinition[] {
  const indicators = INDICATORS.map((item) => item.key);
  const tools = drawingTools();
  const chartTypes = CHART_TYPES.map((item) => item.id);
  return [
    {
      name: "add_indicator",
      description: "Show a supported chart indicator.",
      parameters: {
        type: "object",
        properties: { indicator: { type: "string", enum: indicators } },
        required: ["indicator"],
      },
    },
    {
      name: "remove_indicator",
      description: "Hide a supported chart indicator.",
      parameters: {
        type: "object",
        properties: { indicator: { type: "string", enum: indicators } },
        required: ["indicator"],
      },
    },
    {
      name: "toggle_indicator",
      description: "Toggle a supported chart indicator.",
      parameters: {
        type: "object",
        properties: { indicator: { type: "string", enum: indicators } },
        required: ["indicator"],
      },
    },
    {
      name: "draw_tool",
      description: "Select a drawing tool and optionally place a drawing.",
      parameters: {
        type: "object",
        properties: {
          tool: { type: "string", enum: tools },
          points: { type: "array", description: 'JSON array like [{"time":1717200000,"price":67500}]' },
          text: { type: "string" },
        },
        required: ["tool"],
      },
    },
    {
      name: "highlight_section",
      description: "Dim the UI except the target section. Chat stays unhighlighted unless include_chat is true.",
      parameters: {
        type: "object",
        properties: {
          target: { type: "string", enum: Object.keys(SECTION_SELECTORS) },
          label: { type: "string" },
          message: { type: "string" },
          include_chat: { type: "boolean", default: false },
        },
        required: ["target"],
      },
    },
    {
      name: "highlight_chart_area",
      description: "Highlight a rectangular area inside the chart by percentages.",
      parameters: {
        type: "object",
        properties: {
          left_pct: { type: "number", default: 20, description: "0-100 left position." },
          top_pct: { type: "number", default: 20, description: "0-100 top position." },
          width_pct: { type: "number", default: 40, description: "0-100 width." },
          height_pct: { type: "number", default: 30, description: "0-100 height." },
          label: { type: "string" },
          message: { type: "string" },
        },
      },
    },
    {
      name: "highlight_candles",
      description: "Highlight candles by index range or by time range.",
      parameters: {
        type: "object",
        properties: {
          from_index: { type: "integer", description: "Zero-based candle index." },
          to_index: { type: "integer", description: "Zero-based candle index." },
          start_time: { type: "integer", description: "Unix seconds or milliseconds." },
          end_time: { type: "integer", description: "Unix seconds or milliseconds." },
          label: { type: "string" },
          message: { type: "string" },
        },
      },
    },
    {
      name: "set_chart_type",
      description: "Switch chart type.",
      parameters: {
        type: "object",
        properties: { chart_type: { type: "string", enum: chartTypes } },
        required: ["chart_type"],
      },
    },
    {
      name: "set_timeframe",
      description: "Switch chart timeframe.",
      parameters: {
        type: "object",
        properties: { timeframe: { type: "string", enum: TIMEFRAMES } },
        required: ["timeframe"],
      },
    },
    {
      name: "set_symbol",
      description: "Switch selected market symbol (e.g. BTCUSDT, ETHUSDT).",
      parameters: {
        type: "object",
        properties: { symbol: { type: "string", default: "BTCUSDT" } },
        required: ["symbol"],
      },
    },
    {
      name: "configure_indicator",
      description: "Update indicator parameters (period, colors, etc.).",
      parameters: {
        type: "object",
        properties: {
          indicator: { type: "string", enum: indicators },
          settings: { type: "object", description: "Indicator settings to override (e.g. { period: 14, color: '#f00' })." },
        },
        required: ["indicator", "settings"],
      },
    },
    {
      name: "clear_drawings",
      description: "Remove all AI-placed drawings from the chart.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "delete_drawing",
      description: "Delete a specific drawing by id.",
      parameters: {
        type: "object",
        properties: { drawing_id: { type: "string" } },
        required: ["drawing_id"],
      },
    },
    {
      name: "set_drawing_color",
      description: "Recolor an existing drawing.",
      parameters: {
        type: "object",
        properties: {
          drawing_id: { type: "string" },
          color: { type: "string", description: "CSS color (hex, rgb, etc.)" },
        },
        required: ["drawing_id", "color"],
      },
    },
    {
      name: "open_panel",
      description: "Open a right-panel target for the user and optionally highlight it.",
      parameters: {
        type: "object",
        properties: {
          target: { type: "string", enum: PANEL_TARGETS },
          highlight: { type: "boolean", default: true },
          label: { type: "string" },
          message: { type: "string" },
        },
        required: ["target"],
      },
    },
    {
      name: "close_panel",
      description: "Close the right panel.",
      parameters: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "switch_panel_tab",
      description: "Switch the right panel to watchlist, order book, or recent trades.",
      parameters: {
        type: "object",
        properties: {
          tab: { type: "string", enum: ["watchlist", "orderBook", "recentTrades"] },
          highlight: { type: "boolean", default: true },
        },
        required: ["tab"],
      },
    },
    {
      name: "switch_app_view",
      description: "Switch between charts, markets/news, and screener views.",
      parameters: {
        type: "object",
        properties: {
          view: { type: "string", enum: APP_VIEWS },
          highlight: { type: "boolean", default: true },
        },
        required: ["view"],
      },
    },
    {
      name: "view_section",
      description: "Open and highlight a major app section.",
      parameters: {
        type: "object",
        properties: { target: { type: "string", enum: Object.keys(SECTION_SELECTORS) } },
        required: ["target"],
      },
    },
    {
      name: "zoom_chart",
      description: "Zoom chart in or out.",
      parameters: {
        type: "object",
        properties: {
          direction: { type: "string", enum: ["in", "out"] },
          anchor_ratio: { type: "number", default: 0.5, description: "0 left edge, 1 right edge." },
        },
        required: ["direction"],
      },
    },
    {
      name: "scroll_chart",
      description: "Scroll chart horizontally.",
      parameters: {
        type: "object",
        properties: {
          target: { type: "string", enum: ["start", "end", "left", "right"] },
          bars: { type: "integer", default: 20 },
        },
        required: ["target"],
      },
    },
    {
      name: "fetch_historical_prices",
      description: "Fetch historical candles for current or requested market. 1s is live-only.",
      parameters: {
        type: "object",
        properties: {
          symbol: { type: "string", default: "BTCUSDT" },
          timeframe: { type: "string", enum: HISTORICAL_TIMEFRAMES, default: "1h" },
          start_ms: { type: "integer" },
          end_ms: { type: "integer" },
          limit: { type: "integer", default: 100 },
        },
        required: ["start_ms", "end_ms"],
      },
    },
    {
      name: "open_settings",
      description: "Open the settings modal.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "close_settings",
      description: "Close the settings modal.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "reset_chart_view",
      description: "Reset chart zoom + scroll to default (latest live candles).",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "export_chart",
      description: "Export current chart as image or CSV.",
      parameters: {
        type: "object",
        properties: {
          format: { type: "string", enum: ["png", "svg", "csv"], default: "png" },
          filename: { type: "string" },
        },
      },
    },
    {
      name: "scroll_chart_to_time",
      description: "Scroll chart to a specific timestamp (unix seconds or ms).",
      parameters: {
        type: "object",
        properties: { time: { type: "integer" } },
        required: ["time"],
      },
    },
    {
      name: "end_tour",
      description: "End the currently active tour.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "start_tour",
      description: "Start a user-paced LMView tour. Most use cases use the dynamic Interact-mode tour planner; this is kept for the static overview tour.",
      parameters: {
        type: "object",
        properties: {
          tour_id: { type: "string", default: "lmview-overview" },
          start_step: { type: "integer", default: 0 },
        },
      },
    },
    {
      name: "clear_ai_annotations",
      description: "Clear AI highlights and action overlays.",
      parameters: { type: "object", properties: {} },
    },
    {
      name: "restore_ui_state",
      description: "Return the UI to the state saved before the latest AI navigation.",
      parameters: { type: "object", properties: {} },
    },
  ];
}

export function AiActionProvider({ children }: { children: React.ReactNode }) {
  const definitions = useMemo(actionDefinitions, []);
  const runtimeRef = useRef<AiActionRuntime>({});
  const [debugOpen, setDebugOpen] = useState(false);
  const [highlight, setHighlight] = useState<HighlightState | null>(null);
  const [actionLog, setActionLog] = useState<Array<{ call: AiActionCall; at: number; detail: string }>>([]);
  const actionLogRef = useRef<Array<{ call: AiActionCall; at: number; detail: string }>>([]);
  const uiSnapshotRef = useRef<UiSnapshot | null>(null);
  const [restoreAvailable, setRestoreAvailable] = useState(false);

  const recordAction = useCallback((call: AiActionCall, detail: string) => {
    const entry = { call, at: Date.now(), detail };
    actionLogRef.current = [...actionLogRef.current, entry];
    setActionLog(actionLogRef.current);
  }, []);

  const setRuntime = useCallback((runtime: Partial<AiActionRuntime>) => {
    runtimeRef.current = { ...runtimeRef.current, ...runtime };
  }, []);

  const captureUiSnapshot = useCallback(() => {
    if (uiSnapshotRef.current) return;
    const runtime = runtimeRef.current;
    uiSnapshotRef.current = {
      currentView: runtime.currentView,
      rightPanelOpen: runtime.rightPanelOpen,
      rightPanelTopTab: runtime.rightPanelTopTab,
      rightPanelTab: runtime.rightPanelTab,
    };
    // NB: do NOT setRestoreAvailable(true) here. The banner is only
    // useful AFTER a tour finishes so the user can decide whether to
    // revert; flashing it during every step is noise.
  }, []);

  const restoreUiState = useCallback(() => {
    const runtime = runtimeRef.current;
    const snapshot = uiSnapshotRef.current;
    if (!snapshot) return;
    if (snapshot.currentView) runtime.setView?.(snapshot.currentView);
    if (typeof snapshot.rightPanelOpen === "boolean") {
      runtime.setRightPanelOpen?.(snapshot.rightPanelOpen);
    }
    if (snapshot.rightPanelTopTab) {
      runtime.setRightPanelTopTab?.(snapshot.rightPanelTopTab);
    }
    if (snapshot.rightPanelTab) {
      runtime.setRightPanelTab?.(snapshot.rightPanelTab);
    }
    runtime.closeSettings?.();
    uiSnapshotRef.current = null;
    setRestoreAvailable(false);
    setHighlight(null);
  }, []);

  const showSection = useCallback((target: string) => {
    captureUiSnapshot();
    const runtime = runtimeRef.current;
    if (target === "marketsNews") switchAppView(runtime, "marketsNews");
    if (target === "screener") switchAppView(runtime, "screener");
    if (
      ["chart", "chartToolbar", "chartCanvas", "drawingTools", "rightPanel", "rightPanelOverview", "watchlist", "watchlistList", "orderBook", "recentTrades", "ai"].includes(target)
    ) {
      runtime.setView?.("charts");
    }
    if (target === "rightPanel" || target === "rightPanelOverview") {
      openPanelTarget(runtime, "overview");
    }
    if (target === "watchlist" || target === "watchlistList") {
      openPanelTarget(runtime, "watchlist");
    }
    if (target === "orderBook" || target === "recentTrades" || target === "ai") {
      openPanelTarget(runtime, target as PanelTarget);
    }
    if (target === "settings" || target === "account") runtime.openSettings?.();
  }, [captureUiSnapshot]);

  const executeAction = useCallback(async (call: AiActionCall) => {
    const args = call.arguments || {};
    const runtime = runtimeRef.current;
    const done = (ok: boolean, detail: string) => {
      recordAction(call, detail);
      return { ok, detail };
    };

    // Build a dispatch context for the modular handlers. Handlers do the
    // real work; this function just routes + records.
    const handler = getActionHandler(call.name);
    if (!handler) {
      return done(false, `unsupported action: ${call.name}`);
    }
    try {
      const dispatchContext: import("@/features/ai/actions/handlers").ActionDispatchContext = {
        runtime: runtime as unknown as import("@/features/ai/actions/handlers").ActionDispatchContext["runtime"],
        setHighlight: ((highlight) => setHighlight(highlight as HighlightState | null)) as import("@/features/ai/actions/handlers").ActionDispatchContext["setHighlight"],
        showSection: (target) => showSection(target),
        captureUiSnapshot: () => captureUiSnapshot(),
        restoreUiState: () => restoreUiState(),
        args,
        fetchHistoricalCandles: async (
          symbol: string,
          startMs: number,
          endMs: number,
          limit: number,
          timeframe: string,
        ) => {
          const candles = await fetchHistoricalCandles(symbol, startMs, endMs, limit, timeframe);
          return candles as unknown as Array<Record<string, unknown>>;
        },
      };
      const detail = await handler(dispatchContext);
      // NOTE: We deliberately do NOT call `setHighlight` from the success
      // breadcrumb anymore. The highlight overlay is a full-screen dim
      // (z-[680]) — using it to flash a "what just happened" message
      // would dim the whole UI and mask the very step overlay the
      // breadcrumb was meant to complement. The action log in the
      // AI Action debug window already records every action; that's
      // the right place for a breadcrumb.
      return done(detail.startsWith("success"), detail);
    } catch (error) {
      return done(false, `error: ${sanitizeTechnicalDetails(error || "unknown")}`);
    }
  }, [captureUiSnapshot, recordAction, restoreUiState, showSection]);

  useEffect(() => {
    const openDebug = () => setDebugOpen(true);
    const captureUi = () => captureUiSnapshot();
    const restoreUi = () => restoreUiState();
    window.addEventListener("lmview:open-ai-action-debug", openDebug);
    window.addEventListener("lmview:ai-tour-capture-ui", captureUi);
    window.addEventListener("lmview:ai-tour-restore-ui", restoreUi);
    const clearHighlights = () => setHighlight(null);
    const onTourStart = () => {
      // Capture the pre-tour UI state so the user can revert after the
      // tour finishes. We do this on tour START (not on first step)
      // so the banner doesn't flash mid-tour.
      captureUiSnapshot();
    };
    const onTourEnd = () => {
      clearHighlights();
      // Show the restore banner ONLY after the tour ends, if a
      // snapshot was captured. This replaces the old behaviour of
      // flashing the banner on every highlight_section step.
      if (uiSnapshotRef.current) {
        setRestoreAvailable(true);
      }
    };
    window.addEventListener("lmview:ai-clear-highlights", clearHighlights);
    window.addEventListener("lmview:ai-tour-start", onTourStart);
    window.addEventListener("lmview:ai-tour-end", onTourEnd);
    return () => {
      window.removeEventListener("lmview:open-ai-action-debug", openDebug);
      window.removeEventListener("lmview:ai-tour-capture-ui", captureUi);
      window.removeEventListener("lmview:ai-tour-restore-ui", restoreUi);
      window.removeEventListener("lmview:ai-clear-highlights", clearHighlights);
      window.removeEventListener("lmview:ai-tour-start", onTourStart);
      window.removeEventListener("lmview:ai-tour-end", onTourEnd);
    };
  }, [captureUiSnapshot, restoreUiState]);

  // Static tour steps are deprecated. The Interact-mode tour planner
  // in useAiChat produces dynamic plans at runtime; the static
  // ``lmview-overview`` tour is still triggerable via the start_tour
  // action for the AI Action debug window.
  const activeHighlight = highlight;

  return (
    <AiActionContext.Provider
      value={{
        definitions,
        executeAction,
        openDebugWindow: () => setDebugOpen(true),
        setRuntime,
        actionLog,
        clearActionLog: () => {
          actionLogRef.current = [];
          setActionLog([]);
        },
      }}
    >
      {children}
      {restoreAvailable && (
        <RestoreUiBanner
          onRestore={restoreUiState}
          onDismiss={() => {
            uiSnapshotRef.current = null;
            setRestoreAvailable(false);
          }}
        />
      )}
      {activeHighlight && (
        <HighlightOverlay
          target={activeHighlight.target}
          label={activeHighlight.label}
          message={activeHighlight.message}
          includeChat={activeHighlight.includeChat}
          region={activeHighlight.region}
          onClose={() => setHighlight(null)}
        />
      )}
      {debugOpen && (
        <AiActionDebugWindow
          definitions={definitions}
          actionLog={actionLog}
          onClearLog={() => {
            actionLogRef.current = [];
            setActionLog([]);
          }}
          onRun={(call) => executeAction(call)}
          onClose={() => setDebugOpen(false)}
        />
      )}
    </AiActionContext.Provider>
  );
}

export function useAiActions(): AiActionContextValue {
  const context = useContext(AiActionContext);
  if (!context) {
    throw new Error("useAiActions must be used inside AiActionProvider");
  }
  return context;
}

function RestoreUiBanner({
  onRestore,
  onDismiss,
}: {
  onRestore: () => void;
  onDismiss: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="fixed bottom-5 left-1/2 z-[675] flex max-w-[calc(100vw-2rem)] -translate-x-1/2 flex-wrap items-center justify-center gap-2 rounded border border-sky-500/30 bg-gray-950 px-3 py-2 text-xs text-gray-100 shadow-2xl">
      <span className="text-gray-300">{t("aiChangedView")}</span>
      <button
        type="button"
        onClick={onRestore}
        className="rounded bg-blue-600 px-2.5 py-1 font-semibold text-white transition-colors hover:bg-blue-500"
      >
        {t("returnToPreviousView")}
      </button>
      <button
        type="button"
        onClick={onDismiss}
        className="rounded border border-gray-700 px-2.5 py-1 font-semibold text-gray-300 transition-colors hover:border-gray-500 hover:text-white"
      >
        {t("close")}
      </button>
    </div>
  );
}

function HighlightOverlay({
  target,
  label,
  message,
  includeChat = false,
  region,
  onClose,
}: {
  target: string;
  label?: string;
  message?: string;
  includeChat?: boolean;
  region?: ChartRegion;
  onClose: () => void;
}) {
  const [rects, setRects] = useState<DOMRect[]>([]);
  const selector = SECTION_SELECTORS[target] || target;
  // When a guided analysis is active, the step overlay is rendered
  // inside the AI panel (via a portal to body). We want the AI panel
  // to stay UN-dimmed so the user can still read the step text and
  // click Next/Finish. So we always add the AI panel rect to the
  // cutouts when a tour is running.
  const [tourActive, setTourActive] = useState(false);
  useEffect(() => {
    const onTourStart = () => setTourActive(true);
    const onTourEnd = () => setTourActive(false);
    window.addEventListener("lmview:ai-tour-start", onTourStart);
    window.addEventListener("lmview:ai-tour-end", onTourEnd);
    return () => {
      window.removeEventListener("lmview:ai-tour-start", onTourStart);
      window.removeEventListener("lmview:ai-tour-end", onTourEnd);
    };
  }, []);

  useEffect(() => {
    const update = () => {
      const targetEl = document.querySelector(selector);
      const targetRect = targetEl?.getBoundingClientRect();
      const primaryRect = targetRect && region
        ? rectFromRegion(targetRect, region)
        : targetRect;
      const aiEl = (includeChat || tourActive) ? document.querySelector(SECTION_SELECTORS.ai) : null;
      const menuRects = Array.from(document.querySelectorAll(".lm-menu-surface, [data-ai-highlight-hole='true']"))
        .map((element) => element.getBoundingClientRect());
      const next = [primaryRect, aiEl?.getBoundingClientRect(), ...menuRects]
        .filter((item): item is DOMRect => Boolean(item))
        .filter((rect) => rect.width > 0 && rect.height > 0);
      setRects(next);
    };
    update();
    const timer = window.setTimeout(update, 80);
    const interval = window.setInterval(update, 250);
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.clearTimeout(timer);
      window.clearInterval(interval);
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [includeChat, region, selector]);

  const cells = useMemo(() => dimCells(rects), [rects]);
  const primary = rects[0];

  return (
    <div className="pointer-events-none fixed inset-0 z-[680]">
      {cells.map((cell) => (
        <div
          key={cell.key}
          className="absolute bg-black/65 backdrop-blur-[1px]"
          style={{ left: cell.left, top: cell.top, width: cell.width, height: cell.height }}
        />
      ))}
      {rects.map((rect, index) => (
        <div
          key={`${rect.left}-${rect.top}-${index}`}
          className="absolute rounded border-2 border-sky-400 shadow-[0_0_0_1px_rgba(14,165,233,0.35)]"
          style={{
            left: rect.left - 4,
            top: rect.top - 4,
            width: rect.width + 8,
            height: rect.height + 8,
          }}
        />
      ))}
      {primary && (
        <div
          className="pointer-events-auto fixed max-w-xs rounded border border-sky-500/50 bg-gray-950 px-3 py-2 text-xs text-gray-100 shadow-2xl"
          style={primary.right > window.innerWidth - 360 ? { left: 16, bottom: 78 } : { right: 16, bottom: 78 }}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              {label && <div className="font-semibold text-white">{label}</div>}
              {message && <div className="mt-1 leading-5 text-gray-300">{message}</div>}
            </div>
            <button type="button" onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white">
              <X size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function dimCells(holes: DOMRect[]) {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const xs = [0, width];
  const ys = [0, height];
  holes.forEach((rect) => {
    xs.push(Math.max(0, rect.left - 6), Math.min(width, rect.right + 6));
    ys.push(Math.max(0, rect.top - 6), Math.min(height, rect.bottom + 6));
  });
  const sx = [...new Set(xs)].sort((a, b) => a - b);
  const sy = [...new Set(ys)].sort((a, b) => a - b);
  const cells: Array<{ key: string; left: number; top: number; width: number; height: number }> = [];
  for (let xi = 0; xi < sx.length - 1; xi += 1) {
    for (let yi = 0; yi < sy.length - 1; yi += 1) {
      const left = sx[xi];
      const right = sx[xi + 1];
      const top = sy[yi];
      const bottom = sy[yi + 1];
      const cx = (left + right) / 2;
      const cy = (top + bottom) / 2;
      const insideHole = holes.some((rect) => cx >= rect.left - 6 && cx <= rect.right + 6 && cy >= rect.top - 6 && cy <= rect.bottom + 6);
      if (!insideHole) cells.push({ key: `${xi}-${yi}`, left, top, width: right - left, height: bottom - top });
    }
  }
  return cells;
}

function rectFromRegion(base: DOMRect, region: ChartRegion): DOMRect {
  const left = base.left + (base.width * clampPercent(region.leftPct)) / 100;
  const top = base.top + (base.height * clampPercent(region.topPct)) / 100;
  const width = (base.width * clampPercent(region.widthPct)) / 100;
  const height = (base.height * clampPercent(region.heightPct)) / 100;
  return new DOMRect(left, top, width, height);
}

function AiActionDebugWindow({
  definitions,
  actionLog,
  onClearLog,
  onRun,
  onClose,
}: {
  definitions: AiActionDefinition[];
  actionLog: Array<{ call: AiActionCall; at: number; detail: string }>;
  onClearLog: () => void;
  onRun: (call: AiActionCall) => Promise<{ ok: boolean; detail: string }>;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const [selected, setSelected] = useState("");
  const [params, setParams] = useState<Record<string, string>>({});
  const [result, setResult] = useState("");
  const [running, setRunning] = useState(false);
  const [pos, setPos] = useState({ x: 80, y: 80 });
  const dragRef = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  const definition = definitions.find((item) => item.name === selected) || null;

  const run = async () => {
    if (!definition) {
      setResult(`error: ${t("chooseFunction")}`);
      return;
    }
    setRunning(true);
    try {
      const parsed = parseParams(definition, params);
      const output = await onRun({ name: definition.name, arguments: parsed });
      setResult(`${output.ok ? "success" : "error"}: ${output.detail}`);
    } catch (error) {
      setResult(`error: ${sanitizeTechnicalDetails(error || "unknown")}`);
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    const onMove = (event: MouseEvent) => {
      if (!dragRef.current) return;
      setPos({
        x: dragRef.current.ox + event.clientX - dragRef.current.x,
        y: dragRef.current.oy + event.clientY - dragRef.current.y,
      });
    };
    const onUp = () => {
      dragRef.current = null;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  return (
    <div className="fixed z-[720] w-[min(460px,92vw)] rounded border border-gray-700 bg-gray-950 text-gray-100 shadow-2xl" style={{ left: pos.x, top: pos.y }}>
      <div
        className="flex cursor-move items-center justify-between border-b border-gray-800 px-3 py-2"
        onMouseDown={(event) => {
          dragRef.current = { x: event.clientX, y: event.clientY, ox: pos.x, oy: pos.y };
        }}
      >
        <div className="flex items-center gap-2 text-xs font-semibold"><Move size={14} /> {t("aiActionDebug")}</div>
        <button type="button" onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white"><X size={14} /></button>
      </div>
      <div className="space-y-3 p-3">
        <label className="block text-xs text-gray-400">
          {t("functionCall")}
          <select
            value={selected}
            onChange={(event) => {
              setSelected(event.target.value);
              setParams({});
              setResult("");
            }}
            className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-xs text-white"
          >
            <option value="">{t("chooseFunction")}</option>
            {definitions.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}
          </select>
        </label>
        <div className="grid gap-2">
          {definition ? Object.entries(definition.parameters.properties).map(([key, schema]) => (
            <label key={key} className="block text-xs text-gray-400">
              {key}{definition.parameters.required?.includes(key) ? " *" : ""}
              {schema.description && <span className="ml-1 text-[10px] text-gray-600">{schema.description}</span>}
              {schema.enum ? (
                <select
                  value={params[key] ?? String(schema.default ?? "")}
                  onChange={(event) => setParams((draft) => ({ ...draft, [key]: event.target.value }))}
                  className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-xs text-white"
                >
                  <option value="">{t("chooseValue")}</option>
                  {schema.enum.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              ) : key === "points" ? (
                <div className="mt-1 space-y-1">
                  <textarea
                    value={params[key] ?? ""}
                    onChange={(event) => setParams((draft) => ({ ...draft, [key]: event.target.value }))}
                    className="h-20 w-full resize-none rounded border border-gray-700 bg-gray-900 px-2 py-1.5 font-mono text-xs text-white"
                    placeholder='[{"time": 1717200000, "price": 67500}, {"time": 1717203600, "price": 68100}]'
                  />
                  <div className="flex flex-wrap gap-1">
                    <button
                      type="button"
                      onClick={() => setParams((draft) => ({ ...draft, [key]: '[{"time":1717200000,"price":67500},{"time":1717203600,"price":68100}]' }))}
                      className="rounded border border-gray-700 px-1.5 py-0.5 text-[10px] text-gray-300"
                    >
                      time/price
                    </button>
                  </div>
                </div>
              ) : (
                <input
                  value={params[key] ?? String(schema.default ?? "")}
                  onChange={(event) => setParams((draft) => ({ ...draft, [key]: event.target.value }))}
                  className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-xs text-white"
                  placeholder={schema.type === "array" || schema.type === "object" ? "JSON" : schema.type}
                />
              )}
            </label>
          )) : (
            <div className="rounded border border-gray-800 bg-gray-900 px-2 py-3 text-xs text-gray-500">
              {t("chooseFunction")}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={run} disabled={running} className="inline-flex items-center gap-2 rounded bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-60">
            <Play size={13} /> {t("run")}
          </button>
          <button type="button" onClick={() => { setParams({}); setResult(""); }} className="rounded border border-gray-700 px-2.5 py-1.5 text-xs text-gray-200">
            {t("reset")}
          </button>
        </div>
        <div className="min-h-8 rounded border border-gray-800 bg-gray-900 px-2 py-1.5 text-xs text-gray-300">
          {result || t("debugNoResult")}
        </div>
        {/* Action log — shows everything that's been executed */}
        <div className="mt-2 border-t border-gray-800 pt-2">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">
              {t("actionLogTitle")} ({actionLog.length})
            </span>
            <button
              type="button"
              onClick={onClearLog}
              className="rounded px-1.5 py-0.5 text-[10px] text-gray-500 hover:bg-gray-800 hover:text-gray-200"
            >
              Clear
            </button>
          </div>
          <div className="max-h-40 overflow-y-auto rounded border border-gray-800 bg-gray-900/50 text-[10px] font-mono">
            {actionLog.length === 0 ? (
              <div className="px-2 py-1.5 text-gray-600">{t("actionLogEmpty")}</div>
            ) : (
              actionLog.slice(-20).reverse().map((entry, idx) => (
                <div key={`${entry.at}-${idx}`} className="border-b border-gray-800/50 px-2 py-1 last:border-b-0">
                  <div className="flex items-center gap-2 text-gray-400">
                    <span className="text-gray-600">{new Date(entry.at).toLocaleTimeString()}</span>
                    <span className="font-semibold text-amber-300">{entry.call.name}</span>
                    {entry.call.reason && (
                      <span className="truncate text-gray-500" title={entry.call.reason}>
                        {String(entry.call.reason)}
                      </span>
                    )}
                  </div>
                  <div className="ml-1 mt-0.5 truncate text-gray-500" title={entry.detail}>
                    {entry.detail}
                  </div>
                  {entry.call.arguments && Object.keys(entry.call.arguments).length > 0 && (
                    <div className="ml-1 mt-0.5 truncate text-gray-600" title={JSON.stringify(entry.call.arguments)}>
                      {JSON.stringify(entry.call.arguments)}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function parseParams(definition: AiActionDefinition, params: Record<string, string>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, schema] of Object.entries(definition.parameters.properties)) {
    const raw = params[key] ?? schema.default;
    if (raw === undefined || raw === "") continue;
    if (schema.type === "number" || schema.type === "integer") out[key] = Number(raw);
    else if (schema.type === "boolean") out[key] = String(raw) === "true";
    else if (schema.type === "array" || schema.type === "object") out[key] = typeof raw === "string" ? JSON.parse(raw || (schema.type === "array" ? "[]" : "{}")) : raw;
    else out[key] = String(raw);
  }
  for (const key of definition.parameters.required || []) {
    if (out[key] === undefined) throw new Error(`${key} required`);
  }
  return out;
}

export function buildIndicatorSettingsPatch(
  settings: Record<string, IndicatorSettings>,
  indicator: string,
  visible: boolean,
) {
  return {
    ...settings,
    [indicator]: {
      ...settings[indicator],
      visible,
    },
  };
}
