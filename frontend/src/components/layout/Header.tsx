import React, { useEffect, useRef, useState } from "react";
import {
  AreaChart,
  BarChart3,
  CandlestickChart as CandleIcon,
  LineChart,
  Menu,
  Search,
  TrendingUp,
  X,
} from "lucide-react";
import { getDataSourceLabel, DATA_SOURCE } from "@/constants/env";
import { TIMEFRAME_KEYS, TIMEFRAMES } from "@/constants/timeframes";
import LanguageSwitcher from "@/components/ui/LanguageSwitcher";
import SystemHealthCard from "@/components/ui/SystemHealthCard";
import { useI18n } from "@/i18n";
import type { ChartType, TimeframeKey } from "@/types";
import type { TranslationKey } from "@/i18n/translations";

const NAV_ITEMS_KEYS: TranslationKey[] = [
  "products",
  "community",
  "markets",
  "news",
  "brokers",
];

const CHART_TYPE_ICONS: Record<ChartType, typeof CandleIcon> = {
  candles: CandleIcon,
  bars: BarChart3,
  line: LineChart,
  area: AreaChart,
};

const CHART_TYPE_LABELS: Record<ChartType, TranslationKey> = {
  candles: "candlestick",
  bars: "bars",
  line: "line",
  area: "area",
};

interface HeaderProps {
  selectedSymbol: string;
  symbols: string[];
  onSymbolChange: (symbol: string) => void;
  timeframe: TimeframeKey;
  onTimeframeChange: (timeframe: TimeframeKey) => void;
  chartType: ChartType;
  onChartTypeChange: (type: ChartType) => void;
}

const Header: React.FC<HeaderProps> = ({
  selectedSymbol,
  symbols,
  onSymbolChange,
  timeframe,
  onTimeframeChange,
  chartType,
  onChartTypeChange,
}) => {
  const { t } = useI18n();
  const [showNavDrawer, setShowNavDrawer] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        setShowNavDrawer(false);
      }
    };
    if (showNavDrawer) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showNavDrawer]);

  const filteredSymbols = symbols.filter((symbol) =>
    symbol.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <>
      <header className="bg-gray-900 border-b border-gray-700 px-3 py-2 flex items-center gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xl font-bold text-blue-500">LMView</span>
          <SystemHealthCard />
        </div>

        <div className="w-px h-6 bg-gray-700" />

        <div className="relative">
          <button
            onClick={() => setSearchOpen((open) => !open)}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 hover:bg-gray-750 border border-gray-700 rounded text-sm font-semibold transition-colors"
          >
            <TrendingUp size={14} className="text-blue-400" />
            <span>{selectedSymbol}</span>
          </button>
          {searchOpen && (
            <div className="absolute top-full left-0 mt-1 w-64 bg-gray-850 border border-gray-700 rounded shadow-lg z-50 max-h-80 overflow-y-auto">
              <div className="sticky top-0 bg-gray-850 p-2 border-b border-gray-700">
                <div className="relative">
                  <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t("searchSymbol")}
                    className="w-full pl-8 pr-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    autoFocus
                  />
                </div>
              </div>
              <div className="p-1">
                {filteredSymbols.map((symbol) => (
                  <button
                    key={symbol}
                    onClick={() => {
                      onSymbolChange(symbol);
                      setSearchOpen(false);
                      setSearchQuery("");
                    }}
                    className={`w-full text-left px-3 py-1.5 rounded text-xs hover:bg-gray-700 transition-colors ${
                      symbol === selectedSymbol ? "bg-gray-700 text-blue-400" : "text-gray-300"
                    }`}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="w-px h-6 bg-gray-700" />

        <div className="flex items-center gap-1">
          {TIMEFRAME_KEYS.map((key) => (
            <button
              key={key}
              onClick={() => onTimeframeChange(key)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                timeframe === key
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              {TIMEFRAMES[key].label}
            </button>
          ))}
        </div>

        <div className="w-px h-6 bg-gray-700" />

        <div className="flex items-center gap-1">
          {(Object.keys(CHART_TYPE_ICONS) as ChartType[]).map((type) => {
            const Icon = CHART_TYPE_ICONS[type];
            return (
              <button
                key={type}
                onClick={() => onChartTypeChange(type)}
                className={`p-1.5 rounded transition-colors ${
                  chartType === type
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`}
                title={t(CHART_TYPE_LABELS[type])}
              >
                <Icon size={16} />
              </button>
            );
          })}
        </div>

        <div className="ml-auto flex items-center gap-3">
          <div
            className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
              DATA_SOURCE === "mock"
                ? "bg-amber-500/20 text-amber-500 border border-amber-500/30"
                : "bg-emerald-500/20 text-emerald-500 border border-emerald-500/30"
            }`}
            title={t("dataSource")}
          >
            {getDataSourceLabel()}
          </div>
          <LanguageSwitcher />
          <button
            onClick={() => setShowNavDrawer(true)}
            className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-gray-800 transition-colors"
            title={t("menu")}
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </header>

      {showNavDrawer && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-[300]">
          <div
            ref={drawerRef}
            className="absolute right-0 top-0 h-full w-64 bg-gray-800 shadow-2xl flex flex-col"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
              <span className="text-lg font-bold text-blue-500">LMView</span>
              <button
                onClick={() => setShowNavDrawer(false)}
                className="text-gray-400 hover:text-white transition-colors"
                title={t("closeMenu")}
              >
                <X size={20} />
              </button>
            </div>
            <nav className="flex flex-col p-4 space-y-1">
              {NAV_ITEMS_KEYS.map((key) => (
                <a
                  key={key}
                  href="#"
                  onClick={() => setShowNavDrawer(false)}
                  className="px-4 py-2.5 rounded-lg text-gray-300 hover:text-white hover:bg-gray-700 transition-colors duration-150 font-medium"
                >
                  {t(key)}
                </a>
              ))}
            </nav>
          </div>
        </div>
      )}
    </>
  );
};

export default Header;
