import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Clock,
  Search,
  ExternalLink,
  Flame
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
  language: string;
  region: string;
}

interface TrendingSymbol {
  symbol: string;
  mention_count: number;
  avg_sentiment: number;
}

const NewsPage: React.FC = () => {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedSymbol, setSelectedSymbol] = useState('all');
  const [timeRange, setTimeRange] = useState(24);
  const [activeTab, setActiveTab] = useState('latest');

  // Fetch news data
  useEffect(() => {
    fetchNews();
    fetchTrending();

    // Auto-refresh every 5 minutes
    const interval = setInterval(() => {
      fetchNews();
      fetchTrending();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [selectedSource, selectedSymbol, timeRange]);

  const fetchNews = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        limit: '50',
        hours: timeRange.toString()
      });

      if (selectedSource !== 'all') {
        params.append('source', selectedSource);
      }

      if (selectedSymbol !== 'all') {
        params.append('symbol', selectedSymbol);
      }

      const response = await fetch(`/api/news/latest?${params}`);
      const data = await response.json();
      setArticles(data.articles || []);
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
      fetchNews();
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`/api/news/search?q=${encodeURIComponent(searchQuery)}&limit=50`);
      const data = await response.json();
      setArticles(data.articles || []);
    } catch (error) {
      console.error('Error searching news:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.05) return 'text-green-400 bg-green-400/10 border-green-400/20';
    if (score < -0.05) return 'text-red-400 bg-red-400/10 border-red-400/20';
    return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
  };

  const getSentimentIcon = (score: number) => {
    if (score > 0.05) return <TrendingUp size={14} className="mr-1" />;
    if (score < -0.05) return <TrendingDown size={14} className="mr-1" />;
    return null;
  };

  const formatTimeAgo = (timestamp: number) => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);

    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const sources = [
    'all', 'CryptoPanic', 'CoinDesk', 'CoinTelegraph', 'Decrypt',
    'The Block', 'Bitcoin Magazine', 'CryptoSlate', 'BeInCrypto',
    'NewsBTC', 'U.Today', 'Bitcoinist', 'CryptoNews'
  ];

  const symbols = ['all', 'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'MATIC', 'DOT', 'AVAX'];

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto text-gray-100">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2 flex items-center">
          <span className="mr-3 text-2xl">📰</span> Crypto News Feed
        </h1>
        <p className="text-sm text-gray-400">
          Real-time news from 12+ sources • Updated every 5 minutes
        </p>
      </div>

      {/* Filters */}
      <div className="bg-gray-800/60 backdrop-blur-md rounded-xl border border-gray-700 p-4 mb-6 shadow-lg shadow-black/20">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
          <div className="md:col-span-4 relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search size={16} className="text-gray-500" />
            </div>
            <input
              type="text"
              placeholder="Search news..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full bg-gray-900 border border-gray-700 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block pl-10 p-2.5 text-white placeholder-gray-400 transition-colors"
            />
          </div>

          <div className="md:col-span-2">
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="bg-gray-900 border border-gray-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 outline-none transition-colors"
            >
              {sources.map(source => (
                <option key={source} value={source}>
                  {source === 'all' ? 'All Sources' : source}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="bg-gray-900 border border-gray-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 outline-none transition-colors"
            >
              {symbols.map(symbol => (
                <option key={symbol} value={symbol}>
                  {symbol === 'all' ? 'All Symbols' : symbol}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(Number(e.target.value))}
              className="bg-gray-900 border border-gray-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 outline-none transition-colors"
            >
              <option value={1}>Last Hour</option>
              <option value={6}>Last 6 Hours</option>
              <option value={24}>Last 24 Hours</option>
              <option value={72}>Last 3 Days</option>
              <option value={168}>Last Week</option>
            </select>
          </div>

          <div className="md:col-span-2 text-right">
            <span className="text-sm font-medium text-gray-400 bg-gray-900 px-3 py-1.5 rounded-full border border-gray-700 inline-block">
              {articles.length} articles
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {/* Tabs */}
          <div className="flex space-x-1 border-b border-gray-700 mb-6">
            <button
              onClick={() => setActiveTab('latest')}
              className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'latest'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'
              }`}
            >
              Latest News
            </button>
            <button
              onClick={() => setActiveTab('trending')}
              className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'trending'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'
              }`}
            >
              Trending
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center items-center py-20">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : (
            <div className="space-y-4">
              {articles.map((article) => (
                <div key={article.id} className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden hover:border-gray-600 transition-colors shadow-lg shadow-black/10">
                  <div className="flex flex-col md:flex-row">
                    {/* Image */}
                    {article.image_url && (
                      <div className="md:w-1/3 xl:w-1/4 relative overflow-hidden bg-gray-900 group">
                        <img
                          src={article.image_url}
                          alt={article.title}
                          className="w-full h-full object-cover min-h-[160px] md:min-h-full transition-transform duration-500 group-hover:scale-105"
                          onError={(e) => { e.currentTarget.style.display = 'none'; }}
                        />
                      </div>
                    )}

                    {/* Content */}
                    <div className="p-5 flex-1 flex flex-col justify-between">
                      <div>
                        {/* Source & Time */}
                        <div className="flex items-center mb-3 text-xs">
                          <span className="bg-blue-900/40 text-blue-300 border border-blue-800/50 px-2 py-0.5 rounded-md font-medium mr-3">
                            {article.source}
                          </span>
                          <span className="flex items-center text-gray-400">
                            <Clock size={12} className="mr-1" />
                            {formatTimeAgo(article.published_at)}
                          </span>
                        </div>

                        {/* Title */}
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="group"
                        >
                          <h3 className="text-lg font-bold mb-2 text-gray-100 group-hover:text-blue-400 transition-colors flex items-start">
                            {article.title}
                            <ExternalLink size={14} className="ml-1.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                          </h3>
                        </a>

                        {/* Summary */}
                        <p className="text-sm text-gray-400 mb-4 line-clamp-2">
                          {article.summary}
                        </p>
                      </div>

                      {/* Metadata */}
                      <div className="flex flex-wrap gap-2 items-center mt-auto">
                        {/* Sentiment */}
                        <span className={`flex items-center text-xs px-2 py-1 rounded-md border ${getSentimentColor(article.sentiment_score)}`}>
                          {getSentimentIcon(article.sentiment_score)}
                          Sentiment: {article.sentiment_score.toFixed(2)}
                        </span>

                        {/* Symbols */}
                        {article.symbols.map(symbol => (
                          <span key={symbol} className="text-xs font-mono font-medium px-2 py-1 rounded-md border border-gray-700 bg-gray-800/50 text-gray-300">
                            {symbol}
                          </span>
                        ))}

                        {/* Tags */}
                        {article.tags.slice(0, 3).map(tag => (
                          <span key={tag} className="text-xs px-2 py-1 rounded-md border border-gray-700/50 bg-gray-900/50 text-gray-500 lowercase">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {articles.length === 0 && !loading && (
                <div className="bg-gray-800/50 border border-gray-700 border-dashed rounded-xl p-10 text-center">
                  <p className="text-gray-400">No articles found. Try adjusting your filters.</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Trending Symbols */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-lg shadow-black/10">
            <div className="px-5 py-4 border-b border-gray-700 bg-gray-800/80">
              <h2 className="font-bold flex items-center text-lg">
                <Flame size={18} className="text-orange-500 mr-2" /> Trending Symbols
              </h2>
            </div>
            <div className="p-2">
              {trendingSymbols.map((item, index) => (
                <div key={item.symbol} className="flex justify-between items-center p-3 hover:bg-gray-700/50 rounded-lg transition-colors">
                  <div className="flex items-center">
                    <span className="w-6 text-center text-sm font-bold text-gray-500 mr-2">
                      {index + 1}
                    </span>
                    <span className="font-mono font-bold bg-gray-900 border border-gray-700 px-2 py-0.5 rounded text-sm text-gray-200">
                      {item.symbol}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-400 mb-0.5">
                      {item.mention_count} mentions
                    </div>
                    <div className={`text-xs font-medium ${item.avg_sentiment > 0 ? 'text-green-400' : item.avg_sentiment < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                      {item.avg_sentiment > 0 ? '+' : ''}{item.avg_sentiment.toFixed(2)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sources */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-lg shadow-black/10">
            <div className="px-5 py-4 border-b border-gray-700 bg-gray-800/80">
              <h2 className="font-bold text-lg">📡 News Sources</h2>
            </div>
            <div className="p-5">
              <p className="text-sm text-gray-400 mb-4">
                Aggregating news from 12 major crypto publications:
              </p>
              <div className="flex flex-wrap gap-2">
                {sources.filter(s => s !== 'all').map(source => (
                  <button
                    key={source}
                    onClick={() => setSelectedSource(source)}
                    className={`text-xs px-2.5 py-1.5 rounded-md border transition-colors ${
                      selectedSource === source
                        ? 'bg-blue-600 border-blue-500 text-white'
                        : 'bg-gray-900 border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500'
                    }`}
                  >
                    {source}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewsPage;
