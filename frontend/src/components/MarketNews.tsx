import React, { useState, useEffect } from "react";
import { 
  fetchMarketOverview, 
  fetchTopGainers, 
  fetchTopLosers, 
  fetchLatestMarketNews 
} from "../services/marketOverviewService";

interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  url: string;
  source: string;
  image_url?: string;
  published_at: string;
  sentiment_label: string;
  sentiment_score: number;
  symbols: string[];
}

interface MarketMetrics {
  btc_price: number;
  total_market_cap: number;
  total_volume_24h: number;
  btc_dominance: number;
  total_symbols: number;
}

interface PriceItem {
  symbol: string;
  change_24h_pct: number;
}

const MarketNews: React.FC = () => {
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [metrics, setMetrics] = useState<MarketMetrics | null>(null);
  const [gainers, setGainers] = useState<PriceItem[]>([]);
  const [losers, setLosers] = useState<PriceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch news, market overview, gainers, losers in parallel
        const [newsRes, overviewRes, gainersRes, losersRes] = await Promise.all([
          fetchLatestMarketNews(100, 24),
          fetchMarketOverview(),
          fetchTopGainers(5),
          fetchTopLosers(5),
        ]);

        setNews(newsRes.articles || newsRes.data || []);
        setMetrics(overviewRes.data);
        setGainers(gainersRes.data || []);
        setLosers(losersRes.data || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        console.error("Error fetching data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const formatNumber = (num: number): string => {
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
    return `$${num.toFixed(2)}`;
  };

  const formatDate = (date: string): string => {
    return new Date(date).toLocaleString();
  };

  const getSentimentColor = (score: number): string => {
    if (score > 0.5) return "text-green-400";
    if (score < -0.5) return "text-red-400";
    return "text-yellow-400";
  };

  const getSentimentBg = (score: number): string => {
    if (score > 0.5) return "bg-green-900/20 border-green-700";
    if (score < -0.5) return "bg-red-900/20 border-red-700";
    return "bg-gray-800 border-gray-700";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-white text-lg">Loading market data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-red-400 text-lg">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen bg-gray-900 flex flex-col">
      {/* HEADER SECTION - NOT SCROLLABLE */}
      <div className="flex-shrink-0 p-4">
        {/* Market Overview */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-white mb-3">Market Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div className="text-xs text-gray-400 mb-1">BTC Price</div>
              <div className="text-lg font-semibold text-white">
                {formatNumber(metrics?.btc_price || 0)}
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div className="text-xs text-gray-400 mb-1">Market Cap</div>
              <div className="text-lg font-semibold text-white">
                {formatNumber(metrics?.total_market_cap || 0)}
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div className="text-xs text-gray-400 mb-1">24h Volume</div>
              <div className="text-lg font-semibold text-white">
                {formatNumber(metrics?.total_volume_24h || 0)}
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div className="text-xs text-gray-400 mb-1">BTC Dominance</div>
              <div className="text-lg font-semibold text-white">
                {(metrics?.btc_dominance || 0).toFixed(1)}%
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div className="text-xs text-gray-400 mb-1">Symbols</div>
              <div className="text-lg font-semibold text-white">
                {metrics?.total_symbols || 0}
              </div>
            </div>
          </div>
        </div>

        {/* Top Gainers & Losers */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 mt-4">
          {/* Gainers */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h3 className="text-sm font-semibold text-white mb-3">🔥 Top Gainers (24h)</h3>
            <div className="space-y-2">
              {gainers.map((g) => (
                <div key={g.symbol} className="flex items-center justify-between">
                  <span className="text-sm text-gray-300">{g.symbol.replace("USDT", "")}</span>
                  <span className="text-sm font-semibold text-green-400">
                    +{g.change_24h_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Losers */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h3 className="text-sm font-semibold text-white mb-3">📉 Top Losers (24h)</h3>
            <div className="space-y-2">
              {losers.map((l) => (
                <div key={l.symbol} className="flex items-center justify-between">
                  <span className="text-sm text-gray-300">{l.symbol.replace("USDT", "")}</span>
                  <span className="text-sm font-semibold text-red-400">
                    {l.change_24h_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* NEWS FEED SECTION - SCROLLABLE */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto p-4">
          <h2 className="text-lg font-semibold text-white mb-3 sticky top-0 bg-gray-900 pb-2">Latest News</h2>
          <div className="space-y-3">
            {news.map((article) => (
              <a
                key={article.id}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`block rounded-lg p-4 border transition-colors hover:border-blue-500 ${getSentimentBg(article.sentiment_score)}`}
              >
                <div className="flex items-start gap-3">
                  {article.image_url && (
                    <img
                      src={article.image_url}
                      alt=""
                      className="w-20 h-20 rounded object-cover flex-shrink-0"
                      onError={(e) => {
                        e.currentTarget.style.display = "none";
                      }}
                    />
                  )}
                  <div className="flex-grow min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-gray-400">{article.source}</span>
                      <span className="text-xs text-gray-500">•</span>
                      <span className="text-xs text-gray-400">
                        {formatDate(article.published_at)}
                      </span>
                      {article.sentiment_score !== 0 && (
                        <>
                          <span className="text-xs text-gray-500">•</span>
                          <span className={`text-xs font-semibold ${getSentimentColor(article.sentiment_score)}`}>
                            {article.sentiment_label}
                          </span>
                        </>
                      )}
                    </div>
                    <h3 className="text-sm font-semibold text-white mb-1 line-clamp-2">
                      {article.title}
                    </h3>
                    <p className="text-xs text-gray-400 line-clamp-2 mb-2">
                      {article.summary}
                    </p>
                    {article.symbols.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {article.symbols.slice(0, 5).map((sym) => (
                          <span
                            key={sym}
                            className="text-xs px-2 py-0.5 bg-blue-900/30 text-blue-400 rounded"
                          >
                            {sym}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketNews;
