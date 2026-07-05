/**
 * AiChatMessage — renders a single chat message bubble (full rewrite).
 *
 * Rules:
 * - User messages: right-aligned, blue background
 * - Agent answers: left-aligned, contrast background
 *   Ask mode:     border-gray-800 bg-gray-850
 *   Interact mode: border-amber-700/30 bg-gray-850
 * - Knowledge segments → hat icon (📖) expand/collapse
 * - Number formatting: prices $XX,XXX, percentages +X.XX%
 * - Disclaimer section: separate dropdown below answers
 * - Confidence level with explanation below answer
 * - Interact mode: replay button at end
 */
import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import {
  Bot,
  BookOpen,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Info,
  RotateCcw,
  Shield,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  UserRound,
} from "lucide-react";
import { useI18n } from "@/i18n";
import { DisclaimerSection } from "@/features/ai/components/DisclaimerSection";
import type { AiMessage } from "@/features/ai/types";

// ── Types ─────────────────────────────────────────────────────────────────

interface AiChatMessageProps {
  message: AiMessage;
  isUser: boolean;
  assistantLabel: string;
  isAdmin: boolean;
  /** Rendering mode — controls border style */
  mode?: "ask" | "interact";
  tourRunning?: boolean;
  onReplayTour?: () => void;
  onRate?: (messageId: string, rating: 1 | -1) => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function formatShortTime(dateStr?: string | null): string {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

// ── Markdown content with number formatting ──────────────────────────────

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="ai-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// ── Knowledge Hat Icon ───────────────────────────────────────────────────

function KnowledgeHat({
  chunks,
}: {
  chunks: NonNullable<AiMessage["knowledge_chunks"]>;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  if (chunks.length === 0) return null;

  return (
    <div className="mt-1.5">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1 rounded border border-blue-500/20 bg-blue-500/[0.04] px-1.5 py-0.5 text-[10px] text-blue-300 hover:border-blue-500/40"
        title={t("knowledgeSourcesUsed") || "Knowledge sources used"}
      >
        <BookOpen size={11} />
        {chunks.length} source{chunks.length !== 1 ? "s" : ""}
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>

      {open && (
        <div className="mt-1 space-y-1 rounded border border-blue-500/10 bg-blue-500/[0.02] p-2">
          {chunks.map((chunk, idx) => (
            <div key={idx} className="text-[10px] leading-relaxed text-gray-400">
              <div className="flex items-center gap-1 font-medium text-gray-300">
                <ExternalLink size={8} />
                {chunk.title || chunk.source}
                {chunk.credibility_level && (
                  <span
                    className={`rounded px-1 text-[8px] font-semibold ${
                      chunk.credibility_level === "high"
                        ? "bg-emerald-500/15 text-emerald-300"
                        : chunk.credibility_level === "medium"
                          ? "bg-blue-500/15 text-blue-300"
                          : "bg-gray-700 text-gray-400"
                    }`}
                  >
                    {chunk.credibility_level}
                  </span>
                )}
                <span className="text-gray-600">
                  {(chunk.score * 100).toFixed(0)}%
                </span>
              </div>
              {chunk.heading && (
                <p className="pl-3 text-[9px] text-gray-600">{chunk.heading}</p>
              )}
              <p className="mt-0.5 pl-3 text-gray-500">{chunk.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Structured Response Sections ────────────────────────────────────────

function normalizeSectionText(value: string): string {
  return value
    .replace(/\s+/g, " ")
    .replace(/[*_`#>\-]/g, "")
    .trim()
    .toLowerCase();
}

function ResponseSections({
  sections,
  messageContent,
}: {
  sections: NonNullable<AiMessage["response_sections"]>;
  messageContent: string;
}) {
  const visibleSections = sections.filter(
    (section) =>
      section.content.trim() &&
      normalizeSectionText(section.content) !== normalizeSectionText(messageContent),
  );
  const [open, setOpen] = useState<Record<number, boolean>>({ 0: true });
  if (visibleSections.length === 0) return null;

  return (
    <div className="mt-2 space-y-1.5">
      {visibleSections.map((section, idx) => (
        <div key={`${section.title}-${idx}`} className="rounded border border-gray-800 bg-gray-900/50">
          <button
            type="button"
            onClick={() => setOpen((prev) => ({ ...prev, [idx]: !prev[idx] }))}
            className="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-left text-[10px] font-semibold text-gray-300 hover:text-gray-100"
          >
            <span>{section.title || `Section ${idx + 1}`}</span>
            {open[idx] ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          </button>
          {open[idx] && (
            <div className="border-t border-gray-800 px-2 py-1.5 text-[11px] leading-5 text-gray-300">
              <MarkdownContent content={section.content} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Confidence Display ──────────────────────────────────────────────────

function ConfidenceBadge({
  confidence,
}: {
  confidence: number;
}) {
  const { t } = useI18n();
  const label =
    confidence >= 0.7
      ? (t("confidenceHigh") || "High")
      : confidence >= 0.4
        ? (t("confidenceMedium") || "Medium")
        : (t("confidenceLow") || "Low");

  const colorClass =
    confidence >= 0.7
      ? "text-emerald-300 border-emerald-500/30 bg-emerald-500/10"
      : confidence >= 0.4
        ? "text-blue-300 border-blue-500/30 bg-blue-500/10"
        : "text-amber-300 border-amber-500/30 bg-amber-500/10";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] font-medium ${colorClass}`}
      title={`Confidence: ${(confidence * 100).toFixed(0)}%. Derived from expert consensus and data freshness.`}
    >
      <Shield size={9} />
      {(confidence * 100).toFixed(0)}% · {label}
    </span>
  );
}

// ── Confidence Display ──────────────────────────────────────────────────

function AdminDebug({ message }: { message: AiMessage }) {
  const [open, setOpen] = useState(false);
  if (!message.confidence && !message.provider_metadata && !message.token_input) return null;

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-[9px] text-gray-600 hover:text-gray-400"
      >
        <Info size={9} />
        Debug
        {open ? <ChevronUp size={9} /> : <ChevronDown size={9} />}
      </button>
      {open && (
        <div className="mt-0.5 space-y-0.5 rounded border border-dashed border-gray-800 bg-gray-900 p-2 text-[9px] text-gray-500">
          {message.confidence != null && (
            <div>Confidence: {(message.confidence * 100).toFixed(0)}%</div>
          )}
          {message.token_input != null && message.token_output != null && (
            <div>
              Tokens: {message.token_input} → {message.token_output}
              {message.estimated_cost_usd != null && (
                <span className="text-green-500">
                  {" "}${message.estimated_cost_usd.toFixed(4)}
                </span>
              )}
            </div>
          )}
          {message.provider_metadata && (
            <div>
              Provider: {String(
                (message.provider_metadata as Record<string, unknown>)
                  .effective_provider || "?",
              )}{" "}
              / {String(
                (message.provider_metadata as Record<string, unknown>)
                  .model || "?",
              )}{" "}
              ({String(
                (message.provider_metadata as Record<string, unknown>)
                  .latency_ms || "?",
              )})
            </div>
          )}
          {message.sources && message.sources.length > 0 && (
            <div>
              Sources: {message.sources.length}
              {message.sources.slice(0, 5).map((s, i) => (
                <div key={i} className="pl-2">
                  · {s.title} ({(s.score || 0) * 100}%)
                </div>
              ))}
            </div>
          )}
          {message.warnings && message.warnings.length > 0 && (
            <div className="text-amber-400/70">
              {message.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────

const AiChatMessage: React.FC<AiChatMessageProps> = ({
  message,
  isUser,
  assistantLabel,
  isAdmin,
  mode,
  tourRunning,
  onReplayTour,
  onRate,
}) => {
  const { t } = useI18n();

  const hasTourPlan = !!message.tour_plan && !!message.tour_plan.steps?.length;
  // During active walkthrough: show content + walkthrough badge
  // After completion: show content + Replay button
  const isActiveWalkthrough = hasTourPlan && tourRunning;
  const isCompletedWalkthrough = hasTourPlan && !tourRunning;

  // Bubble style — always standard mode-based, no emerald recap
  const userBubble = "bg-blue-600 text-white rounded-2xl rounded-tr-sm";
  const askBubble =
    "border border-gray-800 bg-gray-850 text-gray-200 rounded-2xl rounded-tl-sm";
  const interactBubble =
    "border border-amber-700/30 bg-gray-850 text-gray-200 rounded-2xl rounded-tl-sm";
  const bubbleStyle = isUser
    ? userBubble
    : (message.mode || mode) === "interact"
      ? interactBubble
      : askBubble;

  return (
    <div
      key={message.id}
      data-testid={`ai-message-${message.id}`}
      className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {/* Avatar (assistant only) */}
      {!isUser && (
        <div className="mt-1 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-blue-500/10 text-blue-300">
          <Bot size={13} />
        </div>
      )}

      <div className={`max-w-[88%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Label row */}
        <div
          className={`mb-1 flex items-center gap-1.5 text-[10px] text-gray-500 ${
            isUser ? "justify-end" : ""
          }`}
        >
          {isUser ? <UserRound size={10} /> : <Sparkles size={10} />}
          <span>{isUser ? t("you") : assistantLabel}</span>
          {message.created_at && (
            <span className="text-[9px] text-gray-600">
              {formatShortTime(message.created_at)}
            </span>
          )}
          {!isUser && (message.mode || mode) && (
            <span
              className={`rounded px-1 text-[8px] font-semibold ${
                (message.mode || mode) === "interact"
                  ? "bg-amber-500/10 text-amber-300"
                  : "bg-blue-500/10 text-blue-300"
              }`}
            >
              {(message.mode || mode) === "interact" ? t("interactMode") : t("askMode")}
            </span>
          )}
        </div>

        {/* Bubble */}
        <div className={`max-w-full px-3.5 py-2.5 text-xs leading-6 shadow-sm ${bubbleStyle}`}>
          {isActiveWalkthrough ? (
            <>
              <MarkdownContent content={message.content} />
              <div className="mt-2 flex items-center gap-1.5 text-[10px] text-amber-400/70">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
                {t("walkthroughInProgress") || "Walkthrough in progress..."}
              </div>
            </>
          ) : isCompletedWalkthrough ? (
            <>
              <MarkdownContent content={message.content} />
              {onReplayTour && (
                <div className="mt-2 flex items-center gap-2 border-t border-amber-500/20 pt-2">
                  <button
                    type="button"
                    onClick={onReplayTour}
                    disabled={tourRunning}
                    className="flex items-center gap-1 rounded bg-amber-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-amber-500 disabled:opacity-50"
                    data-testid="ai-tour-replay"
                  >
                    <RotateCcw size={10} />
                    {t("replay")}
                  </button>
                </div>
              )}
            </>
          ) : (
            <MarkdownContent content={message.content} />
          )}
          {!isUser && message.response_sections && message.response_sections.length > 0 && (
            <ResponseSections sections={message.response_sections} messageContent={message.content} />
          )}
        </div>

        {/* Knowledge hat icon (for KB-backed responses) */}
        {!isUser &&
          message.knowledge_chunks &&
          message.knowledge_chunks.length > 0 && (
            <KnowledgeHat chunks={message.knowledge_chunks} />
          )}

        {/* Confidence badge */}
        {!isUser && message.confidence != null && (
          <div className="mt-1 flex items-center gap-1.5">
            <ConfidenceBadge confidence={message.confidence} />
          </div>
        )}

        {/* Disclaimer section */}
        {!isUser && (
          <DisclaimerSection
            caveats={message.data_caveats}
            isInteract={(message.mode || mode) === "interact"}
          />
        )}

        {/* Rating buttons (only for API responses) */}
        {!isUser && message.id.startsWith("api-") && onRate && (
          <div className="mt-1.5 flex items-center gap-2">
            <button
              onClick={() => onRate(message.id, 1)}
              className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] text-gray-500 transition-colors hover:bg-emerald-500/10 hover:text-emerald-300"
              title={t("ratingHelpful") || "Helpful"}
            >
              <ThumbsUp size={10} />
            </button>
            <button
              onClick={() => onRate(message.id, -1)}
              className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] text-gray-500 transition-colors hover:bg-red-500/10 hover:text-red-300"
              title={t("ratingNotHelpful") || "Not helpful"}
            >
              <ThumbsDown size={10} />
            </button>
          </div>
        )}

        {/* Admin debug panel */}
        {isAdmin && !isUser && <AdminDebug message={message} />}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="mt-1 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gray-800 text-gray-300">
          <UserRound size={13} />
        </div>
      )}
    </div>
  );
};

export { AiChatMessage };
export type { AiChatMessageProps };
