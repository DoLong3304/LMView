import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import {
  AlertTriangle,
  Bot,
  BookOpen,
  ChevronDown,
  ChevronUp,
  CircleDot,
  CornerDownLeft,
  ExternalLink,
  Info,
  Loader2,
  MoreHorizontal,
  Newspaper,
  Play,
  Plus,
  Send,
  Shield,
  Sparkles,
  UserRound,
} from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";
import { useAiActions } from "@/features/ai/actions/AiActionProvider";
import { useAiChat } from "@/features/ai/hooks/useAiChat";
import { useI18n } from "@/i18n";
import type { ChartContextForAi } from "@/features/ai/types";
import type { Candle } from "@/types";

interface AiAssistantPanelProps {
  selectedSymbol: string;
  timeframe: string;
  candles?: Candle[];
  selectedIndicators?: string[];
  exchange?: string;
  onOpenSettings?: () => void;
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
}) => {
  const { t } = useI18n();
  const { user } = useAuth();
  const { executeAction } = useAiActions();
  const { messages, loading, error, mode, setMode, sendMessage, clearChat } = useAiChat();
  const [inputValue, setInputValue] = useState("");
  const [suggestionsOpen, setSuggestionsOpen] = useState(true);
  const [actionResult, setActionResult] = useState("");
  const [tourSummary, setTourSummary] = useState<{ summary: string; actions: number } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const autoExecutedRef = useRef<Set<string>>(new Set());
  const [debugOpen, setDebugOpen] = useState(false);
  const isAdmin = user?.role === "admin";

  const chartContext: ChartContextForAi = useMemo(() => {
    const lastCandle = candles[candles.length - 1];
    return {
      symbol: selectedSymbol,
      exchange,
      timeframe,
      chart_type: "candles",
      selected_indicators: selectedIndicators,
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
      frontend_context_version: "2.0.0",
    };
  }, [selectedSymbol, exchange, timeframe, selectedIndicators, candles]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    if (messages.some((message) => message.role === "user")) setSuggestionsOpen(false);
  }, [messages]);

  useEffect(() => {
    if (mode !== "interact") return;
    const latest = messages[messages.length - 1];
    if (!latest || latest.role !== "assistant" || !latest.tool_calls?.length) return;
    latest.tool_calls.forEach((call, index) => {
      const key = `${latest.id}-${index}`;
      if (autoExecutedRef.current.has(key) || call.requires_approval) return;
      autoExecutedRef.current.add(key);
      void executeAction({ name: call.name, arguments: call.arguments || {}, reason: call.reason }).then((result) => {
        setActionResult(result.detail);
      });
    });
  }, [executeAction, messages, mode]);

  useEffect(() => {
    const onTourComplete = (event: Event) => {
      const detail = (event as CustomEvent<{ summary?: string; actions?: unknown[] }>).detail;
      setTourSummary({
        summary: detail?.summary || t("tourRecapBody"),
        actions: Array.isArray(detail?.actions) ? detail.actions.length : 0,
      });
      setActionResult(t("tourCompleted"));
    };
    window.addEventListener("lmview:ai-tour-complete", onTourComplete);
    return () => window.removeEventListener("lmview:ai-tour-complete", onTourComplete);
  }, [t]);

  const handleSend = () => {
    const trimmed = inputValue.trim();
    if (!trimmed || loading) return;
    setInputValue("");
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

  const suggestions = [
    t("aiSuggestionLmview"),
    t("aiSuggestionDrawingTools"),
    t("aiSuggestionIndicatorsHelp"),
  ];
  const assistantLabel = t("assistantName");
  const allMessages = [
    { id: "intro", role: "assistant" as const, content: introMessage },
    ...messages,
  ];

  return (
    <div data-ai-section="ai-panel" className="flex min-h-0 flex-1 flex-col bg-gray-900">
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
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-3">
          {error && (
            <div className="rounded border border-red-500/25 bg-red-500/10 px-3 py-2 text-[11px] leading-5 text-red-200">{error}</div>
          )}

          {allMessages.map((message) => {
            const isUser = message.role === "user";
            const actionCalls = "tool_calls" in message && Array.isArray(message.tool_calls) ? message.tool_calls : [];
            return (
              <div key={message.id} className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
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
                  <div className={`max-w-full rounded px-3 py-2 text-xs leading-5 shadow-sm ${isUser ? "bg-blue-600 text-white" : "border border-gray-800 bg-gray-850 text-gray-200"}`}>
                    <MarkdownContent content={message.content} compact={isUser} />
                  </div>
                  {!isUser && actionCalls.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {actionCalls.map((call, index) => (
                        <button
                          key={`${call.name}-${index}`}
                          type="button"
                          onClick={async () => {
                            const result = await executeAction({ name: call.name, arguments: call.arguments || {} });
                            setActionResult(result.detail);
                          }}
                          className="inline-flex items-center gap-1 rounded border border-blue-500/40 bg-blue-500/10 px-2 py-1 text-[11px] font-semibold text-blue-200 hover:bg-blue-500/20"
                        >
                          <Play size={11} /> {call.name}
                        </button>
                      ))}
                    </div>
                  )}
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

          {actionResult && (
            <div className="rounded border border-blue-500/25 bg-blue-500/10 px-3 py-2 text-[11px] text-blue-100">{actionResult}</div>
          )}

          {tourSummary && (
            <div className="rounded border border-emerald-500/25 bg-emerald-500/10 px-3 py-2 text-[11px] leading-5 text-emerald-100">
              <div className="font-semibold">{t("tourRecapTitle")}</div>
              <div className="mt-1 text-emerald-100/80">{tourSummary.summary}</div>
              <div className="mt-1 text-emerald-100/60">{tourSummary.actions} {t("actionsSaved")}</div>
              <button
                type="button"
                onClick={() => void executeAction({ name: "start_tour", arguments: { tour_id: "lmview-overview" } })}
                className="mt-2 rounded bg-emerald-600 px-2 py-1 text-[10px] font-semibold text-white"
              >
                {t("replay")}
              </button>
            </div>
          )}

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
    </div>
  );
};

export default AiAssistantPanel;
