import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Move, Play, RotateCcw, X } from "lucide-react";
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

interface TourSnapshot {
  timeframe?: TimeframeKey;
  selectedSymbol?: string;
  chartType?: ChartType;
  currentView?: AppView;
  rightPanelOpen?: boolean;
  rightPanelTopTab?: RightPanelTopTab;
  rightPanelTab?: RightPanelTab;
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

interface TourStep {
  target: string;
  label: string;
  message: string;
  includeChat?: boolean;
  region?: ChartRegion;
  action?: AiActionCall;
  pauseForUser?: boolean;
  task?: "change_timeframe";
}

interface AiActionContextValue {
  definitions: AiActionDefinition[];
  executeAction: (call: AiActionCall) => Promise<{ ok: boolean; detail: string }>;
  openDebugWindow: () => void;
  setRuntime: (runtime: Partial<AiActionRuntime>) => void;
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

function parseDrawingDataPoints(points: unknown[]): Drawing["dataPoints"] | null {
  const parsed = points.map((point) => {
    if (!point || typeof point !== "object") return null;
    const candidate = point as Record<string, unknown>;
    const time = Number(candidate.time);
    const price = Number(candidate.price);
    if (!Number.isFinite(time) || !Number.isFinite(price)) return null;
    return { time, price };
  });
  if (parsed.some((point) => point === null)) return null;
  return parsed as Drawing["dataPoints"];
}

function panelTargetToSection(target: PanelTarget): string {
  if (target === "ai") return "ai";
  if (target === "overview") return "rightPanelOverview";
  return target;
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
  if (view === "charts") return;
  runtime.setRightPanelOpen?.(false);
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
      name: "set_market",
      description: "Switch selected market symbol.",
      parameters: {
        type: "object",
        properties: { symbol: { type: "string", default: "BTCUSDT" } },
        required: ["symbol"],
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
      name: "start_tour",
      description: "Start a user-paced LMView tour.",
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
  const { t } = useI18n();
  const definitions = useMemo(actionDefinitions, []);
  const runtimeRef = useRef<AiActionRuntime>({});
  const [debugOpen, setDebugOpen] = useState(false);
  const [highlight, setHighlight] = useState<HighlightState | null>(null);
  const [tourIndex, setTourIndex] = useState<number | null>(null);
  const [tourDone, setTourDone] = useState(false);
  const [tourBaseline, setTourBaseline] = useState<{ timeframe?: TimeframeKey } | null>(null);
  const [actionLog, setActionLog] = useState<Array<{ call: AiActionCall; at: number; detail: string }>>([]);
  const actionLogRef = useRef<Array<{ call: AiActionCall; at: number; detail: string }>>([]);
  const tourSnapshotRef = useRef<TourSnapshot | null>(null);
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
    setRestoreAvailable(true);
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

    // Try handler registry first (Batch 10 modular handlers)
    const handler = getActionHandler(call.name);
    if (handler) {
      const detail = await handler(call, (msg) => setHighlight({ target: "debug", message: msg }));
      return done(true, detail);
    }

    // Fallback to inline handlers for LMView-specific UI actions
    switch (call.name) {
      case "add_indicator":
        runtime.chartController?.setIndicatorVisible(String(args.indicator), true);
        return done(true, `Added indicator ${String(args.indicator)}`);
      case "remove_indicator":
        runtime.chartController?.setIndicatorVisible(String(args.indicator), false);
        return done(true, `Removed indicator ${String(args.indicator)}`);
      case "toggle_indicator":
        runtime.chartController?.toggleIndicator(String(args.indicator));
        return done(true, `Toggled indicator ${String(args.indicator)}`);
      case "draw_tool": {
        const tool = String(args.tool || "cursor");
        runtime.setDrawingTool?.(tool);
        const points = Array.isArray(args.points) ? args.points : [];
        if (points.length && runtime.addDrawing) {
          const dataPoints = parseDrawingDataPoints(points);
          if (!dataPoints) {
            return done(false, 'Drawing points must be [{"time": unixSeconds, "price": value}].');
          }
          runtime.addDrawing({
            id: `ai-${Date.now()}`,
            tool,
            dataPoints,
            text: typeof args.text === "string" ? args.text : undefined,
            settings: { color: "#38bdf8", lineWidth: 2 },
          });
          runtime.setDrawingTool?.("cursor");
          return done(true, `Placed ${tool} drawing`);
        }
        return done(true, `Selected drawing tool ${tool}`);
      }
      case "highlight_section":
        showSection(String(args.target || "chart"));
        setHighlight({
          target: String(args.target || "chart"),
          label: typeof args.label === "string" ? args.label : undefined,
          message: typeof args.message === "string" ? args.message : undefined,
          includeChat: args.include_chat === true || String(args.target || "") === "ai",
        });
        return done(true, `Highlighted ${String(args.target || "chart")}`);
      case "highlight_chart_area": {
        showSection("chart");
        setHighlight({
          target: "chartCanvas",
          label: typeof args.label === "string" ? args.label : "Chart area",
          message: typeof args.message === "string" ? args.message : undefined,
          region: {
            leftPct: clampPercent(Number(args.left_pct ?? 20)),
            topPct: clampPercent(Number(args.top_pct ?? 20)),
            widthPct: clampPercent(Number(args.width_pct ?? 40)),
            heightPct: clampPercent(Number(args.height_pct ?? 30)),
          },
        });
        return done(true, "Highlighted chart area");
      }
      case "highlight_candles": {
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
        return done(true, "Highlighted candle range");
      }
      case "set_chart_type": {
        const chartType = String(args.chart_type || "candles") as ChartType;
        runtime.setChartType?.(chartType);
        showSection("chartToolbar");
        return done(true, `Changed chart type to ${chartType}`);
      }
      case "set_timeframe": {
        const timeframe = String(args.timeframe || "1h") as TimeframeKey;
        runtime.setTimeframe?.(timeframe);
        showSection("chartToolbar");
        return done(true, `Changed timeframe to ${timeframe}`);
      }
      case "set_market": {
        const symbol = String(args.symbol || "BTCUSDT").toUpperCase();
        runtime.setSymbol?.(symbol);
        showSection("chartToolbar");
        return done(true, `Changed market to ${symbol}`);
      }
      case "open_panel": {
        const target = PANEL_TARGETS.includes(String(args.target) as PanelTarget)
          ? String(args.target) as PanelTarget
          : "overview";
        captureUiSnapshot();
        openPanelTarget(runtime, target);
        if (args.highlight !== false) {
          setHighlight({
            target: panelTargetToSection(target),
            label: typeof args.label === "string" ? args.label : undefined,
            message: typeof args.message === "string" ? args.message : undefined,
            includeChat: target === "ai",
          });
        }
        return done(true, `Opened ${target} panel`);
      }
      case "close_panel": {
        captureUiSnapshot();
        runtime.setRightPanelOpen?.(false);
        return done(true, "Closed right panel");
      }
      case "switch_panel_tab": {
        const tab = String(args.tab || "watchlist") as RightPanelTab;
        if (!["watchlist", "orderBook", "recentTrades"].includes(tab)) {
          return done(false, `Unsupported right-panel tab: ${String(args.tab)}`);
        }
        captureUiSnapshot();
        openPanelTarget(runtime, tab);
        if (args.highlight !== false) {
          setHighlight({ target: panelTargetToSection(tab), label: tab });
        }
        return done(true, `Switched right panel to ${tab}`);
      }
      case "switch_app_view": {
        const view = String(args.view || "charts") as AppView;
        if (!APP_VIEWS.includes(view)) {
          return done(false, `Unsupported app view: ${String(args.view)}`);
        }
        captureUiSnapshot();
        switchAppView(runtime, view);
        if (args.highlight !== false) {
          setHighlight({
            target: view === "marketsNews" ? "marketsNews" : view === "screener" ? "screener" : "chart",
            label: view,
          });
        }
        return done(true, `Switched app view to ${view}`);
      }
      case "view_section": {
        const target = String(args.target || "chart");
        showSection(target);
        setHighlight({ target, label: target });
        return done(true, `Opened ${target}`);
      }
      case "restore_ui_state":
        restoreUiState();
        return done(true, "Restored previous UI state");
      case "zoom_chart": {
        const direction = String(args.direction || "in") === "out" ? "out" : "in";
        runtime.chartController?.zoomChart(direction, Number(args.anchor_ratio ?? 0.5));
        return done(true, `Zoomed chart ${direction}`);
      }
      case "scroll_chart": {
        const target = String(args.target || "end") as "start" | "end" | "left" | "right";
        const bars = Number(args.bars ?? 20);
        runtime.chartController?.scrollChart(target === "left" || target === "right" ? (target === "left" ? -Math.abs(bars) : Math.abs(bars)) : target);
        return done(true, `Scrolled chart ${target}`);
      }
      case "fetch_historical_prices": {
        const symbol = String(args.symbol || runtime.selectedSymbol || "BTCUSDT").toUpperCase();
        const timeframe = String(args.timeframe || runtime.currentTimeframe || "1h");
        if (timeframe === "1s") {
          return done(false, "1s historical candles are not supported. Use live mode or choose 1m+.");
        }
        const candles = await fetchHistoricalCandles(
          symbol,
          Number(args.start_ms),
          Number(args.end_ms),
          Number(args.limit ?? 100),
          timeframe,
        );
        return done(true, `Fetched ${candles.length} historical ${timeframe} candles for ${symbol}`);
      }
      case "start_tour":
        tourSnapshotRef.current = {
          timeframe: runtime.currentTimeframe,
          selectedSymbol: runtime.selectedSymbol,
          chartType: runtime.chartType,
          currentView: runtime.currentView,
          rightPanelOpen: runtime.rightPanelOpen,
          rightPanelTopTab: runtime.rightPanelTopTab,
          rightPanelTab: runtime.rightPanelTab,
        };
        actionLogRef.current = [];
        setActionLog([]);
        setTourBaseline({ timeframe: runtime.currentTimeframe });
        setTourDone(false);
        setTourIndex(Number(args.start_step || 0));
        return done(true, "Started tour");
      case "clear_ai_annotations":
        setHighlight(null);
        setTourIndex(null);
        setTourDone(false);
        return done(true, "Cleared AI annotations");
      default:
        return done(false, `Unsupported action: ${call.name}`);
    }
  }, [captureUiSnapshot, recordAction, restoreUiState, showSection]);

