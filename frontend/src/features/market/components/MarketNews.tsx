import React, { useEffect, useState } from "react";
import {
  fetchMarketOverview,
  fetchTopGainers,
  fetchTopLosers,
} from "@/services/marketOverviewService";
import { fetchLatestNews } from "@/services/newsService";
import { useI18n } from "@/i18n";
import type { MarketMetrics, NewsArticle, TopMover } from "@/types";

const MarketNews: React.FC = () => {
  const { t } = useI18n();
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [metrics, setMetrics] = useState<MarketMetrics | null>(null);
  const [gainers, setGainers] = useState<TopMover[]>([]);
  const [losers, setLosers] = useState<TopMover[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [newsItems, overview, topGainers, topLosers] = await Promise.all([
          fetchLatestNews({ limit: 100, hours: 24 }),
          fetchMarketOverview(),
          fetchTopGainers(5),
          fetchTopLosers(5),
        ]);

        setNews(newsItems);
        setMetrics(overview);
        setGainers(topGainers);
        setLosers(topLosers);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : t("unexpectedError"));
        console.error("Error fetching data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [t]);

  const formatNumber = (num: number): string => {
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
    return `$${num.toFixed(2)}`;
  };

  const formatDate = (date: number | string): string => {
    const value = typeof date === "string" ? date : new Date(date).toISOString();
    return new Date(value).toLocaleString();
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
        <div className="text-white text-lg">{t("loadingMarketData")}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-red-400 text-lg">
          {t("error")}: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen bg-gray-900 flex flex-col">
      <div className="flex-shrink-0 p-4">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-white mb-3">{t("marketOverviewTitle")}</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <MarketStat label={t("btcPrice")} value={formatNumber(metrics?.btc_price || 0)} />
            <MarketStat label={t("marketCap")} value={formatNumber(metrics?.total_market_cap || 0)} />
            <MarketStat label={t("volume24h")} value={formatNumber(metrics?.total_volume_24h || 0)} />
            <MarketStat label={t("btcDominance")} value={`${(metrics?.btc_dominance || 0).toFixed(1)}%`} />
            <MarketStat label={t("symbols")} value={String(metrics?.total_symbols || 0)} />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 mt-4">
          <MoverPanel title={t("topGainers24h")} items={gainers} positive />
          <MoverPanel title={t("topLosers24h")} items={losers} />
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto p-4">
          <h2 className="text-lg font-semibold text-white mb-3 sticky top-0 bg-gray-900 pb-2">
            {t("latestNews")}
          </h2>
          <div className="space-y-3">
            {news.map((article) => (
              <a
                key={article.id}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`block rounded p-4 border transition-colors hover:border-blue-500 ${getSentimentBg(
                  article.sentiment_score,
                )}`}
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
                      <span className="text-xs text-gray-500">|</span>
                      <span className="text-xs text-gray-400">
                        {formatDate(article.published_at)}
                      </span>
                      {article.sentiment_score !== 0 && (
                        <>
                          <span className="text-xs text-gray-500">|</span>
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
                    {(article.symbolsMentioned || article.symbols).length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {(article.symbolsMentioned || article.symbols).slice(0, 5).map((symbol) => (
                          <span
                            key={symbol}
                            className="text-xs px-2 py-0.5 bg-blue-900/30 text-blue-400 rounded"
                          >
                            {symbol}
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

function MarketStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800 rounded p-3 border border-gray-700">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className="text-lg font-semibold text-white">{value}</div>
    </div>
  );
}

function MoverPanel({
  title,
  items,
  positive = false,
}: {
  title: string;
  items: TopMover[];
  positive?: boolean;
}) {
  return (
    <div className="bg-gray-800 rounded p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-white mb-3">{title}</h3>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.symbol} className="flex items-center justify-between">
            <span className="text-sm text-gray-300">{item.symbol.replace("USDT", "")}</span>
            <span className={`text-sm font-semibold ${positive ? "text-green-400" : "text-red-400"}`}>
              {positive ? "+" : ""}
              {item.change_24h_pct.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default MarketNews;
