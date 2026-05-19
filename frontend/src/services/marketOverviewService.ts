import { 
  generateMockMarketOverview, 
  generateMockGainers, 
  generateMockLosers, 
  generateMockNews 
} from "../mock/mockDataGenerator";

const DATA_SOURCE = import.meta.env.VITE_DATA_SOURCE === "mock" ? "mock" : "api";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export async function fetchMarketOverview() {
  if (DATA_SOURCE === "mock") {
    return { data: generateMockMarketOverview() };
  }
  const res = await fetch(`${API_BASE_URL}/market/overview`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function fetchTopGainers(limit: number = 5) {
  if (DATA_SOURCE === "mock") {
    return { data: generateMockGainers().slice(0, limit) };
  }
  const res = await fetch(`${API_BASE_URL}/market/gainers?limit=${limit}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function fetchTopLosers(limit: number = 5) {
  if (DATA_SOURCE === "mock") {
    return { data: generateMockLosers().slice(0, limit) };
  }
  const res = await fetch(`${API_BASE_URL}/market/losers?limit=${limit}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function fetchLatestMarketNews(limit: number = 100, hours: number = 24) {
  if (DATA_SOURCE === "mock") {
    return { data: generateMockNews(limit) };
  }
  const res = await fetch(`${API_BASE_URL}/news/latest?limit=${limit}&hours=${hours}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}