  useEffect(() => {
    const openDebug = () => setDebugOpen(true);
    window.addEventListener("lmview:open-ai-action-debug", openDebug);
    return () => window.removeEventListener("lmview:open-ai-action-debug", openDebug);
  }, []);

  const tourSteps = useMemo<TourStep[]>(
    () => [
      { target: "app", label: t("tourOverallTitle"), message: t("tourOverallBody") },
      { target: "chartCanvas", label: t("tourChartTitle"), message: t("tourChartBody") },
      { target: "chartToolbar", label: t("tourMarketTitle"), message: t("tourMarketBody"), pauseForUser: true },
      { target: "chartToolbar", label: t("tourTimeframeTitle"), message: t("tourTimeframeBody"), pauseForUser: true, task: "change_timeframe" },
      { target: "chartToolbar", label: t("tourChartTypeTitle"), message: t("tourChartTypeBody") },
      { target: "chartToolbar", label: t("tourHistoricalTitle"), message: t("tourHistoricalBody") },
      { target: "drawingTools", label: t("tourDrawingTitle"), message: t("tourDrawingBody"), action: { name: "draw_tool", arguments: { tool: "rectangle" } }, pauseForUser: true },
      { target: "chartCanvas", label: t("tourRectangleTitle"), message: t("tourRectangleBody"), region: { leftPct: 24, topPct: 28, widthPct: 36, heightPct: 28 } },
      { target: "chartToolbar", label: t("tourIndicatorsTitle"), message: t("tourIndicatorsBody") },
      { target: "chartCanvas", label: t("tourZoomTitle"), message: t("tourZoomBody") },
      { target: "rightPanelOverview", label: t("tourRightPanelTitle"), message: t("tourRightPanelBody") },
      { target: "watchlistList", label: t("tourWatchlistTitle"), message: t("tourWatchlistBody"), action: { name: "open_panel", arguments: { target: "watchlist", highlight: false } } },
      { target: "orderBook", label: t("tourOrderBookTitle"), message: t("tourOrderBookBody"), action: { name: "switch_panel_tab", arguments: { tab: "orderBook", highlight: false } } },
      { target: "recentTrades", label: t("tourTradesTitle"), message: t("tourTradesBody"), action: { name: "switch_panel_tab", arguments: { tab: "recentTrades", highlight: false } } },
      { target: "marketsNews", label: t("tourMarketsNewsTitle"), message: t("tourMarketsNewsBody"), action: { name: "switch_app_view", arguments: { view: "marketsNews", highlight: false } } },
      { target: "screener", label: t("tourScreenerTitle"), message: t("tourScreenerBody"), action: { name: "switch_app_view", arguments: { view: "screener", highlight: false } } },
      { target: "header", label: t("tourHeaderTitle"), message: t("tourHeaderBody") },
      { target: "settings", label: t("tourSettingsTitle"), message: t("tourSettingsBody"), action: { name: "view_section", arguments: { target: "settings" } } },
      { target: "ai", label: t("tourAiTitle"), message: t("tourAiBody"), includeChat: true },
    ],
    [t],
  );
  const activeTourStep = tourIndex !== null ? tourSteps[Math.min(tourIndex, tourSteps.length - 1)] : null;
  const activeHighlight = activeTourStep || highlight;

