import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  Search,
  Star,
  ChevronUp,
  ChevronDown,
  Filter,
  X,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import { useI18n } from "@/i18n";
import type {
  EnhancedWatchlistItem,
  WatchlistColumn,
  WatchlistSortKey,
  WatchlistSortDir,
  WatchlistFilter,
} from "@/types";

interface EnhancedWatchlistProps {
  /** Initial items - can be enriched later */
  items: EnhancedWatchlistItem[];
  /** Filter to specific symbols only */
  symbols?: string[];
  /** Show filter panel */
  showFilters?: boolean;
  /** Show bulk selection actions */
  showBulkActions?: boolean;
  /** Called when user clicks a symbol */
  onSymbolClick?: (symbol: string) => void;
  /** Max rows to display */
  maxRows?: number;
  /** Default sort */
  defaultSort?: { key: WatchlistSortKey; dir: WatchlistSortDir };
  /** Loading state */
  loading?: boolean;
  /** Called when selection changes */
  onSelectionChange?: (symbols: string[]) => void;
  /** External filter applied */
  externalFilter?: WatchlistFilter;
  /** External sort applied */
  externalSort?: { key: WatchlistSortKey; dir: WatchlistSortDir };
}

const COLUMN_DEFAULTS: WatchlistColumn[] = [
  { id: "rank", labelKey: "#", key: "rank", align: "center", width: 40, sortable: true },
  { id: "name", labelKey: "name", key: "symbol", align: "left", width: 120, sortable: true },
  { id: "price", labelKey: "price", key: "price", align: "right", width: 100, sortable: true, format: "price" },
  { id: "change24h", labelKey: "24h", key: "change24h", align: "right", width: 80, sortable: true, format: "percent" },
  { id: "change7d", labelKey: "7d", key: "change7d", align: "right", width: 80, sortable: true, format: "percent" },
  { id: "volume24h", labelKey: "24hVol", key: "volume24h", align: "right", width: 100, sortable: true, format: "volume" },
  { id: "marketCap", labelKey: "marketCap", key: "marketCap", align: "right", width: 100, sortable: true, format: "marketCap" },
  { id: "rsi14", labelKey: "RSI(14)", key: "rsi14", align: "right", width: 60, sortable: true },
  { id: "trend", labelKey: "trend", key: "trend", align: "center", width: 80, sortable: false },
  { id: "volatility", labelKey: "volatility", key: "volatility24h", align: "right", width: 80, sortable: true, format: "percent" },
];

