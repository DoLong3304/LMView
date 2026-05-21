/**
 * chartStorageService.ts
 *
 * Future-proof chart storage service for drawings and chart state.
 * Designed to support user accounts in the future while working with anonymous users now.
 */

import type { Drawing } from "@/types";

export interface ChartStorageScope {
  userId?: string;
  workspaceId?: string;
  symbol: string;
  timeframe: string;
  chartId?: string;
  storageVersion: number;
}

export interface StoredChartDrawings {
  version: number;
  userId?: string;
  workspaceId: string;
  chartId: string;
  symbol: string;
  timeframe: string;
  updatedAt: number;
  drawings: Drawing[];
}

const STORAGE_VERSION = 1;
const DEFAULT_USER_ID = 'anonymous';
const DEFAULT_WORKSPACE_ID = 'default';
const DEFAULT_CHART_ID = 'main';

/**
 * Generate localStorage key from scope
 */
function generateStorageKey(scope: ChartStorageScope): string {
  const userId = scope.userId || DEFAULT_USER_ID;
  const workspaceId = scope.workspaceId || DEFAULT_WORKSPACE_ID;
  const chartId = scope.chartId || DEFAULT_CHART_ID;

  return `chart:v${scope.storageVersion}:${userId}:${workspaceId}:${chartId}:${scope.symbol}:${scope.timeframe}:drawings`;
}

/**
 * Load drawings for a given scope
 */
export async function loadDrawings(scope: ChartStorageScope): Promise<Drawing[]> {
  try {
    const key = generateStorageKey(scope);
    const stored = localStorage.getItem(key);

    if (!stored) {
      return [];
    }

    const data: StoredChartDrawings = JSON.parse(stored);

    // Version migration logic (future-proof)
    if (data.version !== STORAGE_VERSION) {
      console.warn(`[chartStorage] Version mismatch: stored=${data.version}, current=${STORAGE_VERSION}`);
      // In the future, add migration logic here
      return [];
    }

    // Validate drawings have required data-space coordinates
    const validDrawings = data.drawings.filter(d => {
      // Check if drawing has data-space coordinates
      if (d.dataPoints && Array.isArray(d.dataPoints)) {
        return d.dataPoints.every(p =>
          typeof p.time === 'number' && typeof p.price === 'number'
        );
      }
      // Legacy pixel-based drawings are invalid
      return false;
    });

    if (validDrawings.length !== data.drawings.length) {
      console.warn(`[chartStorage] Filtered out ${data.drawings.length - validDrawings.length} invalid drawings`);
    }

    return validDrawings;
  } catch (error) {
    console.error('[chartStorage] Failed to load drawings:', error);
    return [];
  }
}

/**
 * Save drawings for a given scope
 */
export async function saveDrawings(scope: ChartStorageScope, drawings: Drawing[]): Promise<void> {
  try {
    const key = generateStorageKey(scope);

    const data: StoredChartDrawings = {
      version: STORAGE_VERSION,
      userId: scope.userId || DEFAULT_USER_ID,
      workspaceId: scope.workspaceId || DEFAULT_WORKSPACE_ID,
      chartId: scope.chartId || DEFAULT_CHART_ID,
      symbol: scope.symbol,
      timeframe: scope.timeframe,
      updatedAt: Date.now(),
      drawings,
    };

    localStorage.setItem(key, JSON.stringify(data));
  } catch (error) {
    console.error('[chartStorage] Failed to save drawings:', error);
    throw error;
  }
}

/**
 * Delete all drawings for a given scope
 */
export async function deleteDrawings(scope: ChartStorageScope): Promise<void> {
  try {
    const key = generateStorageKey(scope);
    localStorage.removeItem(key);
  } catch (error) {
    console.error('[chartStorage] Failed to delete drawings:', error);
    throw error;
  }
}

/**
 * Export drawings as JSON string
 */
export async function exportDrawings(scope: ChartStorageScope): Promise<string> {
  try {
    const drawings = await loadDrawings(scope);

    const exportData = {
      version: STORAGE_VERSION,
      symbol: scope.symbol,
      timeframe: scope.timeframe,
      exportedAt: Date.now(),
      drawings,
    };

    return JSON.stringify(exportData, null, 2);
  } catch (error) {
    console.error('[chartStorage] Failed to export drawings:', error);
    throw error;
  }
}

/**
 * Import drawings from JSON string
 */
export async function importDrawings(scope: ChartStorageScope, payload: string): Promise<Drawing[]> {
  try {
    const data = JSON.parse(payload);

    if (!data.drawings || !Array.isArray(data.drawings)) {
      throw new Error('Invalid import format: missing drawings array');
    }

    // Validate and filter valid drawings
    const validDrawings = data.drawings.filter((d: Drawing) => {
      if (!d.dataPoints || !Array.isArray(d.dataPoints)) {
        return false;
      }
      return d.dataPoints.every(p =>
        typeof p.time === 'number' && typeof p.price === 'number'
      );
    });

    if (validDrawings.length === 0) {
      throw new Error('No valid drawings found in import data');
    }

    // Save imported drawings
    await saveDrawings(scope, validDrawings);

    return validDrawings;
  } catch (error) {
    console.error('[chartStorage] Failed to import drawings:', error);
    throw error;
  }
}

/**
 * List all stored chart keys (for debugging/management)
 */
export function listStoredCharts(): string[] {
  const keys: string[] = [];

  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith('chart:v')) {
      keys.push(key);
    }
  }

  return keys;
}

/**
 * Clear all chart storage (use with caution)
 */
export async function clearAllChartStorage(): Promise<void> {
  const keys = listStoredCharts();

  for (const key of keys) {
    localStorage.removeItem(key);
  }

  console.log(`[chartStorage] Cleared ${keys.length} chart storage entries`);
}
