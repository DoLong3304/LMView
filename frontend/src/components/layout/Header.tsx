import React, { useState } from "react";
import {
  AreaChart,
  BarChart3,
  CandlestickChart as CandleIcon,
  LineChart,
  Moon,
  Newspaper,
  PanelLeft,
  PanelRight,
  Search,
  Settings,
  Sun,
  TrendingUp,
  UserRound,
} from "lucide-react";
import { getDataSourceLabel, DATA_SOURCE } from "@/constants/env";
import { TIMEFRAME_KEYS, TIMEFRAMES } from "@/constants/timeframes";
import LanguageSwitcher from "@/components/ui/LanguageSwitcher";
import SystemHealthCard from "@/components/ui/SystemHealthCard";
import { useI18n } from "@/i18n";
import type { ChartType, TimeframeKey } from "@/types";
import type { TranslationKey } from "@/i18n/translations";

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

const SHOW_DEVELOPER_TOOLS = false;

type AppView = "charts" | "marketsNews";

interface HeaderProps {
  selectedSymbol: string;
  symbols: string[];
  onSymbolChange: (symbol: string) => void;
  timeframe: TimeframeKey;
  onTimeframeChange: (timeframe: TimeframeKey) => void;
  chartType: ChartType;
  onChartTypeChange: (type: ChartType) => void;
  themeMode: "dark" | "light";
  onThemeToggle: () => void;
  isCompactLayout: boolean;
  isDrawingToolbarOpen: boolean;
  onToggleDrawingToolbar: () => void;
  isRightPanelOpen: boolean;
  onToggleRightPanel: () => void;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
}

const Header: React.FC<HeaderProps> = ({
  selectedSymbol,
  symbols,
  onSymbolChange,
  timeframe,
  onTimeframeChange,
  chartType,
  onChartTypeChange,
  themeMode,
  onThemeToggle,
  isCompactLayout,
  isDrawingToolbarOpen,
  onToggleDrawingToolbar,
  isRightPanelOpen,
  onToggleRightPanel,
  activeView,
  onViewChange,
}) => {
  const { t } = useI18n();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredSymbols = symbols.filter((symbol) =>
    symbol.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <>
      <header className="bg-gray-900 border-b border-gray-700 px-2 sm:px-3 py-2 flex flex-wrap lg:flex-nowrap items-center gap-2 lg:gap-3">
        <div className="flex items-center gap-2 min-w-0 flex-shrink-0">
          <span className="text-lg sm:text-xl font-bold text-blue-500 leading-none">LMView</span>
          <span className="hidden xl:block max-w-72 truncate text-xs text-gray-500">
            {t("appTagline")}
          </span>
          {SHOW_DEVELOPER_TOOLS && <SystemHealthCard />}
        </div>

        <div className="hidden lg:block w-px h-6 bg-gray-700" />

        {isCompactLayout && activeView === "charts" && (
          <button
            onClick={onToggleDrawingToolbar}
            className={`p-1.5 rounded border border-gray-700 transition-colors ${
              isDrawingToolbarOpen
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
            title={t("toggleDrawingTools")}
          >
            <PanelLeft size={16} />
          </button>
        )}

        {activeView === "charts" && (
          <>
        <div className="relative min-w-0">
          <button
            onClick={() => setSearchOpen((open) => !open)}
            className="flex items-center gap-2 px-2.5 sm:px-3 py-1.5 bg-gray-800 hover:bg-gray-750 border border-gray-700 rounded text-sm font-semibold transition-colors max-w-[150px] sm:max-w-none"
          >
            <TrendingUp size={14} className="text-blue-400" />
            <span className="truncate">{selectedSymbol}</span>
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

        <div className="hidden lg:block w-px h-6 bg-gray-700" />

        <div className="order-last flex w-full items-center gap-1 overflow-x-auto pb-0.5 lg:order-none lg:w-auto lg:pb-0">
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

        <div className="hidden sm:block w-px h-6 bg-gray-700" />

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
          </>
        )}

        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <div className="flex items-center gap-1 rounded border border-gray-700 bg-gray-800 p-0.5">
            <button
              onClick={() => onViewChange("charts")}
              className={`flex items-center gap-1 rounded px-2 py-1 text-xs font-medium transition-colors ${
                activeView === "charts"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:bg-gray-700 hover:text-white"
              }`}
              title={t("charts")}
            >
              <CandleIcon size={14} />
              <span className="hidden sm:inline">{t("charts")}</span>
            </button>
            <button
              onClick={() => onViewChange("marketsNews")}
              className={`flex items-center gap-1 rounded px-2 py-1 text-xs font-medium transition-colors ${
                activeView === "marketsNews"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:bg-gray-700 hover:text-white"
              }`}
              title={t("marketsAndNews")}
            >
              <Newspaper size={14} />
              <span className="hidden sm:inline">{t("marketsAndNews")}</span>
            </button>
          </div>
          {SHOW_DEVELOPER_TOOLS && (
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
          )}
          <button
            onClick={onThemeToggle}
            className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-gray-800 transition-colors"
            title={themeMode === "dark" ? t("switchToLightMode") : t("switchToDarkMode")}
          >
            {themeMode === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
          {activeView === "charts" && (
            <button
              onClick={onToggleRightPanel}
              className={`p-1.5 rounded transition-colors ${
                isRightPanelOpen
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
              title={t("toggleOverviewPanel")}
            >
              <PanelRight className="w-5 h-5" />
            </button>
          )}
          <LanguageSwitcher />
          <button
            type="button"
            className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-gray-800 transition-colors"
            title={t("settings")}
          >
            <Settings className="w-5 h-5" />
          </button>
          <button
            type="button"
            className="flex items-center gap-1.5 rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-gray-700 hover:text-white"
            title={t("login")}
          >
            <UserRound className="w-4 h-4" />
            <span className="hidden md:inline">{t("login")}</span>
          </button>
        </div>
      </header>
    </>
  );
};

export default Header;
