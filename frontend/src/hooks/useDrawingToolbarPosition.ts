import { useCallback, useEffect, useState, useRef } from 'react';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import type { Drawing, DataPoint } from '../types';

interface ToolbarPosition {
  x: number;
  y: number;
  visible: boolean;
}

interface UseDrawingToolbarPositionProps {
  drawing: Drawing | null;
  chartApi: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
  offset?: { x: number; y: number };
}

/**
 * Hook to calculate floating toolbar position from drawing coordinates
 *
 * Automatically updates position when:
 * - Chart is panned
 * - Chart is zoomed
 * - Drawing is moved
 * - Window is resized
 */
export function useDrawingToolbarPosition({
  drawing,
  chartApi,
  candleSeries,
  offset = { x: 10, y: -50 }, // Default: 10px right, 50px above
}: UseDrawingToolbarPositionProps): ToolbarPosition {
  const [position, setPosition] = useState<ToolbarPosition>({
    x: 0,
    y: 0,
    visible: false,
  });

  const rafRef = useRef<number | null>(null);

  // Convert data-space point to pixel coordinates
  const dataToPixel = useCallback((dataPoint: DataPoint): { x: number; y: number } | null => {
    if (!chartApi || !candleSeries) return null;

    const x = chartApi.timeScale().timeToCoordinate(dataPoint.time as any);
    const y = candleSeries.priceToCoordinate(dataPoint.price);

    if (x === null || y === null) return null;

    return { x, y };
  }, [chartApi, candleSeries]);

  // Calculate toolbar position from drawing
  const calculatePosition = useCallback(() => {
    if (!drawing || !drawing.dataPoints || drawing.dataPoints.length === 0) {
      setPosition({ x: 0, y: 0, visible: false });
      return;
    }

    // Use first data point as anchor
    const anchorPoint = drawing.dataPoints[0];
    const pixel = dataToPixel(anchorPoint);

    if (!pixel) {
      // Drawing is off-screen
      setPosition({ x: 0, y: 0, visible: false });
      return;
    }

    // Apply offset
    const x = pixel.x + offset.x;
    const y = pixel.y + offset.y;

    // Check if position is within viewport
    const container = chartApi?.chartElement();
    if (container) {
      const rect = container.getBoundingClientRect();
      const isVisible = x >= 0 && x <= rect.width && y >= 0 && y <= rect.height;

      setPosition({
        x,
        y,
        visible: isVisible,
      });
    } else {
      setPosition({ x, y, visible: true });
    }
  }, [drawing, dataToPixel, offset, chartApi]);

  // Update position using requestAnimationFrame for smooth updates
  const scheduleUpdate = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }

    rafRef.current = requestAnimationFrame(() => {
      calculatePosition();
      rafRef.current = null;
    });
  }, [calculatePosition]);

  // Subscribe to chart events
  useEffect(() => {
    if (!chartApi) return;

    const timeScale = chartApi.timeScale();

    // Update on visible range change (pan/zoom)
    const handleVisibleRangeChange = () => {
      scheduleUpdate();
    };

    timeScale.subscribeVisibleLogicalRangeChange(handleVisibleRangeChange);

    // Initial calculation
    scheduleUpdate();

    return () => {
      timeScale.unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange);
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [chartApi, scheduleUpdate]);

  // Update when drawing changes
  useEffect(() => {
    scheduleUpdate();
  }, [drawing, scheduleUpdate]);

  // Update on window resize
  useEffect(() => {
    const handleResize = () => {
      scheduleUpdate();
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [scheduleUpdate]);

  return position;
}
