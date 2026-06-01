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
} from "lucide-react";
import { MARKET_REFRESH_MS } from "@/constants/market";
import {
  fetchMarketOverview,
  fetchTopGainers,
  fetchTopLosers,
} from "@/services/marketOverviewService";
import { useI18n } from "@/i18n";
import type { MarketMetrics, TopMover } from "@/types";

const MarketOverviewPage: React.FC = () => {
  const { t } = useI18n();
  const [metrics, setMetrics] = useState<MarketMetrics | null>(null);
  const [gainers, setGainers] = useState<TopMover[]>([]);
  const [losers, setLosers] = useState<TopMover[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [overview, topGainers, topLosers] = await Promise.all([
        fetchMarketOverview(),
        fetchTopGainers(10),
        fetchTopLosers(10),
      ]);
      setMetrics(overview);
      setGainers(topGainers);
      setLosers(topLosers);
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
        <div className="mb-6">
          <h1 className="text-2xl md:text-3xl font-bold mb-2 flex items-center gap-3">
            <Activity className="text-blue-400" size={32} />
            {t("marketOverviewTitle")}
          </h1>
          <p className="text-sm text-gray-400">{t("marketOverviewSubtitle")}</p>
        </div>

        {metrics ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 md:gap-4 mb-6">
            <MetricCard
              accent="orange"
              icon={<span className="text-orange-400 font-bold text-sm">BTC</span>}
              label={t("bitcoin")}
              value={formatNumber(metrics.btc_price)}
              detail="BTC/USDT"
            />
            <MetricCard
              accent="blue"
              icon={<DollarSign size={16} className="text-blue-400" />}
              label={t("marketCap")}
              value={formatNumber(metrics.total_market_cap)}
              detail={t("totalValue")}
            />
            <MetricCard
              accent="purple"
              icon={<BarChart3 size={16} className="text-purple-400" />}
              label={t("volume24h")}
              value={formatNumber(metrics.total_volume_24h)}
              detail={t("tradingVolume")}
            />
            <MetricCard
              accent="green"
              icon={<Activity size={16} className="text-green-400" />}
              label={t("btcDominance")}
              value={`${metrics.btc_dominance.toFixed(1)}%`}
              detail={t("marketShare")}
            />
            <MetricCard
              accent="cyan"
              icon={<Activity size={16} className="text-cyan-400" />}
              label={t("ethDominance")}
              value={`${(metrics.eth_dominance || 0).toFixed(1)}%`}
              detail={t("marketShare")}
            />
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 flex-1 overflow-hidden">
          <section className="bg-gray-850 border border-gray-800 rounded overflow-hidden flex flex-col">
            <div className="bg-gradient-to-r from-green-500/10 to-transparent border-b border-gray-800 px-5 py-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <TrendingUp className="text-green-400" size={20} />
                <span className="text-white">{t("topGainers")}</span>
                <span className="text-xs text-gray-500 ml-auto">{t("last24hShort")}</span>
              </h2>
            </div>
            <div className="divide-y divide-gray-800 overflow-y-auto flex-1">
              {renderMoverList(gainers, "gainers")}
            </div>
          </section>

          <section className="bg-gray-850 border border-gray-800 rounded overflow-hidden flex flex-col">
            <div className="bg-gradient-to-r from-red-500/10 to-transparent border-b border-gray-800 px-5 py-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <TrendingDown className="text-red-400" size={20} />
                <span className="text-white">{t("topLosers")}</span>
                <span className="text-xs text-gray-500 ml-auto">{t("last24hShort")}</span>
              </h2>
            </div>
            <div className="divide-y divide-gray-800 overflow-y-auto flex-1">
              {renderMoverList(losers, "losers")}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

interface MetricCardProps {
  accent: "orange" | "blue" | "purple" | "green" | "cyan" | "gray";
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
}

function MetricCard({ accent, icon, label, value, detail }: MetricCardProps) {
  const accents: Record<MetricCardProps["accent"], string> = {
    orange: "from-orange-500/10 to-orange-600/5 border-orange-500/20 hover:border-orange-500/40",
    blue: "from-blue-500/10 to-blue-600/5 border-blue-500/20 hover:border-blue-500/40",
    purple: "from-purple-500/10 to-purple-600/5 border-purple-500/20 hover:border-purple-500/40",
    green: "from-green-500/10 to-green-600/5 border-green-500/20 hover:border-green-500/40",
    cyan: "from-cyan-500/10 to-cyan-600/5 border-cyan-500/20 hover:border-cyan-500/40",
    gray: "from-gray-500/10 to-gray-600/5 border-gray-500/20 hover:border-gray-500/40",
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
      <div className="text-xs text-gray-500">{detail}</div>
    </div>
  );
}

export default MarketOverviewPage;
