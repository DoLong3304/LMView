import { useEffect, useCallback, useRef } from 'react';
import type { Drawing, DataPoint, Command } from "@/types";

interface UseChartKeyboardShortcutsProps {
  drawings: Drawing[];
  selectedDrawingIds: (string | number)[];
  onSetDrawings: (drawings: Drawing[]) => void;
  onSetSelectedDrawingIds: (ids: (string | number)[]) => void;
  onDeleteDrawings: (ids: (string | number)[]) => void;
  onSaveDrawings: () => Promise<void>;
  isDrawing: boolean;
  onCancelDrawing: () => void;
  chartContainerRef: React.RefObject<HTMLElement | null>;
}

const MAX_HISTORY = 50;

export function useChartKeyboardShortcuts({
  drawings,
  selectedDrawingIds,
  onSetDrawings,
  onSetSelectedDrawingIds,
  onDeleteDrawings,
  onSaveDrawings,
  isDrawing,
  onCancelDrawing,
  chartContainerRef,
}: UseChartKeyboardShortcutsProps) {
  const commandHistoryRef = useRef<Command[]>([]);
  const historyIndexRef = useRef(-1);
  const clipboardRef = useRef<Drawing[]>([]);
  const isChartFocusedRef = useRef(false);
  const drawingsSnapshotRef = useRef<Drawing[]>(drawings);

  // Keep snapshot updated
  useEffect(() => {
    drawingsSnapshotRef.current = drawings;
  }, [drawings]);

  // Track chart focus
  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container) return;

    const handleMouseEnter = () => {
      isChartFocusedRef.current = true;
    };

    const handleMouseLeave = () => {
      isChartFocusedRef.current = false;
    };

    container.addEventListener('mouseenter', handleMouseEnter);
    container.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      container.removeEventListener('mouseenter', handleMouseEnter);
      container.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [chartContainerRef]);

  // Add command to history
  const addCommand = useCallback((command: Command) => {
    // Remove any redo entries after current index
    commandHistoryRef.current = commandHistoryRef.current.slice(0, historyIndexRef.current + 1);

    // Add new command
    commandHistoryRef.current.push(command);

    // Limit history size
    if (commandHistoryRef.current.length > MAX_HISTORY) {
      commandHistoryRef.current.shift();
    } else {
      historyIndexRef.current++;
    }
  }, []);

  // Execute undo for a command
  const undoCommand = useCallback((command: Command): Drawing[] => {
    const current = [...drawingsSnapshotRef.current];

    switch (command.type) {
      case 'add': {
        // Remove the added drawing
        return current.filter(d => d.id !== command.drawingId);
      }

      case 'delete': {
        // Restore the deleted drawing(s)
        if (Array.isArray(command.before)) {
          return [...current, ...command.before];
        } else if (command.before) {
          return [...current, command.before];
        }
        return current;
      }

      case 'update': {
        // Revert to before state
        if (command.before && !Array.isArray(command.before)) {
          return current.map(d =>
            d.id === command.drawingId ? command.before as Drawing : d
          );
        }
        return current;
      }

      case 'move': {
        // Revert to before position
        if (command.before && !Array.isArray(command.before)) {
          return current.map(d =>
            d.id === command.drawingId ? command.before as Drawing : d
          );
        }
        return current;
      }

      case 'batch': {
        // Revert batch operation
        if (Array.isArray(command.before)) {
          return command.before;
        }
        return current;
      }

      default:
        return current;
    }
  }, []);

  // Execute redo for a command
  const redoCommand = useCallback((command: Command): Drawing[] => {
    const current = [...drawingsSnapshotRef.current];

    switch (command.type) {
      case 'add': {
        // Re-add the drawing
        if (command.after && !Array.isArray(command.after)) {
          return [...current, command.after];
        }
        return current;
      }

      case 'delete': {
        // Re-delete the drawing(s)
        if (command.drawingIds) {
          return current.filter(d => !command.drawingIds!.includes(d.id));
        } else if (command.drawingId) {
          return current.filter(d => d.id !== command.drawingId);
        }
        return current;
      }

      case 'update': {
        // Re-apply the update
        if (command.after && !Array.isArray(command.after)) {
          return current.map(d =>
            d.id === command.drawingId ? command.after as Drawing : d
          );
        }
        return current;
      }

      case 'move': {
        // Re-apply the move
        if (command.after && !Array.isArray(command.after)) {
          return current.map(d =>
            d.id === command.drawingId ? command.after as Drawing : d
          );
        }
        return current;
      }

      case 'batch': {
        // Re-apply batch operation
        if (Array.isArray(command.after)) {
          return command.after;
        }
        return current;
      }

      default:
        return current;
    }
  }, []);

  // Undo
  const undo = useCallback(() => {
    if (historyIndexRef.current >= 0) {
      const command = commandHistoryRef.current[historyIndexRef.current];
      const newDrawings = undoCommand(command);
      historyIndexRef.current--;
      onSetDrawings(newDrawings);
    }
  }, [onSetDrawings, undoCommand]);

  // Redo
  const redo = useCallback(() => {
    if (historyIndexRef.current < commandHistoryRef.current.length - 1) {
      historyIndexRef.current++;
      const command = commandHistoryRef.current[historyIndexRef.current];
      const newDrawings = redoCommand(command);
      onSetDrawings(newDrawings);
    }
  }, [onSetDrawings, redoCommand]);

  // Copy
  const copy = useCallback(() => {
    if (selectedDrawingIds.length === 0) return;

    const selectedDrawings = drawings.filter(d => selectedDrawingIds.includes(d.id));
    clipboardRef.current = JSON.parse(JSON.stringify(selectedDrawings));
  }, [drawings, selectedDrawingIds]);

  // Cut
  const cut = useCallback(() => {
    if (selectedDrawingIds.length === 0) return;

    copy();

    // Record delete command
    const deletedDrawings = drawings.filter(d => selectedDrawingIds.includes(d.id));
    addCommand({
      type: 'delete',
      timestamp: Date.now(),
      drawingIds: selectedDrawingIds,
      before: deletedDrawings,
      description: `Cut ${selectedDrawingIds.length} drawing(s)`,
    });

    onDeleteDrawings(selectedDrawingIds);
  }, [copy, onDeleteDrawings, selectedDrawingIds, drawings, addCommand]);

  // Paste
  const paste = useCallback(() => {
    if (clipboardRef.current.length === 0) return;

    const newDrawings = clipboardRef.current.map(d => {
      const newId = Date.now() + Math.random();

      // Offset position slightly
      const offsetTime = 300; // 5 minutes in seconds
      const offsetPrice = 0.01; // 1% price offset

      const newDataPoints = d.dataPoints?.map((dp: DataPoint) => ({
        time: dp.time + offsetTime,
        price: dp.price * (1 + offsetPrice),
      }));

      return {
        ...d,
        id: newId,
        dataPoints: newDataPoints,
      };
    });

    // Record batch add command
    addCommand({
      type: 'batch',
      timestamp: Date.now(),
      before: drawings,
      after: [...drawings, ...newDrawings],
      description: `Paste ${newDrawings.length} drawing(s)`,
    });

    const updatedDrawings = [...drawings, ...newDrawings];
    onSetDrawings(updatedDrawings);

    // Select pasted drawings
    onSetSelectedDrawingIds(newDrawings.map(d => d.id));
  }, [drawings, onSetDrawings, onSetSelectedDrawingIds, addCommand]);

  // Select all
  const selectAll = useCallback(() => {
    onSetSelectedDrawingIds(drawings.map(d => d.id));
  }, [drawings, onSetSelectedDrawingIds]);

  // Delete
  const deleteSelected = useCallback(() => {
    if (selectedDrawingIds.length === 0) return;

    // Record delete command
    const deletedDrawings = drawings.filter(d => selectedDrawingIds.includes(d.id));
    addCommand({
      type: 'delete',
      timestamp: Date.now(),
      drawingIds: selectedDrawingIds,
      before: deletedDrawings,
      description: `Delete ${selectedDrawingIds.length} drawing(s)`,
    });

    onDeleteDrawings(selectedDrawingIds);
  }, [selectedDrawingIds, onDeleteDrawings, drawings, addCommand]);

  // Check if target is text input
  const isTextInput = useCallback((target: EventTarget | null): boolean => {
    if (!target || !(target instanceof HTMLElement)) return false;

    const tagName = target.tagName.toLowerCase();
    const isEditable = target.isContentEditable;
    const isInput = ['input', 'textarea', 'select'].includes(tagName);

    return isInput || isEditable;
  }, []);

  // Keyboard event handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if typing in text field
      if (isTextInput(e.target)) {
        return;
      }

      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const ctrlOrCmd = isMac ? e.metaKey : e.ctrlKey;

      // Escape: Cancel drawing or deselect
      if (e.key === 'Escape') {
        if (isDrawing) {
          onCancelDrawing();
        } else if (selectedDrawingIds.length > 0) {
          onSetSelectedDrawingIds([]);
        }
        return;
      }

      // Delete/Backspace: Delete selected drawings
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedDrawingIds.length > 0) {
        e.preventDefault();
        deleteSelected();
        return;
      }

      // Only handle shortcuts when chart is focused
      if (!isChartFocusedRef.current) return;

      // Ctrl/Cmd + Z: Undo
      if (ctrlOrCmd && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
        return;
      }

      // Ctrl/Cmd + Shift + Z or Ctrl/Cmd + Y: Redo
      if (ctrlOrCmd && ((e.key === 'z' && e.shiftKey) || e.key === 'y')) {
        e.preventDefault();
        redo();
        return;
      }

      // Ctrl/Cmd + C: Copy
      if (ctrlOrCmd && e.key === 'c' && selectedDrawingIds.length > 0) {
        e.preventDefault();
        copy();
        return;
      }

      // Ctrl/Cmd + X: Cut
      if (ctrlOrCmd && e.key === 'x' && selectedDrawingIds.length > 0) {
        e.preventDefault();
        cut();
        return;
      }

      // Ctrl/Cmd + V: Paste
      if (ctrlOrCmd && e.key === 'v' && clipboardRef.current.length > 0) {
        e.preventDefault();
        paste();
        return;
      }

      // Ctrl/Cmd + A: Select all
      if (ctrlOrCmd && e.key === 'a') {
        e.preventDefault();
        selectAll();
        return;
      }

      // Ctrl/Cmd + S: Save
      if (ctrlOrCmd && e.key === 's') {
        e.preventDefault();
        onSaveDrawings();
        return;
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    isDrawing,
    selectedDrawingIds,
    onCancelDrawing,
    onSetSelectedDrawingIds,
    deleteSelected,
    undo,
    redo,
    copy,
    cut,
    paste,
    selectAll,
    onSaveDrawings,
    isTextInput,
  ]);

  return {
    undo,
    redo,
    copy,
    cut,
    paste,
    selectAll,
    addCommand, // Expose for App.tsx to record commands
    canUndo: historyIndexRef.current >= 0,
    canRedo: historyIndexRef.current < commandHistoryRef.current.length - 1,
    hasClipboard: clipboardRef.current.length > 0,
  };
}
