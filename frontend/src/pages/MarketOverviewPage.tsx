/**
 * Market Overview Page - Redesigned
 * Inspired by TradingView & Binance
 *
 * Features:
 * - Real-time market metrics (no scrolling needed)
 * - Top gainers/losers with auto-update
 * - Market dominance charts
 * - Clean, professional layout
 */
import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  BarChart3,
  Flame,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';

interface MarketMetrics {
  total_symbols: number;
  total_market_cap: number;
  total_volume_24h: number;
  btc_dominance: number;
  eth_dominance: number;
  btc_price: number;
}

interface TopMover {
  symbol: string;
  price: number;
  change_24h_pct: number;
  volume_24h: number;
  rank?: number;
}

const MarketOverviewPage: React.FC = () => {
  const [metrics, setMetrics] = useState<MarketMetrics | null>(null);
  const [gainers, setGainers] = useState<TopMover[]>([]);
  const [losers, setLosers] = useState<TopMover[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Update every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [overviewRes, gainersRes, losersRes] = await Promise.all([
        fetch('/api/market/overview'),
        fetch('/api/market/gainers?limit=10&timeframe=24h'),
        fetch('/api/market/losers?limit=10&timeframe=24h'),
      ]);

      if (overviewRes.ok) {
        const data = await overviewRes.json();
        setMetrics(data);
      }

      if (gainersRes.ok) {
        const data = await gainersRes.json();
        setGainers(data.gainers || []);
      }

      if (losersRes.ok) {
        const data = await losersRes.json();
        setLosers(data.losers || []);
      }

      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch market data:', error);
      setLoading(false);
    }
  };

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0B0E11]">
        <div className="text-gray-400">Loading market data...</div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-[#0B0E11] text-gray-100 flex flex-col overflow-hidden">
      <div className="max-w-[1920px] mx-auto w-full p-4 md:p-6 flex flex-col h-full">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl md:text-3xl font-bold mb-2 flex items-center gap-3">
            <Activity className="text-blue-400" size={32} />
            Market Overview
          </h1>
          <p className="text-sm text-gray-400">
            Real-time cryptocurrency market data • Updated every 30 seconds
          </p>
        </div>

        {/* Market Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 md:gap-4 mb-6">
          {/* BTC Price */}
          <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/5 border border-orange-500/20 rounded-xl p-4 hover:border-orange-500/40 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-full bg-orange-500/20 flex items-center justify-center">
                <span className="text-orange-400 font-bold text-sm">₿</span>
              </div>
              <span className="text-xs text-gray-400 font-medium">Bitcoin</span>
            </div>
            <div className="text-xl md:text-2xl font-bold text-white mb-1">
              {formatNumber(metrics?.btc_price || 0)}
            </div>
            <div className="text-xs text-gray-500">BTC/USDT</div>
          </div>

          {/* Market Cap */}
          <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 rounded-xl p-4 hover:border-blue-500/40 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign size={16} className="text-blue-400" />
              <span className="text-xs text-gray-400 font-medium">Market Cap</span>
            </div>
            <div className="text-xl md:text-2xl font-bold text-white mb-1">
              {formatNumber(metrics?.total_market_cap || 0)}
            </div>
            <div className="text-xs text-gray-500">Total Value</div>
          </div>

          {/* 24h Volume */}
          <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border border-purple-500/20 rounded-xl p-4 hover:border-purple-500/40 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 size={16} className="text-purple-400" />
              <span className="text-xs text-gray-400 font-medium">24h Volume</span>
            </div>
            <div className="text-xl md:text-2xl font-bold text-white mb-1">
              {formatNumber(metrics?.total_volume_24h || 0)}
            </div>
            <div className="text-xs text-gray-500">Trading Volume</div>
          </div>

          {/* BTC Dominance */}
          <div className="bg-gradient-to-br from-green-500/10 to-green-600/5 border border-green-500/20 rounded-xl p-4 hover:border-green-500/40 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <Activity size={16} className="text-green-400" />
              <span className="text-xs text-gray-400 font-medium">BTC Dominance</span>
            </div>
            <div className="text-xl md:text-2xl font-bold text-white mb-1">
              {(metrics?.btc_dominance || 0).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">Market Share</div>
          </div>

          {/* ETH Dominance */}
          <div className="bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 border border-cyan-500/20 rounded-xl p-4 hover:border-cyan-500/40 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <Activity size={16} className="text-cyan-400" />
              <span className="text-xs text-gray-400 font-medium">ETH Dominance</span>
            </div>
            <div className="text-xl md:text-2xl font-bold text-white mb-1">
              {(metrics?.eth_dominance || 0).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">Market Share</div>
          </div>

          {/* Active Symbols */}
          <div className="bg-gradient-to-br from-gray-500/10 to-gray-600/5 border border-gray-500/20 rounded-xl p-4 hover:border-gray-500/40 transition-all">
            <div className="flex items-center gap-2 mb-2">
              <Flame size={16} className="text-gray-400" />
              <span className="text-xs text-gray-400 font-medium">Active Symbols</span>
            </div>
            <div className="text-xl md:text-2xl font-bold text-white mb-1">
              {metrics?.total_symbols || 0}
            </div>
            <div className="text-xs text-gray-500">Trading Pairs</div>
          </div>
        </div>

        {/* Top Movers Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 flex-1 overflow-hidden">
          {/* Top Gainers */}
          <div className="bg-[#131722] border border-gray-800 rounded-xl overflow-hidden flex flex-col">
            <div className="bg-gradient-to-r from-green-500/10 to-transparent border-b border-gray-800 px-5 py-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <TrendingUp className="text-green-400" size={20} />
                <span className="text-white">Top Gainers</span>
                <span className="text-xs text-gray-500 ml-auto">24h</span>
              </h2>
            </div>
            <div className="divide-y divide-gray-800 overflow-y-auto flex-1">
              {gainers.length > 0 ? (
                gainers.map((coin, index) => (
                  <div
                    key={coin.symbol}
                    className="px-5 py-3 hover:bg-gray-800/30 transition-colors flex items-center gap-4"
                  >
                    <div className="w-6 text-center">
                      <span className="text-sm font-bold text-gray-600">
                        {index + 1}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-mono font-bold text-white text-sm">
                        {coin.symbol.replace('USDT', '')}
                      </div>
                      <div className="text-xs text-gray-500">
                        Vol: {formatNumber(coin.volume_24h)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-sm text-white mb-0.5">
                        ${formatPrice(coin.price)}
                      </div>
                      <div className="flex items-center justify-end gap-1 text-green-400 font-bold text-sm">
                        <ArrowUpRight size={14} />
                        +{coin.change_24h_pct.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="px-5 py-8 text-center text-gray-500">
                  No gainers data available
                </div>
              )}
            </div>
          </div>

          {/* Top Losers */}
          <div className="bg-[#131722] border border-gray-800 rounded-xl overflow-hidden flex flex-col">
            <div className="bg-gradient-to-r from-red-500/10 to-transparent border-b border-gray-800 px-5 py-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <TrendingDown className="text-red-400" size={20} />
                <span className="text-white">Top Losers</span>
                <span className="text-xs text-gray-500 ml-auto">24h</span>
              </h2>
            </div>
            <div className="divide-y divide-gray-800 overflow-y-auto flex-1">
              {losers.length > 0 ? (
                losers.map((coin, index) => (
                  <div
                    key={coin.symbol}
                    className="px-5 py-3 hover:bg-gray-800/30 transition-colors flex items-center gap-4"
                  >
                    <div className="w-6 text-center">
                      <span className="text-sm font-bold text-gray-600">
                        {index + 1}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-mono font-bold text-white text-sm">
                        {coin.symbol.replace('USDT', '')}
                      </div>
                      <div className="text-xs text-gray-500">
                        Vol: {formatNumber(coin.volume_24h)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-sm text-white mb-0.5">
                        ${formatPrice(coin.price)}
                      </div>
                      <div className="flex items-center justify-end gap-1 text-red-400 font-bold text-sm">
                        <ArrowDownRight size={14} />
                        {coin.change_24h_pct.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="px-5 py-8 text-center text-gray-500">
                  No losers data available
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketOverviewPage;
