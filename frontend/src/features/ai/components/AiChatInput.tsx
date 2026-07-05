/**
 * AiChatInput — textarea + mode toggle + send + cached unsent input.
 *
 * Rewrite for Phase D:
 * - Suggested prompts appear below the textarea when user is typing
 *   (not as a persistent dropdown)
 * - Unsent message cached in localStorage to survive accidental reload
 * - On API error, question is reverted back into the input field
 * - Ctrl/Cmd+Enter to send, plain Enter for newline
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CornerDownLeft, Sparkles, X } from "lucide-react";
import { useI18n } from "@/i18n";
import type { AiMode } from "@/types";

// ── Cached input key ────────────────────────────────────────────────────

const CACHED_INPUT_KEY = "lmview_ai_unsent_input";

function saveUnsentInput(value: string) {
  try {
    if (value.trim()) {
      localStorage.setItem(CACHED_INPUT_KEY, value);
    } else {
      localStorage.removeItem(CACHED_INPUT_KEY);
    }
  } catch {
    // Storage full — ignore
  }
}

function loadUnsentInput(): string {
  try {
    return localStorage.getItem(CACHED_INPUT_KEY) || "";
  } catch {
    return "";
  }
}

function clearUnsentInput() {
  try {
    localStorage.removeItem(CACHED_INPUT_KEY);
  } catch {
    // Ignore
  }
}

// ── Suggested prompts ────────────────────────────────────────────────────

function buildSuggestions(symbol: string, timeframe: string, t?: (key: any) => string): string[] {
  const pool = [
    `Analyze ${symbol} trend on ${timeframe}`,
    `Key support levels for ${symbol}?`,
    `What indicators say about ${symbol}?`,
    `Show me ${symbol} order flow`,
    `${symbol} breakout levels`,
    `Compare ${symbol} with BTC`,
    (t && t("suggestTrend")) || "Analyze recent trend direction",
    (t && t("suggestSupportResistance")) || "Find support and resistance levels",
    (t && t("suggestPatterns")) || "Detect candlestick patterns",
    (t && t("suggestMultiTimeframe")) || "Compare multiple timeframes",
    (t && t("suggestVolume")) || "Check volume confirmation",
    (t && t("suggestIndicators")) || "Explain current indicator signals",
  ];
  const shuffled = [...pool].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 3);
}

// ── Props ────────────────────────────────────────────────────────────────

interface AiChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  mode: AiMode;
  onModeChange: (mode: AiMode) => void;
  loading: boolean;
  /** Force-disable input during walkthrough (prevents new questions mid-tour) */
  disabled?: boolean;
  placeholder: string;
  /** Focus textarea when this key changes */
  focusKey?: number;
  /** Symbol for contextual suggestions */
  symbol?: string;
  /** Timeframe for contextual suggestions */
  timeframe?: string;
  /** Error state — show revert-to-input button */
  error?: string | null;
  /** Called to clear the error and let user retry */
  onClearError?: () => void;
  /** Past user messages for up/down arrow history navigation */
  messageHistory?: string[];
}

// ── Component ────────────────────────────────────────────────────────────

