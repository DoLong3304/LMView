import React, { useState, useMemo } from "react";
import {
  ArrowLeftRight,
  Bot,
  BookOpen,
  Star,
  Search,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useI18n } from "@/i18n";
import { useSymbolMeta } from "@/hooks/useSymbolMeta";
import { DEFAULT_SYMBOL_ICON } from "@/services/symbolMetaService";
import OrderBook from "@/features/market/components/OrderBook";
import RecentTrades from "@/features/market/components/RecentTrades";
import AiAssistantPanel from "@/features/ai/components/AiAssistantPanel";
import type { WatchlistItem, Candle } from "@/types";
import type { TranslationKey } from "@/i18n/translations";

type RightPanelTopTab = "overview" | "aiHelper";
type RightPanelTab = "watchlist" | "orderBook" | "recentTrades";

const TOP_TABS: Array<{
  id: RightPanelTopTab;
  labelKey: TranslationKey;
  icon: LucideIcon;
}> = [
  { id: "overview", labelKey: "overview", icon: TrendingUp },
  { id: "aiHelper", labelKey: "aiHelper", icon: Bot },
];

const PANEL_TABS: Array<{
  id: RightPanelTab;
  labelKey: TranslationKey;
  icon: LucideIcon;
}> = [
  { id: "watchlist", labelKey: "watchlist", icon: Star },
  { id: "orderBook", labelKey: "orderBook", icon: BookOpen },
  { id: "recentTrades", labelKey: "recentTrades", icon: ArrowLeftRight },
];

interface RightPanelProps {
  items: WatchlistItem[];
  selectedSymbol: string;
  starredSymbols: string[];
  onSymbolSelect: (symbol: string) => void;
  onToggleStar: (symbol: string) => void;
  width?: number;
  candles?: Candle[];
  timeframe?: string;
}

