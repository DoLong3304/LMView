import React from "react";
import { Search, TrendingUp, BarChart3, CandlestickChart as CandleIcon, LineChart, AreaChart } from "lucide-react";
import { useI18n } from "../i18n";

interface TopToolbarProps {
  selectedSymbol: string;
  symbols: string[];
  onSymbolChange: (symbol: string) => void;
  timeframe: string;
  onTimeframeChange: (timeframe: string) => void;
  chartType: "candles" | "line" | "area" | "bars";
  onChartTypeChange: (type: "candles" | "line" | "area" | "bars") => void;
}

const TIMEFRAMES = ["1s", "1m", "5m", "15m", "1H", "4H", "1D", "1W"];

const TopToolbar: React.FC<TopToolbarProps> = ({
  selectedSymbol,
  symbols,
  onSymbolChange,
  timeframe,
  onTimeframeChange,
  chartType,
  onChartTypeChange,
}) => {
  const { t } = useI18n();
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState("");

  const filteredSymbols = symbols.filter((s) =>
    s.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const chartTypeIcons = {
    candles: CandleIcon,
    bars: BarChart3,
    line: LineChart,
    area: AreaChart,
  };

  return (
    <div className="bg-gray-900 border-b border-gray-700 px-3 py-2 flex items-center gap-3">
      {/* Symbol selector */}
      <div className="relative">
        <button
          onClick={() => setSearchOpen(!searchOpen)}
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
              {filteredSymbols.map((sym) => (
                <button
                  key={sym}
                  onClick={() => {
                    onSymbolChange(sym);
                    setSearchOpen(false);
                    setSearchQuery("");
                  }}
                  className={`w-full text-left px-3 py-1.5 rounded text-xs hover:bg-gray-700 transition-colors ${
                    sym === selectedSymbol ? "bg-gray-700 text-blue-400" : "text-gray-300"
                  }`}
                >
                  {sym}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Separator */}
      <div className="w-px h-6 bg-gray-700" />

      {/* Timeframes */}
      <div className="flex items-center gap-1">
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf}
            onClick={() => onTimeframeChange(tf)}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              timeframe === tf
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
          >
            {tf}
          </button>
        ))}
      </div>

      {/* Separator */}
      <div className="w-px h-6 bg-gray-700" />

      {/* Chart types */}
      <div className="flex items-center gap-1">
        {(Object.keys(chartTypeIcons) as Array<keyof typeof chartTypeIcons>).map((type) => {
          const Icon = chartTypeIcons[type];
          return (
            <button
              key={type}
              onClick={() => onChartTypeChange(type)}
              className={`p-1.5 rounded transition-colors ${
                chartType === type
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
              title={type}
            >
              <Icon size={16} />
            </button>
          );
        })}
      </div>

      {/* Mode Indicator */}
      <div className="ml-auto">
        <div
          className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
            import.meta.env.VITE_DATA_SOURCE === "mock"
              ? "bg-amber-500/20 text-amber-500 border border-amber-500/30"
              : "bg-emerald-500/20 text-emerald-500 border border-emerald-500/30"
          }`}
          title="Current Data Source"
        >
          {import.meta.env.VITE_DATA_SOURCE === "mock" ? "MOCK" : "API"}
        </div>
      </div>
    </div>
  );
};

export default TopToolbar;
