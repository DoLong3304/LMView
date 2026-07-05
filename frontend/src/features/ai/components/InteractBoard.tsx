/**
 * InteractBoard — draggable popup controlling the pace of Interact mode analysis.
 *
 * Phase E: Supports multi-action steps (multiple simultaneous actions per step).
 * Displays:
 * - Progress meter (step X of N + percentage)
 * - Explanation with WHY/WHAT/LOOKFOR reasoning
 * - Action chips for each action in the step
 * - Navigation buttons (back / next / finish)
 *
 * Drag handle at top. Rendered via portal to body so it floats over everything.
 * Disappears when the final step completes.
 */
import React, { useCallback, useRef, useState } from "react";
import { createPortal } from "react-dom";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import {
  ChevronLeft,
  ChevronRight,
  GripVertical,
  Sparkles,
  Eye,
  MousePointerClick,
  Paintbrush,
  ArrowUpDown,
  ZoomIn,
  PanelRight,
  ScrollText,
  Timer,
  Hash,
  Pencil,
  Trash2,
  Layout,
} from "lucide-react";
import { useI18n } from "@/i18n";

// ── Action type icons ───────────────────────────────────────────────────────

const ACTION_ICONS: Record<string, React.ReactNode> = {
  add_indicator: <Eye size={12} />,
  remove_indicator: <Trash2 size={12} />,
  toggle_indicator: <Eye size={12} />,
  draw_tool: <Paintbrush size={12} />,
  draw_trendline: <Pencil size={12} />,
  create_annotation: <Pencil size={12} />,
  highlight_section: <Layout size={12} />,
  highlight_region: <Hash size={12} />,
  highlight_area: <Hash size={12} />,
  highlight_candle: <Hash size={12} />,
  highlight_indicator: <Eye size={12} />,
  highlight_candles: <Hash size={12} />,
  highlight_contextual_zone: <Hash size={12} />,
  set_timeframe: <Timer size={12} />,
  set_chart_type: <Layout size={12} />,
  set_symbol: <ArrowUpDown size={12} />,
  zoom_chart: <ZoomIn size={12} />,
  scroll_chart: <ScrollText size={12} />,
  open_panel: <PanelRight size={12} />,
  switch_panel_tab: <PanelRight size={12} />,
  switch_app_view: <Layout size={12} />,
  clear_drawings: <Trash2 size={12} />,
  clear_ai_annotations: <Trash2 size={12} />,
  fetch_historical_prices: <Timer size={12} />,
  export_chart: <Layout size={12} />,
  reset_chart_view: <Layout size={12} />,
  scroll_chart_to_time: <ScrollText size={12} />,
  enter_replay: <Timer size={12} />,
  open_news_popup: <PanelRight size={12} />,
  navigate_tab: <MousePointerClick size={12} />,
};

function iconForAction(type: string): React.ReactNode {
  return ACTION_ICONS[type] || <MousePointerClick size={12} />;
}

function labelForActionType(type: string): string {
  const labels: Record<string, string> = {
    add_indicator: "actAddIndicator",
    remove_indicator: "actRemoveIndicator",
    toggle_indicator: "actToggleIndicator",
    toggle_timeframe: "actToggleTimeframe",
    toggle_chart: "actToggleChart",
    toggle_market: "actToggleMarket",
    pause_live_stream: "actPauseLiveStream",
    resume_live_stream: "actResumeLiveStream",
    set_visible_range: "actSetVisibleRange",
    move_resize_chart: "actMoveResizeChart",
    replay_chart: "actReplayChart",
    add_note: "actAddNote",
    capture_chart_snapshot: "actCaptureChartSnapshot",
    view_section: "actViewSection",
    draw_tool: "actDrawTool",
    draw_trendline: "actDrawTrendline",
    create_annotation: "actCreateAnnotation",
    highlight_section: "actHighlightSection",
    highlight_region: "actHighlightRegion",
    highlight_area: "actHighlightArea",
    highlight_candle: "actHighlightCandle",
    highlight_indicator: "actHighlightIndicator",
    highlight_candles: "actHighlightCandles",
    highlight_contextual_zone: "actHighlightContextualZone",
    set_timeframe: "actSetTimeframe",
    set_chart_type: "actSetChartType",
    set_symbol: "actSetSymbol",
    zoom_chart: "actZoomChart",
    scroll_chart: "actScrollChart",
    open_panel: "actOpenPanel",
    switch_panel_tab: "actSwitchPanelTab",
    switch_app_view: "actSwitchAppView",
    clear_drawings: "actClearDrawings",
    clear_ai_annotations: "actClearAiAnnotations",
    fetch_historical_prices: "actFetchHistoricalPrices",
    export_chart: "actExportChart",
    reset_chart_view: "actResetChartView",
    scroll_chart_to_time: "actScrollChartToTime",
    enter_replay: "actEnterReplay",
    open_news_popup: "actOpenNewsPopup",
    navigate_tab: "actNavigateTab",
  };
  return labels[type] || type;
}