function formatPrice(v: number): string {
  if (v >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (v >= 1) return v.toFixed(4);
  return v.toFixed(6);
}

function formatVolume(v: number): string {
  if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(1) + "K";
  return v.toFixed(2);
}

function formatMarketCap(v: number): string {
  if (v >= 1e12) return (v / 1e12).toFixed(2) + "T";
  if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
  return v.toFixed(0);
}

function renderCellValue(item: EnhancedWatchlistItem, col: WatchlistColumn): React.ReactNode {
  const value = item[col.key as keyof EnhancedWatchlistItem];
  if (value === undefined || value === null) return <span className="text-gray-500">-</span>;

  switch (col.format) {
    case "price":
      return <span className="font-mono">{formatPrice(value as number)}</span>;
    case "percent":
      const pct = value as number;
      return (
        <span className={pct >= 0 ? "text-green-400" : "text-red-400"}>
          {pct >= 0 ? "+" : ""}{(pct).toFixed(2)}%
        </span>
      );
    case "volume":
      return <span className="text-gray-400">{formatVolume(value as number)}</span>;
    case "marketCap":
      return <span className="text-gray-400">{formatMarketCap(value as number)}</span>;
    default:
      // Special render for trend column
      if (col.id === "trend") {
        const trend = value as string;
        if (trend === "bullish") return <span className="text-green-400 flex items-center gap-1 justify-center"><TrendingUp size={12} /> Bullish</span>;
        if (trend === "bearish") return <span className="text-red-400 flex items-center gap-1 justify-center"><TrendingDown size={12} /> Bearish</span>;
        return <span className="text-gray-400 flex items-center gap-1 justify-center"><Minus size={12} /> Neutral</span>;
      }
      // RSI coloring
      if (col.id === "rsi14") {
        const rsi = value as number;
        if (rsi > 70) return <span className="text-red-400">{rsi.toFixed(0)}</span>;
        if (rsi < 30) return <span className="text-green-400">{rsi.toFixed(0)}</span>;
        return <span className="text-gray-400">{rsi.toFixed(0)}</span>;
      }
      return String(value);
  }
}

const EnhancedWatchlist: React.FC<EnhancedWatchlistProps> = ({
  items,
  symbols,
  showFilters = true,
  showBulkActions = false,
  onSymbolClick,
  maxRows,
  defaultSort = { key: "rank", dir: "asc" },
  loading = false,
  onSelectionChange,
  externalFilter,
  externalSort,
}) => {
  const { t } = useI18n();
  const [searchQuery, setSearchQuery] = useState("");
  const [localSort, setLocalSort] = useState(defaultSort);
  const [localFilter, setLocalFilter] = useState<WatchlistFilter>({});
  const [selectedSymbols, setSelectedSymbols] = useState<Set<string>>(new Set());
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  // Use external sort/filter if provided, otherwise local
  const sort = externalSort ?? localSort;
  const filter = externalFilter ?? localFilter;

  const setSort = useCallback((s: { key: WatchlistSortKey; dir: WatchlistSortDir }) => {
    if (!externalSort) setLocalSort(s);
  }, [externalSort]);

  const setFilter = useCallback((f: WatchlistFilter) => {
    if (!externalFilter) setLocalFilter(f);
  }, [externalFilter]);

  // Filter to specific symbols if provided
  const filteredBySymbols = useMemo(() => {
    if (!symbols?.length) return items;
    const symbolSet = new Set(symbols);
    return items.filter(item => symbolSet.has(item.symbol));
  }, [items, symbols]);

  // Apply search, sort, filter
  const processedItems = useMemo(() => {
    let result = [...filteredBySymbols];

    // Search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(item =>
        item.symbol.toLowerCase().includes(query) ||
        (item.name?.toLowerCase().includes(query) ?? false)
      );
    }

    // Apply filters
    if (filter.categories?.length) {
      result = result.filter(item => item.category && filter.categories!.includes(item.category));
    }
    if (filter.minVolume != null) {
      result = result.filter(item => item.volume24h >= filter.minVolume!);
    }
    if (filter.minPrice != null) {
      result = result.filter(item => item.price >= filter.minPrice!);
    }
    if (filter.maxPrice != null) {
      result = result.filter(item => item.price <= filter.maxPrice!);
    }
    if (filter.rsiRange) {
      result = result.filter(item =>
        item.rsi14 != null &&
        item.rsi14 >= filter.rsiRange!.min &&
        item.rsi14 <= filter.rsiRange!.max
      );
    }
    if (filter.changeRange) {
      result = result.filter(item =>
        item.change24h >= filter.changeRange!.min &&
        item.change24h <= filter.changeRange!.max
      );
    }
    if (filter.trends?.length) {
      result = result.filter(item => item.trend && filter.trends!.includes(item.trend));
    }
    if (filter.isNewListing) {
      result = result.filter(item => item.isNewListing);
    }
    if (filter.isActive !== undefined) {
      result = result.filter(item => item.isActive === filter.isActive);
    }

    // Sort
    result.sort((a, b) => {
      const aVal = a[sort.key as keyof EnhancedWatchlistItem];
      const bVal = b[sort.key as keyof EnhancedWatchlistItem];
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sort.dir === "asc" ? aVal - bVal : bVal - aVal;
      }
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sort.dir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return 0;
    });

    // Limit rows
    if (maxRows) {
      result = result.slice(0, maxRows);
    }

    return result;
  }, [filteredBySymbols, sort, filter, searchQuery, maxRows]);

  // Selection handling
  useEffect(() => {
    onSelectionChange?.(Array.from(selectedSymbols));
  }, [selectedSymbols, onSelectionChange]);

  const toggleSelection = useCallback((symbol: string, selected: boolean) => {
    setSelectedSymbols(prev => {
      const next = new Set(prev);
      if (selected) next.add(symbol);
      else next.delete(symbol);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedSymbols(new Set(processedItems.map(i => i.symbol)));
  }, [processedItems]);

  const clearSelection = useCallback(() => {
    setSelectedSymbols(new Set());
  }, []);

  const handleSort = useCallback((key: WatchlistSortKey) => {
    setSort({
      key,
      dir: sort.key === key && sort.dir === "asc" ? "desc" : "asc",
    });
  }, [sort, setSort]);

  const clearFilters = useCallback(() => {
    setLocalFilter({});
    setSearchQuery("");
  }, []);

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

  const columns = COLUMN_DEFAULTS;

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header Toolbar */}
      <div className="flex items-center gap-2 p-2 border-b border-gray-800">
        {/* Search */}
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("searchSymbol")}
            className="w-full pl-8 pr-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {/* Filter toggle */}
        {showFilters && (
          <button
            onClick={() => setShowFilterPanel(p => !p)}
            className={`flex items-center gap-1 px-2 py-1.5 rounded text-xs transition-colors ${
              showFilterPanel || hasActiveFilters
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700"
            }`}
          >
            <Filter size={12} />
            <span>{t("filter")}</span>
          </button>
        )}

        {/* Results count */}
        <span className="text-xs text-gray-500 px-2">
          {processedItems.length} {t("results")}
        </span>
      </div>

      {/* Filter Panel */}
      {showFilters && showFilterPanel && (
        <div className="border-b border-gray-800 bg-gray-850 p-3 space-y-3">
          {/* Quick filter buttons */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFilter({ rsiRange: { min: 0, max: 30 } })}
              className={`px-2 py-1 rounded text-xs ${
                filter.rsiRange?.max === 30 ? "bg-green-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {t("oversold")}
            </button>
            <button
              onClick={() => setFilter({ rsiRange: { min: 70, max: 100 } })}
              className={`px-2 py-1 rounded text-xs ${
                filter.rsiRange?.min === 70 ? "bg-red-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {t("overbought")}
            </button>
            <button
              onClick={() => setFilter({ changeRange: { min: 5, max: 100 } })}
              className={`px-2 py-1 rounded text-xs ${
                filter.changeRange?.min === 5 ? "bg-green-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {t("topGainers")}
            </button>
            <button
              onClick={() => setFilter({ changeRange: { min: -100, max: -5 } })}
              className={`px-2 py-1 rounded text-xs ${
                filter.changeRange?.max === -5 ? "bg-red-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {t("topLosers")}
            </button>
            <button
              onClick={() => setFilter({ trends: ["bullish"] })}
              className={`px-2 py-1 rounded text-xs ${
                filter.trends?.includes("bullish") ? "bg-green-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {t("bullish")}
            </button>
            <button
              onClick={() => setFilter({ trends: ["bearish"] })}
              className={`px-2 py-1 rounded text-xs ${
                filter.trends?.includes("bearish") ? "bg-red-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {t("bearish")}
            </button>
          </div>

          {/* Advanced filters row */}
          <div className="flex flex-wrap gap-3">
            {/* Price range */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">{t("price")}:</span>
              <input
                type="number"
                placeholder="Min"
                value={filter.minPrice ?? ""}
                onChange={(e) => setFilter({ ...filter, minPrice: e.target.value ? Number(e.target.value) : undefined })}
                className="w-20 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <span className="text-gray-600">-</span>
              <input
                type="number"
                placeholder="Max"
                value={filter.maxPrice ?? ""}
                onChange={(e) => setFilter({ ...filter, maxPrice: e.target.value ? Number(e.target.value) : undefined })}
                className="w-20 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Volume min */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">{t("volume")}:</span>
              <input
                type="number"
                placeholder="Min"
                value={filter.minVolume ?? ""}
                onChange={(e) => setFilter({ ...filter, minVolume: e.target.value ? Number(e.target.value) : undefined })}
                className="w-24 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Market Cap min */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">{t("marketCap")}:</span>
              <input
                type="number"
                placeholder="Min"
                value={filter.minMarketCap ?? ""}
                onChange={(e) => setFilter({ ...filter, minMarketCap: e.target.value ? Number(e.target.value) : undefined })}
                className="w-28 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Clear filters */}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              {t("clearAll")} ({t("filter")})
            </button>
          )}
        </div>
      )}

      {/* Bulk Actions Bar */}
      {showBulkActions && selectedSymbols.size > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 bg-blue-900/30 border-b border-blue-800">
          <span className="text-xs text-blue-300">
            {selectedSymbols.size} selected
          </span>
          <button
            onClick={selectAll}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            {t("selectAll")}
          </button>
          <button
            onClick={clearSelection}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            {t("clearSelection")}
          </button>
        </div>
      )}

      {/* Table Header */}
      <div className="flex items-center px-2 py-1.5 bg-gray-850 border-b border-gray-800 text-[10px] text-gray-500 uppercase">
        {showBulkActions && (
          <div className="w-6 flex-shrink-0">
            <input
              type="checkbox"
              checked={selectedSymbols.size === processedItems.length && processedItems.length > 0}
              onChange={(e) => {
                if (e.target.checked) selectAll();
                else clearSelection();
              }}
              className="rounded"
            />
          </div>
        )}
        {columns.map((col) => (
          <div
            key={col.id}
            className={`flex-shrink-0 px-1 cursor-pointer hover:text-white ${
              col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : "text-left"
            } ${col.sortable ? "select-none" : ""}`}
            style={{ width: col.width }}
            onClick={() => col.sortable && handleSort(col.key as WatchlistSortKey)}
          >
            <span className="flex items-center gap-0.5 justify-end">
              {t(col.labelKey as Parameters<typeof t>[0])}
              {col.sortable && sort.key === col.key && (
                sort.dir === "asc" ? <ChevronUp size={10} /> : <ChevronDown size={10} />
              )}
            </span>
          </div>
        ))}
      </div>

      {/* Table Body */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500" />
          </div>
        ) : processedItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500 text-sm">
            <Star size={24} className="mb-2 opacity-50" />
            {t("noResults")}
          </div>
        ) : (
          processedItems.map((item) => {
            const isSelected = selectedSymbols.has(item.symbol);

            return (
              <div
                key={item.symbol}
                className={`flex items-center px-2 py-1.5 border-b border-gray-800 hover:bg-gray-800 cursor-pointer transition-colors ${
                  isSelected ? "bg-blue-900/20" : ""
                }`}
                onClick={() => onSymbolClick?.(item.symbol)}
              >
                {showBulkActions && (
                  <div className="w-6 flex-shrink-0">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleSelection(item.symbol, e.target.checked);
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded"
                    />
                  </div>
                )}
                {columns.map((col) => (
                  <div
                    key={col.id}
                    className={`flex-shrink-0 px-1 text-xs ${
                      col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : "text-left"
                    } ${col.id === "name" ? "text-white font-medium" : ""}`}
                    style={{ width: col.width }}
                  >
                    {renderCellValue(item, col)}
                  </div>
                ))}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-3 py-1.5 border-t border-gray-800 text-[10px] text-gray-500">
        <span>{processedItems.length} {t("results")}</span>
        <span>{t("lastUpdated")}: {new Date().toLocaleTimeString()}</span>
      </div>
    </div>
  );
};

export default EnhancedWatchlist;
