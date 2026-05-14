import { renderHook } from '@testing-library/react';
import { useChartKeyboardShortcuts } from '../useChartKeyboardShortcuts';
import type { Drawing } from '../../types';

const mockDrawings: Drawing[] = [
  {
    id: 1,
    tool: 'trendline',
    dataPoints: [
      { time: 1000, price: 100 },
      { time: 2000, price: 200 },
    ],
    settings: { color: '#3b82f6', lineWidth: 2 },
  },
  {
    id: 2,
    tool: 'horizontal',
    dataPoints: [{ time: 1500, price: 150 }],
    settings: { color: '#ef4444', lineWidth: 2 },
  },
];

describe('useChartKeyboardShortcuts', () => {
  let mockOnSetDrawings: jest.Mock;
  let mockOnSetSelectedDrawingIds: jest.Mock;
  let mockOnDeleteDrawings: jest.Mock;
  let mockOnSaveDrawings: jest.Mock;
  let mockOnCancelDrawing: jest.Mock;
  let mockChartContainerRef: React.RefObject<HTMLDivElement>;

  beforeEach(() => {
    mockOnSetDrawings = jest.fn();
    mockOnSetSelectedDrawingIds = jest.fn();
    mockOnDeleteDrawings = jest.fn();
    mockOnSaveDrawings = jest.fn().mockResolvedValue(undefined);
    mockOnCancelDrawing = jest.fn();
    mockChartContainerRef = { current: document.createElement('div') };

    // Clear all event listeners
    document.removeEventListener('keydown', jest.fn());
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Delete/Backspace Key', () => {
    it('should delete selected drawings on Delete key', () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [1],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      const event = new KeyboardEvent('keydown', { key: 'Delete' });
      document.dispatchEvent(event);

      expect(mockOnDeleteDrawings).toHaveBeenCalledWith([1]);
    });

    it('should delete selected drawings on Backspace key', () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [2],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      const event = new KeyboardEvent('keydown', { key: 'Backspace' });
      document.dispatchEvent(event);

      expect(mockOnDeleteDrawings).toHaveBeenCalledWith([2]);
    });

    it('should not delete if no drawings selected', () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      const event = new KeyboardEvent('keydown', { key: 'Delete' });
      document.dispatchEvent(event);

      expect(mockOnDeleteDrawings).not.toHaveBeenCalled();
    });
  });

  describe('Escape Key', () => {
    it('should cancel drawing when isDrawing is true', () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: true,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      const event = new KeyboardEvent('keydown', { key: 'Escape' });
      document.dispatchEvent(event);

      expect(mockOnCancelDrawing).toHaveBeenCalled();
    });

    it('should deselect drawings when not drawing', () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [1, 2],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      const event = new KeyboardEvent('keydown', { key: 'Escape' });
      document.dispatchEvent(event);

      expect(mockOnSetSelectedDrawingIds).toHaveBeenCalledWith([]);
    });
  });

  describe('Undo/Redo', () => {
    it('should handle Ctrl+Z for undo', () => {
      const { result } = renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      // Simulate mouse enter to focus chart
      mockChartContainerRef.current?.dispatchEvent(new Event('mouseenter'));

      const event = new KeyboardEvent('keydown', {
        key: 'z',
        ctrlKey: true,
      });
      document.dispatchEvent(event);

      // Should not undo if no history
      expect(result.current.canUndo).toBe(false);
    });

    it('should handle Ctrl+Y for redo', () => {
      const { result } = renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      // Simulate mouse enter to focus chart
      mockChartContainerRef.current?.dispatchEvent(new Event('mouseenter'));

      const event = new KeyboardEvent('keydown', {
        key: 'y',
        ctrlKey: true,
      });
      document.dispatchEvent(event);

      // Should not redo if no history
      expect(result.current.canRedo).toBe(false);
    });
  });

  describe('Copy/Cut/Paste', () => {
    it('should copy selected drawings on Ctrl+C', () => {
      const { result } = renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [1],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      // Simulate mouse enter to focus chart
      mockChartContainerRef.current?.dispatchEvent(new Event('mouseenter'));

      const event = new KeyboardEvent('keydown', {
        key: 'c',
        ctrlKey: true,
      });
      document.dispatchEvent(event);

      expect(result.current.hasClipboard).toBe(true);
    });

    it('should not copy if no drawings selected', () => {
      const { result } = renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      // Simulate mouse enter to focus chart
      mockChartContainerRef.current?.dispatchEvent(new Event('mouseenter'));

      const event = new KeyboardEvent('keydown', {
        key: 'c',
        ctrlKey: true,
      });
      document.dispatchEvent(event);

      expect(result.current.hasClipboard).toBe(false);
    });
  });

  describe('Select All', () => {
    it('should select all drawings on Ctrl+A', () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      // Simulate mouse enter to focus chart
      mockChartContainerRef.current?.dispatchEvent(new Event('mouseenter'));

      const event = new KeyboardEvent('keydown', {
        key: 'a',
        ctrlKey: true,
      });
      document.dispatchEvent(event);

      expect(mockOnSetSelectedDrawingIds).toHaveBeenCalledWith([1, 2]);
    });
  });

  describe('Save', () => {
    it('should save drawings on Ctrl+S', async () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      // Simulate mouse enter to focus chart
      mockChartContainerRef.current?.dispatchEvent(new Event('mouseenter'));

      const event = new KeyboardEvent('keydown', {
        key: 's',
        ctrlKey: true,
      });
      document.dispatchEvent(event);

      expect(mockOnSaveDrawings).toHaveBeenCalled();
    });
  });

  describe('Input Protection', () => {
    it('should not intercept shortcuts when typing in input field', () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [1],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      const input = document.createElement('input');
      document.body.appendChild(input);

      const event = new KeyboardEvent('keydown', {
        key: 'Delete',
        bubbles: true,
      });
      Object.defineProperty(event, 'target', { value: input, enumerable: true });

      document.dispatchEvent(event);

      expect(mockOnDeleteDrawings).not.toHaveBeenCalled();

      document.body.removeChild(input);
    });

    it('should not intercept shortcuts when typing in textarea', () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      const textarea = document.createElement('textarea');
      document.body.appendChild(textarea);

      const event = new KeyboardEvent('keydown', {
        key: 'a',
        ctrlKey: true,
        bubbles: true,
      });
      Object.defineProperty(event, 'target', { value: textarea, enumerable: true });

      document.dispatchEvent(event);

      expect(mockOnSetSelectedDrawingIds).not.toHaveBeenCalled();

      document.body.removeChild(textarea);
    });
  });

  describe('Chart Focus Tracking', () => {
    it('should track chart focus on mouse enter/leave', () => {
      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      // Mouse enter
      mockChartContainerRef.current?.dispatchEvent(new Event('mouseenter'));

      // Ctrl+A should work
      const event1 = new KeyboardEvent('keydown', {
        key: 'a',
        ctrlKey: true,
      });
      document.dispatchEvent(event1);
      expect(mockOnSetSelectedDrawingIds).toHaveBeenCalled();

      mockOnSetSelectedDrawingIds.mockClear();

      // Mouse leave
      mockChartContainerRef.current?.dispatchEvent(new Event('mouseleave'));

      // Ctrl+A should not work
      const event2 = new KeyboardEvent('keydown', {
        key: 'a',
        ctrlKey: true,
      });
      document.dispatchEvent(event2);
      expect(mockOnSetSelectedDrawingIds).not.toHaveBeenCalled();
    });
  });

  describe('Mac vs Windows', () => {
    it('should use metaKey on Mac', () => {
      // Mock Mac platform
      Object.defineProperty(navigator, 'platform', {
        value: 'MacIntel',
        writable: true,
      });

      renderHook(() =>
        useChartKeyboardShortcuts({
          drawings: mockDrawings,
          selectedDrawingIds: [],
          onSetDrawings: mockOnSetDrawings,
          onSetSelectedDrawingIds: mockOnSetSelectedDrawingIds,
          onDeleteDrawings: mockOnDeleteDrawings,
          onSaveDrawings: mockOnSaveDrawings,
          isDrawing: false,
          onCancelDrawing: mockOnCancelDrawing,
          chartContainerRef: mockChartContainerRef,
        })
      );

      // Simulate mouse enter to focus chart
      mockChartContainerRef.current?.dispatchEvent(new Event('mouseenter'));

      const event = new KeyboardEvent('keydown', {
        key: 'a',
        metaKey: true, // Cmd key on Mac
      });
      document.dispatchEvent(event);

      expect(mockOnSetSelectedDrawingIds).toHaveBeenCalledWith([1, 2]);
    });
  });
});
