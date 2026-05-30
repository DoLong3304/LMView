import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Clock,
  ExternalLink,
  Flame,
  LayoutGrid,
  List,
  Newspaper,
  RefreshCw,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { NEWS_REFRESH_MS, NEWS_SOURCES, NEWS_SYMBOLS } from "@/constants/market";
import {
  fetchLatestNews,
  fetchTrendingSymbols,
  searchNews,
} from "@/services/newsService";
import { useI18n } from "@/i18n";
import type { NewsArticle, TrendingSymbol } from "@/types";

const ARTICLES_PER_PAGE = 10;
const GRID_MODE_QUERY = "(min-width: 640px)";
type NewsViewMode = "list" | "grid";

const NewsPage: React.FC = () => {
  const { t } = useI18n();
  const listRef = React.useRef<HTMLElement | null>(null);
  const [allArticles, setAllArticles] = useState<NewsArticle[]>([]);
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSource, setSelectedSource] = useState("all");
  const [selectedSymbol, setSelectedSymbol] = useState("all");
  const [timeRange, setTimeRange] = useState(24);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [currentPage, setCurrentPage] = useState(1);
  const [viewMode, setViewMode] = useState<NewsViewMode>("list");
  const [canUseGrid, setCanUseGrid] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia(GRID_MODE_QUERY).matches;
  });

  const filters = useMemo(
    () => ({
      limit: 100,
      hours: timeRange,
      source: selectedSource,
      symbol: selectedSymbol,
      query: searchQuery,
    }),
    [searchQuery, selectedSource, selectedSymbol, timeRange],
  );

  const fetchNewsData = useCallback(async () => {
    try {
      setLoading(true);
      const articles = searchQuery.trim()
        ? await searchNews(filters)
        : await fetchLatestNews(filters);
      setAllArticles(articles);
      setLastUpdate(new Date());
    } catch (error) {
      console.error("Error fetching news:", error);
    } finally {
      setLoading(false);
    }
  }, [filters, searchQuery]);

  const fetchTrending = useCallback(async () => {
    try {
      setTrendingSymbols(await fetchTrendingSymbols(10));
    } catch (error) {
      console.error("Error fetching trending:", error);
    }
  }, []);

  useEffect(() => {
    fetchNewsData();
    fetchTrending();

    const interval = setInterval(() => {
      fetchNewsData();
      fetchTrending();
    }, NEWS_REFRESH_MS);

    return () => clearInterval(interval);
  }, [fetchNewsData, fetchTrending]);

  useEffect(() => {
    const mediaQuery = window.matchMedia(GRID_MODE_QUERY);
    const syncGridAvailability = () => {
      const available = mediaQuery.matches;
      setCanUseGrid(available);
      if (!available) setViewMode("list");
    };

    syncGridAvailability();
    mediaQuery.addEventListener("change", syncGridAvailability);
    return () => mediaQuery.removeEventListener("change", syncGridAvailability);
  }, []);

  const articles = useMemo(() => {
    const startIndex = (currentPage - 1) * ARTICLES_PER_PAGE;
    return allArticles.slice(startIndex, startIndex + ARTICLES_PER_PAGE);
  }, [allArticles, currentPage]);

  const totalPages = Math.ceil(allArticles.length / ARTICLES_PER_PAGE);
  const isGridView = viewMode === "grid" && canUseGrid;
  const articleLayoutClass = isGridView
    ? "grid grid-cols-2 xl:grid-cols-3 gap-4 pb-6"
    : "space-y-4 pb-6";

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    listRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleRefresh = () => {
    fetchNewsData();
    fetchTrending();
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.2) return "text-green-400 bg-green-500/10 border-green-500/30";
    if (score < -0.2) return "text-red-400 bg-red-500/10 border-red-500/30";
    return "text-gray-400 bg-gray-500/10 border-gray-500/30";
  };

  const getSentimentIcon = (score: number) => {
    if (score > 0.2) return <TrendingUp size={12} />;
    if (score < -0.2) return <TrendingDown size={12} />;
    return null;
  };

  const formatTimeAgo = (timestamp: number | string) => {
    const rawTime = typeof timestamp === "string" ? Date.parse(timestamp) : timestamp;
    const seconds = Math.max(0, Math.floor((Date.now() - rawTime) / 1000));
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  };

  const stripHtmlTags = (html: string): string => {
    if (!html) return "";
    const text = html.replace(/<[^>]*>/g, "");
    const textarea = document.createElement("textarea");
    textarea.innerHTML = text;
    return textarea.value;
  };

  return (
    <div className="h-full min-h-0 bg-gray-900 text-gray-100 flex flex-col">
      <div className="flex-shrink-0 p-3 md:p-4">
        <div className="mb-3">
          <h1 className="text-xl md:text-2xl font-bold mb-1.5 flex items-center gap-2">
            <Newspaper className="text-blue-400" size={24} />
            {t("newsFeedTitle")}
          </h1>
          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-400">
            <span>{t("newsFeedSubtitle")}</span>
            <span>|</span>
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {t("updatedAgo")} {formatTimeAgo(lastUpdate.getTime())}
            </span>
          </div>
        </div>

        <div className="bg-gray-850 border border-gray-800 rounded p-2.5">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-12">
            <div className="relative sm:col-span-2 lg:col-span-3">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                placeholder={t("searchNews")}
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                onKeyDown={(e) => e.key === "Enter" && fetchNewsData()}
                className="w-full bg-gray-800 border border-gray-700 text-xs rounded pl-8 pr-2.5 py-1.5 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
              />
            </div>

            <FilterSelect
              className="lg:col-span-2"
              value={selectedSource}
              onChange={(value) => {
                setSelectedSource(value);
                setCurrentPage(1);
              }}
              options={[...NEWS_SOURCES]}
              allLabel={t("allSources")}
            />

            <FilterSelect
              className="lg:col-span-2"
              value={selectedSymbol}
              onChange={(value) => {
                setSelectedSymbol(value);
                setCurrentPage(1);
              }}
              options={[...NEWS_SYMBOLS]}
              allLabel={t("allSymbols")}
            />

            <div className="lg:col-span-2">
              <select
                value={timeRange}
                onChange={(e) => {
                  setTimeRange(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="w-full bg-gray-800 border border-gray-700 text-white text-xs rounded px-2.5 py-1.5 focus:border-blue-500 focus:outline-none transition-colors"
              >
                <option value={1}>{t("lastHour")}</option>
                <option value={6}>{t("last6Hours")}</option>
                <option value={24}>{t("last24Hours")}</option>
                <option value={72}>{t("last3Days")}</option>
                <option value={168}>{t("lastWeek")}</option>
              </select>
            </div>

            <div className="lg:col-span-1">
              <button
                onClick={handleRefresh}
                title={t("refresh")}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white text-xs rounded px-2 py-1.5 flex items-center justify-center gap-1.5 transition-colors"
              >
                <RefreshCw size={14} />
                <span className="lg:hidden xl:inline">{t("refresh")}</span>
              </button>
            </div>

            <div className="flex items-center gap-0.5 rounded border border-gray-700 bg-gray-800 p-0.5 lg:col-span-2">
              <button
                onClick={() => setViewMode("list")}
                className={`flex flex-1 items-center justify-center rounded px-2 py-1 transition-colors ${
                  viewMode === "list"
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:bg-gray-700 hover:text-white"
                }`}
                title={t("listView")}
              >
                <List size={14} />
              </button>
              {canUseGrid && (
                <button
                  onClick={() => setViewMode("grid")}
                  className={`flex flex-1 items-center justify-center rounded px-2 py-1 transition-colors ${
                    viewMode === "grid"
                      ? "bg-blue-600 text-white"
                      : "text-gray-400 hover:bg-gray-700 hover:text-white"
                  }`}
                  title={t("gridView")}
                >
                  <LayoutGrid size={14} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden px-3 md:px-4 pb-3 md:pb-4">
        <div className="grid h-full min-h-0 grid-cols-1 gap-6 lg:grid-cols-4">
          <main ref={listRef} className="lg:col-span-3 min-h-0 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
            {loading ? (
              <div className="flex justify-center items-center py-20">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <>
                <div className={articleLayoutClass}>
                  {articles.map((article) => (
                    <a
                      key={article.id}
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block bg-gray-850 border border-gray-800 rounded overflow-hidden hover:border-gray-700 transition-all group"
                    >
                      <div className={isGridView ? "flex h-full flex-col" : "flex flex-col md:flex-row"}>
                        {article.image_url && (
                          <div className={isGridView ? "relative h-40 overflow-hidden bg-gray-900" : "md:w-64 relative overflow-hidden bg-gray-900"}>
                            <img
                              src={article.image_url}
                              alt={article.title}
                              className={isGridView ? "h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" : "w-full h-48 md:h-full object-cover transition-transform duration-500 group-hover:scale-105"}
                              onError={(e) => {
                                e.currentTarget.style.display = "none";
                              }}
                            />
                          </div>
                        )}

                        <div className="p-5 flex-1">
                          <div className="flex flex-wrap items-center gap-2 mb-3 text-xs">
                            <span className="bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-1 rounded font-medium">
                              {article.source}
                            </span>
                            <span className="flex items-center text-gray-500">
                              <Clock size={12} className="mr-1" />
                              {formatTimeAgo(article.published_at)}
                            </span>
                            <span
                              className={`flex items-center gap-1 px-2 py-1 rounded border text-xs font-medium ${getSentimentColor(
                                article.sentiment_score,
                              )}`}
                            >
                              {getSentimentIcon(article.sentiment_score)}
                              {article.sentiment_score > 0 ? "+" : ""}
                              {article.sentiment_score.toFixed(2)}
                            </span>
                          </div>

                          <h3 className="text-base md:text-lg font-bold mb-2 text-white group-hover:text-blue-400 transition-colors flex items-start">
                            {article.title}
                            <ExternalLink size={14} className="ml-2 mt-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                          </h3>

                          <p className="text-sm text-gray-400 mb-3 line-clamp-2">
                            {stripHtmlTags(article.summary)}
                          </p>

                          <div className="flex flex-wrap gap-2">
                            {article.symbols.slice(0, 5).map((symbol) => (
                              <span
                                key={symbol}
                                className="text-xs font-mono font-bold px-2 py-1 rounded bg-gray-800 border border-gray-700 text-gray-300"
                              >
                                {symbol}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </a>
                  ))}

                  {articles.length === 0 && !loading && (
                    <div className="bg-gray-850 border border-gray-800 border-dashed rounded p-10 text-center">
                      <p className="text-gray-500">{t("noArticlesFound")}</p>
                    </div>
                  )}
                </div>

                {allArticles.length > ARTICLES_PER_PAGE && (
                  <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    totalArticles={allArticles.length}
                    articlesPerPage={ARTICLES_PER_PAGE}
                    onPageChange={handlePageChange}
                  />
                )}
              </>
            )}
          </main>

          <aside className="lg:col-span-1 min-h-0 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
            <TrendingPanel
              items={trendingSymbols}
              onSelectSymbol={(symbol) => {
                setSelectedSymbol(symbol);
                setCurrentPage(1);
              }}
            />
          </aside>
        </div>
      </div>
    </div>
  );
};

interface FilterSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  allLabel: string;
  className?: string;
}

function FilterSelect({ value, onChange, options, allLabel, className = "" }: FilterSelectProps) {
  return (
    <div className={className}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 text-white text-xs rounded px-2.5 py-1.5 focus:border-blue-500 focus:outline-none transition-colors"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option === "all" ? allLabel : option}
          </option>
        ))}
      </select>
    </div>
  );
}

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalArticles: number;
  articlesPerPage: number;
  onPageChange: (page: number) => void;
}

function Pagination({
  currentPage,
  totalPages,
  totalArticles,
  articlesPerPage,
  onPageChange,
}: PaginationProps) {
  const { t } = useI18n();
  const first = (currentPage - 1) * articlesPerPage + 1;
  const last = Math.min(currentPage * articlesPerPage, totalArticles);

  return (
    <div className="flex items-center justify-between bg-gray-850 border border-gray-800 rounded p-4 mt-6">
      <div className="text-sm text-gray-400">
        {t("showing")} {first} - {last} {t("of")} {totalArticles} {t("articles")}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
            currentPage === 1
              ? "bg-gray-800 text-gray-600 cursor-not-allowed"
              : "bg-gray-800 text-white hover:bg-gray-700"
          }`}
        >
          {t("previous")}
        </button>

        <div className="flex items-center gap-1">
          {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
            let pageNum: number;
            if (totalPages <= 7) pageNum = i + 1;
            else if (currentPage <= 4) pageNum = i + 1;
            else if (currentPage >= totalPages - 3) pageNum = totalPages - 6 + i;
            else pageNum = currentPage - 3 + i;

            return (
              <button
                key={pageNum}
                onClick={() => onPageChange(pageNum)}
                className={`w-10 h-10 rounded text-sm font-medium transition-colors ${
                  currentPage === pageNum
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                }`}
              >
                {pageNum}
              </button>
            );
          })}
        </div>

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
            currentPage === totalPages
              ? "bg-gray-800 text-gray-600 cursor-not-allowed"
              : "bg-gray-800 text-white hover:bg-gray-700"
          }`}
        >
          {t("next")}
        </button>
      </div>
    </div>
  );
}