const RightPanel: React.FC<RightPanelProps> = ({
  items,
  selectedSymbol,
  starredSymbols,
  onSymbolSelect,
  onToggleStar,
  width = 286,
  candles = [],
  timeframe = "1m",
}) => {
  const { t } = useI18n();
  const { getMeta } = useSymbolMeta();
  const [filter, setFilter] = useState<"all" | "starred">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTopTab, setActiveTopTab] = useState<RightPanelTopTab>("overview");
  const [activeTab, setActiveTab] = useState<RightPanelTab>("watchlist");


  // Sort: starred first, then by % change (gainers → losers)
  const sortedItems = useMemo(() => {
    const filtered = items.filter((item) => {
      const matchesFilter = filter === "all" || starredSymbols.includes(item.symbol);
      const matchesSearch = item.symbol.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
    });

    return [...filtered].sort((a, b) => {
      const aStarred = starredSymbols.includes(a.symbol);
      const bStarred = starredSymbols.includes(b.symbol);

      // Starred items first
      if (aStarred && !bStarred) return -1;
      if (!aStarred && bStarred) return 1;

      // Then sort by % change (descending - gainers first)
      const aChange = a.change || 0;
      const bChange = b.change || 0;
      return bChange - aChange;
    });
  }, [items, filter, searchQuery, starredSymbols]);

  // Get selected item data for CoinSummary
  const selectedItem = useMemo(() => {
    return items.find(item => item.symbol === selectedSymbol);
  }, [items, selectedSymbol]);

  const meta = getMeta(selectedSymbol);
  const isUp = (selectedItem?.change ?? 0) >= 0;

  const formatPrice = (p: number) => {
    if (p >= 1000) return p.toLocaleString(undefined, { maximumFractionDigits: 2 });
    if (p >= 1) return p.toFixed(4);
    return p.toFixed(6);
  };

  // Overview chart calculations
  const lastCandle = candles[candles.length - 1];
  const firstCandle = candles[0];
  const high24 = candles.length > 0 ? Math.max(...candles.map((c) => c.high)) : 0;
  const low24 = candles.length > 0 ? Math.min(...candles.map((c) => c.low)) : 0;
  const totalVol = candles.reduce((s, c) => s + c.volume, 0);

  // Mini sparkline
  const sparklineData = useMemo(() => {
    if (candles.length === 0) return { points: "", color: "#888" };

    const prices = candles.map((c) => c.close);
    const minP = Math.min(...prices);
    const maxP = Math.max(...prices);
    const pRange = maxP - minP || 1;
    const w = 220;
    const h = 38;

    const points = prices
      .filter((_, i) => i % Math.max(1, Math.floor(prices.length / 100)) === 0)
      .map((p, i, arr) => {
        const x = (i / (arr.length - 1)) * w;
        const y = h - ((p - minP) / pRange) * h;
        return `${x},${y}`;
      })
      .join(" ");

    return { points, color: isUp ? "#26a69a" : "#ef5350" };
  }, [candles, isUp]);

  const f = (v: number | null | undefined) =>
    v != null
      ? v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : "-";
  const fCompact = (v: number) => {
    if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
    if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
    if (v >= 1e3) return (v / 1e3).toFixed(1) + "K";
    return v.toFixed(2);
  };

  // Price position within range
  const rangeSpan = high24 - low24 || 1;
  const positionPct = lastCandle ? ((lastCandle.close - low24) / rangeSpan) * 100 : 50;

  return (
    <div
      className="bg-gray-900 border-l border-gray-700 flex h-full min-w-0 flex-col overflow-hidden"
      style={{ width, minWidth: width, maxWidth: "100%" }}
    >
      <div className="grid grid-cols-2 gap-1 border-b border-gray-800 bg-gray-900 px-1.5 py-1.5">
        {TOP_TABS.map(({ id, labelKey, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setActiveTopTab(id)}
            className={`flex min-w-0 items-center justify-center gap-1.5 rounded px-2 py-1.5 text-xs font-semibold transition-colors ${
              activeTopTab === id
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
            title={t(labelKey)}
          >
            <Icon size={13} />
            <span className="truncate">{t(labelKey)}</span>
          </button>
        ))}
      </div>

      {activeTopTab === "aiHelper" ? (
        <AiAssistantPanel
          selectedSymbol={selectedSymbol}
          timeframe={timeframe}
          candles={candles}
        />
      ) : (
        <>
      {/* Coin Summary - Fixed at top */}
      <div className="px-2.5 py-2 border-b border-gray-800 bg-gray-850">
        {/* Symbol header */}
        <div className="flex items-center gap-1.5 mb-1.5">
          <img
            src={meta.icon}
            alt={meta.name}
            className="w-5 h-5 rounded-full"
            onError={(e) => {
              e.currentTarget.src = DEFAULT_SYMBOL_ICON;
            }}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-white">{selectedSymbol}</span>
              {meta?.name && (
                <span className="text-xs text-gray-500 truncate">{meta.name}</span>
              )}
            </div>
          </div>
          <div className={`flex items-center gap-1 ${isUp ? "text-green-400" : "text-red-400"}`}>
            {isUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
            <span className="text-xs font-medium">
              {isUp ? "+" : ""}{(selectedItem?.change ?? 0).toFixed(2)}%
            </span>
          </div>
        </div>

        {/* Price */}
        <div className="flex items-baseline gap-2">
          <span className={`text-lg font-bold font-mono ${isUp ? "text-green-400" : "text-red-400"}`}>
            ${formatPrice(selectedItem?.price ?? 0)}
          </span>
        </div>
      </div>

      {/* Mini Sparkline */}
      {candles.length > 0 && (
        <div className="px-2.5 py-1.5 border-b border-gray-800 bg-gray-850">
          <svg viewBox="0 0 220 38" className="w-full" style={{ height: 38 }}>
            <defs>
              <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={sparklineData.color} stopOpacity={0.25} />
                <stop offset="100%" stopColor={sparklineData.color} stopOpacity={0} />
              </linearGradient>
            </defs>
            {sparklineData.points && (
              <>
                <polygon
                  points={`0,38 ${sparklineData.points} 220,38`}
                  fill="url(#spark-grad)"
                />
                <polyline
                  points={sparklineData.points}
                  fill="none"
                  stroke={sparklineData.color}
                  strokeWidth="1.5"
                />
              </>
            )}
          </svg>
        </div>
      )}

      {/* 24h Range */}
      {candles.length > 0 && (
        <div className="px-2.5 py-1.5 border-b border-gray-800 bg-gray-850">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>{t("low24h")}</span>
            <span>{t("high24h")}</span>
          </div>
          <div className="relative h-1.5 bg-gray-700 rounded-full">
            <div
              className={`absolute top-0 left-0 h-full rounded-full ${isUp ? "bg-green-500" : "bg-red-500"}`}
              style={{ width: `${positionPct}%` }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white border border-gray-900"
              style={{ left: `${positionPct}%`, transform: "translate(-50%, -50%)" }}
            />
          </div>
          <div className="flex justify-between text-xs font-mono text-gray-400 mt-1">
            <span>{f(low24)}</span>
            <span>{f(high24)}</span>
          </div>
        </div>
      )}

      {/* OHLCV Stats */}
      {candles.length > 0 && lastCandle && (
        <div className="px-2.5 py-1.5 border-b border-gray-800 bg-gray-850">
          <div className="grid grid-cols-2 gap-x-1.5 gap-y-1 text-[11px]">
            <div className="flex justify-between">
              <span className="text-gray-500">{t("open")}</span>
              <span className="font-mono text-gray-300">{f(firstCandle.open)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">{t("high")}</span>
              <span className="font-mono text-green-400">{f(lastCandle.high)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">{t("close")}</span>
              <span className={`font-mono ${isUp ? "text-green-400" : "text-red-400"}`}>{f(lastCandle.close)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">{t("low")}</span>
              <span className="font-mono text-red-400">{f(lastCandle.low)}</span>
            </div>
            <div className="flex justify-between col-span-2">
              <span className="text-gray-500">{t("volume24h")}</span>
              <span className="font-mono text-gray-300">{fCompact(totalVol)}</span>
            </div>
          </div>
        </div>
      )}

      <div className="border-b border-gray-800 bg-gray-900 px-1 py-1">
        <div className="grid grid-cols-3 overflow-hidden rounded border border-gray-800 bg-gray-850">
        {PANEL_TABS.map(({ id, labelKey, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex min-w-0 items-center justify-center gap-0.5 border-r border-gray-800 px-0.5 py-1 text-[9px] font-medium leading-none transition-colors last:border-r-0 ${
              activeTab === id
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
            title={t(labelKey)}
          >
            <Icon size={10} className={id === "watchlist" && activeTab === id ? "fill-white" : ""} />
            <span className="truncate">{t(labelKey)}</span>
          </button>
        ))}
        </div>
      </div>

      {activeTab === "watchlist" && (
        <>
      {/* Filter tabs */}
      <div className="px-2 py-1.5 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <div className="flex-1 relative">
            <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("searchSymbol")}
              className="w-full pl-8 pr-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex gap-1">
            <button
              onClick={() => setFilter("all")}
              className={`px-1.5 py-1 rounded text-xs transition-colors ${
                filter === "all"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              {t("all")}
            </button>
            <button
              onClick={() => setFilter("starred")}
              className={`px-1.5 py-1 rounded text-xs transition-colors ${
                filter === "starred"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              <Star size={12} className={filter === "starred" ? "fill-white" : ""} />
            </button>
          </div>
        </div>
      </div>

      {/* Watchlist - Scrollable, no pagination */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {sortedItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500 text-sm">
            <Star size={24} className="mb-2 opacity-50" />
            {filter === "starred" ? t("noStarredSymbols") : t("noSymbols")}
          </div>
        ) : (
          sortedItems.map((item) => {
            const isSelected = item.symbol === selectedSymbol;
            const isStarred = starredSymbols.includes(item.symbol);
            const priceChange = item.change || 0;
            const itemUp = priceChange >= 0;

            return (
              <div
                key={item.symbol}
                onClick={() => onSymbolSelect(item.symbol)}
                className={`px-2.5 py-1.5 border-b border-gray-800 cursor-pointer transition-colors ${
                  isSelected ? "bg-gray-800" : "hover:bg-gray-800"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleStar(item.symbol);
                      }}
                      className="text-gray-500 hover:text-yellow-400 transition-colors p-0.5"
                    >
                      <Star
                        size={12}
                        className={isStarred ? "fill-yellow-400 text-yellow-400" : ""}
                      />
                    </button>
                    <span className="truncate text-xs font-medium text-white">{item.symbol}</span>
                  </div>
                  <div className={`flex flex-shrink-0 items-center gap-1 text-xs ${itemUp ? "text-green-400" : "text-red-400"}`}>
                    <span className="font-medium">
                      {itemUp ? "+" : ""}{priceChange.toFixed(2)}%
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between pl-5">
                  <span className={`text-xs font-mono ${item.color === "green" ? "text-green-400" : item.color === "red" ? "text-red-400" : "text-gray-500"}`}>
                    {item.price > 0 ? item.price.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 6,
                    }) : "—"}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
        </>
      )}

      {activeTab === "orderBook" && (
        <div className="flex-1 min-h-0 overflow-hidden">
          <OrderBook symbol={selectedSymbol} />
        </div>
      )}

      {activeTab === "recentTrades" && (
        <div className="flex-1 min-h-0 overflow-hidden">
          <RecentTrades symbol={selectedSymbol} />
        </div>
      )}
        </>
      )}
    </div>
  );
};

export default RightPanel;
