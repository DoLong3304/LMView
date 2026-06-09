import React, { useEffect, useState, useCallback } from "react";
import { ArrowLeft } from "lucide-react";
import Screener from "@/features/watchlist/components/Screener";
import { fetchScreenerResults } from "@/services/screenerService";
import type { EnhancedWatchlistItem } from "@/types";
import { useI18n } from "@/i18n";

interface ScreenerPageProps {
  /** Navigate back to charts */
  onBack?: () => void;
  /** Called when user selects a symbol to view chart */
  onSymbolSelect?: (symbol: string) => void;
}

const ScreenerPage: React.FC<ScreenerPageProps> = ({ onBack, onSymbolSelect }) => {
  const { t } = useI18n();
  const [items, setItems] = useState<EnhancedWatchlistItem[]>([]);

  const loadData = useCallback(async () => {
    try {
      const results = await fetchScreenerResults({}, "change24h", "desc", 100);
      setItems(results);
    } catch (e) {
      console.error("Failed to load screener data:", e);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSymbolClick = useCallback((symbol: string) => {
    onSymbolSelect?.(symbol);
  }, [onSymbolSelect]);

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 bg-gray-850">
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors"
          >
            <ArrowLeft size={14} />
            <span>Back</span>
          </button>
        )}
        <div className="flex-1">
          <h1 className="text-lg font-semibold text-white">{t("screener") || "Screener"}</h1>
          <p className="text-xs text-gray-500">{t("screenerDescription") || "Filter symbols by technical indicators"}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {items.length} {t("results") || "results"}
          </span>
          <button
            onClick={loadData}
            className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-xs text-white transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Screener component */}
      <div className="flex-1 min-h-0">
        <Screener
          onSymbolSelect={handleSymbolClick}
          items={items}
        />
      </div>
    </div>
  );
};

export default ScreenerPage;