interface TrendingPanelProps {
  items: TrendingSymbol[];
  onSelectSymbol: (symbol: string) => void;
}

function TrendingPanel({ items, onSelectSymbol }: TrendingPanelProps) {
  const { t } = useI18n();

  return (
    <div className="bg-gray-850 border border-gray-800 rounded overflow-hidden">
      <div className="bg-gradient-to-r from-orange-500/10 to-transparent border-b border-gray-800 px-4 py-4">
        <h2 className="font-bold flex items-center gap-2 text-white">
          <Flame size={18} className="text-orange-500" />
          {t("trending")}
        </h2>
      </div>
      <div className="divide-y divide-gray-800">
        {items.map((item, index) => (
          <button
            key={item.symbol}
            className="w-full text-left px-4 py-3 hover:bg-gray-800/30 transition-colors"
            onClick={() => onSelectSymbol(item.symbol)}
          >
            <div className="flex items-center gap-3">
              <span className="w-6 text-center text-sm font-bold text-gray-600">{index + 1}</span>
              <div className="flex-1">
                <div className="font-mono font-bold text-white text-sm">{item.symbol}</div>
                <div className="text-xs text-gray-500">
                  {item.mention_count} {t("mentions")}
                </div>
              </div>
              <div
                className={`text-xs font-bold ${
                  item.avg_sentiment > 0
                    ? "text-green-400"
                    : item.avg_sentiment < 0
                      ? "text-red-400"
                      : "text-gray-400"
                }`}
              >
                {item.avg_sentiment > 0 ? "+" : ""}
                {item.avg_sentiment.toFixed(2)}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default NewsPage;