const AiChatInput: React.FC<AiChatInputProps> = ({
  value,
  onChange,
  onSend,
  mode,
  onModeChange,
  loading,
  disabled = false,
  placeholder,
  focusKey,
  symbol = "",
  timeframe = "",
  error,
  onClearError,
  messageHistory,
}) => {
  const { t } = useI18n();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const historyDraftRef = useRef("");
  const suggestions = useMemo(
    () => buildSuggestions(symbol, timeframe, t),
    [symbol, timeframe],
  );

  // Load cached input on mount
  useEffect(() => {
    const cached = loadUnsentInput();
    if (cached && !value) {
      onChange(cached);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-focus on mount and when focusKey changes
  useEffect(() => {
    textareaRef.current?.focus();
    setHistoryIdx(-1);
  }, [focusKey]);

  // Save to cache on change
  useEffect(() => {
    saveUnsentInput(value);
  }, [value]);

  // Show suggestions when user focuses/ties, hide on send
  useEffect(() => {
    if (value.trim().length > 0 && !loading) {
      setShowSuggestions(true);
    }
  }, [value, loading]);

  // Hide suggestions when user sends
  useEffect(() => {
    if (loading) setShowSuggestions(false);
  }, [loading]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        clearUnsentInput();
        setHistoryIdx(-1);
        onSend();
        return;
      }

      const ta = textareaRef.current;
      if (!ta) return;

      // Up arrow at cursor start → navigate backward in message history
      if (event.key === "ArrowUp" && ta.selectionStart === 0 && ta.selectionEnd === 0) {
        const history = messageHistory;
        if (!history || history.length === 0) return;
        event.preventDefault();

        if (historyIdx === -1) {
          historyDraftRef.current = value;
        }
        const nextIdx = historyIdx === -1 ? 0 : Math.min(historyIdx + 1, history.length - 1);
        if (nextIdx !== historyIdx) {
          setHistoryIdx(nextIdx);
          onChange(history[nextIdx]);
        }
        return;
      }

      // Down arrow at cursor end → navigate forward in message history
      if (event.key === "ArrowDown" && ta.selectionStart >= value.length && ta.selectionEnd >= value.length) {
        const history = messageHistory;
        if (!history || history.length === 0) return;
        event.preventDefault();

        if (historyIdx >= 0) {
          if (historyIdx === 0) {
            // Restore draft
            setHistoryIdx(-1);
            onChange(historyDraftRef.current);
          } else {
            const nextIdx = historyIdx - 1;
            setHistoryIdx(nextIdx);
            onChange(history[nextIdx]);
          }
        }
        return;
      }

      // Any other key during history browsing — stay in browse mode
      // Textarea's onChange will catch manual edits and reset historyIdx
    },
    [onSend, messageHistory, historyIdx, value, onChange],
  );

  const handleSend = useCallback(() => {
    clearUnsentInput();
    onSend();
  }, [onSend]);

  const pickSuggestion = useCallback(
    (suggestion: string) => {
      onChange(suggestion);
      setShowSuggestions(false);
    },
    [onChange],
  );

  return (
    <div className="space-y-1.5">
      {/* Error bar with revert */}
      {error && onClearError && (
        <div className="flex items-center gap-2 rounded border border-red-500/25 bg-red-500/10 px-2.5 py-1.5">
          <span className="flex-1 text-[10px] leading-relaxed text-red-200">
            {error}
          </span>
          <button
            type="button"
            onClick={onClearError}
            className="flex items-center gap-1 rounded bg-red-600/50 px-2 py-1 text-[9px] font-semibold text-white hover:bg-red-500"
          >
            <CornerDownLeft size={9} />
            {t("retry") || "Retry"}
          </button>
        </div>
      )}

      {/* Input box */}
      <div className="rounded border border-gray-700 bg-gray-900 transition-colors focus-within:border-blue-500">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setHistoryIdx(-1); // User typed manually — exit history browse
            onChange(e.target.value);
            if (e.target.value.trim()) setShowSuggestions(true);
          }}
          onFocus={() => {
            if (value.trim()) setShowSuggestions(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={loading || disabled}
          rows={2}
          className="min-h-[48px] w-full resize-none rounded-t bg-transparent px-3 py-2 text-xs text-white outline-none placeholder-gray-500 disabled:cursor-not-allowed"
        />

        {/* Suggested prompts (shown while typing, not persistent) */}
        {historyIdx >= 0 && messageHistory && messageHistory.length > 0 && (
          <div className="border-t border-gray-800 px-2 py-1">
            <span className="text-[9px] font-medium text-gray-500">
              {historyIdx + 1} / {messageHistory.length}
            </span>
          </div>
        )}

        {showSuggestions && value.trim().length > 0 && !loading && (
          <div className="border-t border-gray-800 px-2 py-1.5">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[9px] font-semibold uppercase tracking-wide text-gray-600">
                {t("suggestedPrompts")}
              </span>
              <button
                type="button"
                onClick={() => setShowSuggestions(false)}
                className="text-gray-600 hover:text-gray-400"
              >
                <X size={11} />
              </button>
            </div>
            <div className="flex flex-wrap gap-1">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => pickSuggestion(s)}
                  className="rounded border border-gray-800 bg-gray-900 px-2 py-1 text-[10px] text-gray-400 hover:border-blue-500/40 hover:text-white"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Bottom bar: mode toggle + send */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-800 px-2 py-1.5">
          {/* Mode toggle */}
          <label className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[11px] font-semibold text-gray-400">
            <span className={mode === "ask" ? "text-blue-300" : ""}>
              {t("askMode")}
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={mode === "interact"}
              onClick={() => onModeChange(mode === "ask" ? "interact" : "ask")}
              disabled={loading || disabled}
              className={`relative inline-flex h-4 w-7 flex-shrink-0 cursor-pointer items-center rounded-full border border-gray-600 transition-colors duration-200 focus:outline-none ${
                mode === "interact" ? "bg-blue-600" : "bg-gray-700"
              } disabled:cursor-not-allowed disabled:opacity-50`}
            >
              <span
                className={`inline-block h-3 w-3 transform rounded-full bg-white shadow-sm transition-transform duration-200 ${
                  mode === "interact" ? "translate-x-3.5" : "translate-x-0.5"
                }`}
              />
            </button>
            <span className={mode === "interact" ? "text-amber-300" : ""}>
              {t("interactMode")}
            </span>
          </label>

          {/* Send button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={!value.trim() || loading || disabled}
            className="flex items-center gap-1 rounded bg-blue-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? (
              <>
                <Sparkles size={11} className="animate-pulse" />
                {t("thinking")}
              </>
            ) : (
              <>
                <CornerDownLeft size={11} />
                {t("send")}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export { AiChatInput };
export type { AiChatInputProps };
