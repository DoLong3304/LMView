import { API_BASE_URL } from "@/constants/env";
import { createApiError } from "@/utils/errors";

export function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }
  return query.toString();
}

export async function apiGet<T>(path: string, timeoutMs: number = 30000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw createApiError("market", response.status, payload, { endpoint: path });
    }
    return response.json() as Promise<T>;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw createApiError("market", 408, { detail: "Request timeout" }, { endpoint: path });
    }
    throw error;
  }
}

export function getWsBaseUrl(): string {
  if (API_BASE_URL.startsWith("http")) {
    return API_BASE_URL.replace(/^http/, "ws");
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${API_BASE_URL}`;
}