  const restoreTourState = useCallback(() => {
    const runtime = runtimeRef.current;
    const snapshot = tourSnapshotRef.current;
    if (snapshot?.selectedSymbol) runtime.setSymbol?.(snapshot.selectedSymbol);
    if (snapshot?.timeframe) runtime.setTimeframe?.(snapshot.timeframe);
    if (snapshot?.chartType) runtime.setChartType?.(snapshot.chartType);
    runtime.setDrawingTool?.("cursor");
    runtime.closeSettings?.();
    if (snapshot?.currentView) runtime.setView?.(snapshot.currentView);
    runtime.setRightPanelOpen?.(snapshot?.rightPanelOpen ?? true);
    if (snapshot?.rightPanelTopTab) runtime.setRightPanelTopTab?.(snapshot.rightPanelTopTab);
    if (snapshot?.rightPanelTab) runtime.setRightPanelTab?.(snapshot.rightPanelTab);
  }, []);

  function completeTour() {
    restoreTourState();
    setTourIndex(null);
    setHighlight(null);
    setTourDone(true);
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-complete", {
      detail: {
        summary: t("tourRecapBody"),
        actions: actionLogRef.current,
      },
    }));
  }

  useEffect(() => {
    if (tourIndex === null) return;
    const step = tourSteps[tourIndex];
    if (!step) return;
    showSection(step.target);
    if (step.action) {
      void executeAction(step.action);
    }
  }, [executeAction, showSection, tourIndex, tourSteps]);

  const isCurrentTourTaskComplete = useCallback(() => {
    const step = tourIndex === null ? null : tourSteps[tourIndex];
    if (!step?.task) return true;
    if (step.task === "change_timeframe") {
      return Boolean(tourBaseline?.timeframe && runtimeRef.current.currentTimeframe !== tourBaseline.timeframe);
    }
    return true;
  }, [tourBaseline?.timeframe, tourIndex, tourSteps]);

  return (
    <AiActionContext.Provider value={{ definitions, executeAction, openDebugWindow: () => setDebugOpen(true), setRuntime }}>
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
          onClose={() => {
            setHighlight(null);
            if (tourIndex !== null) {
              restoreTourState();
              setTourIndex(null);
            }
          }}
        />
      )}
      {tourIndex !== null && (
        <TourControls
          index={tourIndex}
          count={tourSteps.length}
          paused={Boolean(activeTourStep?.pauseForUser)}
          taskComplete={isCurrentTourTaskComplete()}
          onPrev={() => setTourIndex((value) => Math.max(0, (value || 0) - 1))}
          onNext={() => {
            if (tourIndex >= tourSteps.length - 1) completeTour();
            else setTourIndex(tourIndex + 1);
          }}
          onClose={() => {
            restoreTourState();
            setTourIndex(null);
            setHighlight(null);
          }}
        />
      )}
      {tourDone && (
        <TourRecap
          actionCount={actionLog.length}
          onReplay={() => {
            const runtime = runtimeRef.current;
            tourSnapshotRef.current = {
              timeframe: runtime.currentTimeframe,
              selectedSymbol: runtime.selectedSymbol,
              chartType: runtime.chartType,
              currentView: runtime.currentView,
              rightPanelOpen: runtime.rightPanelOpen,
              rightPanelTopTab: runtime.rightPanelTopTab,
              rightPanelTab: runtime.rightPanelTab,
            };
            actionLogRef.current = [];
            setActionLog([]);
            setTourBaseline({ timeframe: runtime.currentTimeframe });
            setTourDone(false);
            setTourIndex(0);
          }}
          onClose={() => setTourDone(false)}
        />
      )}
      {debugOpen && (
        <AiActionDebugWindow
          definitions={definitions}
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

  useEffect(() => {
    const update = () => {
      const targetEl = document.querySelector(selector);
      const targetRect = targetEl?.getBoundingClientRect();
      const primaryRect = targetRect && region
        ? rectFromRegion(targetRect, region)
        : targetRect;
      const aiEl = includeChat ? document.querySelector(SECTION_SELECTORS.ai) : null;
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

function TourControls({
  index,
  count,
  paused,
  taskComplete,
  onPrev,
  onNext,
  onClose,
}: {
  index: number;
  count: number;
  paused: boolean;
  taskComplete: boolean;
  onPrev: () => void;
  onNext: () => void;
  onClose: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="fixed bottom-5 left-1/2 z-[700] flex -translate-x-1/2 items-center gap-2 rounded border border-gray-700 bg-gray-950 px-3 py-2 shadow-2xl">
      <span className="text-xs text-gray-400">{index + 1} / {count}</span>
      <button type="button" onClick={onPrev} disabled={index === 0} className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-200 disabled:opacity-40">{t("previous")}</button>
      <button
        type="button"
        onClick={onNext}
        className={`rounded px-2 py-1 text-xs font-semibold text-white ${paused && !taskComplete ? "bg-amber-600" : "bg-blue-600"}`}
      >
        {index === count - 1 ? t("finish") : paused && !taskComplete ? t("skip") : t("next")}
      </button>
      <button type="button" onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white"><X size={14} /></button>
    </div>
  );
}

function TourRecap({ actionCount, onReplay, onClose }: { actionCount: number; onReplay: () => void; onClose: () => void }) {
  const { t } = useI18n();
  return (
    <div className="fixed bottom-5 right-5 z-[690] w-80 rounded border border-gray-700 bg-gray-950 p-3 text-sm text-gray-100 shadow-2xl">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-white">{t("tourRecapTitle")}</h3>
          <p className="mt-1 text-xs leading-5 text-gray-400">{t("tourRecapBody")}</p>
          <p className="mt-1 text-[11px] text-gray-500">{actionCount} {t("actionsSaved")}</p>
        </div>
        <button type="button" onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white"><X size={14} /></button>
      </div>
      <button type="button" onClick={onReplay} className="mt-3 inline-flex items-center gap-2 rounded bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white">
        <RotateCcw size={13} /> {t("replay")}
      </button>
    </div>
  );
}

function AiActionDebugWindow({
  definitions,
  onRun,
  onClose,
}: {
  definitions: AiActionDefinition[];
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
