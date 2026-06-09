import React, { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  AlertTriangle,
  BarChart3,
  DollarSign,
  Flame,
  TrendingDown,
  TrendingUp,
  ChevronDown,
} from "lucide-react";
import { MARKET_REFRESH_MS } from "@/constants/market";
import {
  fetchMarketOverview,
  fetchTopGainers,
  fetchTopLosers,
  fetchSectorPerformance,
} from "@/services/marketOverviewService";
import { useI18n } from "@/i18n";
import type {
  MarketOverview,
  MarketPeriod,
  SectorPerformance,
  TopMover,
} from "@/types";

const PERIODS: MarketPeriod[] = ["1h", "24h", "7d", "30d"];

const MarketOverviewPage: React.FC = () => {
  const { t } = useI18n();
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [gainers, setGainers] = useState<TopMover[]>([]);
  const [losers, setLosers] = useState<TopMover[]>([]);
  const [sectors, setSectors] = useState<SectorPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<MarketPeriod>("24h");
  const [periodDropdownOpen, setPeriodDropdownOpen] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [overviewData, topGainers, topLosers, sectorData] = await Promise.all([
        fetchMarketOverview(),
        fetchTopGainers(10),
        fetchTopLosers(10),
        fetchSectorPerformance(),
      ]);
      setOverview(overviewData);
      setGainers(topGainers);
      setLosers(topLosers);
      setSectors(sectorData);
    } catch (error) {
      console.error("Failed to fetch market data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, MARKET_REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetchData]);

  const formatNumber = (num: number, decimals: number = 2): string => {
    if (num >= 1e12) return `$${(num / 1e12).toFixed(decimals)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(decimals)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(decimals)}M`;
    if (num >= 1e3) return `$${(num / 1e3).toFixed(decimals)}K`;
    return `$${num.toFixed(decimals)}`;
  };

  const formatPrice = (price: number): string => {
    if (price >= 1000) return price.toFixed(2);
    if (price >= 1) return price.toFixed(4);
    return price.toFixed(6);
  };

  const getFearGreedColor = (value?: number): string => {
    if (!value) return "text-gray-400";
    if (value <= 25) return "text-red-500";
    if (value <= 45) return "text-orange-400";
    if (value <= 55) return "text-yellow-400";
    if (value <= 75) return "text-green-400";
    return "text-emerald-500";
  };

  const getFearGreedLabel = (value?: number): string => {
    if (!value) return t("noData");
    if (value <= 25) return t("fearGreedExtremeFear");
    if (value <= 45) return t("fearGreedFear");
    if (value <= 55) return t("fearGreedNeutral");
    if (value <= 75) return t("fearGreedGreed");
    return t("fearGreedExtremeGreed");
  };

  const metrics = overview?.market_summary;
  const marketBreadth = metrics?.advancing_count && metrics?.declining_count
    ? (metrics.advancing_count / (metrics.advancing_count + metrics.declining_count)) * 100
    : null;

  const renderMoverList = (
    items: TopMover[],
    kind: "gainers" | "losers",
  ) => {
    const isGainer = kind === "gainers";
    const Icon = isGainer ? ArrowUpRight : ArrowDownRight;
    const emptyKey = isGainer ? "noGainersData" : "noLosersData";

    return items.length > 0 ? (
      items.map((coin, index) => (
        <div
          key={coin.symbol}
          className="px-5 py-3 hover:bg-gray-800/30 transition-colors flex items-center gap-4"
        >
          <div className="w-6 text-center">
            <span className="text-sm font-bold text-gray-600">{index + 1}</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-mono font-bold text-white text-sm">
              {coin.symbol.replace("USDT", "")}
            </div>
            <div className="text-xs text-gray-500">
              {t("volume")}: {formatNumber(coin.volume_24h)}
            </div>
          </div>
          <div className="text-right">
            <div className="font-mono text-sm text-white mb-0.5">
              ${formatPrice(coin.price)}
            </div>
            <div
              className={`flex items-center justify-end gap-1 font-bold text-sm ${
                isGainer ? "text-green-400" : "text-red-400"
              }`}
            >
              <Icon size={14} />
              {isGainer ? "+" : ""}
              {coin.change_24h_pct.toFixed(2)}%
            </div>
          </div>
        </div>
      ))
    ) : (
      <div className="px-5 py-8 text-center text-gray-500">{t(emptyKey)}</div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-gray-400">{t("loadingMarketData")}</div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-900 text-gray-100 flex flex-col overflow-hidden">
      <div className="max-w-[1920px] mx-auto w-full p-4 md:p-6 flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold mb-2 flex items-center gap-3">
              <Activity className="text-blue-400" size={32} />
              {t("marketOverviewTitle")}
            </h1>
            <p className="text-sm text-gray-400">{t("marketOverviewSubtitle")}</p>
          </div>
          {/* Period Selector */}
          <div className="relative">
            <button
              onClick={() => setPeriodDropdownOpen(!periodDropdownOpen)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
            >
              <span className="text-sm font-medium">{t(period)}</span>
              <ChevronDown size={16} className={`transition-transform ${periodDropdownOpen ? "rotate-180" : ""}`} />
            </button>
            {periodDropdownOpen && (
              <div className="absolute right-0 mt-2 w-32 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-10">
                {PERIODS.map((p) => (
                  <button
                    key={p}
                    onClick={() => {
                      setPeriod(p);
                      setPeriodDropdownOpen(false);
                    }}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-700 transition-colors ${
                      period === p ? "text-blue-400 font-medium" : ""
                    }`}
                  >
                    {t(p)}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {overview?.metadata?.warning && (
          <div className="mb-4 flex items-start gap-3 rounded border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            <AlertTriangle size={18} className="mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-semibold">{t("marketOverviewUnavailable")}</div>
              <div className="mt-1 text-xs text-amber-200/80">{overview.metadata.warning}</div>
            </div>
          </div>
        )}

        {/* Metrics Grid */}
        {metrics ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-3 md:gap-4 mb-6">
            {/* BTC */}
            <MetricCard
              accent="orange"
              icon={<span className="text-orange-400 font-bold text-sm">BTC</span>}
              label={t("bitcoin")}
              value={formatNumber(metrics.btc_price)}
              detail={`${(metrics.btc_change_24h ?? 0) >= 0 ? "+" : ""}${(metrics.btc_change_24h ?? 0).toFixed(2)}%`}
              detailColor={(metrics.btc_change_24h ?? 0) >= 0 ? "text-green-400" : "text-red-400"}
            />
            {/* Market Cap */}
            <MetricCard
              accent="blue"
              icon={<DollarSign size={16} className="text-blue-400" />}
              label={t("marketCap")}
              value={formatNumber(metrics.total_market_cap)}
              detail={t("totalValue")}
            />
            {/* Volume */}
            <MetricCard
              accent="purple"
              icon={<BarChart3 size={16} className="text-purple-400" />}
              label={t("volume24h")}
              value={formatNumber(metrics.total_volume_24h)}
              detail={t("tradingVolume")}
            />
            {/* BTC Dominance */}
            <MetricCard
              accent="green"
              icon={<Activity size={16} className="text-green-400" />}
              label={t("btcDominance")}
              value={`${metrics.btc_dominance.toFixed(1)}%`}
              detail={t("marketShare")}
            />
            {/* ETH Dominance */}
            <MetricCard
              accent="cyan"
              icon={<Activity size={16} className="text-cyan-400" />}
              label={t("ethDominance")}
              value={`${(metrics.eth_dominance || 0).toFixed(1)}%`}
              detail={t("marketShare")}
            />
            {/* Fear & Greed */}
            <MetricCard
              accent={metrics.fear_greed_index && metrics.fear_greed_index <= 45 ? "red" : "green"}
              icon={<Flame size={16} className={getFearGreedColor(metrics.fear_greed_index)} />}
              label={t("fearGreedIndex")}
              value={metrics.fear_greed_index?.toString() || "-"}
              detail={getFearGreedLabel(metrics.fear_greed_index)}
              detailColor={getFearGreedColor(metrics.fear_greed_index)}
            />
            {/* Active Symbols */}
            <MetricCard
              accent="gray"
              icon={<Flame size={16} className="text-gray-400" />}
              label={t("activeSymbols")}
              value={String(metrics.total_symbols)}
              detail={t("tradingPairs")}
            />
          </div>
        ) : (
          <div className="mb-6 flex items-start gap-3 rounded border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            <AlertTriangle size={18} className="mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-semibold">{t("marketOverviewUnavailable")}</div>
              <div className="mt-1 text-xs text-amber-200/80">{t("apiPlaceholderUnavailable")}</div>
            </div>
          </div>
        )}

        {/* Market Breadth Section */}
        {metrics && metrics.advancing_count !== undefined && (
          <div className="mb-6 bg-gray-850 border border-gray-800 rounded p-4">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">{t("marketBreadth")}</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <BreadthItem
                label={t("advancing")}
                value={metrics.advancing_count ?? "-"}
                color="text-green-400"
              />
              <BreadthItem
                label={t("declining")}
                value={metrics.declining_count ?? "-"}
                color="text-red-400"
              />
              <BreadthItem
                label={t("marketBreadthRatio")}
                value={marketBreadth !== null ? `${marketBreadth.toFixed(1)}%` : "-"}
                color={marketBreadth !== null && marketBreadth > 50 ? "text-green-400" : "text-red-400"}
              />
              <BreadthItem
                label={t("newHighsLows24h")}
                value={`${metrics.new_highs_24h || 0} / ${metrics.new_lows_24h || 0}`}
                color="text-blue-400"
              />
            </div>
          </div>
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mb-6">
          {/* Top Gainers */}
          <section className="bg-gray-850 border border-gray-800 rounded overflow-hidden flex flex-col">
            <div className="bg-gradient-to-r from-green-500/10 to-transparent border-b border-gray-800 px-5 py-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <TrendingUp className="text-green-400" size={20} />
                <span className="text-white">{t("topGainers")}</span>
                <span className="text-xs text-gray-500 ml-auto">{t(period)}</span>
              </h2>
            </div>
            <div className="divide-y divide-gray-800 overflow-y-auto flex-1 max-h-[300px]">
              {renderMoverList(gainers, "gainers")}
            </div>
          </section>

          {/* Top Losers */}
          <section className="bg-gray-850 border border-gray-800 rounded overflow-hidden flex flex-col">
            <div className="bg-gradient-to-r from-red-500/10 to-transparent border-b border-gray-800 px-5 py-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <TrendingDown className="text-red-400" size={20} />
                <span className="text-white">{t("topLosers")}</span>
                <span className="text-xs text-gray-500 ml-auto">{t(period)}</span>
              </h2>
            </div>
            <div className="divide-y divide-gray-800 overflow-y-auto flex-1 max-h-[300px]">
              {renderMoverList(losers, "losers")}
            </div>
          </section>
        </div>

        {/* Sector Performance */}
        {sectors.length > 0 && (
          <section className="bg-gray-850 border border-gray-800 rounded overflow-hidden">
            <div className="bg-gradient-to-r from-blue-500/10 to-transparent border-b border-gray-800 px-5 py-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <BarChart3 className="text-blue-400" size={20} />
                <span className="text-white">{t("sectorPerformance")}</span>
              </h2>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {sectors.slice(0, 12).map((sector) => (
                  <SectorCard key={sector.sector} sector={sector} />
                ))}
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
};

interface MetricCardProps {
  accent: "orange" | "blue" | "purple" | "green" | "cyan" | "gray" | "red";
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
  detailColor?: string;
}

function MetricCard({ accent, icon, label, value, detail, detailColor }: MetricCardProps) {
  const accents: Record<MetricCardProps["accent"], string> = {
    orange: "from-orange-500/10 to-orange-600/5 border-orange-500/20 hover:border-orange-500/40",
    blue: "from-blue-500/10 to-blue-600/5 border-blue-500/20 hover:border-blue-500/40",
    purple: "from-purple-500/10 to-purple-600/5 border-purple-500/20 hover:border-purple-500/40",
    green: "from-green-500/10 to-green-600/5 border-green-500/20 hover:border-green-500/40",
    cyan: "from-cyan-500/10 to-cyan-600/5 border-cyan-500/20 hover:border-cyan-500/40",
    gray: "from-gray-500/10 to-gray-600/5 border-gray-500/20 hover:border-gray-500/40",
    red: "from-red-500/10 to-red-600/5 border-red-500/20 hover:border-red-500/40",
  };

  return (
    <div className={`bg-gradient-to-br border rounded p-4 transition-all ${accents[accent]}`}>
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-gray-900/40 flex items-center justify-center">
          {icon}
        </div>
        <span className="text-xs text-gray-400 font-medium">{label}</span>
      </div>
      <div className="text-xl md:text-2xl font-bold text-white mb-1">{value}</div>
      <div className={`text-xs ${detailColor || "text-gray-500"}`}>{detail}</div>
    </div>
  );
}

interface BreadthItemProps {
  label: string;
  value: string | number;
  color: string;
}

function BreadthItem({ label, value, color }: BreadthItemProps) {
  return (
    <div className="text-center">
      <div className={`text-xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

interface SectorCardProps {
  sector: SectorPerformance;
}

function SectorCard({ sector }: SectorCardProps) {
  const changeColor = sector.change_24h_pct >= 0 ? "text-green-400" : "text-red-400";
  const bgColor = sector.change_24h_pct >= 0 ? "bg-green-500/10" : "bg-red-500/10";
  const borderColor = sector.change_24h_pct >= 0 ? "border-green-500/20" : "border-red-500/20";

  return (
    <div className={`border ${borderColor} rounded p-3 ${bgColor}`}>
      <div className="font-medium text-sm text-white mb-1">{sector.name}</div>
      <div className={`text-lg font-bold ${changeColor}`}>
        {sector.change_24h_pct >= 0 ? "+" : ""}{sector.change_24h_pct.toFixed(2)}%
      </div>
      <div className="flex flex-wrap gap-1 mt-2">
        {sector.top_coins.slice(0, 3).map((coin) => (
          <span key={coin} className="text-[10px] px-1.5 py-0.5 bg-gray-800 rounded text-gray-400">
            {coin}
          </span>
        ))}
      </div>
    </div>
  );
}

export default MarketOverviewPage;
