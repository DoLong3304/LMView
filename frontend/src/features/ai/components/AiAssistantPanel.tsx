import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import {
  AlertTriangle,
  Bot,
  BookOpen,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  CircleDot,
  CornerDownLeft,
  ExternalLink,
  GripVertical,
  Info,
  Loader2,
  MoreHorizontal,
  Newspaper,
  Plus,
  RotateCcw,
  Undo2,
  Check,
  Send,
  Shield,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  UserRound,
} from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";
import { useAiActions } from "@/features/ai/actions/AiActionProvider";
import { useAiChat } from "@/features/ai/hooks/useAiChat";
import { useI18n } from "@/i18n";
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

interface AiAssistantPanelProps {
  selectedSymbol: string;
  timeframe: string;
  candles?: Candle[];
  selectedIndicators?: string[];
  exchange?: string;
  onOpenSettings?: () => void;
  /** Optional indicator settings for richer AI context */
  indSettings?: Record<string, IndicatorSettings>;
}

function MarkdownContent({ content, compact = false }: { content: string; compact?: boolean }) {
  return (
    <div className={compact ? "ai-md ai-md-compact" : "ai-md"}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

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
    liveMessageIdsRef,
    setMessages,
    sessionId,
  } = useAiChat();
  const [inputValue, setInputValue] = useState("");
  // Suggested prompts visible until user sends their first message in the session.
  // Reloaded sessions with prior user messages also stay hidden.
  const [suggestionsOpen, setSuggestionsOpen] = useState(true);
  // actionResult captures the last auto-executed tool_call result.
  // It is logged to the dev console and kept for any future debug
  // panel; it is intentionally NOT surfaced as a banner to normal
  // users because action results frequently contain internal terms
  // like "error: unsupported X" which are not actionable for end-users.
  // The setter is referenced elsewhere; the value is intentionally
  // left unread for normal-user UX.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [actionResult, setActionResult] = useState("");
  void actionResult;
  const [tourRunning, setTourRunning] = useState(false);
  // Last completed/active tour plan kept in memory so the Replay button
  // can re-trigger the same analysis without needing a fresh LLM call.
  const lastTourPlanRef = useRef<{
    tour_id: string;
    title: string;
    summary: string;
    steps: Array<{
      action_type: string;
      params: Record<string, unknown>;
      explanation: string;
      target_selector?: string | null;
      requires_approval?: boolean;
    }>;
    chart_snapshot?: Record<string, unknown> | null;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const autoExecutedRef = useRef<Set<string>>(new Set());
  const autoExecutedStepRef = useRef<Set<string>>(new Set());
  // Tour step overlay: draggable. The header acts as the drag handle.
  // Position is in pixels relative to the AI panel's top-left so the
  // box can be moved out of the way of the highlighted chart region.
  const [overlayPos, setOverlayPos] = useState<{ x: number; y: number } | null>(null);
  const dragStartRef = useRef<{ pointerX: number; pointerY: number; baseX: number; baseY: number } | null>(null);
  // NB: tourRestorePromptOpen is a placeholder kept for legacy callers;
  // the restore-prompt UI itself is no longer rendered (the AI
  // automatically restores state via capture/restore events).
  const [_tourRestorePromptOpen, setTourRestorePromptOpen] = useState(false);
  const [debugOpen, setDebugOpen] = useState(false);
  const isAdmin = user?.role === "admin";

  // Rating handler
  const rateMessage = useCallback(async (messageId: string, rating: 1 | -1) => {
    try {
      const { rateMessage: apiRate } = await import("@/services/aiService");
      await apiRate(messageId, rating);
    } catch (err) {
      console.warn("Failed to rate message:", err);
    }
  }, []);

  const chartContext: ChartContextForAi = useMemo(() => {
    const lastCandle = candles[candles.length - 1];
    // Send last 20 candles as lightweight preview
    const recentCandles = candles.slice(-20).map(c => ({
      time: c.time ?? 0,
      open: c.open ?? 0,
      high: c.high ?? 0,
      low: c.low ?? 0,
      close: c.close ?? 0,
      volume: c.volume ?? 0,
    }));
    // Compute *actual* indicator values from the current candle series so
    // the backend experts can read real numbers (RSI, SMA, EMA, BB,
    // MACD, S/R levels). Previously the chart context only carried the
    // indicator *settings* (visible flag, period) but ``value`` was
    // always null, so the LLM received no real numbers for indicators.
    const lastPoint = <T extends { time: number; value: number }>(arr: T[]): number | null =>
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
        params: cfg ? { ...cfg } : {},
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
      const bands = candles.length >= period ? calcBollingerBands(candles, period) : null;
      pushIndicator("bb_upper", bands ? lastPoint(bands.upper) : null, null, indSettings.bb);
      pushIndicator("bb_middle", bands ? lastPoint(bands.middle) : null, null, indSettings.bb);
      pushIndicator("bb_lower", bands ? lastPoint(bands.lower) : null, null, indSettings.bb);
    }
    if (indSettings?.macd?.visible) {
      const fast = Number(indSettings.macd.fast ?? 12);
      const slow = Number(indSettings.macd.slow ?? 26);
      const signalPeriod = Number(indSettings.macd.signal ?? 9);
      const m = candles.length >= slow ? calcMACD(candles, fast, slow, signalPeriod) : null;
      const macdLast = m ? lastPoint(m.macd) : null;
      const signalLast = m ? lastPoint(m.signal) : null;
      const histLast = m ? lastPoint(m.histogram) : null;
      pushIndicator("macd", macdLast, null, indSettings.macd);
      pushIndicator("macd_signal", signalLast, null, indSettings.macd);
      pushIndicator(
        "macd_histogram",
        histLast,
        macdLast != null && signalLast != null
          ? macdLast > signalLast ? "bullish_crossover" : "bearish_crossover"
          : null,
        indSettings.macd,
      );
    }

    // Add S/R levels as computed values
    if (indSettings?.support_resistance?.visible && candles.length >= 10) {
      const srLevels = calcSupportResistance(candles, Number(indSettings.support_resistance.lookback ?? 50));
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
      indicator_values: indicatorValues.length > 0 ? indicatorValues : undefined,
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
    };
  }, [selectedSymbol, exchange, timeframe, selectedIndicators, candles, indSettings, lang]);

  // Only auto-scroll the chat when a *new* message arrives, not on every
  // re-render. The chat is anchored to the bottom only on incremental
  // updates so the user can scroll up freely when a tour is active.
  const lastMessageIdRef = useRef<string | null>(null);
  // Track suggestion visibility against message list changes. We key on
  // the *length* and last-message ID rather than the array reference so
  // that an unrelated re-render (chart tick, settings save, etc.) does
  // not collapse a dropdown the user has explicitly opened.
  const lastSuggestionsMessageKeyRef = useRef<string | null>(null);
  useEffect(() => {
    const last = messages[messages.length - 1];
    const lastId = last?.id || null;
    const key = `${messages.length}:${lastId ?? ""}`;
    if (key !== lastSuggestionsMessageKeyRef.current) {
      lastSuggestionsMessageKeyRef.current = key;
      if (messages.some((message) => message.role === "user")) {
        setSuggestionsOpen(false);
      } else {
        setSuggestionsOpen(true);
      }
    }
    if (lastId !== lastMessageIdRef.current) {
      lastMessageIdRef.current = lastId;
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Defensive: if a session is loaded that already contains user messages, keep
  // suggestions hidden (covers reload-from-DB case where the dependency above
  // may not fire on the first render pass).
  useEffect(() => {
    if (messages.some((message) => message.role === "user")) {
      setSuggestionsOpen(false);
    }
    // We intentionally do NOT depend on `messages` here — only on initial mount
    // — so user re-opening suggestions (if any future feature) is preserved.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (mode !== "interact") return;
    const latest = messages[messages.length - 1];
    if (!latest || latest.role !== "assistant" || !latest.tool_calls?.length) return;
    latest.tool_calls.forEach((call, index) => {
      const key = `${latest.id}-${index}`;
      if (autoExecutedRef.current.has(key) || call.requires_approval) return;
      autoExecutedRef.current.add(key);
      void executeAction({ name: call.name, arguments: call.arguments || {}, reason: call.reason }).then((result) => {
        // Only surface success results in the AI Action debug panel.
        // Errors (e.g. "error: unsupported drawing tool X") are
        // logged to the console for developers but never shown to
        // normal users — they would just see a confusing internal
        // error message.
        if (!result.detail?.startsWith("error:")) {
          setActionResult(result.detail);
        } else {
          console.warn("[AI Action] skipped unsupported action:", call.name, result.detail);
        }
      });
    });
  }, [executeAction, messages, mode]);

  // Capture the most recent tour_plan from messages so the Replay
  // button can re-run an analysis after the user reloads the session
  // or finishes a tour. Runs whenever messages change but skips while
  // a tour is already in flight.
  useEffect(() => {
    if (tourRunning) return;
    if (!messages.length) return;
    // Find the latest assistant message that has a tour_plan
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const m = messages[i];
      if (m.role !== "assistant") continue;
      const plan = m.tour_plan;
      if (!plan || !plan.steps?.length) continue;
      const normalized = {
        tour_id: plan.tour_id,
        title: plan.title,
        summary: plan.summary,
        chart_snapshot: plan.chart_snapshot || null,
        steps: plan.steps.map((s) => ({
          action_type: s.action_type,
          params: s.params || {},
          explanation: s.explanation || "",
          target_selector: s.target_selector,
          requires_approval: s.requires_approval ?? false,
        })),
      };
      // Only update if the plan actually changed to avoid noise.
      const current = lastTourPlanRef.current;
      if (
        !current ||
        current.tour_id !== normalized.tour_id ||
        current.steps.length !== normalized.steps.length
      ) {
        lastTourPlanRef.current = normalized;
      }
      break;
    }
  }, [messages, tourRunning]);

  // Auto-start a guided analysis when a fresh assistant response carries
  // a `tour_plan`. We gate on TWO things to avoid restart-loops:
  //   1. The most recent assistant message must have a tour_plan
  //   2. The user must be in interact mode
  // We DO NOT gate on liveMessageIdsRef anymore because that caused
  // sessions loaded from the server to never auto-start their tour
  // (the user would see the analysis card in the chat but the overlay
  // never appeared). Instead we track which message ids we have
  // already auto-started (autoExecutedStepRef is per-message) and
  // skip if the same message has been started before in this mount.
  const autoExecutedTourIdsRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (mode !== "interact") return;
    if (tourRunning) return;
    const latest = messages[messages.length - 1];
    if (!latest || latest.role !== "assistant") return;
    if (!latest.tour_plan || !latest.tour_plan.steps?.length) return;
    if (!latest.id) return;
    if (autoExecutedTourIdsRef.current.has(latest.id)) return;
    // Mark as auto-started BEFORE doing any state changes so a
    // re-render mid-tour doesn't fire a second auto-start.
    autoExecutedTourIdsRef.current.add(latest.id);

    const plan = latest.tour_plan;
    const normalizedPlan = {
      tour_id: plan.tour_id,
      title: plan.title,
      summary: plan.summary,
      chart_snapshot: plan.chart_snapshot || null,
      steps: plan.steps.map((s) => ({
        action_type: s.action_type,
        params: s.params || {},
        explanation: s.explanation || "",
        target_selector: s.target_selector,
        requires_approval: s.requires_approval ?? false,
      })),
    };
    lastTourPlanRef.current = normalizedPlan;
    autoExecutedStepRef.current = new Set();
    
    setActionResult("");
    setTourRestorePromptOpen(false);
    // Drop the in-flight "Progressing…" placeholder from the previous
    // tour, if any, so the new tour starts with a clean chat list.
    setMessages((prev) =>
      prev.filter(
        (m) => !(m.role === "assistant" && (m as AiMessage & { _placeholder?: boolean })._placeholder),
      ),
    );
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-capture-ui"));
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-start"));
    setActiveTour({ plan: normalizedPlan, currentStep: 0, active: true });
    setTourRunning(true);
    setSuggestionsOpen(false);
    window.dispatchEvent(new CustomEvent("lmview:chart-freeze", { detail: { frozen: true } }));
    // Append a single "Progressing…" placeholder that lives in the
    // chat list. The onTourComplete listener swaps this placeholder
    // for the recap final-response message when the tour ends.
    setMessages((prev) => [
      ...prev,
      {
        id: `progressing-${Date.now()}`,
        role: "assistant",
        content: t("tourProgressingLabel").replace("{current}", "1").replace("{total}", String(normalizedPlan.steps.length)),
        created_at: new Date().toISOString(),
        // Mark as placeholder so the renderer can show a spinner
        // and the onTourComplete swap can find + remove it.
        _placeholder: true,
      } as AiMessage & { _placeholder?: boolean },
    ]);
  }, [messages, mode, tourRunning, setActiveTour, liveMessageIdsRef, setMessages, t]);

  // Replay the most recent tour plan (button at the bottom of the recap).
  const replayTour = useCallback(() => {
    const plan = lastTourPlanRef.current;
    if (!plan) return;
    autoExecutedStepRef.current = new Set();
    setActiveTour({ plan, currentStep: 0, active: true });
    setTourRunning(true);
    
    setActionResult("");
    setTourRestorePromptOpen(false);
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-capture-ui"));
    window.dispatchEvent(new CustomEvent("lmview:chart-freeze", { detail: { frozen: true } }));
  }, [setActiveTour]);

  useEffect(() => {
    const onTourComplete = (event: Event) => {
      const detail = (event as CustomEvent<{ summary?: string; actions?: unknown[] }>).detail;
      const summary = detail?.summary || t("tourRecapBody");
      const actionCount = Array.isArray(detail?.actions) ? detail.actions.length : 0;
      setActionResult("");
      setTourRunning(false);
      // The recap is the final assistant response. We surface it
      // as a chat message (not a floating banner) so the user has
      // a single source of truth for the analysis outcome, and the
      // chat list itself doubles as a history of past analyses.
      setMessages((prev) => {
        // Drop the in-flight "Progressing…" placeholder if any.
        const withoutProgressing = prev.filter(
          (m) => !(m.role === "assistant" && (m as AiMessage & { _placeholder?: boolean })._placeholder),
        );
        const recapMessage: AiMessage & { _placeholder?: boolean } = {
          id: `recap-${Date.now()}`,
          role: "assistant",
          content: summary,
          created_at: new Date().toISOString(),
          // Carry the recap payload so the chat bubble can render the
          // Replay button + the step count without re-reading global
          // state.
          tool_calls: [
            {
              name: "tour_recap",
              arguments: {
                action_count: actionCount,
                tour_id: lastTourPlanRef.current?.tour_id || "",
                title: lastTourPlanRef.current?.title || "",
                // Embed the tour plan so the replay button works after
                // page reload (lastTourPlanRef.current resets on remount).
                tour_plan: lastTourPlanRef.current || null,
              },
              reason: "Analysis complete",
              requires_approval: false,
            },
          ],
        };
        return [...withoutProgressing, recapMessage];
      });

      // Persist the recap to the server so it survives page reload.
      // Without this, reloading a session loses the recap and the
      // Replay button (the original tour message comes back from the
      // DB but the recap was only in local state).
      if (sessionId && user?.id) {
        void (async () => {
          try {
            const { aiPersistSessionMessage } = await import("@/services/aiService");
            await aiPersistSessionMessage(sessionId, {
              role: "assistant",
              content: summary,
              metadata: {
                tour_complete: true,
                tour_plan: lastTourPlanRef.current || null,
                action_count: actionCount,
                // Include tool_calls in metadata so the server stores
                // it in the JSONB field. On reload, the frontend reads
                // metadata.tool_calls to detect recap messages and
                // render the Replay / Keep / Revert buttons.
                tool_calls: [
                  {
                    name: "tour_recap",
                    arguments: {
                      action_count: actionCount,
                      tour_id: lastTourPlanRef.current?.tour_id || "",
                      title: lastTourPlanRef.current?.title || "",
                      tour_plan: lastTourPlanRef.current || null,
                    },
                    reason: "Analysis complete",
                    requires_approval: false,
                  },
                ],
                provider: "tour_recap",
                model_name: "tour_recap",
              },
            });
          } catch (err) {
            // Non-blocking: log and continue; local state still has the recap.
            if (isAdmin) console.warn("[AI] failed to persist tour recap:", err);
          }
        })();
      }
    };
    window.addEventListener("lmview:ai-tour-complete", onTourComplete);
    return () => window.removeEventListener("lmview:ai-tour-complete", onTourComplete);
  }, [setMessages, t, sessionId, user?.id, isAdmin]);

  // Auto-execute current tour step action
  useEffect(() => {
    if (!activeTour || !activeTour.active) {
      return;
    }
    const step = activeTour.plan.steps[activeTour.currentStep];
    if (!step) return;
    const key = `${activeTour.plan.tour_id}-${activeTour.currentStep}`;
    if (autoExecutedStepRef.current.has(key)) {
      return;
    }
    autoExecutedStepRef.current.add(key);
    // Update the "Progressing…" placeholder with the current step
    // number so the chat row stays in sync with the step overlay.
    setMessages((prev) =>
      prev.map((m) => {
        const placeholder = m as AiMessage & { _placeholder?: boolean };
        if (placeholder._placeholder) {
          return {
            ...placeholder,
            content: t("tourProgressingLabel")
              .replace("{current}", String(activeTour.currentStep + 1))
              .replace("{total}", String(activeTour.plan.steps.length)),
          };
        }
        return m;
      }),
    );
    void executeAction({
      name: step.action_type,
      arguments: step.params || {},
      reason: `tour:${activeTour.plan.title} step ${activeTour.currentStep + 1}`,
    });
  }, [activeTour, executeAction, setMessages, t]);

  // Tour navigation
  const tourNextStep = useCallback(() => {
    if (!activeTour || !activeTour.active) return;
    const nextIdx = activeTour.currentStep + 1;
    if (nextIdx >= activeTour.plan.steps.length) {
      // Tour complete
      setActiveTour(null);
      setTourRunning(false);
      window.dispatchEvent(new CustomEvent("lmview:chart-freeze", { detail: { frozen: false } }));
      window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));
      window.dispatchEvent(new CustomEvent("lmview:ai-tour-complete", {
        detail: { summary: activeTour.plan.summary, actions: activeTour.plan.steps },
      }));
      window.dispatchEvent(new CustomEvent("lmview:right-panel-top-tab", { detail: { tab: "aiHelper" } }));
      return;
    }
    setActiveTour({ ...activeTour, currentStep: nextIdx });
  }, [activeTour, setActiveTour]);

  const tourPrevStep = useCallback(() => {
    if (!activeTour || !activeTour.active) return;
    const prevIdx = Math.max(0, activeTour.currentStep - 1);
    setActiveTour({ ...activeTour, currentStep: prevIdx });
  }, [activeTour, setActiveTour]);

  const cancelTour = useCallback(() => {
    setActiveTour(null);
    setTourRunning(false);
    setTourRestorePromptOpen(false);
    setOverlayPos(null);
    // Clear freeze + highlight + tour-end atomically so the chart, the
    // dim overlay, and the step overlay all close together — this is
    // the single source of truth for "user is done with the analysis".
    window.dispatchEvent(new CustomEvent("lmview:chart-freeze", { detail: { frozen: false } }));
    window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));
    window.dispatchEvent(new CustomEvent("lmview:ai-tour-end"));
    // Restore the right panel to the AI Helper tab so the textarea is
    // visible. During the tour, open_panel steps may have switched the
    // right panel to "overview" / "orderBook" / etc.
    window.dispatchEvent(new CustomEvent("lmview:right-panel-top-tab", { detail: { tab: "aiHelper" } }));
  }, [setActiveTour]);

  // Reset overlay position when a new tour starts so the box is
  // back in its default location (top of the panel).
  useEffect(() => {
    if (activeTour?.active && overlayPos === null) {
      setOverlayPos(null); // no-op, kept for clarity
    } else if (!activeTour?.active) {
      setOverlayPos(null);
    }
  }, [activeTour?.active, overlayPos]);

  // Drag handlers for the tour step overlay. The header bar is the
  // drag handle. We track the pointer position and adjust the box's
  // top/left in real time. Releases on pointerup or pointercancel.
  const onDragStart = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!activeTour?.active) return;
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    const cur = overlayPos ?? { x: 0, y: 0 };
    dragStartRef.current = { pointerX: e.clientX, pointerY: e.clientY, baseX: cur.x, baseY: cur.y };
  }, [activeTour?.active, overlayPos]);

  const onDragMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    const start = dragStartRef.current;
    if (!start) return;
    setOverlayPos({
      x: start.baseX + (e.clientX - start.pointerX),
      y: start.baseY + (e.clientY - start.pointerY),
    });
  }, []);

  const onDragEnd = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragStartRef.current) return;
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
    dragStartRef.current = null;
  }, []);

  useEffect(() => {
    if (messages.length === 0) {
      setActionResult("");
      
      setTourRestorePromptOpen(false);
      autoExecutedStepRef.current = new Set();
    }
  }, [messages.length]);

  const handleSend = () => {
    const trimmed = inputValue.trim();
    if (!trimmed || loading) return;
    setInputValue("");
    // Clear any in-flight tour state so a new request can start fresh.
    // The auto-start effect will re-evaluate the new assistant message
    // and trigger a new tour if it carries a tour_plan.
    if (activeTour?.active) {
      setActiveTour(null);
      setTourRunning(false);
      autoExecutedStepRef.current = new Set();
      window.dispatchEvent(new CustomEvent("lmview:chart-freeze", { detail: { frozen: false } }));
      window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));
    }
    void sendMessage(trimmed, chartContext);
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      handleSend();
    }
  };

  const introMessage = t("lmviewHelpReadyMessage")
    .replace("{symbol}", selectedSymbol)
    .replace("{timeframe}", timeframe.toUpperCase());

  const suggestions = useMemo(() => {
    const pool = [
      t("aiSuggestionLmview"),
      t("aiSuggestionDrawingTools"),
      t("aiSuggestionIndicatorsHelp"),
      "Analyze recent trend direction",
      "Find support and resistance levels",
      "Detect candlestick patterns",
      "Compare multiple timeframes",
      "Check volume confirmation",
      "Explain current indicator signals",
    ];
    // Symbol-specific prompts
    if (selectedSymbol) {
      pool.push(`Analyze ${selectedSymbol} trend on ${timeframe}`);
      pool.push(`Key support levels for ${selectedSymbol}?`);
      pool.push(`What indicators say about ${selectedSymbol}?`);
      pool.push(`Show me ${selectedSymbol} order flow`);
      pool.push(`${selectedSymbol} breakout levels`);
      pool.push(`Compare ${selectedSymbol} with BTC`);
    }
    // Pick random 3
    const shuffled = [...pool].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 3);
  }, [t, selectedSymbol, timeframe]);
  const assistantLabel = t("assistantName");
  const allMessages = [
    { id: "intro", role: "assistant" as const, content: introMessage },
    ...messages,
  ];

  return (
    <div data-ai-section="ai-panel" className="relative flex min-h-0 flex-1 flex-col bg-gray-900">
      <div className="border-b border-gray-800 bg-gray-850 px-3 py-2.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded bg-blue-500/10 text-blue-300">
              <Sparkles size={15} />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold text-white">{t("lmviewAi")}</h2>
              <p className="truncate text-[11px] text-gray-500">{t("assistantWorkspace")}</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button type="button" onClick={clearChat} className="flex h-7 w-7 items-center justify-center rounded text-gray-400 hover:bg-gray-800 hover:text-white" title={t("newChat")}>
              <Plus size={14} />
            </button>
            <button type="button" onClick={onOpenSettings} className="flex h-7 w-7 items-center justify-center rounded text-gray-400 hover:bg-gray-800 hover:text-white" title={t("assistantOptions")}>
              <MoreHorizontal size={15} />
            </button>
          </div>
        </div>
      </div>

      <div className="border-b border-gray-800 bg-gray-900 px-3 py-2">
        <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          <CircleDot size={10} /> {t("chartContext")}
        </div>
        <div className="flex flex-wrap gap-1.5">
          <span className="rounded border border-gray-700 bg-gray-850 px-2 py-1 text-[10px] font-medium text-gray-300">{selectedSymbol}</span>
          <span className="rounded border border-gray-700 bg-gray-850 px-2 py-1 text-[10px] font-medium text-gray-300">{timeframe.toUpperCase()}</span>
          <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[10px] font-medium text-blue-300">{mode === "ask" ? t("askMode") : t("interactMode")}</span>
          {selectedIndicators.length > 0 && (
            <span className="rounded border border-gray-700 bg-gray-850 px-2 py-1 text-[10px] font-medium text-gray-300">
              {selectedIndicators.length} {t("indicators")}
            </span>
          )}
        </div>
        {/* Model badge — visible for all users after first response */}
        {(() => {
          const last = [...messages].reverse().find(m => m.role === "assistant");
          const modelName: string | undefined = last?.model_name ?? undefined;
          const providerName: string | undefined = last?.provider ?? undefined;
          const pm = last?.provider_metadata;
          if (!modelName && !providerName) return null;
          const shortModel = modelName ? modelName.replace("openai/", "") : null;
          const fallbackUsed = (pm as Record<string, unknown>)?.model_fallback_used || (pm as Record<string, unknown>)?.key_fallback_used;
          const latencyMs = (pm as Record<string, unknown>)?.latency_ms;
          return (
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              {shortModel && (
                <span className="inline-flex items-center gap-1 rounded border border-purple-500/30 bg-purple-500/10 px-1.5 py-0.5 text-[9px] font-medium text-purple-300" title={String(modelName || "")}>
                  <Bot size={9} />
                  {shortModel}
                </span>
              )}
              {isAdmin && providerName && (
                <span className="inline-flex items-center gap-1 rounded border border-gray-600 bg-gray-800 px-1.5 py-0.5 text-[9px] font-medium text-gray-400">
                  {providerName}{fallbackUsed ? " (fallback)" : ""}
                </span>
              )}
              {isAdmin && latencyMs != null && (
                <span className="inline-flex items-center gap-1 rounded border border-gray-600 bg-gray-800 px-1.5 py-0.5 text-[9px] font-medium text-gray-400">
                  {String(latencyMs)}ms
                </span>
              )}
            </div>
          );
        })()}
      </div>

      {/* AI Context Quality Chips — shown after first assistant message */}
      {messages.some(m => m.role === "assistant") && (() => {
        const lastAssistant = [...messages].reverse().find(m => m.role === "assistant");
        if (!lastAssistant) return null;
        const nc = lastAssistant.news_context;
        const conf = lastAssistant.confidence;
        const caveats = lastAssistant.data_caveats;
        const hasDegraded = !nc || nc.article_count === 0 || (conf != null && conf < 0.4);
        return (
          <div className="border-b border-gray-800 bg-gray-900/80 px-3 py-1.5">
            <div className="flex flex-wrap gap-1">
              {/* News chip */}
              {nc && nc.article_count > 0 ? (
                <span className="inline-flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-medium text-emerald-300">
                  <Newspaper size={9} />
                  {nc.article_count} {t("aiContextArticles")}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[9px] font-medium text-amber-300">
                  <Newspaper size={9} />
                  {t("aiContextNoNews")}
                </span>
              )}
              {/* Sentiment chip */}
              {nc && nc.sentiment_summary && nc.article_count > 0 && (
                <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] font-medium ${
                  nc.sentiment_summary.direction === "bullish" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : nc.sentiment_summary.direction === "bearish" ? "border-red-500/30 bg-red-500/10 text-red-300"
                  : "border-gray-600 bg-gray-800 text-gray-400"
                }`}>
                  {t("aiContextSentiment")}: {nc.sentiment_summary.direction}
                </span>
              )}
              {/* Freshness chip */}
              {nc && nc.freshness && nc.freshness.newest_age_hours != null && (
                <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] font-medium ${
                  nc.freshness.is_stale ? "border-amber-500/30 bg-amber-500/10 text-amber-300" : "border-blue-500/30 bg-blue-500/10 text-blue-300"
                }`}>
                  {nc.freshness.is_stale ? t("aiContextStale") : t("aiContextFresh")}: {nc.freshness.newest_age_hours.toFixed(0)}h
                </span>
              )}
              {/* Confidence chip */}
              {conf != null && (
                <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] font-medium ${
                  conf >= 0.7 ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : conf >= 0.4 ? "border-blue-500/30 bg-blue-500/10 text-blue-300"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-300"
                }`}>
                  <Shield size={9} />
                  {(conf * 100).toFixed(0)}%
                </span>
              )}
              {/* Degraded warnings */}
              {hasDegraded && caveats && caveats.length > 2 && (
                <span className="inline-flex items-center gap-1 rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[9px] font-medium text-amber-300">
                  <AlertTriangle size={9} />
                  {t("aiContextLowConfidence")}
                </span>
              )}
            </div>
          </div>
        );
      })()}

      <div className="flex min-h-0 flex-1 flex-col">
        <div
          className="min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-3"
        >
          {error && (
            <div className="rounded border border-red-500/25 bg-red-500/10 px-3 py-2 text-[11px] leading-5 text-red-200">{error}</div>
          )}

          {allMessages.map((message) => {
            const isUser = message.role === "user";
            return (
              <div key={message.id} data-testid={`ai-message-${message.id}`} className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
                {!isUser && (
                  <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-blue-500/10 text-blue-300">
                    <Bot size={13} />
                  </div>
                )}
                <div className={`max-w-[88%] ${isUser ? "items-end" : "items-start"}`}>
                  <div className={`mb-1 flex items-center gap-1.5 text-[10px] text-gray-500 ${isUser ? "justify-end" : ""}`}>
                    {isUser ? <UserRound size={10} /> : <Sparkles size={10} />}
                    <span>{isUser ? t("you") : assistantLabel}</span>
                  </div>
                  <div
                    className={`max-w-full rounded px-3 py-2 text-xs leading-5 shadow-sm ${
                      isUser
                        ? "bg-blue-600 text-white"
                        : message.tour_plan && message.tour_plan.steps?.length
                          ? "border border-amber-500/40 bg-amber-500/5"
                          : "border border-gray-800 bg-gray-850 text-gray-200"
                    }`}
                  >
                    {(() => {
                      // Render priority: tour_recap > tour_plan > markdown.
                      // Check tour_recap FIRST because the server surfaces
                      // tour_plan from metadata for recap messages too.
                      const recapCall = message.tool_calls?.find(
                        (c) => c.name === "tour_recap",
                      );
                      if (recapCall) {
                        return (
                          // The final response of a guided analysis: the
                          // recap. Rendered as a regular chat bubble with
                          // an embedded Replay button so the chat list is
                          // the single source of truth for the analysis
                          // outcome (no floating banner).
                          <div className="space-y-1.5" data-testid="ai-tour-recap">
                            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-200">
                              <Sparkles size={11} className="text-emerald-300" />
                              {t("tourRecapTitle")}
                            </div>
                            <div className="text-[11px] leading-5 text-emerald-100/90 whitespace-pre-line">
                              {message.content}
                            </div>
                            <div className="mt-1 flex flex-wrap items-center gap-2">
                              <button
                                type="button"
                                onClick={() => {
                                  const embeddedPlan = (recapCall.arguments as { tour_plan?: unknown } | undefined)?.tour_plan;
                                  if (embeddedPlan && typeof embeddedPlan === "object") {
                                    lastTourPlanRef.current = embeddedPlan as typeof lastTourPlanRef.current;
                                  }
                                  replayTour();
                                }}
                                disabled={
                                  !lastTourPlanRef.current &&
                                  !(recapCall.arguments as { tour_plan?: unknown } | undefined)?.tour_plan
                                }
                                className="flex items-center gap-1 rounded bg-emerald-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                                data-testid="ai-tour-replay"
                              >
                                <RotateCcw size={10} />
                                {t("replay")}
                              </button>
                              <span className="text-[9px] text-emerald-100/60">
                                {lastTourPlanRef.current?.title ||
                                  (recapCall.arguments as { title?: string } | undefined)?.title || ""}
                              </span>
                            </div>
                            {/* Keep / Revert live inside the recap message
                                instead of cluttering the last-step overlay. */}
                            <div className="mt-2 flex items-center gap-2 border-t border-emerald-500/20 pt-2">
                              <span className="text-[9px] text-emerald-100/60">{t("tourFinalChoiceLabel")}</span>
                              <button
                                type="button"
                                onClick={cancelTour}
                                className="flex items-center gap-1 rounded bg-emerald-700 px-2 py-1 text-[10px] font-semibold text-white hover:bg-emerald-600"
                                data-testid="ai-tour-keep"
                              >
                                <Check size={10} />
                                {t("tourKeep")}
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  cancelTour();
                                  window.dispatchEvent(new CustomEvent("lmview:ai-tour-restore-ui"));
                                }}
                                className="flex items-center gap-1 rounded border border-emerald-500/30 px-2 py-1 text-[10px] text-emerald-100 hover:bg-emerald-500/10"
                                data-testid="ai-tour-revert"
                              >
                                <Undo2 size={10} />
                                {t("tourRevert")}
                              </button>
                            </div>
                          </div>
                        );
                      }
                      const tp = message.tour_plan;
                      if (tp && tp.steps?.length) {
                        return (
                          // In Interact mode the assistant message *is* the
                          // visual analysis: don't dump the LLM narrative in
                          // chat (it's repeated in the step overlay + recap).
                          // Render a compact card pointing to the step overlay.
                          <div className="space-y-1.5" data-testid="ai-analysis-card">
                            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-200">
                              <Sparkles size={11} className="text-amber-300" />
                              {tp.title || "Guided analysis"}
                            </div>
                            <div className="text-[11px] leading-5 text-amber-100/90">
                              {tp.summary || t("analysisReadyBody")}
                            </div>
                            <div className="flex items-center gap-1.5 text-[10px] text-amber-200/70">
                              <Sparkles size={9} />
                              {tp.steps.length} {t("analysisSteps")}
                              {activeTour?.plan?.tour_id === tp.tour_id && (
                                <span className="ml-1 rounded bg-amber-500/30 px-1.5 py-0.5 text-[9px] font-semibold">
                                  Running
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      }
                      return <MarkdownContent content={message.content} compact={isUser} />;
                    })()}
                  </div>
                  {/* Admin tool-call replay buttons. These used to be
                      rendered inline in the chat, but exposing action
                      names like "start_tour" in the chat confuses
                      regular users and clutters the screen during a
                      guided analysis. The dedicated AI Action debug
                      window (openable via `lmview:open-ai-action-debug`)
                      is the right place for these. */}
                  {isAdmin && !isUser && (message.token_input || message.token_output || message.estimated_cost_usd) && (
                    <div className="mt-1 flex items-center gap-2 text-[9px] text-gray-600">
                      {message.token_input && message.token_output && <span>{message.token_input}{" -> "}{message.token_output} tokens</span>}
                      {message.estimated_cost_usd && <span className="text-green-500">${message.estimated_cost_usd.toFixed(4)}</span>}
                    </div>
                  )}
                  {/* Sources used */}
                  {!isUser && "sources" in message && Array.isArray(message.sources) && message.sources.length > 0 && (
                    <details className="mt-1.5">
                      <summary className="flex cursor-pointer items-center gap-1 text-[9px] font-semibold text-gray-500 hover:text-gray-300">
                        <BookOpen size={9} />
                        {t("aiContextSources")} ({message.sources.length})
                      </summary>
                      <div className="mt-1 space-y-0.5 pl-3">
                        {message.sources.map((src, idx) => (
                          <div key={src.chunk_id || idx} className="flex items-center gap-1.5 text-[9px] text-gray-500">
                            <ExternalLink size={8} />
                            <span className="truncate">{src.title || src.source || "Unknown"}</span>
                            {src.score != null && <span className="text-gray-600">({(src.score * 100).toFixed(0)}%)</span>}
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                  {/* Risk events */}
                  {!isUser && message.news_context && message.news_context.risk_events.length > 0 && (
                    <div className="mt-1.5 rounded border border-amber-500/25 bg-amber-500/5 px-2 py-1">
                      <div className="flex items-center gap-1 text-[9px] font-semibold text-amber-300">
                        <AlertTriangle size={9} />
                        {t("aiContextRiskEvents")} ({message.news_context.risk_events.length})
                      </div>
                      <div className="mt-0.5 space-y-0.5">
                        {message.news_context.risk_events.slice(0, 3).map((event, idx) => (
                          <div key={idx} className="text-[9px] leading-4 text-amber-200/70">{event}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* Rating buttons (👍/👎) for assistant messages */}
                  {!isUser && message.id.startsWith("api-") && (
                    <div className="mt-1.5 flex items-center gap-2">
                      <button
                        onClick={() => rateMessage(message.id, 1)}
                        className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] text-gray-500 hover:text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                        title="Helpful"
                      >
                        <ThumbsUp size={10} />
                      </button>
                      <button
                        onClick={() => rateMessage(message.id, -1)}
                        className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] text-gray-500 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                        title="Not helpful"
                      >
                        <ThumbsDown size={10} />
                      </button>
                    </div>
                  )}
                </div>
                {isUser && (
                  <div className="mt-5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-gray-800 text-gray-300">
                    <UserRound size={13} />
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="flex justify-start gap-2">
              <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-blue-500/10 text-blue-300">
                <Bot size={13} />
              </div>
              <div className="flex-1">
                <div className="rounded border border-gray-800 bg-gray-850 px-3 py-2 text-xs text-gray-400">
                  <Loader2 size={14} className="mr-1.5 inline animate-spin" />
                  {t("thinking")}
                </div>
                {/* Loading skeleton */}
                <div className="mt-2 animate-pulse space-y-1.5">
                  <div className="h-2 w-3/4 rounded bg-gray-800" />
                  <div className="h-2 w-1/2 rounded bg-gray-800" />
                  <div className="h-2 w-5/6 rounded bg-gray-800" />
                </div>
              </div>
            </div>
          )}

          {/* actionResult is shown only inside the AI Action debug
              window for admin/developer visibility (see
              AiActionDebugPanel below). It is intentionally NOT
              surfaced as a banner to normal users because action
              results frequently contain internal terms like
              "error: unsupported drawing tool X" which are not
              actionable for end-users. */}

          <div className="rounded border border-dashed border-gray-800 bg-gray-850/70">
            <button
              type="button"
              onClick={() => setSuggestionsOpen((open) => !open)}
              className="flex w-full items-center justify-between px-2 py-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500"
            >
              {t("suggestedPrompts")}
              {suggestionsOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
            {suggestionsOpen && (
              <div className="space-y-1.5 px-2 pb-2">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => setInputValue(suggestion)}
                    className="w-full rounded border border-gray-800 bg-gray-900 px-2 py-1.5 text-left text-[11px] text-gray-300 hover:border-blue-500/50 hover:text-white"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Admin debug: context preview */}
          {isAdmin && messages.some(m => m.role === "assistant") && (() => {
            const lastA = [...messages].reverse().find(m => m.role === "assistant");
            if (!lastA) return null;
            return (
              <div className="rounded border border-dashed border-gray-800 bg-gray-850/70">
                <button
                  type="button"
                  onClick={() => setDebugOpen(o => !o)}
                  className="flex w-full items-center justify-between px-2 py-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500"
                >
                  <span className="flex items-center gap-1"><Info size={10} /> {t("aiContextDebug")}</span>
                  {debugOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                </button>
                {debugOpen && (
                  <div className="space-y-1 px-2 pb-2 text-[9px] text-gray-500">
                    {lastA.confidence != null && <div>Confidence: {(lastA.confidence * 100).toFixed(0)}%</div>}
                    {lastA.provider_metadata && (
                      <div>Provider: {String(lastA.provider_metadata.effective_provider || "?")} / {String(lastA.provider_metadata.model || "?")} ({String(lastA.provider_metadata.latency_ms || "?")}ms)</div>
                    )}
                    {lastA.news_context && (
                      <div>
                        News: {lastA.news_context.article_count} articles, {lastA.news_context.source_count} sources,
                        sentiment: {lastA.news_context.sentiment_summary.direction} ({lastA.news_context.sentiment_summary.avg_score.toFixed(2)})
                      </div>
                    )}
                    {lastA.data_caveats && lastA.data_caveats.length > 0 && (
                      <div>
                        <div className="font-semibold text-amber-400/70">Caveats:</div>
                        {lastA.data_caveats.map((c, i) => <div key={i} className="pl-2 text-gray-600">• {c}</div>)}
                      </div>
                    )}
                    {lastA.sources && lastA.sources.length > 0 && (
                      <div>
                        <div className="font-semibold">RAG chunks: {lastA.sources.length}</div>
                        {lastA.sources.map((s, i) => (
                          <div key={i} className="pl-2 text-gray-600">
                            {s.title} ({((s.score || 0) * 100).toFixed(0)}%)
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })()}

          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-gray-800 bg-gray-850 p-2.5">
          <div className="rounded border border-gray-700 bg-gray-900 focus-within:border-blue-500">
            <textarea
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("aiHelperPlaceholder").replace("{symbol}", selectedSymbol)}
              className="min-h-20 w-full resize-none rounded-t bg-transparent px-3 py-2 text-xs text-white outline-none placeholder-gray-500"
              disabled={loading}
            />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-800 px-2 py-1.5">
              <label className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[11px] font-semibold text-gray-400">
                <span>{t("askMode")}</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={mode === "interact"}
                  onClick={() => setMode(mode === "ask" ? "interact" : "ask")}
                  className={`h-4 w-8 rounded-full p-0.5 transition-colors ${mode === "interact" ? "bg-blue-600" : "bg-gray-700"}`}
                >
                  <span className={`block h-3 w-3 rounded-full bg-white transition-transform ${mode === "interact" ? "translate-x-4" : "translate-x-0"}`} />
                </button>
                <span>{t("interactMode")}</span>
              </label>
              <div className="order-last flex min-w-0 flex-1 items-center gap-1.5 text-[10px] text-gray-500 sm:order-none">
                <CornerDownLeft size={11} />
                <span className="hidden truncate sm:inline">{t("sendHint")}</span>
              </div>
              <button
                type="button"
                onClick={handleSend}
                disabled={!inputValue.trim() || loading}
                className={`flex h-7 flex-shrink-0 items-center gap-1.5 rounded px-2 text-xs font-semibold ${inputValue.trim() && !loading ? "bg-blue-600 text-white hover:bg-blue-500" : "cursor-not-allowed bg-gray-800 text-gray-600"}`}
                title={t("sendMessage")}
              >
                {loading ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                {t("send")}
              </button>
            </div>
          </div>
        </div>
      </div>
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
        .ai-md-compact code { background: rgba(15, 23, 42, .45); color: white; }
      `}</style>

      {/* Tour Step Overlay */}
      {activeTour?.active && activeTour.plan.steps[activeTour.currentStep] && (() => {
        const stepIdx = activeTour.currentStep;
        const totalSteps = activeTour.plan.steps.length;
        const isLastStep = stepIdx >= totalSteps - 1;
        const currentStep = activeTour.plan.steps[stepIdx];
        // NB: the highlight dim is `fixed inset-0 z-[680]` at the body
        // level. Positioning our overlay as `absolute` inside the AI
        // panel would put us inside the panel's own stacking context,
        // and the dim would still cover us. Render at the body level
        // via a portal so our z-[720] actually wins against z-[680].
        const overlayPosStyle: React.CSSProperties = overlayPos
          ? { top: `${Math.max(8, overlayPos.y)}px`, left: `${Math.max(8, overlayPos.x)}px`, right: 'auto' }
          : { top: '88px', left: '50%', transform: 'translateX(-50%)' };
        const overlayNode = (
          <div
            className="fixed z-[720] w-[min(420px,calc(100vw-32px))] rounded-lg border border-amber-500/40 bg-gray-850/95 p-3 shadow-2xl backdrop-blur"
            data-testid="ai-tour-overlay"
            style={overlayPosStyle}
          >
          {/* Drag handle header */}
          <div
            onPointerDown={onDragStart}
            onPointerMove={onDragMove}
            onPointerUp={onDragEnd}
            onPointerCancel={onDragEnd}
            className="-mx-3 -mt-3 mb-2 flex cursor-move select-none items-center justify-between rounded-t-lg border-b border-amber-500/20 bg-amber-500/10 px-3 py-1.5 active:cursor-grabbing"
            title="Drag to move"
          >
            <div className="flex items-center gap-2">
              <GripVertical size={12} className="text-amber-300/70" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-200">
                Step {stepIdx + 1} of {totalSteps}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-1 w-20 overflow-hidden rounded-full bg-gray-700/60">
                <div
                  className="h-full rounded-full bg-amber-400 transition-all duration-500"
                  style={{ width: `${((stepIdx + 1) / totalSteps) * 100}%` }}
                />
              </div>
              <span className="text-[9px] tabular-nums text-amber-300/70">
                {Math.round(((stepIdx + 1) / totalSteps) * 100)}%
              </span>
            </div>
          </div>
          {/* Step info. We show action verb + plan title as a
              compact breadcrumb, but only when they actually add
              information. The template title "LMView Workspace"
              already appears in the chart overlay (breadcrumb +
              tour title in the chat recap), so concatenating it
              here would just look like "LocateLMView Workspace". */}
          <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-300/80">
            {labelForAction(currentStep.action_type)}
          </p>
          <p className="mt-1 text-[11px] leading-relaxed text-gray-300">
            {currentStep.explanation}
          </p>
          {/* Navigation */}
          <div className="mt-2 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={cancelTour}
              className="rounded bg-gray-700 px-2 py-1 text-[10px] font-semibold text-gray-300 hover:bg-gray-600"
            >
              {t("cancel")}
            </button>
            <div className="flex items-center gap-1.5">
              {stepIdx > 0 && (
                <button
                  type="button"
                  onClick={tourPrevStep}
                  className="rounded bg-gray-700 px-2.5 py-1 text-[10px] font-semibold text-gray-300 hover:bg-gray-600"
                  data-testid="ai-tour-prev"
                >
                  {t("previous")}
                </button>
              )}
              <button
                type="button"
                onClick={tourNextStep}
                className={`flex items-center gap-1 rounded px-3 py-1 text-[10px] font-semibold ${
                  isLastStep
                    ? "bg-emerald-600 text-white hover:bg-emerald-500"
                    : "bg-amber-600 text-white hover:bg-amber-500"
                }`}
                data-testid="ai-tour-next"
              >
                {isLastStep ? t("finish") : t("next")}
                <ChevronRight size={10} />
              </button>
            </div>
          </div>
          {/* Keep / Revert moved to the recap message bubble — they
              only matter after the tour finishes, so showing them on
              the last step is redundant clutter. */}
          </div>
        );
        // Portal the overlay to body so its z-[720] escapes the AI
        // panel's stacking context and actually sits above the
        // highlight dim (z-[680]).
        return createPortal(overlayNode, document.body);
      })()}
    </div>
  );
};

function labelForAction(actionType: string): string {
  switch (actionType) {
    case "highlight_section":
      return "Locate";
    case "highlight_chart_area":
      return "Highlight zone";
    case "highlight_candles":
      return "Highlight candles";
    case "add_indicator":
      return "Add indicator";
    case "remove_indicator":
      return "Remove indicator";
    case "draw_tool":
    case "draw_trendline":
      return "Draw on chart";
    case "create_annotation":
      return "Add note";
    case "set_timeframe":
      return "Change timeframe";
    case "set_chart_type":
      return "Change chart type";
    case "zoom_chart":
      return "Zoom";
    case "scroll_chart":
      return "Scroll";
    case "open_panel":
    case "switch_panel_tab":
      return "Open panel";
    case "switch_app_view":
      return "Switch view";
    case "fetch_historical_prices":
      return "Load history";
    default:
      return "Step";
  }
}

export default AiAssistantPanel;
