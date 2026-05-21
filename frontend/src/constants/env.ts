export const DATA_SOURCE = import.meta.env.VITE_DATA_SOURCE === "mock" ? "mock" : "api";
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export function getDataSourceLabel(): string {
  return DATA_SOURCE === "mock" ? "MOCK" : "API";
}
