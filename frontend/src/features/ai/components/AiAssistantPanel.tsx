/**
 * AiAssistantPanel — extracted AI assistant chat panel.
 *
 * Previously embedded in RightPanel. Now a standalone feature component
 * that uses useAiChat hook and aiService for backend communication.
 */

import React, { useRef, useEffect, useMemo } from "react";
import {
  Bot,
  CircleDot,
  CornerDownLeft,
  Lock,
  Loader2,
  MoreHorizontal,
  Plus,
  Send,
  Sparkles,
  UserRound,
} from "lucide-react";
import { DATA_SOURCE } from "@/constants/env";
import { useI18n } from "@/i18n";
import { useAiChat } from "@/features/ai/hooks/useAiChat";
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

const AiAssistantPanel: React.FC<AiAssistantPanelProps> = ({
  selectedSymbol,
  timeframe,
  candles = [],
  selectedIndicators = [],
  exchange = "binance",
  onOpenSettings,
}) => {
  const { t } = useI18n();
  const { messages, loading, error, mode, setMode, sendMessage, clearChat } = useAiChat();
  const [inputValue, setInputValue] = React.useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Build chart context for AI
  const chartContext: ChartContextForAi = useMemo(() => {
    const lastCandle = candles[candles.length - 1];
    return {
      symbol: selectedSymbol,
      exchange,
      timeframe,
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
      frontend_context_version: "1.0.0",
    };
  }, [selectedSymbol, exchange, timeframe, selectedIndicators, candles]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const trimmed = inputValue.trim();
    if (!trimmed || loading) return;
    setInputValue("");
    sendMessage(trimmed, chartContext);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
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
  const assistantLabel = DATA_SOURCE === "api" ? t("lmviewHelpMode") : t("assistantName");

  // Combine intro + messages
  const allMessages = [
    { id: "intro", role: "assistant" as const, content: introMessage },
    ...messages,
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-gray-900">
      {/* Header */}
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
              className="flex h-7 w-7 items-center justify-center rounded text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
              title={t("newChat")}
            >
              <Plus size={14} />
            </button>
            <button
              type="button"
              onClick={onOpenSettings}
              className="flex h-7 w-7 items-center justify-center rounded text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
              title={t("assistantOptions")}
            >
              <MoreHorizontal size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* Context chips */}
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
          <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[10px] font-medium text-blue-300">
            {mode === "ask" ? t("lmviewHelpMode") : t("aiInteractUnavailable")}
          </span>
          {selectedIndicators.length > 0 && (
            <span className="rounded border border-gray-700 bg-gray-850 px-2 py-1 text-[10px] font-medium text-gray-300">
              {selectedIndicators.length} indicators
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-3">
          <div className="flex rounded border border-gray-800 bg-gray-850 p-1">
            <button
              type="button"
              onClick={() => setMode("ask")}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded px-2 py-1.5 text-[11px] font-semibold transition-colors ${
                mode === "ask"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white"
              }`}
            >
              <Sparkles size={12} />
              {t("askMode")}
            </button>
            <button
              type="button"
              disabled
              className="flex flex-1 cursor-not-allowed items-center justify-center gap-1.5 rounded px-2 py-1.5 text-[11px] font-semibold text-gray-600"
              title={t("aiInteractUnavailable")}
            >
              <Lock size={12} />
              {t("interactMode")}
            </button>
          </div>

          {DATA_SOURCE === "api" && (
            <div className="rounded border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-[11px] leading-5 text-amber-100">
              {t("aiApiUnavailableHelpOnly")}
            </div>
          )}

          {error && (
            <div className="rounded border border-red-500/25 bg-red-500/10 px-3 py-2 text-[11px] leading-5 text-red-200">
              {error}
            </div>
          )}

          {allMessages.map((message) => {
            const isUser = message.role === "user";
            return (
              <div
                key={message.id}
                className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}
              >
                {!isUser && (
                  <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-blue-500/10 text-blue-300">
                    <Bot size={13} />
                  </div>
                )}
                <div className={`max-w-[86%] ${isUser ? "items-end" : "items-start"}`}>
                  <div
                    className={`mb-1 flex items-center gap-1.5 text-[10px] text-gray-500 ${isUser ? "justify-end" : ""}`}
                  >
                    {isUser ? <UserRound size={10} /> : <Sparkles size={10} />}
                    <span>{isUser ? t("you") : assistantLabel}</span>
                  </div>
                  <div
                    className={`rounded-lg px-3 py-2 text-xs leading-5 shadow-sm ${
                      isUser
                        ? "bg-blue-600 text-white"
                        : "border border-gray-800 bg-gray-850 text-gray-200"
                    }`}
                  >
                    {message.content}
                  </div>
                </div>
                {isUser && (
                  <div className="mt-5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-gray-800 text-gray-300">
                    <UserRound size={13} />
                  </div>
                )}
              </div>
            );
          })}

          {/* Loading indicator */}
          {loading && (
            <div className="flex gap-2 justify-start">
              <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-blue-500/10 text-blue-300">
                <Bot size={13} />
              </div>
              <div className="rounded-lg border border-gray-800 bg-gray-850 px-3 py-2 text-xs text-gray-400">
                <Loader2 size={14} className="animate-spin inline mr-1.5" />
                Thinking...
              </div>
            </div>
          )}

          {/* Suggestions */}
          <div className="rounded-lg border border-dashed border-gray-800 bg-gray-850/70 p-2">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
              {t("suggestedPrompts")}
            </div>
            <div className="space-y-1.5">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setInputValue(suggestion)}
                  className="w-full rounded border border-gray-800 bg-gray-900 px-2 py-1.5 text-left text-[11px] text-gray-300 transition-colors hover:border-blue-500/50 hover:text-white"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-800 bg-gray-850 p-2.5">
          <div className="rounded-lg border border-gray-700 bg-gray-900 transition-colors focus-within:border-blue-500">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("aiHelperPlaceholder").replace("{symbol}", selectedSymbol)}
              className="min-h-20 w-full resize-none rounded-t-lg bg-transparent px-3 py-2 text-xs text-white placeholder-gray-500 outline-none"
              disabled={loading}
            />
            <div className="flex items-center justify-between gap-2 border-t border-gray-800 px-2 py-1.5">
              <div className="flex min-w-0 items-center gap-1.5 text-[10px] text-gray-500">
                <CornerDownLeft size={11} />
                <span className="truncate">{t("sendHint")}</span>
              </div>
              <button
                type="button"
                onClick={handleSend}
                disabled={!inputValue.trim() || loading || mode === "interact"}
                className={`flex h-7 items-center gap-1.5 rounded px-2 text-xs font-semibold transition-colors ${
                  inputValue.trim() && !loading && mode !== "interact"
                    ? "bg-blue-600 text-white hover:bg-blue-500"
                    : "cursor-not-allowed bg-gray-800 text-gray-600"
                }`}
                title={t("sendMessage")}
              >
                {loading ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Send size={12} />
                )}
                {t("send")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AiAssistantPanel;
