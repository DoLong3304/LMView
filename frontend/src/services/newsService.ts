import { DATA_SOURCE } from "@/constants/env";
import { apiGet, buildQuery } from "@/services/apiClient";
import { isUnavailableApiPayload } from "@/services/apiMetadata";
import { makeClientCacheKey, withClientCache } from "@/services/clientCache";
import { getMockDataAdapter } from "@/services/dataSourceAdapter";
import type { NewsArticle, NewsFilters, TrendingSymbol } from "@/types";

const NEWS_CACHE_MS = 60_000;
const TRENDING_SYMBOLS_CACHE_MS = 60_000;
const mockDataAdapter = getMockDataAdapter();

function normalizeNewsItem(item: Partial<NewsArticle>): NewsArticle {
  const rawSymbols = (item as NewsArticle & { symbolsMentioned?: string[] }).symbolsMentioned || item.symbols || [];
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
    symbols: rawSymbols,
    sentiment_score: Number(item.sentiment_score || 0),
    sentiment_label: item.sentiment_label || "neutral",
    language: item.language,
    region: item.region,
  };
}

export async function fetchLatestNews(filters: NewsFilters = {}): Promise<NewsArticle[]> {
  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.fetchLatestNews(filters);
    return payload.articles.map(normalizeNewsItem);
  }

  const query = buildQuery({
    limit: filters.limit || 100,
    hours: filters.hours || 24,
    source: filters.source === "all" ? undefined : filters.source,
    symbol: filters.symbol === "all" ? undefined : filters.symbol,
  });
  const payload = await withClientCache(
    makeClientCacheKey([
      "news-latest",
      filters.limit || 100,
      filters.hours || 24,
      filters.source || "all",
      filters.symbol || "all",
    ]),
    NEWS_CACHE_MS,
    () => apiGet<{ articles?: NewsArticle[] } | NewsArticle[]>(`/news/latest?${query}`),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  const articles = Array.isArray(payload) ? payload : payload.articles || [];
  return articles.map(normalizeNewsItem);
}

export async function searchNews(filters: NewsFilters): Promise<NewsArticle[]> {
  if (!filters.query?.trim()) {
    return fetchLatestNews(filters);
  }

  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.searchNews(filters);
    return payload.articles.map(normalizeNewsItem);
  }

  const query = buildQuery({ q: filters.query, limit: filters.limit || 100 });
  const payload = await withClientCache(
    makeClientCacheKey(["news-search", filters.query, filters.limit || 100]),
    NEWS_CACHE_MS,
    () => apiGet<{ articles?: NewsArticle[] } | NewsArticle[]>(`/news/search?${query}`),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  const articles = Array.isArray(payload) ? payload : payload.articles || [];
  return articles.map(normalizeNewsItem);
}

export async function fetchTrendingSymbols(limit: number = 10): Promise<TrendingSymbol[]> {
  if (DATA_SOURCE === "mock") {
    const payload = await mockDataAdapter.fetchTrendingSymbols(limit);
    return payload.trending_symbols;
  }

  const payload = await withClientCache(
    makeClientCacheKey(["news-trending", limit]),
    TRENDING_SYMBOLS_CACHE_MS,
    () =>
      apiGet<{ trending_symbols?: TrendingSymbol[] } | TrendingSymbol[]>(
        `/news/trending?${buildQuery({ limit })}`,
      ),
    { staleOnError: true },
  );
  if (isUnavailableApiPayload(payload)) return [];
  return Array.isArray(payload) ? payload : payload.trending_symbols || [];
}
