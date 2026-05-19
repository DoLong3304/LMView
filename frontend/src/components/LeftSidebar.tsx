import React from "react";
import {
  MousePointer2,
  TrendingUp,
  Minus,
  Circle,
  Square,
  Triangle,
  Type,
  Ruler,
  Trash2,
  Lock,
  EyeOff,
  Settings,
  Play
} from "lucide-react";
import { useI18n } from "../i18n";
import type { DrawingTool } from "../types";

interface LeftSidebarProps {
  activeTool: DrawingTool;
  onToolChange: (tool: DrawingTool) => void;
  onClearAll: () => void;
  onDeleteSelected: () => void;
  selectedDrawingIds: string[];
  onLockAll: () => void;
  onHideAll: () => void;
  magnetEnabled: boolean;
  onMagnetToggle: () => void;
  onReplayClick: () => void;
  isReplayActive: boolean;
  isReplaySelectionMode: boolean;
}

const DRAWING_TOOLS: Array<{ id: DrawingTool; icon: any; label: string }> = [
  { id: "cursor", icon: MousePointer2, label: "Cursor" },
  { id: "trendline", icon: TrendingUp, label: "Trend Line" },
  { id: "horizontal", icon: Minus, label: "Horizontal Line" },
  { id: "circle", icon: Circle, label: "Circle" },
  { id: "rectangle", icon: Square, label: "Rectangle" },
  { id: "triangle", icon: Triangle, label: "Triangle" },
  { id: "text", icon: Type, label: "Text" },
  { id: "ruler", icon: Ruler, label: "Ruler" },
];

const LeftSidebar: React.FC<LeftSidebarProps> = ({
  activeTool,
  onToolChange,
  onClearAll,
  onDeleteSelected,
  selectedDrawingIds,
  onLockAll,
  onHideAll,
  magnetEnabled,
  onMagnetToggle,
  onReplayClick,
  isReplayActive,
  isReplaySelectionMode,
}) => {
  const { t } = useI18n();

  return (
    <div className="bg-gray-900 border-r border-gray-700 flex flex-col" style={{ width: 56 }}>
      {/* Replay button */}
      <button
        onClick={onReplayClick}
        disabled={isReplaySelectionMode}
        className={`w-full p-3 flex items-center justify-center border-b border-gray-700 transition-colors ${
          isReplayActive
            ? "bg-blue-600 text-white"
            : "text-gray-400 hover:text-white hover:bg-gray-800"
        } ${isReplaySelectionMode ? "opacity-50 cursor-not-allowed" : ""}`}
        title={t("replay")}
      >
        <Play size={20} />
      </button>

      {/* Drawing tools */}
      <div className="flex-1 overflow-y-auto py-2">
        {DRAWING_TOOLS.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => onToolChange(id)}
            className={`w-full p-3 flex items-center justify-center transition-colors ${
              activeTool === id
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
            title={label}
          >
            <Icon size={20} />
          </button>
        ))}
      </div>

      {/* Bottom actions */}
      <div className="border-t border-gray-700">
        <button
          onClick={onMagnetToggle}
          className={`w-full p-3 flex items-center justify-center transition-colors ${
            magnetEnabled
              ? "bg-blue-600 text-white"
              : "text-gray-400 hover:text-white hover:bg-gray-800"
          }`}
          title={t("magnetMode")}
        >
          <Settings size={20} />
        </button>
        <button
          onClick={onLockAll}
          className="w-full p-3 flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          title={t("lockAll")}
        >
          <Lock size={20} />
        </button>
        <button
          onClick={onHideAll}
          className="w-full p-3 flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          title={t("hideAll")}
        >
          <EyeOff size={20} />
        </button>
        <button
          onClick={onDeleteSelected}
          disabled={selectedDrawingIds.length === 0}
          className={`w-full p-3 flex items-center justify-center transition-colors ${
            selectedDrawingIds.length > 0
              ? "text-red-400 hover:text-red-300 hover:bg-gray-800"
              : "text-gray-600 cursor-not-allowed"
          }`}
          title={t("deleteSelected")}
        >
          <Trash2 size={20} />
        </button>
        <button
          onClick={onClearAll}
          className="w-full p-3 flex items-center justify-center text-gray-400 hover:text-red-400 hover:bg-gray-800 transition-colors"
          title={t("clearAll")}
        >
          <Trash2 size={20} />
        </button>
      </div>
    </div>
  );
};

export default LeftSidebar;
