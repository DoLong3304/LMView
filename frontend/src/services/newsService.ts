import { DATA_SOURCE } from "@/constants/env";
import { apiGet, buildQuery } from "@/services/apiClient";
import { generateMockNews } from "@/data/mockDataGenerator";
import type { NewsArticle, NewsFilters, TrendingSymbol } from "@/types";

function normalizeNewsItem(item: Partial<NewsArticle>): NewsArticle {
  return {
    id: item.id || `${item.source || "news"}-${item.published_at || Date.now()}`,
    source: item.source || "",
    title: item.title || "",
    summary: item.summary || "",
    url: item.url || "#",
    author: item.author,
    published_at: item.published_at || Date.now(),
    image_url: item.image_url,
    tags: item.tags || [],
    symbols: item.symbols || [],
    sentiment_score: Number(item.sentiment_score || 0),
    sentiment_label: item.sentiment_label || "Neutral",
    language: item.language,
    region: item.region,
  };
}

function mockNews(filters: NewsFilters): NewsArticle[] {
  return generateMockNews(filters.limit || 20, filters.symbol === "all" ? undefined : filters.symbol)
    .map((item) => normalizeNewsItem({ ...item, published_at: Date.parse(item.published_at) }));
}

export async function fetchLatestNews(filters: NewsFilters = {}): Promise<NewsArticle[]> {
  if (DATA_SOURCE === "mock") {
    return mockNews(filters);
  }

  const query = buildQuery({
    limit: filters.limit || 100,
    hours: filters.hours || 24,
    source: filters.source === "all" ? undefined : filters.source,
    symbol: filters.symbol === "all" ? undefined : filters.symbol,
  });
  const payload = await apiGet<{ articles?: NewsArticle[] } | NewsArticle[]>(`/news/latest?${query}`);
  const articles = Array.isArray(payload) ? payload : payload.articles || [];
  return articles.map(normalizeNewsItem);
}

export async function searchNews(filters: NewsFilters): Promise<NewsArticle[]> {
  if (!filters.query?.trim()) {
    return fetchLatestNews(filters);
  }

  if (DATA_SOURCE === "mock") {
    const q = filters.query.toLowerCase();
    return mockNews(filters).filter((item) =>
      `${item.title} ${item.summary}`.toLowerCase().includes(q),
    );
  }

  const query = buildQuery({ q: filters.query, limit: filters.limit || 100 });
  const payload = await apiGet<{ articles?: NewsArticle[] } | NewsArticle[]>(`/news/search?${query}`);
  const articles = Array.isArray(payload) ? payload : payload.articles || [];
  return articles.map(normalizeNewsItem);
}

export async function fetchTrendingSymbols(limit: number = 10): Promise<TrendingSymbol[]> {
  if (DATA_SOURCE === "mock") {
    return [
      { symbol: "BTC", mention_count: 42, avg_sentiment: 0.18 },
      { symbol: "ETH", mention_count: 35, avg_sentiment: 0.12 },
      { symbol: "SOL", mention_count: 28, avg_sentiment: 0.32 },
      { symbol: "BNB", mention_count: 20, avg_sentiment: 0.04 },
    ].slice(0, limit);
  }

  const payload = await apiGet<{ trending_symbols?: TrendingSymbol[] } | TrendingSymbol[]>(
    `/news/trending?${buildQuery({ limit })}`,
  );
  return Array.isArray(payload) ? payload : payload.trending_symbols || [];
}
