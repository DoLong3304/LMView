import React, { useRef, useEffect, useState } from 'react';
import { Type, Trash2, Bell } from 'lucide-react';
import { useI18n } from "@/i18n";
import type { Drawing } from "@/types";

interface DrawingContextToolbarProps {
  drawing: Drawing;
  position: { x: number; y: number; visible: boolean };
  onUpdateDrawing: (updates: Partial<Drawing>) => void;
  onDelete: () => void;
  onAddAlert: () => void;
  onClose: () => void;
}

/**
 * Floating context toolbar for selected drawings
 *
 * Features:
 * - Add/Edit text label
 * - Adjust line width (1-4px)
 * - Change color
 * - Create price alert
 * - Delete drawing
 *
 * Positioning:
 * - Follows drawing during pan/zoom
 * - Auto-hides when drawing goes off-screen
 * - Click outside to close
 */
const DrawingContextToolbar: React.FC<DrawingContextToolbarProps> = ({
  drawing,
  position,
  onUpdateDrawing,
  onDelete,
  onAddAlert,
  onClose,
}) => {
  const { t } = useI18n();
  const toolbarRef = useRef<HTMLDivElement>(null);
  const [showTextInput, setShowTextInput] = useState(false);
  const [textValue, setTextValue] = useState(drawing.text || '');

  // Get current settings
  const currentColor = drawing.settings?.color || '#3b82f6';
  const currentLineWidth = drawing.settings?.lineWidth || 2;

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (toolbarRef.current && !toolbarRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  // Handle text input submit
  const handleTextSubmit = () => {
    onUpdateDrawing({ text: textValue });
    setShowTextInput(false);
  };

  // Handle text input cancel
  const handleTextCancel = () => {
    setTextValue(drawing.text || '');
    setShowTextInput(false);
  };

  // Handle line width change
  const handleLineWidthChange = (width: number) => {
    onUpdateDrawing({
      settings: {
        ...drawing.settings,
        lineWidth: width,
      },
    });
  };

  // Handle color change
  const handleColorChange = (color: string) => {
    onUpdateDrawing({
      settings: {
        ...drawing.settings,
        color,
      },
    });
  };

  if (!position.visible) return null;

  return (
    <div
      ref={toolbarRef}
      className="fixed z-[300] bg-gray-800 border border-gray-600 rounded-lg shadow-2xl animate-fadeIn"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        minWidth: '200px',
      }}
    >
      {/* Main toolbar */}
      <div className="flex items-center gap-1 p-2">
        {/* Text button */}
        <button
          onClick={() => setShowTextInput(!showTextInput)}
          className="p-2 rounded hover:bg-gray-700 transition-colors text-gray-300 hover:text-white"
          title={t('addText')}
        >
          <Type size={16} />
        </button>

        {/* Line width selector */}
        <div className="flex items-center gap-1 px-2 border-l border-gray-600">
          <span className="text-xs text-gray-400">{currentLineWidth}px</span>
          <select
            value={currentLineWidth}
            onChange={(e) => handleLineWidthChange(Number(e.target.value))}
            className="bg-gray-700 text-white text-xs rounded px-1 py-1 border border-gray-600 focus:outline-none focus:border-blue-500"
          >
            <option value={1}>1px</option>
            <option value={1.5}>1.5px</option>
            <option value={2}>2px</option>
            <option value={2.5}>2.5px</option>
            <option value={3}>3px</option>
            <option value={4}>4px</option>
          </select>
        </div>

        {/* Color picker */}
        <div className="flex items-center gap-1 px-2 border-l border-gray-600">
          <input
            type="color"
            value={currentColor}
            onChange={(e) => handleColorChange(e.target.value)}
            className="w-6 h-6 rounded cursor-pointer border-0 bg-transparent"
            title={t('changeColor')}
          />
        </div>

        {/* Alert button */}
        <button
          onClick={onAddAlert}
          className="p-2 rounded hover:bg-gray-700 transition-colors text-gray-300 hover:text-white border-l border-gray-600"
          title={t('addAlert')}
        >
          <Bell size={16} />
        </button>

        {/* Delete button */}
        <button
          onClick={onDelete}
          className="p-2 rounded hover:bg-red-600 transition-colors text-gray-300 hover:text-white border-l border-gray-600"
          title={t('delete')}
        >
          <Trash2 size={16} />
        </button>
      </div>

      {/* Text input panel (expandable) */}
      {showTextInput && (
        <div className="border-t border-gray-600 p-2 animate-slideDown">
          <input
            type="text"
            value={textValue}
            onChange={(e) => setTextValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleTextSubmit();
              if (e.key === 'Escape') handleTextCancel();
            }}
            placeholder={t('enterNote')}
            className="w-full bg-gray-700 text-white text-sm rounded px-2 py-1 border border-gray-600 focus:outline-none focus:border-blue-500"
            autoFocus
          />
          <div className="flex items-center justify-end gap-2 mt-2">
            <button
              onClick={handleTextCancel}
              className="px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              {t('cancel')}
            </button>
            <button
              onClick={handleTextSubmit}
              className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
            >
              {t('apply')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DrawingContextToolbar;
