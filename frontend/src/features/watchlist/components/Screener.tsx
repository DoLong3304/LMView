import React, { useState, useMemo, useCallback } from "react";
import {
  Search,
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
  BarChart3,
  Target,
} from "lucide-react";
import { useI18n } from "@/i18n";
import type {
  WatchlistFilter,
  WatchlistSortKey,
  WatchlistSortDir,
  ScreenerPreset,
  EnhancedWatchlistItem,
} from "@/types";

interface ScreenerProps {
  /** Called when user selects a symbol */
  onSymbolSelect?: (symbol: string) => void;
  /** Initial filter presets to apply */
  initialFilter?: WatchlistFilter;
  /** Title for the component */
  title?: string;
  /** Data items to display */
  items?: EnhancedWatchlistItem[];
}

/** Screener presets */
const PRESETS: ScreenerPreset[] = [
  {
    id: "oversold",
    name: "Oversold",
    description: "RSI below 30",
    filters: { rsiRange: { min: 0, max: 30 } },
  },
  {
    id: "overbought",
    name: "Overbought",
    description: "RSI above 70",
    filters: { rsiRange: { min: 70, max: 100 } },
  },
  {
    id: "high_volume",
    name: "High Volume",
    description: "Above average volume",
    filters: { minVolume: 1e8 },
  },
  {
    id: "top_gainers",
    name: "Top Gainers",
    description: "Best performing",
    filters: { changeRange: { min: 5, max: 100 } },
  },
  {
    id: "top_losers",
    name: "Top Losers",
    description: "Worst performing",
    filters: { changeRange: { min: -100, max: -5 } },
  },
  {
    id: "strong_bullish",
    name: "Strong Bullish",
    description: "Bullish trend, high volume",
    filters: {
      trends: ["bullish"],
      minVolume: 1e7,
    },
  },
  {
    id: "strong_bearish",
    name: "Strong Bearish",
    description: "Bearish trend",
    filters: { trends: ["bearish"] },
  },
];

