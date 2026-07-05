/**
 * Action handler registry — maps action names to handler functions.
 *
 * Handlers receive a fully-populated dispatch context (runtime + UI
 * helpers) so they can perform real chart / UI side-effects. Returning a
 * string is still allowed for status messages; throwing an error will be
 * surfaced in the AI action debug log.
 */
import type { ChartType, TimeframeKey } from "@/types";

export type ActionResult = Promise<string> | string;

export interface ActionDispatchContext {
  runtime: {
    setDrawingTool?: (tool: string) => void;
    addDrawing?: (drawing: {
      id: string;
      tool: string;
      dataPoints: Array<{ time: number; price: number }>;
      text?: string;
      settings?: Record<string, unknown>;
    }) => void;
    clearDrawings?: () => void;
    setTimeframe?: (timeframe: TimeframeKey) => void;
    setSymbol?: (symbol: string) => void;
    setChartType?: (chartType: ChartType) => void;
    setView?: (view: string) => void;
    setRightPanelOpen?: (open: boolean) => void;
    setRightPanelTopTab?: (tab: string) => void;
    setRightPanelTab?: (tab: string) => void;
    openSettings?: () => void;
    closeSettings?: () => void;
    currentView?: string;
    rightPanelOpen?: boolean;
    rightPanelTopTab?: string;
    rightPanelTab?: string;
    currentTimeframe?: TimeframeKey;
    selectedSymbol?: string;
    chartType?: ChartType;
    chartController?: {
      setIndicatorVisible: (indicator: string, visible: boolean) => void;
      toggleIndicator: (indicator: string) => void;
      zoomChart: (direction: "in" | "out", anchorRatio?: number) => void;
      scrollChart: (target: "start" | "end" | "left" | "right" | number) => void;
      rangeToChartRegion: (args: Record<string, unknown>) => Record<string, number> | null;
    } | null;
  };
  setHighlight: (highlight: {
    target: string;
    label?: string;
    message?: string;
    includeChat?: boolean;
    region?: Record<string, number>;
  } | null) => void;
  showSection: (target: string) => void;
  captureUiSnapshot: () => void;
  restoreUiState: () => void;
  args: Record<string, unknown>;
  fetchHistoricalCandles: (
    symbol: string,
    startMs: number,
    endMs: number,
    limit: number,
    timeframe: string,
  ) => Promise<Array<Record<string, unknown>>>;
}

export type ActionHandler = (
  ctx: ActionDispatchContext,
) => ActionResult;

/**
 * Map of action name → handler. We use a plain object (not the generic
 * ``Record<string, ActionHandler>`` lookup) so the LLM-side tour planner
 * and the front-end dispatcher share the same source of truth.
 */
import { handleAddIndicator } from "./indicatorHandler";
import { handleDrawTool, handleCreateAnnotation, handleDrawHorizontalLine, handleDrawFib, handleDrawRectangle } from "./drawToolHandler";
import {
  handleHighlight,
  handleHighlightSection,
  handleHighlightChartArea,
  handleHighlightCandles,
  handleHighlightContextualZone,
} from "./highlightHandler";
import { handleSetTimeframe, handleSetChartType, handleSetSymbol } from "./chartTypeHandler";
import {
  handleOpenPanel,
  handleClosePanel,
  handleSwitchPanelTab,
  handleSwitchAppView,
  handleViewSection,
  handleOpenSettings,
  handleCloseSettings,
} from "./panelHandler";
import {
  handleZoomChart,
  handleScrollChart,
  handleResetChartView,
  handleScrollChartToTime,
} from "./navigationHandler";
import {
  handleRemoveIndicator,
  handleToggleIndicator,
  handleConfigureIndicator,
} from "./indicatorHandler";
import {
  handleClearDrawings,
  handleDeleteDrawing,
  handleSetDrawingColor,
} from "./drawingToolSettingsHandler";
import { handleFetchHistoricalPrices } from "./historicalHandler";
import { handleClearAiAnnotations, handleExportChart } from "./miscHandler";
import { handleStartTour, handleEndTour } from "./tourHandler";
import { handleOpenNewsPopup, handleNavigateTab, handleEnterReplay } from "./walkthroughHandler";

export const handlerRegistry: Record<string, ActionHandler> = {
  // Indicators
  add_indicator: handleAddIndicator,
  remove_indicator: handleRemoveIndicator,
  toggle_indicator: handleToggleIndicator,
  configure_indicator: handleConfigureIndicator,

  // Drawing tools
  draw_tool: handleDrawTool,
  draw_trendline: handleDrawTool,
  draw_horizontal_line: handleDrawHorizontalLine,
  draw_fib: handleDrawFib,
  draw_rectangle: handleDrawRectangle,
  create_annotation: handleCreateAnnotation,
  clear_drawings: handleClearDrawings,
  delete_drawing: handleDeleteDrawing,
  set_drawing_color: handleSetDrawingColor,

  // Highlights
  highlight: handleHighlight,
  highlight_region: handleHighlight,
  highlight_section: handleHighlightSection,
  highlight_chart_area: handleHighlightChartArea,
  highlight_candles: handleHighlightCandles,
  highlight_contextual_zone: handleHighlightContextualZone,

  // Chart core
  set_chart_type: handleSetChartType,
  set_timeframe: handleSetTimeframe,
  set_symbol: handleSetSymbol,

  // Panel + view
  open_panel: handleOpenPanel,
  close_panel: handleClosePanel,
  switch_panel_tab: handleSwitchPanelTab,
  switch_app_view: handleSwitchAppView,
  view_section: handleViewSection,
  open_settings: handleOpenSettings,
  close_settings: handleCloseSettings,

  // Chart navigation
  zoom_chart: handleZoomChart,
  scroll_chart: handleScrollChart,
  reset_chart_view: handleResetChartView,
  scroll_chart_to_time: handleScrollChartToTime,

  // Historical data
  fetch_historical_prices: handleFetchHistoricalPrices,

  // Walkthrough-specific
  open_news_popup: handleOpenNewsPopup,
  navigate_tab: handleNavigateTab,
  enter_replay: handleEnterReplay,

  // Tours + cleanup
  start_tour: handleStartTour,
  end_tour: handleEndTour,
  clear_ai_annotations: handleClearAiAnnotations,
  export_chart: handleExportChart,
};

export function getActionHandler(name: string): ActionHandler | undefined {
  return handlerRegistry[name];
}

export function getRegisteredActions(): string[] {
  return Object.keys(handlerRegistry);
}
