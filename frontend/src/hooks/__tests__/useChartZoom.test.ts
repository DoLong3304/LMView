import { renderHook, act } from '@testing-library/react';
import { useChartZoom } from '../useChartZoom';
import type { IChartApi } from 'lightweight-charts';

// Mock lightweight-charts
const mockApplyOptions = jest.fn();
const mockFitContent = jest.fn();

const createMockChartApi = (): IChartApi => {
  return {
    timeScale: () => ({
      applyOptions: mockApplyOptions,
      fitContent: mockFitContent,
    }),
  } as any;
};

describe('useChartZoom', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize with default barSpacing', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
          minBarSpacing: 3,
          maxBarSpacing: 50,
        })
      );

      expect(mockApplyOptions).toHaveBeenCalledWith({
        barSpacing: 8,
      });
    });

    it('should not apply options if chartApi is null', () => {
      renderHook(() =>
        useChartZoom({
          chartApi: null,
          initialBarSpacing: 8,
        })
      );

      expect(mockApplyOptions).not.toHaveBeenCalled();
    });
  });

  describe('Zoom In', () => {
    it('should increase barSpacing by ZOOM_STEP (1.2x)', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
          minBarSpacing: 3,
          maxBarSpacing: 50,
        })
      );

      act(() => {
        result.current.zoomIn();
      });

      // 8 * 1.2 = 9.6
      expect(mockApplyOptions).toHaveBeenCalledWith({
        barSpacing: 9.6,
      });
    });

    it('should not exceed maxBarSpacing', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 45,
          minBarSpacing: 3,
          maxBarSpacing: 50,
        })
      );

      act(() => {
        result.current.zoomIn();
      });

      // 45 * 1.2 = 54, but clamped to 50
      expect(mockApplyOptions).toHaveBeenCalledWith({
        barSpacing: 50,
      });
    });

    it('should update canZoomIn flag correctly', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 45,
          minBarSpacing: 3,
          maxBarSpacing: 50,
        })
      );

      expect(result.current.canZoomIn).toBe(true);

      act(() => {
        result.current.zoomIn();
      });

      expect(result.current.canZoomIn).toBe(false);
    });
  });

  describe('Zoom Out', () => {
    it('should decrease barSpacing by ZOOM_STEP (1/1.2x)', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 12,
          minBarSpacing: 3,
          maxBarSpacing: 50,
        })
      );

      act(() => {
        result.current.zoomOut();
      });

      // 12 / 1.2 = 10
      expect(mockApplyOptions).toHaveBeenCalledWith({
        barSpacing: 10,
      });
    });

    it('should not go below minBarSpacing', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 3.5,
          minBarSpacing: 3,
          maxBarSpacing: 50,
        })
      );

      act(() => {
        result.current.zoomOut();
      });

      // 3.5 / 1.2 = 2.916..., but clamped to 3
      expect(mockApplyOptions).toHaveBeenCalledWith({
        barSpacing: 3,
      });
    });

    it('should update canZoomOut flag correctly', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 3.5,
          minBarSpacing: 3,
          maxBarSpacing: 50,
        })
      );

      expect(result.current.canZoomOut).toBe(true);

      act(() => {
        result.current.zoomOut();
      });

      expect(result.current.canZoomOut).toBe(false);
    });
  });

  describe('Reset Zoom', () => {
    it('should reset barSpacing to initial value', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
          minBarSpacing: 3,
          maxBarSpacing: 50,
        })
      );

      // Zoom in first
      act(() => {
        result.current.zoomIn();
        result.current.zoomIn();
      });

      // Reset
      act(() => {
        result.current.resetZoom();
      });

      expect(mockApplyOptions).toHaveBeenLastCalledWith({
        barSpacing: 8,
      });
    });

    it('should call fitContent on chart', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
        })
      );

      act(() => {
        result.current.resetZoom();
      });

      expect(mockFitContent).toHaveBeenCalled();
    });

    it('should reset zoom level to 1.0', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
        })
      );

      act(() => {
        result.current.zoomIn();
      });

      let state = result.current.getZoomState();
      expect(state.zoomLevel).toBeGreaterThan(1.0);

      act(() => {
        result.current.resetZoom();
      });

      state = result.current.getZoomState();
      expect(state.zoomLevel).toBe(1.0);
    });
  });

  describe('Get Zoom State', () => {
    it('should return current zoom state', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
        })
      );

      const state = result.current.getZoomState();

      expect(state).toEqual({
        barSpacing: 8,
        zoomLevel: 1.0,
      });
    });

    it('should update zoom state after zoom operations', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
        })
      );

      act(() => {
        result.current.zoomIn();
      });

      const state = result.current.getZoomState();

      expect(state.barSpacing).toBe(9.6);
      expect(state.zoomLevel).toBe(1.2);
    });
  });

  describe('Set Zoom Level', () => {
    it('should set zoom level programmatically', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
        })
      );

      act(() => {
        result.current.setZoomLevel(2.0);
      });

      // 8 * 2.0 = 16
      expect(mockApplyOptions).toHaveBeenCalledWith({
        barSpacing: 16,
      });

      const state = result.current.getZoomState();
      expect(state.zoomLevel).toBe(2.0);
    });

    it('should clamp to maxBarSpacing when setting high zoom level', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
          maxBarSpacing: 20,
        })
      );

      act(() => {
        result.current.setZoomLevel(5.0);
      });

      // 8 * 5.0 = 40, but clamped to 20
      expect(mockApplyOptions).toHaveBeenCalledWith({
        barSpacing: 20,
      });
    });
  });

  describe('Multiple Zoom Operations', () => {
    it('should handle multiple zoom in operations correctly', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
        })
      );

      act(() => {
        result.current.zoomIn();
        result.current.zoomIn();
        result.current.zoomIn();
      });

      // 8 * 1.2^3 = 13.824
      const state = result.current.getZoomState();
      expect(state.barSpacing).toBeCloseTo(13.824, 2);
    });

    it('should handle zoom in then zoom out', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 8,
        })
      );

      act(() => {
        result.current.zoomIn();
        result.current.zoomOut();
      });

      // Should return to approximately initial value
      const state = result.current.getZoomState();
      expect(state.barSpacing).toBeCloseTo(8, 2);
    });
  });

  describe('Edge Cases', () => {
    it('should handle chartApi becoming null', () => {
      const mockChart = createMockChartApi();
      const { result, rerender } = renderHook(
        ({ chartApi }) =>
          useChartZoom({
            chartApi,
            initialBarSpacing: 8,
          }),
        { initialProps: { chartApi: mockChart } }
      );

      // Change chartApi to null
      rerender({ chartApi: null });

      // Should not throw error
      act(() => {
        result.current.zoomIn();
      });
    });

    it('should handle very small barSpacing values', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 0.5,
          minBarSpacing: 0.1,
          maxBarSpacing: 50,
        })
      );

      act(() => {
        result.current.zoomOut();
      });

      const state = result.current.getZoomState();
      expect(state.barSpacing).toBeGreaterThanOrEqual(0.1);
    });

    it('should handle very large barSpacing values', () => {
      const mockChart = createMockChartApi();
      const { result } = renderHook(() =>
        useChartZoom({
          chartApi: mockChart,
          initialBarSpacing: 100,
          minBarSpacing: 3,
          maxBarSpacing: 200,
        })
      );

      act(() => {
        result.current.zoomIn();
      });

      const state = result.current.getZoomState();
      expect(state.barSpacing).toBeLessThanOrEqual(200);
    });
  });
});
