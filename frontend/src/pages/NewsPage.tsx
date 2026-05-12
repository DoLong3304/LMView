import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Grid,
  Chip,
  Avatar,
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Link,
  Divider,
  Tab,
  Tabs
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  AccessTime,
  Language,
  Search as SearchIcon
} from '@mui/icons-material';

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
  const [activeTab, setActiveTab] = useState(0);

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
    if (score > 0.05) return '#4caf50'; // Green
    if (score < -0.05) return '#f44336'; // Red
    return '#9e9e9e'; // Gray
  };

  const getSentimentIcon = (score: number) => {
    if (score > 0.05) return <TrendingUp />;
    if (score < -0.05) return <TrendingDown />;
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
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Typography variant="h4" gutterBottom>
        📰 Crypto News Feed
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Real-time news from 12+ sources • Updated every 5 minutes
      </Typography>

      {/* Filters */}
      <Card sx={{ mb: 3, mt: 2 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                placeholder="Search news..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                InputProps={{
                  startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
                }}
              />
            </Grid>

            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>Source</InputLabel>
                <Select
                  value={selectedSource}
                  onChange={(e) => setSelectedSource(e.target.value)}
                  label="Source"
                >
                  {sources.map(source => (
                    <MenuItem key={source} value={source}>
                      {source === 'all' ? 'All Sources' : source}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>Symbol</InputLabel>
                <Select
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value)}
                  label="Symbol"
                >
                  {symbols.map(symbol => (
                    <MenuItem key={symbol} value={symbol}>
                      {symbol === 'all' ? 'All Symbols' : symbol}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>Time Range</InputLabel>
                <Select
                  value={timeRange}
                  onChange={(e) => setTimeRange(Number(e.target.value))}
                  label="Time Range"
                >
                  <MenuItem value={1}>Last Hour</MenuItem>
                  <MenuItem value={6}>Last 6 Hours</MenuItem>
                  <MenuItem value={24}>Last 24 Hours</MenuItem>
                  <MenuItem value={72}>Last 3 Days</MenuItem>
                  <MenuItem value={168}>Last Week</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={2}>
              <Typography variant="body2" color="text.secondary">
                {articles.length} articles
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 2 }}>
        <Tab label="Latest News" />
        <Tab label="Trending" />
      </Tabs>

      <Grid container spacing={3}>
        {/* Main Content */}
        <Grid item xs={12} md={8}>
          {loading ? (
            <Box display="flex" justifyContent="center" p={5}>
              <CircularProgress />
            </Box>
          ) : (
            <Box>
              {articles.map((article) => (
                <Card key={article.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Grid container spacing={2}>
                      {/* Image */}
                      {article.image_url && (
                        <Grid item xs={12} md={3}>
                          <img
                            src={article.image_url}
                            alt={article.title}
                            style={{ width: '100%', borderRadius: 8 }}
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                          />
                        </Grid>
                      )}

                      {/* Content */}
                      <Grid item xs={12} md={article.image_url ? 9 : 12}>
                        {/* Source & Time */}
                        <Box display="flex" alignItems="center" mb={1}>
                          <Chip
                            label={article.source}
                            size="small"
                            sx={{ mr: 1 }}
                          />
                          <Typography variant="caption" color="text.secondary" display="flex" alignItems="center">
                            <AccessTime sx={{ fontSize: 14, mr: 0.5 }} />
                            {formatTimeAgo(article.published_at)}
                          </Typography>
                        </Box>

                        {/* Title */}
                        <Link
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          underline="hover"
                          color="inherit"
                        >
                          <Typography variant="h6" gutterBottom>
                            {article.title}
                          </Typography>
                        </Link>

                        {/* Summary */}
                        <Typography variant="body2" color="text.secondary" paragraph>
                          {article.summary}
                        </Typography>

                        {/* Metadata */}
                        <Box display="flex" flexWrap="wrap" gap={1} alignItems="center">
                          {/* Sentiment */}
                          <Chip
                            icon={getSentimentIcon(article.sentiment_score) || undefined}
                            label={`Sentiment: ${article.sentiment_score.toFixed(2)}`}
                            size="small"
                            sx={{
                              backgroundColor: getSentimentColor(article.sentiment_score),
                              color: 'white'
                            }}
                          />

                          {/* Symbols */}
                          {article.symbols.map(symbol => (
                            <Chip
                              key={symbol}
                              label={symbol}
                              size="small"
                              variant="outlined"
                            />
                          ))}

                          {/* Tags */}
                          {article.tags.slice(0, 3).map(tag => (
                            <Chip
                              key={tag}
                              label={tag}
                              size="small"
                              variant="outlined"
                              sx={{ opacity: 0.7 }}
                            />
                          ))}
                        </Box>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              ))}

              {articles.length === 0 && !loading && (
                <Card>
                  <CardContent>
                    <Typography variant="body1" color="text.secondary" align="center">
                      No articles found. Try adjusting your filters.
                    </Typography>
                  </CardContent>
                </Card>
              )}
            </Box>
          )}
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Trending Symbols */}
          <Card sx={{ mb: 2 }}>
            <CardHeader title="🔥 Trending Symbols" />
            <Divider />
            <CardContent>
              {trendingSymbols.map((item, index) => (
                <Box key={item.symbol} mb={2}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Box display="flex" alignItems="center">
                      <Typography variant="h6" sx={{ mr: 1 }}>
                        #{index + 1}
                      </Typography>
                      <Chip label={item.symbol} />
                    </Box>
                    <Box textAlign="right">
                      <Typography variant="body2" color="text.secondary">
                        {item.mention_count} mentions
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ color: getSentimentColor(item.avg_sentiment) }}
                      >
                        {item.avg_sentiment > 0 ? '+' : ''}{item.avg_sentiment.toFixed(2)}
                      </Typography>
                    </Box>
                  </Box>
                  {index < trendingSymbols.length - 1 && <Divider sx={{ mt: 2 }} />}
                </Box>
              ))}
            </CardContent>
          </Card>

          {/* Sources */}
          <Card>
            <CardHeader title="📡 News Sources" />
            <Divider />
            <CardContent>
              <Typography variant="body2" color="text.secondary" paragraph>
                Aggregating news from 12 major crypto publications:
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1}>
                {sources.filter(s => s !== 'all').map(source => (
                  <Chip
                    key={source}
                    label={source}
                    size="small"
                    onClick={() => setSelectedSource(source)}
                    color={selectedSource === source ? 'primary' : 'default'}
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default NewsPage;
