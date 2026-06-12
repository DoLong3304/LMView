import { useCallback, useRef, useEffect } from 'react';
import type { IChartApi } from 'lightweight-charts';

/**
 * Custom hook for TradingView-style zoom control
 *
 * Problem: lightweight-charts auto-adjusts barSpacing when zooming,
 * causing candle width to change inversely with visible candle count.
 *
 * Solution: Control barSpacing based on zoom level instead of letting
 * the library auto-adjust. This keeps candle width consistent.
 */

interface UseChartZoomProps {
  chartApi: IChartApi | null;
  initialBarSpacing?: number;
  minBarSpacing?: number;
  maxBarSpacing?: number;
}

interface ZoomState {
  barSpacing: number;
  zoomLevel: number; // 1.0 = default, >1 = zoomed in, <1 = zoomed out
}

const DEFAULT_BAR_SPACING = 2;  // Max zoom out - minimum candle width
const MIN_BAR_SPACING = 2;
const MAX_BAR_SPACING = 30;
const ZOOM_STEP = 1.2; // 20% per zoom step

export function useChartZoom({
  chartApi,
  initialBarSpacing = DEFAULT_BAR_SPACING,
  minBarSpacing = MIN_BAR_SPACING,
  maxBarSpacing = MAX_BAR_SPACING,
}: UseChartZoomProps) {
  const zoomStateRef = useRef<ZoomState>({
    barSpacing: initialBarSpacing,
    zoomLevel: 1.0,
  });

  // Apply barSpacing to chart
  const applyBarSpacing = useCallback((spacing: number) => {
    if (!chartApi) return;

    const clampedSpacing = Math.max(minBarSpacing, Math.min(maxBarSpacing, spacing));

    chartApi.timeScale().applyOptions({
      barSpacing: clampedSpacing,
    });

    zoomStateRef.current.barSpacing = clampedSpacing;
  }, [chartApi, minBarSpacing, maxBarSpacing]);

  // Zoom in (increase barSpacing)
  const zoomIn = useCallback(() => {
    const currentSpacing = zoomStateRef.current.barSpacing;
    const newSpacing = currentSpacing * ZOOM_STEP;
    const clampedSpacing = Math.min(maxBarSpacing, newSpacing);

    applyBarSpacing(clampedSpacing);
    zoomStateRef.current.zoomLevel *= ZOOM_STEP;
  }, [applyBarSpacing, maxBarSpacing]);

  // Zoom out (decrease barSpacing)
  const zoomOut = useCallback(() => {
    const currentSpacing = zoomStateRef.current.barSpacing;
    const newSpacing = currentSpacing / ZOOM_STEP;
    const clampedSpacing = Math.max(minBarSpacing, newSpacing);

    applyBarSpacing(clampedSpacing);
    zoomStateRef.current.zoomLevel /= ZOOM_STEP;
  }, [applyBarSpacing, minBarSpacing]);

  // Reset zoom to default
  const resetZoom = useCallback(() => {
    applyBarSpacing(initialBarSpacing);
    zoomStateRef.current.zoomLevel = 1.0;

    // Don't call fitContent() - it would reset barSpacing
    // Just reset to initial barSpacing value
  }, [applyBarSpacing, initialBarSpacing]);

  // Get current zoom state
  const getZoomState = useCallback((): ZoomState => {
    return { ...zoomStateRef.current };
  }, []);

  // Set zoom level programmatically
  const setZoomLevel = useCallback((level: number) => {
    const newSpacing = initialBarSpacing * level;
    applyBarSpacing(newSpacing);
    zoomStateRef.current.zoomLevel = level;
  }, [applyBarSpacing, initialBarSpacing]);

  // Initialize barSpacing when chart is ready
  useEffect(() => {
    if (chartApi) {
      applyBarSpacing(initialBarSpacing);
    }
  }, [chartApi, initialBarSpacing, applyBarSpacing]);

  return {
    zoomIn,
    zoomOut,
    resetZoom,
    getZoomState,
    setZoomLevel,
    canZoomIn: zoomStateRef.current.barSpacing < maxBarSpacing,
    canZoomOut: zoomStateRef.current.barSpacing > minBarSpacing,
  };
}
