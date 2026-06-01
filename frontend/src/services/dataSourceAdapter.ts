import { DATA_SOURCE } from "@/constants/env";
import { mockDataAdapter } from "@/data/mock";
import type { DataSourceAdapter } from "@/data/mock";

export type { DataSourceAdapter };

export function shouldUseMockDataAdapter(): boolean {
  return DATA_SOURCE === "mock";
}

export function getMockDataAdapter(): DataSourceAdapter {
  return mockDataAdapter;
}