// ── Types ─────────────────────────────────────────────────────────────────

export interface InteractBoardAction {
  type: string;
  params?: Record<string, unknown>;
  requires_approval?: boolean;
}

export interface InteractBoardStep {
  explanation: string;
  actions: InteractBoardAction[];
  keep_effects?: boolean;
  chart_freeze?: boolean;
}

export interface InteractBoardPlan {
  tour_id: string;
  title: string;
  steps: InteractBoardStep[];
  summary?: string;
}

interface InteractBoardProps {
  plan: InteractBoardPlan;
  currentStep: number;
  totalSteps: number;
  onNext: () => void;
  onPrev: () => void;
  onCancel: () => void;
  /** User chose to keep chart effects (final step only) */
  onKeep?: () => void;
  /** User chose to revert chart effects (final step only) */
  onRevert?: () => void;
}

// ── Component ──────────────────────────────────────────────────────────────

const InteractBoard: React.FC<InteractBoardProps> = ({
  plan,
  currentStep,
  totalSteps,
  onNext,
  onPrev,
  onCancel,
  onKeep,
  onRevert,
}) => {
  const { t } = useI18n();
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const dragRef = useRef<{
    px: number; py: number;
    bx: number; by: number;
  } | null>(null);
  const isLastStep = currentStep >= totalSteps - 1;
  const step = plan.steps[currentStep];
  const progressPct = totalSteps > 0
    ? Math.round(((currentStep + 1) / totalSteps) * 100)
    : 0;

  const actions = step?.actions || [];
  const keepEffects = step?.keep_effects !== false;

  const onDragStart = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    dragRef.current = {
      px: e.clientX, py: e.clientY,
      bx: pos?.x ?? 0, by: pos?.y ?? 0,
    };
  }, [pos]);

  const onDragMove = useCallback((e: React.PointerEvent) => {
    const d = dragRef.current;
    if (!d) return;
    setPos({
      x: d.bx + (e.clientX - d.px),
      y: d.by + (e.clientY - d.py),
    });
  }, []);

  const onDragEnd = useCallback((e: React.PointerEvent) => {
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
    dragRef.current = null;
  }, []);

  const boardStyle: React.CSSProperties = pos
    ? { top: Math.max(8, pos.y), left: Math.max(8, pos.x), right: "auto" }
    : { top: "88px", left: "50%", transform: "translateX(-50%)" };

  const node = (
    <div
      className="fixed z-[9999] w-[min(480px,calc(100vw-32px))] rounded-xl border border-amber-500/30 bg-gray-900/95 p-4 shadow-2xl backdrop-blur-md"
      data-testid="interact-board"
      style={boardStyle}
    >
      {/* Drag handle header */}
      <div
        onPointerDown={onDragStart}
        onPointerMove={onDragMove}
        onPointerUp={onDragEnd}
        onPointerCancel={onDragEnd}
        className="-mx-4 -mt-4 mb-3 flex cursor-move select-none items-center justify-between rounded-t-xl border-b border-amber-500/15 bg-amber-500/[0.06] px-4 py-2 active:cursor-grabbing"
      >
        <div className="flex items-center gap-2">
          <GripVertical size={14} className="text-amber-300/60" />
          <span className="flex items-center gap-1.5 text-xs font-bold text-amber-200">
            <Sparkles size={13} className="text-amber-300" />
            {plan.title || t("walkthroughTitle") || "Guided Analysis"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] tabular-nums text-amber-300/60">
            {currentStep + 1}/{totalSteps}
          </span>
          <span className="text-[9px] text-amber-300/40">{progressPct}%</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-3 h-1 overflow-hidden rounded-full bg-gray-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-400 transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Action chips — show all actions in this step */}
      {actions.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {actions.map((a, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/8 px-2 py-0.5 text-[10px] font-medium text-amber-200"
            >
              {iconForAction(a.type)}
              {t(labelForActionType(a.type) as any) || labelForActionType(a.type)}
            </span>
          ))}
          {!keepEffects && (
            <span className="inline-flex items-center gap-1 rounded-full border border-gray-600/30 bg-gray-700/30 px-2 py-0.5 text-[10px] text-gray-400">
              {t("walkthroughResetAction") || "Reset"}
            </span>
          )}
        </div>
      )}

      {/* Explanation — same markdown rendering as AiChatMessage */}
      <div className="mb-3 rounded-lg border border-gray-800 bg-gray-850/80 p-3">
        <div className="prose prose-invert prose-sm max-w-none text-[12px] leading-relaxed text-gray-200 [&_h3]:mb-1 [&_h3]:mt-2 [&_h3]:text-sm [&_h3]:font-bold [&_h3]:text-amber-200 [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_li]:mb-0.5 [&_strong]:text-amber-200 [&_code]:rounded [&_code]:bg-gray-800 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[11px] [&_code]:text-amber-300">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeSanitize]}
            components={{
              code: ({ className, children, ...props }) => {
                const isInline = !className;
                if (isInline) {
                  return <strong className="text-amber-300">{children}</strong>;
                }
                return <code className={className} {...props}>{children}</code>;
              },
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer" className="text-amber-400 underline">{children}</a>
              ),
            }}
          >
            {(step?.explanation || "").replace(/\\n/g, "\n")}
          </ReactMarkdown>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded bg-gray-800 px-2.5 py-1.5 text-[10px] font-semibold text-gray-400 hover:bg-gray-700 hover:text-white"
        >
          {t("cancel") || "Cancel"}
        </button>

        {isLastStep && (onKeep || onRevert) ? (
          <div className="flex items-center gap-2">
            <span className="text-[9px] text-gray-500">
              {t("tourFinalChoiceLabel") || "Did the analysis help?"}
            </span>
            <button
              type="button"
              onClick={onRevert}
              className="flex items-center gap-1 rounded bg-red-600 px-2.5 py-1.5 text-[10px] font-semibold text-white hover:bg-red-500"
              data-testid="interact-board-revert"
            >
              {t("tourRevert") || "Revert"}
            </button>
            <button
              type="button"
              onClick={onKeep}
              className="flex items-center gap-1 rounded border border-gray-600 px-2.5 py-1.5 text-[10px] font-semibold text-gray-300 hover:bg-gray-700"
              data-testid="interact-board-keep"
            >
              {t("tourKeep") || "Keep"}
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            {currentStep > 0 && (
              <button
                type="button"
                onClick={onPrev}
                className="flex items-center gap-1 rounded bg-gray-800 px-2.5 py-1.5 text-[10px] font-semibold text-gray-300 hover:bg-gray-700"
                data-testid="interact-board-prev"
              >
                <ChevronLeft size={11} />
                {t("previous") || "Back"}
              </button>
            )}
            <button
              type="button"
              onClick={onNext}
              className={`flex items-center gap-1 rounded px-3 py-1.5 text-[10px] font-semibold ${
                isLastStep
                  ? "bg-emerald-600 text-white hover:bg-emerald-500"
                  : "bg-amber-600 text-white hover:bg-amber-500"
              }`}
              data-testid="interact-board-next"
            >
              {isLastStep ? (t("finish") || "Finish") : (t("next") || "Next")}
              <ChevronRight size={11} />
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(node, document.body);
};

export { InteractBoard };
export type { InteractBoardProps };