const Screener: React.FC<ScreenerProps> = ({
  items = [],
  initialFilter,
  title = "Screener",
}) => {
  const { t } = useI18n();
  const [filter, setFilter] = useState<WatchlistFilter>(initialFilter || {});
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sort, setSort] = useState<{ key: WatchlistSortKey; dir: WatchlistSortDir }>({
    key: "change24h",
    dir: "desc",
  });

  // Apply preset
  const applyPreset = useCallback((preset: ScreenerPreset) => {
    setFilter(preset.filters);
    setActivePreset(preset.id);
  }, []);

  // Clear all filters
  const clearAll = useCallback(() => {
    setFilter({});
    setActivePreset(null);
    setSearchQuery("");
  }, []);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return (
      searchQuery ||
      (filter.categories?.length ?? 0) > 0 ||
      filter.minVolume != null ||
      filter.minPrice != null ||
      filter.maxPrice != null ||
      filter.rsiRange != null ||
      filter.changeRange != null ||
      (filter.trends?.length ?? 0) > 0 ||
      filter.isNewListing ||
      filter.isActive !== undefined
    );
  }, [searchQuery, filter]);

  // Apply filter + sort to items
  const filteredItems = useMemo(() => {
    let result = [...items];

    // Search filter
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (item) =>
          item.symbol.toLowerCase().includes(q) ||
          (item.name ?? "").toLowerCase().includes(q)
      );
    }

    // Price range filter
    if (filter.minPrice != null) {
      result = result.filter((item) => (item.price ?? 0) >= filter.minPrice!);
    }
    if (filter.maxPrice != null) {
      result = result.filter((item) => (item.price ?? 0) <= filter.maxPrice!);
    }

    // Volume filter
    if (filter.minVolume != null) {
      result = result.filter((item) => (item.volume24h ?? 0) >= filter.minVolume!);
    }

    // Change range filter
    if (filter.changeRange) {
      result = result.filter(
        (item) =>
          (item.change24h ?? 0) >= filter.changeRange!.min &&
          (item.change24h ?? 0) <= filter.changeRange!.max
      );
    }

    // Trend filter
    if (filter.trends?.length) {
      result = result.filter((item) => {
        const change = item.change24h ?? 0;
        const itemTrend =
          change > 2 ? "bullish" : change < -2 ? "bearish" : "neutral";
        return filter.trends!.includes(itemTrend as "bullish" | "bearish" | "neutral");
      });
    }

    // RSI filter
    if (filter.rsiRange) {
      result = result.filter(
        (item) =>
          item.rsi14 != null &&
          item.rsi14 >= filter.rsiRange!.min &&
          item.rsi14 <= filter.rsiRange!.max
      );
    }

    // Sort
    result.sort((a, b) => {
      let aVal = 0;
      let bVal = 0;
      switch (sort.key) {
        case "change24h":
          aVal = a.change24h ?? 0;
          bVal = b.change24h ?? 0;
          break;
        case "volume24h":
          aVal = a.volume24h ?? 0;
          bVal = b.volume24h ?? 0;
          break;
        case "price":
          aVal = a.price ?? 0;
          bVal = b.price ?? 0;
          break;
        case "marketCap":
          aVal = a.marketCap ?? 0;
          bVal = b.marketCap ?? 0;
          break;
        case "rsi14":
          aVal = a.rsi14 ?? 50;
          bVal = b.rsi14 ?? 50;
          break;
        default:
          aVal = a.change24h ?? 0;
          bVal = b.change24h ?? 0;
      }
      const diff = aVal - bVal;
      return sort.dir === "desc" ? -diff : diff;
    });

    return result;
  }, [items, filter, searchQuery, sort]);

  return (
    <div className="flex h-full">
      {/* Filter Panel - Left Sidebar */}
      <div className="w-72 flex-shrink-0 border-r border-gray-800 overflow-y-auto bg-gray-900">
        <div className="p-4 space-y-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Target size={16} />
            {title}
          </h2>

          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("searchSymbol")}
              className="w-full pl-8 pr-3 py-2 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Presets */}
          <div>
            <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1">
              <Zap size={12} />
              {t("presets")}
            </h3>
            <div className="space-y-1">
              {PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  onClick={() => applyPreset(preset)}
                  className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-xs transition-colors ${
                    activePreset === preset.id
                      ? "bg-blue-600 text-white"
                      : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                  }`}
                >
                  <span>{t(preset.name.toLowerCase().replace(/ /g, "_") as Parameters<typeof t>[0]) || preset.name}</span>
                  {activePreset === preset.id && (
                    <Zap size={10} className="text-yellow-400" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Price Range Filter */}
          <div>
            <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1">
              <BarChart3 size={12} />
              {t("priceRange")}
            </h3>
            <div className="flex gap-2">
              <input
                type="number"
                value={filter.minPrice ?? ""}
                onChange={(e) =>
                  setFilter((f) => ({
                    ...f,
                    minPrice: e.target.value ? parseFloat(e.target.value) : undefined,
                  }))
                }
                placeholder={t("min")}
                className="w-1/2 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <input
                type="number"
                value={filter.maxPrice ?? ""}
                onChange={(e) =>
                  setFilter((f) => ({
                    ...f,
                    maxPrice: e.target.value ? parseFloat(e.target.value) : undefined,
                  }))
                }
                placeholder={t("max")}
                className="w-1/2 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Volume Filter */}
          <div>
            <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1">
              {t("volume24h")}
            </h3>
            <div className="flex gap-2">
              <input
                type="number"
                value={filter.minVolume ?? ""}
                onChange={(e) =>
                  setFilter((f) => ({
                    ...f,
                    minVolume: e.target.value ? parseFloat(e.target.value) : undefined,
                  }))
                }
                placeholder={`≥ ${t("volume")}`}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Change Range Filter */}
          <div>
            <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1">
              {t("change24h")}
            </h3>
            <div className="flex gap-2">
              <input
                type="number"
                value={filter.changeRange?.min ?? ""}
                onChange={(e) =>
                  setFilter((f) => ({
                    ...f,
                    changeRange: {
                      min: e.target.value ? parseFloat(e.target.value) : -100,
                      max: f.changeRange?.max ?? 100,
                    },
                  }))
                }
                placeholder={t("min")}
                className="w-1/2 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <input
                type="number"
                value={filter.changeRange?.max ?? ""}
                onChange={(e) =>
                  setFilter((f) => ({
                    ...f,
                    changeRange: {
                      min: f.changeRange?.min ?? -100,
                      max: e.target.value ? parseFloat(e.target.value) : 100,
                    },
                  }))
                }
                placeholder={t("max")}
                className="w-1/2 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Trend Filter */}
          <div>
            <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1">
              {t("trend")}
            </h3>
            <div className="flex flex-wrap gap-1">
              {(["bullish", "bearish", "neutral"] as const).map((trend) => {
                const active = filter.trends?.includes(trend) ?? false;
                return (
                  <button
                    key={trend}
                    onClick={() =>
                      setFilter((f) => {
                        const current = f.trends ?? [];
                        const next = active
                          ? current.filter((t) => t !== trend)
                          : [...current, trend];
                        return { ...f, trends: next.length > 0 ? next : undefined };
                      })
                    }
                    className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-[10px] transition-colors ${
                      active
                        ? trend === "bullish"
                          ? "bg-green-600 text-white"
                          : trend === "bearish"
                          ? "bg-red-600 text-white"
                          : "bg-gray-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    }`}
                  >
                    {trend === "bullish" && <TrendingUp size={10} />}
                    {trend === "bearish" && <TrendingDown size={10} />}
                    {trend === "neutral" && <Minus size={10} />}
                    {t(trend) || trend}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Clear All */}
          {hasActiveFilters && (
            <button
              onClick={clearAll}
              className="w-full py-2 bg-gray-800 rounded text-xs text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
            >
              {t("clearAll")}
            </button>
          )}
        </div>
      </div>

      {/* Results Area - Right Side */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Sort Controls */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 bg-gray-850">
          <span className="text-xs text-gray-500">{t("sortBy")}:</span>
          <select
            value={sort.key}
            onChange={(e) => setSort({ ...sort, key: e.target.value as WatchlistSortKey })}
            className="px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white focus:outline-none focus:border-blue-500"
          >
            <option value="change24h">{t("change24h")}</option>
            <option value="volume24h">{t("volume")}</option>
            <option value="price">{t("price")}</option>
            <option value="marketCap">{t("marketCap")}</option>
            <option value="rsi14">{t("rsi")}</option>
          </select>
          <button
            onClick={() => setSort({ ...sort, dir: sort.dir === "asc" ? "desc" : "asc" })}
            className="p-1.5 bg-gray-800 border border-gray-700 rounded hover:bg-gray-700"
            title={sort.dir === "asc" ? "Ascending" : "Descending"}
          >
            {sort.dir === "asc" ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          </button>
        </div>

        {/* Results count */}
        <div className="px-4 py-2 text-xs text-gray-500 border-b border-gray-800">
          <span>{filteredItems.length} {t("results") || "results"}</span>
          {hasActiveFilters && (
            <span className="ml-2 text-blue-400">
              {searchQuery && ` "${searchQuery}"`}
              {filter.rsiRange && ` RSI ${filter.rsiRange.min}-${filter.rsiRange.max}`}
              {filter.changeRange && ` ${t("change24h")} ${filter.changeRange.min}% - ${filter.changeRange.max}%`}
              {filter.trends?.length && ` ${t("trend")}: ${filter.trends.join(", ")}`}
            </span>
          )}
        </div>

        {/* Results list */}
        <div className="flex-1 overflow-y-auto">
          {filteredItems.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500 text-sm">
              <div className="text-center">
                <BarChart3 size={32} className="mx-auto mb-2 opacity-50" />
                <p>{t("noData") || "No results"}</p>
                <p className="text-xs mt-1">{t("applyFiltersToSeeResults")}</p>
              </div>
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-850 border-b border-gray-800">
                <tr className="text-gray-400">
                  <th className="text-left px-4 py-2 font-medium">{t("symbol") || "Symbol"}</th>
                  <th className="text-right px-4 py-2 font-medium">{t("price") || "Price"}</th>
                  <th className="text-right px-4 py-2 font-medium">{t("change24h") || "24h %"}</th>
                  <th className="text-right px-4 py-2 font-medium">{t("volume") || "Volume"}</th>
                  <th className="text-center px-4 py-2 font-medium">{t("trend") || "Trend"}</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.slice(0, 100).map((item) => {
                  const change = item.change24h ?? 0;
                  const trend =
                    change > 2 ? "bullish" : change < -2 ? "bearish" : "neutral";
                  return (
                    <tr
                      key={item.symbol}
                      onClick={() => {}}
                      className="border-b border-gray-800 hover:bg-gray-800 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-2">
                        <span className="font-medium text-white">{item.symbol.replace("USDT", "")}</span>
                        <span className="text-gray-500 ml-1">USDT</span>
                      </td>
                      <td className="px-4 py-2 text-right text-white">
                        {item.price != null
                          ? item.price.toLocaleString(undefined, {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 6,
                            })
                          : "-"}
                      </td>
                      <td
                        className={`px-4 py-2 text-right font-medium ${
                          change >= 0 ? "text-green-400" : "text-red-400"
                        }`}
                      >
                        {change >= 0 ? "+" : ""}
                        {change.toFixed(2)}%
                      </td>
                      <td className="px-4 py-2 text-right text-gray-400">
                        {item.volume24h != null
                          ? item.volume24h > 1e9
                            ? `${(item.volume24h / 1e9).toFixed(1)}B`
                            : item.volume24h > 1e6
                            ? `${(item.volume24h / 1e6).toFixed(1)}M`
                            : `${(item.volume24h / 1e3).toFixed(0)}K`
                          : "-"}
                      </td>
                      <td className="px-4 py-2 text-center">
                        {trend === "bullish" && (
                          <span className="text-green-400">
                            <TrendingUp size={12} className="inline" />
                          </span>
                        )}
                        {trend === "bearish" && (
                          <span className="text-red-400">
                            <TrendingDown size={12} className="inline" />
                          </span>
                        )}
                        {trend === "neutral" && (
                          <span className="text-gray-400">
                            <Minus size={12} className="inline" />
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default Screener;

// Export presets for external use
export { PRESETS as SCREENER_PRESETS };