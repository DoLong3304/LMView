import { apiGet } from "@/services/apiClient";
import type { HealthData } from "@/types";

export async function fetchHealthStatus(): Promise<HealthData> {
  return apiGet<HealthData>("/health");
}
