/**
 * News Feed Page - Redesigned
 * Inspired by TradingView & Binance News
 *
 * Features:
 * - Clean card-based layout
 * - Real-time sentiment analysis
 * - Trending symbols sidebar
 * - Filter by source/symbol/timeframe
 * - No scrolling needed for key info
 */
import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Clock,
  Search,
  ExternalLink,
  Flame,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

interface NewsArticle {
  id: string;
  source: string;
  title: string;
  summary: string;
  url: string;
  author: string;
  published_at: number;
  image_url?: string;
  tags: string[];
  symbols: string[];
  sentiment_score: number;
  sentiment_label: string;
}

interface TrendingSymbol {
  symbol: string;
  mention_count: number;
  avg_sentiment: number;
}

const NewsPageRedesigned: React.FC = () => {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedSymbol, setSelectedSymbol] = useState('all');
  const [timeRange, setTimeRange] = useState(24);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [currentPage, setCurrentPage] = useState(1);
  const [totalArticles, setTotalArticles] = useState(0);
  const articlesPerPage = 20;

  useEffect(() => {
    fetchNews();
    fetchTrending();

    // Auto-refresh every 5 minutes
    const interval = setInterval(() => {
      fetchNews();
      fetchTrending();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [selectedSource, selectedSymbol, timeRange, currentPage]);

  const fetchNews = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        limit: '100', // Fetch more for pagination
        hours: timeRange.toString()
      });

      if (selectedSource !== 'all') params.append('source', selectedSource);
      if (selectedSymbol !== 'all') params.append('symbol', selectedSymbol);

      const response = await fetch(`/api/news/latest?${params}`);
      const data = await response.json();
      const allArticles = data.articles || [];
      setTotalArticles(allArticles.length);

      // Paginate client-side
      const startIndex = (currentPage - 1) * articlesPerPage;
      const endIndex = startIndex + articlesPerPage;
      setArticles(allArticles.slice(startIndex, endIndex));

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error fetching news:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTrending = async () => {
    try {
      const response = await fetch('/api/news/trending?limit=10');
      const data = await response.json();
      setTrendingSymbols(data.trending_symbols || []);
    } catch (error) {
      console.error('Error fetching trending:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setCurrentPage(1);
      fetchNews();
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`/api/news/search?q=${encodeURIComponent(searchQuery)}&limit=100`);
      const data = await response.json();
      const allArticles = data.articles || [];
      setTotalArticles(allArticles.length);

      const startIndex = (currentPage - 1) * articlesPerPage;
      const endIndex = startIndex + articlesPerPage;
      setArticles(allArticles.slice(startIndex, endIndex));
    } catch (error) {
      console.error('Error searching news:', error);
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(totalArticles / articlesPerPage);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    // Scroll to top of page
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.2) return 'text-green-400 bg-green-500/10 border-green-500/30';
    if (score < -0.2) return 'text-red-400 bg-red-500/10 border-red-500/30';
    return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
  };

  const getSentimentIcon = (score: number) => {
    if (score > 0.2) return <TrendingUp size={12} />;
    if (score < -0.2) return <TrendingDown size={12} />;
    return null;
  };

  const formatTimeAgo = (timestamp: number) => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const stripHtmlTags = (html: string): string => {
    if (!html) return '';
    // Remove HTML tags
    const text = html.replace(/<[^>]*>/g, '');
    // Decode HTML entities
    const textarea = document.createElement('textarea');
    textarea.innerHTML = text;
    return textarea.value;
  };

  const sources = [
    'all', 'CryptoPanic', 'CoinDesk', 'CoinTelegraph', 'Decrypt',
    'The Block', 'Bitcoin Magazine', 'CryptoSlate', 'BeInCrypto',
    'NewsBTC', 'U.Today', 'Bitcoinist', 'CryptoNews'
  ];

  const symbols = ['all', 'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE'];

  return (
    <div className="h-screen bg-[#0B0E11] text-gray-100 flex flex-col">
      {/* HEADER + FILTERS SECTION - NOT SCROLLABLE */}
      <div className="flex-shrink-0 p-4 md:p-6">
        {/* Header */}
        <div className="mb-4">
          <h1 className="text-2xl md:text-3xl font-bold mb-2 flex items-center gap-3">
            <span className="text-2xl">📰</span>
            Crypto News Feed
          </h1>
          <div className="flex items-center gap-3 text-sm text-gray-400">
            <span>Real-time news from 12+ sources</span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock size={14} />
              Updated {formatTimeAgo(lastUpdate.getTime())}
            </span>
          </div>
        </div>

        {/* Filters Bar */}
        <div className="bg-[#131722] border border-gray-800 rounded-xl p-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
            {/* Search */}
            <div className="md:col-span-4 relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                placeholder="Search news..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="w-full bg-[#1E222D] border border-gray-700 text-sm rounded-lg pl-10 pr-3 py-2.5 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
              />
            </div>

            {/* Source Filter */}
            <div className="md:col-span-2">
              <select
                value={selectedSource}
                onChange={(e) => { setSelectedSource(e.target.value); setCurrentPage(1); }}
                className="w-full bg-[#1E222D] border border-gray-700 text-white text-sm rounded-lg px-3 py-2.5 focus:border-blue-500 focus:outline-none transition-colors"
              >
                {sources.map(source => (
                  <option key={source} value={source}>
                    {source === 'all' ? 'All Sources' : source}
                  </option>
                ))}
              </select>
            </div>

            {/* Symbol Filter */}
            <div className="md:col-span-2">
              <select
                value={selectedSymbol}
                onChange={(e) => { setSelectedSymbol(e.target.value); setCurrentPage(1); }}
                className="w-full bg-[#1E222D] border border-gray-700 text-white text-sm rounded-lg px-3 py-2.5 focus:border-blue-500 focus:outline-none transition-colors"
              >
                {symbols.map(symbol => (
                  <option key={symbol} value={symbol}>
                    {symbol === 'all' ? 'All Symbols' : symbol}
                  </option>
                ))}
              </select>
            </div>

            {/* Time Range */}
            <div className="md:col-span-2">
              <select
                value={timeRange}
                onChange={(e) => { setTimeRange(Number(e.target.value)); setCurrentPage(1); }}
                className="w-full bg-[#1E222D] border border-gray-700 text-white text-sm rounded-lg px-3 py-2.5 focus:border-blue-500 focus:outline-none transition-colors"
              >
                <option value={1}>Last Hour</option>
                <option value={6}>Last 6 Hours</option>
                <option value={24}>Last 24 Hours</option>
                <option value={72}>Last 3 Days</option>
                <option value={168}>Last Week</option>
              </select>
            </div>

            {/* Refresh Button */}
            <div className="md:col-span-2">
              <button
                onClick={() => { fetchNews(); fetchTrending(); }}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg px-3 py-2.5 flex items-center justify-center gap-2 transition-colors"
              >
                <RefreshCw size={16} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* MAIN CONTENT SECTION - SCROLLABLE */}
      <div className="flex-1 overflow-hidden px-4 md:px-6 pb-4 md:pb-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full">
          {/* Main News Feed - SCROLLABLE */}
          <div className="lg:col-span-3 h-full overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
            {loading ? (
              <div className="flex justify-center items-center py-20">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : (
              <>
                <div className="space-y-4 pb-6">
                {articles.map((article) => (
                  <div
                    key={article.id}
                    className="bg-[#131722] border border-gray-800 rounded-xl overflow-hidden hover:border-gray-700 transition-all group"
                  >
                    <div className="flex flex-col md:flex-row">
                      {/* Image */}
                      {article.image_url && (
                        <div className="md:w-64 relative overflow-hidden bg-gray-900">
                          <img
                            src={article.image_url}
                            alt={article.title}
                            className="w-full h-48 md:h-full object-cover transition-transform duration-500 group-hover:scale-105"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                          />
                        </div>
                      )}

                      {/* Content */}
                      <div className="p-5 flex-1">
                        {/* Source & Time */}
                        <div className="flex items-center gap-3 mb-3 text-xs">
                          <span className="bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-1 rounded-md font-medium">
                            {article.source}
                          </span>
                          <span className="flex items-center text-gray-500">
                            <Clock size={12} className="mr-1" />
                            {formatTimeAgo(article.published_at)}
                          </span>
                          {/* Sentiment Badge */}
                          <span className={`flex items-center gap-1 px-2 py-1 rounded-md border text-xs font-medium ${getSentimentColor(article.sentiment_score)}`}>
                            {getSentimentIcon(article.sentiment_score)}
                            {article.sentiment_score > 0 ? '+' : ''}{article.sentiment_score.toFixed(2)}
                          </span>
                        </div>

                        {/* Title */}
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="group/link"
                        >
                          <h3 className="text-base md:text-lg font-bold mb-2 text-white group-hover/link:text-blue-400 transition-colors flex items-start">
                            {article.title}
                            <ExternalLink size={14} className="ml-2 mt-1 opacity-0 group-hover/link:opacity-100 transition-opacity flex-shrink-0" />
                          </h3>
                        </a>

                        {/* Summary */}
                        <p className="text-sm text-gray-400 mb-3 line-clamp-2">
                          {stripHtmlTags(article.summary)}
                        </p>

                        {/* Symbols & Tags */}
                        <div className="flex flex-wrap gap-2">
                          {article.symbols.slice(0, 5).map(symbol => (
                            <span
                              key={symbol}
                              className="text-xs font-mono font-bold px-2 py-1 rounded-md bg-gray-800 border border-gray-700 text-gray-300"
                            >
                              {symbol}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {articles.length === 0 && !loading && (
                  <div className="bg-[#131722] border border-gray-800 border-dashed rounded-xl p-10 text-center">
                    <p className="text-gray-500">No articles found. Try adjusting your filters.</p>
                  </div>
                )}
              </div>

              {/* Pagination */}
              {totalArticles > articlesPerPage && (
                <div className="flex items-center justify-between bg-[#131722] border border-gray-800 rounded-xl p-4 mt-6">
                <div className="text-sm text-gray-400">
                  Showing {((currentPage - 1) * articlesPerPage) + 1} - {Math.min(currentPage * articlesPerPage, totalArticles)} of {totalArticles} articles
                </div>
                <div className="flex items-center gap-2">
                  {/* Previous Button */}
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      currentPage === 1
                        ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
                        : 'bg-gray-800 text-white hover:bg-gray-700'
                    }`}
                  >
                    Previous
                  </button>

                  {/* Page Numbers */}
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 7) {
                        pageNum = i + 1;
                      } else if (currentPage <= 4) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 3) {
                        pageNum = totalPages - 6 + i;
                      } else {
                        pageNum = currentPage - 3 + i;
                      }

                      return (
                        <button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          className={`w-10 h-10 rounded-lg text-sm font-medium transition-colors ${
                            currentPage === pageNum
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>

                  {/* Next Button */}
                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      currentPage === totalPages
                        ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
                        : 'bg-gray-800 text-white hover:bg-gray-700'
                    }`}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
            </>
            )}
          </div>

          {/* Sidebar - Trending Symbols */}
          <div className="lg:col-span-1 h-full overflow-y-auto scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
            <div className="bg-[#131722] border border-gray-800 rounded-xl overflow-hidden">
              <div className="bg-gradient-to-r from-orange-500/10 to-transparent border-b border-gray-800 px-4 py-4">
                <h2 className="font-bold flex items-center gap-2 text-white">
                  <Flame size={18} className="text-orange-500" />
                  Trending
                </h2>
              </div>
              <div className="divide-y divide-gray-800">
                {trendingSymbols.map((item, index) => (
                  <div
                    key={item.symbol}
                    className="px-4 py-3 hover:bg-gray-800/30 transition-colors cursor-pointer"
                    onClick={() => { setSelectedSymbol(item.symbol); setCurrentPage(1); }}
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 text-center text-sm font-bold text-gray-600">
                        {index + 1}
                      </span>
                      <div className="flex-1">
                        <div className="font-mono font-bold text-white text-sm">
                          {item.symbol}
                        </div>
                        <div className="text-xs text-gray-500">
                          {item.mention_count} mentions
                        </div>
                      </div>
                      <div className={`text-xs font-bold ${item.avg_sentiment > 0 ? 'text-green-400' : item.avg_sentiment < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                        {item.avg_sentiment > 0 ? '+' : ''}{item.avg_sentiment.toFixed(2)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewsPageRedesigned;
