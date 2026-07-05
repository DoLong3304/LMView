/**
 * AiAssistantPanel — main AI chat container (full rewrite Phase D).
 *
 * Orchestrates chat state, tour lifecycle, error handling.
 * Delegates rendering to: AiChatMessage, AiChatInput, ThinkingIndicator,
 *                          InteractBoard, DisclaimerSection.
 *
 * Key behaviors:
 * - Suggested prompts appear ONLY when user is typing (handled by AiChatInput)
 * - Errors revert question back to input field instead of saving as response
 * - Unsent input cached in localStorage
 * - Old sessions without new-format metadata are handled gracefully
 * - Admin badges show debug info
 * - Chart freeze indicator during Interact mode
 * - InteractBoard draggable popup for step control
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  CircleDot,
  MoreHorizontal,
  Newspaper,
  Plus,
  Shield,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";
import { useAiActions } from "@/features/ai/actions/AiActionProvider";
import { useAiChat } from "@/features/ai/hooks/useAiChat";
import { useI18n } from "@/i18n";
import { AiChatMessage } from "@/features/ai/components/AiChatMessage";
import { AiChatInput } from "@/features/ai/components/AiChatInput";
import { ThinkingIndicator } from "@/features/ai/components/ThinkingIndicator";
import { InteractBoard } from "@/features/ai/components/InteractBoard";
import type { WalkthroughStep } from "@/features/ai/types";
import { normalizeTourSteps } from "@/features/ai/types";
import type { ChartContextForAi } from "@/features/ai/types";
import type { AiMessage } from "@/features/ai/types";
import type { Candle, IndicatorSettings } from "@/types";
import { calcSupportResistance } from "@/features/chart/indicatorUtils";
import {
  calcSMA,
  calcEMA,
  calcRSI,
  calcMACD,
  calcBollingerBands,
} from "@/features/chart/indicatorUtils";

// ── Props ─────────────────────────────────────────────────────────────────

interface AiAssistantPanelProps {
  selectedSymbol: string;
  timeframe: string;
  candles?: Candle[];
  selectedIndicators?: string[];
  exchange?: string;
  onOpenSettings?: () => void;
  indSettings?: Record<string, IndicatorSettings>;
}

// ── Component ──────────────────────────────────────────────────────────────

const AiAssistantPanel: React.FC<AiAssistantPanelProps> = ({
  selectedSymbol,
  timeframe,
  candles = [],
  selectedIndicators = [],
  exchange = "binance",
  onOpenSettings,
  indSettings,
}) => {
  const { t, lang } = useI18n();
  const { user } = useAuth();
  const { executeAction } = useAiActions();
  const {
    messages,
    loading,
    error,
    mode,
    setMode,
    sendMessage,
    clearChat,
    activeTour,
    setActiveTour,
    liveMessageIdsRef: _liveMessageIdsRef,
  } = useAiChat();
  const [inputValue, setInputValue] = useState("");
  const [lastError, setLastError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isAdmin = user?.role === "admin";

  // Track if we've had at least one assistant response (controls skeleton)

  // ── Error handling ────────────────────────────────────────────────────
  // Errors from useAiChat — revert question to input field,
  // clear error so it doesn't appear as a message bubble.
  const lastSentRef = useRef<string>("");

  useEffect(() => {
    if (error && !lastError) {
      setLastError(error);
      // Restore the sent text to input so user can retry
      if (lastSentRef.current) {
        setInputValue(lastSentRef.current);
        lastSentRef.current = "";
      }
    }
  }, [error, lastError]);

  const handleClearError = useCallback(() => {
    setLastError(null);
  }, []);

  // ── Tour lifecycle ────────────────────────────────────────────────────
  const [tourRunning, setTourRunning] = useState(false);
  const lastTourPlanRef = useRef<{
    tour_id: string;
    title: string;
    summary: string;
    steps: WalkthroughStep[];
  } | null>(null);
  const autoExecutedStepRef = useRef<Set<string>>(new Set());
  /** Track which message ID started a tour, so we don't re-trigger after completion */
  const autoStartedTourMsgRef = useRef<string | null>(null);

  const shouldExecuteTourAction = useCallback((action: { type?: string; name?: string }) => {
    const name = action.type || action.name;
    // Full app navigation can unmount AI panel mid-tour, hiding the
    // controller while chart remains frozen/input-disabled. Keep the
    // explanation visible; user can navigate manually after finishing.
    return name !== "switch_app_view";
  }, []);

  const shouldReplayTourAction = useCallback((action: { type?: string; name?: string }) => {
    const name = action.type || action.name || "";
    // Re-apply idempotent/context actions when user navigates Prev/Next.
    // Do not replay drawings or add_indicator: those are persistent and
    // would duplicate visual state or toolbar side effects.
    return (
      name.startsWith("highlight") ||
      [
        "view_section",
        "open_panel",
        "switch_panel_tab",
        "navigate_tab",
        "set_timeframe",
        "toggle_timeframe",
        "set_visible_range",
        "scroll_chart",
        "scroll_chart_to_time",
      ].includes(name)
    );
  }, []);

  const executeTourActions = useCallback((
    actions: Array<{ type?: string; name?: string; params?: Record<string, unknown> }>,
    stepIndex: number,
    replayOnly = false,
  ) => {
    for (const action of actions) {
      const actionName = action.type || action.name;
      if (!actionName) continue;
      if (!shouldExecuteTourAction(action)) continue;
      if (replayOnly && !shouldReplayTourAction(action)) continue;
      void executeAction({
        name: actionName,
        arguments: action.params || {},
        reason: `tour:${activeTour?.plan.title || "Tour"} step ${stepIndex + 1}`,
      });
    }
  }, [activeTour?.plan.title, executeAction, shouldExecuteTourAction, shouldReplayTourAction]);

  // Auto-start tour when Interact mode response has tour_plan
  useEffect(() => {
    if (mode !== "interact") return;
    if (tourRunning) return;
    const latest = messages[messages.length - 1];
    if (!latest || latest.role !== "assistant") return;
    if (!latest.tour_plan || !latest.tour_plan.steps?.length) return;
    if (!latest.id) return;
    // Don't re-trigger the same message's tour after completion (resets tourRunning)
    if (autoStartedTourMsgRef.current === latest.id) return;

    const plan = latest.tour_plan;
    const normalizedSteps = normalizeTourSteps(plan.steps as any);
    const normalizedPlan = {
      tour_id: plan.tour_id || `tour_${Date.now()}`,
      title: plan.title || "Guided Analysis",
      summary: plan.summary || "",
      steps: normalizedSteps,
    };
    lastTourPlanRef.current = {
      tour_id: normalizedPlan.tour_id,
      title: normalizedPlan.title,
      summary: normalizedPlan.summary,
      steps: normalizedPlan.steps,
    };
    autoExecutedStepRef.current = new Set();
    autoStartedTourMsgRef.current = latest.id;
    setActiveTour({ plan: normalizedPlan, currentStep: 0, active: true });
    setTourRunning(true);
    window.dispatchEvent(
      new CustomEvent("lmview:chart-freeze", { detail: { frozen: true } }),
    );
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-capture-ui"));
  }, [messages, mode, tourRunning, setActiveTour]);

  // Tour navigation
  const tourNextStep = useCallback(() => {
    if (!activeTour || !activeTour.active) return;
    const nextIdx = activeTour.currentStep + 1;
    if (nextIdx >= activeTour.plan.steps.length) {
      // Tour complete — keep autoStartedTourMsgRef so same msg won't re-trigger
      setActiveTour(null);
      setTourRunning(false);
      window.dispatchEvent(
        new CustomEvent("lmview:chart-freeze", { detail: { frozen: false } }),
      );
      window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));
      window.dispatchEvent(
        new CustomEvent("lmview:ai-tour-complete", {
          detail: {
            summary: activeTour.plan.summary,
            actions: activeTour.plan.steps,
          },
        }),
      );
      // Also emit tour-end so AiActionProvider can clear overlays and
      // expose the restore-UI banner after normal completion, not only
      // after manual cancel.
      window.dispatchEvent(new CustomEvent("lmview:ai-tour-end"));
      window.dispatchEvent(
        new CustomEvent("lmview:right-panel-top-tab", {
          detail: { tab: "aiHelper" },
        }),
      );
      return;
    }
    setActiveTour({ ...activeTour, currentStep: nextIdx });

    // ── Step reset: always clear sensitive actions (highlights/annotations) ──
    // before applying the next step's. Persistent actions (drawings,
    // indicators, timeframe) are NOT cleared — they accumulate across steps.
    window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));

    // Auto-execute all actions in the step
    const step = activeTour.plan.steps[nextIdx];
    const actions = (step as any).actions || [{ type: (step as any).action_type, params: (step as any).params || {} }];
    const key = `${activeTour.plan.tour_id}-${nextIdx}`;
    if (!autoExecutedStepRef.current.has(key)) {
      autoExecutedStepRef.current.add(key);
      executeTourActions(actions, nextIdx, false);
    } else {
      executeTourActions(actions, nextIdx, true);
    }
  }, [activeTour, setActiveTour, executeTourActions]);

  const tourPrevStep = useCallback(() => {
    if (!activeTour || !activeTour.active) return;
    const prevIdx = Math.max(0, activeTour.currentStep - 1);
    setActiveTour({ ...activeTour, currentStep: prevIdx });
    window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));
    const step = activeTour.plan.steps[prevIdx];
    const actions = (step as any).actions || [{ type: (step as any).action_type, params: (step as any).params || {} }];
    executeTourActions(actions, prevIdx, true);
  }, [activeTour, setActiveTour, executeTourActions]);

  const cancelTour = useCallback(() => {
    setActiveTour(null);
    setTourRunning(false);
    autoExecutedStepRef.current = new Set();
    window.dispatchEvent(
      new CustomEvent("lmview:chart-freeze", { detail: { frozen: false } }),
    );
    window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-end"));
    window.dispatchEvent(
      new CustomEvent("lmview:right-panel-top-tab", {
        detail: { tab: "aiHelper" },
      }),
    );
  }, [setActiveTour]);

  const handleKeep = useCallback(() => {
    // User chose to keep effects — just end tour
    cancelTour();
  }, [cancelTour]);

  const handleRevert = useCallback(() => {
    // User chose to revert — restore UI first, then end tour
    window.dispatchEvent(
      new CustomEvent("lmview:ai-tour-restore-ui"),
    );
    cancelTour();
  }, [cancelTour]);

  // Make Cancel button also revert by default
  const cancelWithRevert = useCallback(() => {
    handleRevert();
  }, [handleRevert]);

  // Auto-execute first step actions on tour start
  useEffect(() => {
    if (!activeTour || !activeTour.active) return;
    const step = activeTour.plan.steps[activeTour.currentStep];
    if (!step) return;
    const key = `${activeTour.plan.tour_id}-${activeTour.currentStep}`;
    if (autoExecutedStepRef.current.has(key)) return;
    autoExecutedStepRef.current.add(key);
    const actions = (step as any).actions || [{ type: (step as any).action_type, params: (step as any).params || {} }];
    executeTourActions(actions, activeTour.currentStep, false);
  }, [activeTour, executeTourActions]);

  // ── Auto-scroll ───────────────────────────────────────────────────────
  const lastMsgIdRef = useRef<string | null>(null);
  useEffect(() => {
    const last = messages[messages.length - 1];
    const lastId = last?.id || null;
    if (lastId !== lastMsgIdRef.current) {
      lastMsgIdRef.current = lastId;
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // ── Chart context ─────────────────────────────────────────────────────
  const chartContext: ChartContextForAi = useMemo(() => {
    const lastCandle = candles[candles.length - 1];
    const recentCandles = candles.slice(-20).map((c) => ({
      time: c.time ?? 0,
      open: c.open ?? 0,
      high: c.high ?? 0,
      low: c.low ?? 0,
      close: c.close ?? 0,
      volume: c.volume ?? 0,
    }));
    const lastPoint = <T extends { time: number; value: number }>(
      arr: T[],
    ): number | null =>
      arr.length > 0 ? arr[arr.length - 1].value : null;

    const indicatorValues: Array<{
      name: string;
      value: number | null;
      signal: string | null;
      params: Record<string, unknown>;
    }> = [];

    const safeNumber = (n: number | null | undefined): number | null =>
      typeof n === "number" && Number.isFinite(n) ? n : null;

    const classifyRsi = (v: number): "oversold" | "overbought" | "neutral" => {
      if (v <= 30) return "oversold";
      if (v >= 70) return "overbought";
      return "neutral";
    };

    const pushIndicator = (
      name: string,
      value: number | null,
      signal: string | null,
      cfg: IndicatorSettings | undefined,
    ) => {
      if (!cfg?.visible) return;
      indicatorValues.push({
        name,
        value: safeNumber(value),
        signal,
        params: cfg ? { ...cfg } : ({} as Record<string, unknown>),
      });
    };

    if (indSettings?.sma20?.visible) {
      const period = Number(indSettings.sma20.period ?? 20);
      const arr = candles.length >= period ? calcSMA(candles, period) : [];
      pushIndicator("sma20", lastPoint(arr), null, indSettings.sma20);
    }
    if (indSettings?.sma50?.visible) {
      const period = Number(indSettings.sma50.period ?? 50);
      const arr = candles.length >= period ? calcSMA(candles, period) : [];
      pushIndicator("sma50", lastPoint(arr), null, indSettings.sma50);
    }
    if (indSettings?.ema12?.visible) {
      const period = Number(indSettings.ema12.period ?? 12);
      const arr = candles.length >= period ? calcEMA(candles, period) : [];
      pushIndicator("ema12", lastPoint(arr), null, indSettings.ema12);
    }
    if (indSettings?.ema26?.visible) {
      const period = Number(indSettings.ema26.period ?? 26);
      const arr = candles.length >= period ? calcEMA(candles, period) : [];
      pushIndicator("ema26", lastPoint(arr), null, indSettings.ema26);
    }
    if (indSettings?.rsi?.visible) {
      const period = Number(indSettings.rsi.period ?? 14);
      const arr = candles.length > period ? calcRSI(candles, period) : [];
      const v = lastPoint(arr);
      pushIndicator(
        "rsi",
        v,
        v != null ? classifyRsi(v) : null,
        indSettings.rsi,
      );
    }
    if (indSettings?.bb?.visible) {
      const period = Number(indSettings.bb.period ?? 20);
      const bands =
        candles.length >= period
          ? calcBollingerBands(candles, period)
          : null;
      pushIndicator(
        "bb_upper",
        bands ? lastPoint(bands.upper) : null,
        null,
        indSettings.bb,
      );
      pushIndicator(
        "bb_middle",
        bands ? lastPoint(bands.middle) : null,
        null,
        indSettings.bb,
      );
      pushIndicator(
        "bb_lower",
        bands ? lastPoint(bands.lower) : null,
        null,
        indSettings.bb,
      );
    }
    if (indSettings?.macd?.visible) {
      const fast = Number(indSettings.macd.fast ?? 12);
      const slow = Number(indSettings.macd.slow ?? 26);
      const signalPeriod = Number(indSettings.macd.signal ?? 9);
      const m =
        candles.length >= slow
          ? calcMACD(candles, fast, slow, signalPeriod)
          : null;
      const macdLast = m ? lastPoint(m.macd) : null;
      const signalLast = m ? lastPoint(m.signal) : null;
      pushIndicator("macd", macdLast, null, indSettings.macd);
      pushIndicator("macd_signal", signalLast, null, indSettings.macd);
      pushIndicator(
        "macd_histogram",
        m ? lastPoint(m.histogram) : null,
        macdLast != null && signalLast != null
          ? macdLast > signalLast
            ? "bullish_crossover"
            : "bearish_crossover"
          : null,
        indSettings.macd,
      );
    }
    if (indSettings?.support_resistance?.visible && candles.length >= 10) {
      const srLevels = calcSupportResistance(
        candles,
        Number(indSettings.support_resistance.lookback ?? 50),
      );
      for (const level of srLevels) {
        indicatorValues.push({
          name: `sr_${level.type}`,
          value: level.price,
          signal: level.type,
          params: { label: level.label },
        });
      }
    }

    return {
      symbol: selectedSymbol,
      exchange,
      timeframe,
      chart_type: "candles",
      selected_indicators: selectedIndicators,
      recent_candles: recentCandles.length > 0 ? recentCandles : undefined,
      indicator_values:
        indicatorValues.length > 0 ? indicatorValues : undefined,
      latest_candle: lastCandle
        ? {
            open_time: lastCandle.time ? lastCandle.time * 1000 : undefined,
            open: lastCandle.open,
            high: lastCandle.high,
            low: lastCandle.low,
            close: lastCandle.close,
            volume: lastCandle.volume,
          }
        : null,
      frontend_context_version: "3.0.1",
      language: lang,
      user_timezone:
        user?.timezone ||
        Intl.DateTimeFormat().resolvedOptions().timeZone ||
        undefined,
    };
  }, [
    selectedSymbol,
    exchange,
    timeframe,
    selectedIndicators,
    candles,
    indSettings,
    lang,
    user?.timezone,
  ]);

  // ── Send handler ──────────────────────────────────────────────────────
  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (!trimmed || loading) return;
    lastSentRef.current = trimmed;
    setInputValue("");
    setLastError(null);

    // Cancel active tour if user sends new message
    if (activeTour?.active) {
      setActiveTour(null);
      setTourRunning(false);
      autoExecutedStepRef.current = new Set();
      autoStartedTourMsgRef.current = null;
      window.dispatchEvent(
        new CustomEvent("lmview:chart-freeze", {
          detail: { frozen: false },
        }),
      );
      window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));
    }

    void sendMessage(trimmed, chartContext);
  }, [inputValue, loading, activeTour, sendMessage, chartContext, setActiveTour]);

  // ── Replay tour ───────────────────────────────────────────────────────
  const replayTour = useCallback(() => {
    const plan = lastTourPlanRef.current;
    if (!plan) return;
    autoExecutedStepRef.current = new Set();
    setActiveTour({
      plan: {
        tour_id: plan.tour_id,
        title: plan.title,
        summary: plan.summary,
        steps: plan.steps,
      },
      currentStep: 0,
      active: true,
    });
    setTourRunning(true);
    window.dispatchEvent(
      new CustomEvent("lmview:chart-freeze", {
        detail: { frozen: true },
      }),
    );
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-capture-ui"));
  }, [setActiveTour]);

  // ── Intro message ─────────────────────────────────────────────────────
  const introMessage = t("lmviewHelpReadyMessage")
    .replace("{symbol}", selectedSymbol)
    .replace("{timeframe}", timeframe.toUpperCase());

  // Prepend intro to messages
  const allMessages = useMemo(
    () => [
      { id: "intro", role: "assistant" as const, content: introMessage, mode: "ask" as const },
      ...messages,
    ],
    [introMessage, messages],
  );

  // ── Model badge for last assistant message ────────────────────────────
  const lastAssistantMsg = useMemo(
    () => [...messages].reverse().find((m) => m.role === "assistant"),
    [messages],
  );

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <div
      data-ai-section="ai-panel"
      className="relative flex min-h-0 flex-1 flex-col bg-gray-900"
    >
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="border-b border-gray-800 bg-gray-850 px-3 py-2.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded bg-blue-500/10 text-blue-300">
              <Sparkles size={15} />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold text-white">
                {t("lmviewAi")}
              </h2>
              <p className="truncate text-[11px] text-gray-500">
                {t("assistantWorkspace")}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={clearChat}
              className="flex h-7 w-7 items-center justify-center rounded text-gray-400 hover:bg-gray-800 hover:text-white"
              title={t("newChat")}
            >
              <Plus size={14} />
            </button>
            <button
              type="button"
              onClick={onOpenSettings}
              className="flex h-7 w-7 items-center justify-center rounded text-gray-400 hover:bg-gray-800 hover:text-white"
              title={t("assistantOptions")}
            >
              <MoreHorizontal size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* ── Chart Context bar ───────────────────────────────────────── */}
      <div className="border-b border-gray-800 bg-gray-900 px-3 py-2">
        <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          <CircleDot size={10} /> {t("chartContext")}
        </div>
        <div className="flex flex-wrap gap-1.5">
          <span className="rounded border border-gray-700 bg-gray-850 px-2 py-1 text-[10px] font-medium text-gray-300">
            {selectedSymbol}
          </span>
          <span className="rounded border border-gray-700 bg-gray-850 px-2 py-1 text-[10px] font-medium text-gray-300">
            {timeframe.toUpperCase()}
          </span>
          <span
            className={`rounded border px-2 py-1 text-[10px] font-medium ${
              mode === "ask"
                ? "border-blue-500/30 bg-blue-500/10 text-blue-300"
                : "border-amber-500/30 bg-amber-500/10 text-amber-300"
            }`}
          >
            {mode === "ask" ? t("askMode") : t("interactMode")}
          </span>
          {selectedIndicators.length > 0 && (
            <span className="rounded border border-gray-700 bg-gray-850 px-2 py-1 text-[10px] font-medium text-gray-300">
              {selectedIndicators.length} {t("indicators")}
            </span>
          )}
        </div>

        {/* Model badge */}
        {lastAssistantMsg &&
          (lastAssistantMsg.model_name || lastAssistantMsg.provider) && (
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              {lastAssistantMsg.model_name && (
                <span
                  className="inline-flex items-center gap-1 rounded border border-purple-500/30 bg-purple-500/10 px-1.5 py-0.5 text-[9px] font-medium text-purple-300"
                  title={lastAssistantMsg.model_name}
                >
                  <Bot size={9} />
                  {lastAssistantMsg.model_name.replace("openai/", "")}
                </span>
              )}
              {isAdmin && lastAssistantMsg.provider && (
                <span className="inline-flex items-center gap-1 rounded border border-gray-600 bg-gray-800 px-1.5 py-0.5 text-[9px] font-medium text-gray-400">
                  {lastAssistantMsg.provider}
                </span>
              )}
              {isAdmin && lastAssistantMsg.provider_metadata && (
                <span className="inline-flex items-center gap-1 rounded border border-gray-600 bg-gray-800 px-1.5 py-0.5 text-[9px] font-medium text-gray-400">
                  {String(
                    (lastAssistantMsg.provider_metadata as Record<string, unknown>)
                      .latency_ms || "?",
                  )}
                  ms
                </span>
              )}
            </div>
          )}

        {/* Context quality chips */}
        {lastAssistantMsg &&
          (lastAssistantMsg.news_context || lastAssistantMsg.confidence != null) && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {lastAssistantMsg.news_context &&
                lastAssistantMsg.news_context.article_count > 0 && (
                  <span className="inline-flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-medium text-emerald-300">
                    <Newspaper size={9} />
                    {lastAssistantMsg.news_context.article_count}{" "}
                    {t("aiContextArticles")}
                  </span>
                )}
              {lastAssistantMsg.confidence != null && (
                <span
                  className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] font-medium ${
                    lastAssistantMsg.confidence >= 0.7
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                      : lastAssistantMsg.confidence >= 0.4
                        ? "border-blue-500/30 bg-blue-500/10 text-blue-300"
                        : "border-amber-500/30 bg-amber-500/10 text-amber-300"
                  }`}
                >
                  <Shield size={9} />
                  {(lastAssistantMsg.confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
          )}
      </div>

      {/* ── Chart freeze note during Interact ──────────────────────── */}
      {tourRunning && (
        <div className="flex items-center gap-2 border-b border-amber-500/20 bg-amber-500/5 px-3 py-1.5">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
          <span className="text-[10px] font-medium text-amber-300">
            Walkthrough in progress — chart frozen
          </span>
        </div>
      )}

      {/* ── Walkthrough interaction blocker ──────────────────────────
        Full-screen overlay during walkthrough. Absorbs all clicks outside
        the InteractBoard (z-[9999]) and other permitted elements.
        The chat panel itself also stays clickable for the Replay button. */}
      {tourRunning && (
        <div
          className="fixed inset-0 z-[600] cursor-not-allowed"
          data-testid="walkthrough-blocker"
        />
      )}

      {/* ── Messages ───────────────────────────────────────────────── */}
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-3">
          {/* Error banner (not saved as message) */}
          {lastError && (
            <div className="rounded border border-red-500/25 bg-red-500/10 px-3 py-2 text-[11px] leading-5 text-red-200">
              {lastError}
            </div>
          )}

          {/* Message list */}
          {allMessages.map((message) => {
            const isUser = message.role === "user";
            const isPlaceholder = !!(
              message as AiMessage & { _placeholder?: boolean }
            )._placeholder;

            // Skip empty streaming placeholders — ThinkingIndicator handles the visual
            if (!isUser && !message.content && message.provider === "streaming") {
              return null;
            }

            // Placeholder during tour — use ThinkingIndicator instead
            if (isPlaceholder) {
              return (
                <div key={message.id}>
                  <ThinkingIndicator active={true} />
                </div>
              );
            }

            return (
              <AiChatMessage
                key={message.id}
                message={message as AiMessage}
                isUser={isUser}
                assistantLabel={
                  message.role === "assistant" ? t("assistantName") : t("you")
                }
                isAdmin={isAdmin}
                mode={mode}
                tourRunning={tourRunning}
                onReplayTour={replayTour}
                onRate={(mid, rating) => {
                  // Rate — uses the existing service
                  import("@/services/aiService")
                    .then((m) => m.rateMessage(mid, rating))
                    .catch(() => {});
                }}
              />
            );
          })}

          {/* Thinking indicator (not first-skeleton anymore — animated facts) */}
          {loading && <ThinkingIndicator active={true} />}

          <div ref={messagesEndRef} />
        </div>

        {/* ── Input area ───────────────────────────────────────────── */}
        <div className="border-t border-gray-800 bg-gray-850 p-2.5">
          <AiChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            mode={mode}
            onModeChange={setMode}
            loading={loading}
            disabled={tourRunning}
            placeholder={t("aiHelperPlaceholder").replace(
              "{symbol}",
              selectedSymbol,
            )}
            focusKey={messages.length}
            symbol={selectedSymbol}
            timeframe={timeframe}
            error={lastError}
            onClearError={handleClearError}
            messageHistory={messages
              .filter((m) => m.role === "user" && m.content.trim())
              .map((m) => m.content)
              .reverse()}
          />
        </div>
      </div>

      {/* ── Interact Board (overlay) ───────────────────────────────── */}
      {activeTour?.active && activeTour.plan.steps[activeTour.currentStep] && (
        <InteractBoard
          plan={{
            tour_id: activeTour.plan.tour_id,
            title: activeTour.plan.title,
            steps: (activeTour.plan.steps as WalkthroughStep[]).map((s) => ({
              explanation: s.explanation,
              actions: s.actions,
              keep_effects: s.keep_effects,
              chart_freeze: s.chart_freeze,
            })),
            summary: activeTour.plan.summary,
          }}
          currentStep={activeTour.currentStep}
          totalSteps={activeTour.plan.steps.length}
          onNext={tourNextStep}
          onPrev={tourPrevStep}
          onCancel={cancelWithRevert}
          onKeep={handleKeep}
          onRevert={handleRevert}
        />
      )}

      {/* ── CSS ────────────────────────────────────────────────────── */}
      <style>{`
        .ai-md { overflow-wrap: anywhere; }
        .ai-md p { margin: 0 0 .5rem; }
        .ai-md p:last-child { margin-bottom: 0; }
        .ai-md em { font-style: italic; }
        .ai-md strong { font-weight: 700; color: inherit; }
        .ai-md ul { list-style: disc; padding-left: 1rem; margin: .35rem 0; }
        .ai-md ol { list-style: decimal; padding-left: 1rem; margin: .35rem 0; }
        .ai-md hr { border: 0; border-top: 1px solid rgb(55 65 81); margin: .75rem 0; }
        .ai-md code { background: rgb(3 7 18); color: rgb(191 219 254); border-radius: 4px; padding: 0 .25rem; font-size: 11px; }
        .ai-md pre { overflow-x: auto; background: rgb(3 7 18); border: 1px solid rgb(55 65 81); border-radius: 6px; padding: .5rem; margin: .5rem 0; }
        .ai-md pre code { background: transparent; padding: 0; color: rgb(229 231 235); }
        .ai-md table { display: block; width: 100%; overflow-x: auto; border-collapse: collapse; margin: .5rem 0; }
        .ai-md th, .ai-md td { border: 1px solid rgb(55 65 81); padding: .25rem .4rem; text-align: left; }
        .ai-md th { background: rgb(31 41 55); color: white; }
        .ai-md a { color: rgb(147 197 253); text-decoration: underline; }
      `}</style>
    </div>
  );
};

export default AiAssistantPanel;
