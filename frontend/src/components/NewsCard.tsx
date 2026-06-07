import React from "react";
import type { NewsArticle } from "@/types";

const SENTIMENT_CONFIG = {
  bullish: { color: "text-green-400", bg: "bg-green-500/10 border-green-500/30", label: "↑ Tích cực" },
  bearish: { color: "text-red-400", bg: "bg-red-500/10 border-red-500/30", label: "↓ Tiêu cực" },
  neutral: { color: "text-gray-400", bg: "bg-gray-500/10 border-gray-500/30", label: "— Trung tính" },
} as const;

interface Props {
  article: NewsArticle;
}

function formatTimeAgo(value: number | string): string {
  const ts = typeof value === "string" ? Date.parse(value) : value;
  const diffMs = Date.now() - ts;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}p trước`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h trước`;
  return `${Math.floor(diffH / 24)}d trước`;
}

export function NewsCard({ article }: Props) {
  const key = (article.sentiment_label || "neutral").toLowerCase() as keyof typeof SENTIMENT_CONFIG;
  const cfg = SENTIMENT_CONFIG[key] || SENTIMENT_CONFIG.neutral;
  const symbols = article.symbolsMentioned || article.symbols || [];

  return (
    <div className="rounded border border-gray-700 bg-gray-850 p-3 hover:border-blue-500 transition-colors">
      <div className="mb-2 flex items-center justify-between gap-2 text-xs text-gray-400">
        <span>{article.source} · {formatTimeAgo(article.published_at)}</span>
        <span className={`rounded border px-2 py-0.5 text-xs font-medium ${cfg.color} ${cfg.bg}`}>
          {cfg.label} ({article.sentiment_score > 0 ? "+" : ""}{article.sentiment_score.toFixed(2)})
        </span>
      </div>
      <a href={article.url} target="_blank" rel="noopener noreferrer" className="block text-sm font-semibold text-white hover:text-blue-400">
        {article.title}
      </a>
      <p className="mt-1 line-clamp-2 text-xs text-gray-400">{article.summary}</p>
      {symbols.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {symbols.slice(0, 5).map((symbol) => (
            <span key={symbol} className="rounded bg-blue-900/30 px-2 py-0.5 text-[10px] text-blue-400">
              {symbol}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
