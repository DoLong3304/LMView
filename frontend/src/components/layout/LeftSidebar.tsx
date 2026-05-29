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
import { useI18n } from "@/i18n";
import type { DrawingTool } from "@/types";
import type { TranslationKey } from "@/i18n/translations";

interface LeftSidebarProps {
  activeTool: DrawingTool;
  onToolChange: (tool: DrawingTool) => void;
  onClearAll: () => void;
  onLockAll: () => void;
  onHideAll: () => void;
  magnetEnabled: boolean;
  onMagnetToggle: () => void;
  onReplayClick: () => void;
  isReplayActive: boolean;
  isReplaySelectionMode: boolean;
}

const DRAWING_TOOLS: Array<{ id: DrawingTool; icon: any; labelKey: TranslationKey }> = [
  { id: "cursor", icon: MousePointer2, labelKey: "cursor" },
  { id: "trendline", icon: TrendingUp, labelKey: "trendline" },
  { id: "horizontal", icon: Minus, labelKey: "horizontalLine" },
  { id: "circle", icon: Circle, labelKey: "circle" },
  { id: "rectangle", icon: Square, labelKey: "rectangle" },
  { id: "triangle", icon: Triangle, labelKey: "triangle" },
  { id: "text", icon: Type, labelKey: "textNotes" },
  { id: "ruler", icon: Ruler, labelKey: "ruler" },
];

const LeftSidebar: React.FC<LeftSidebarProps> = ({
  activeTool,
  onToolChange,
  onClearAll,
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
    <div
      className="flex h-full flex-shrink-0 flex-col justify-start border-r border-gray-700 bg-gray-900"
      style={{ width: 56, minWidth: 56, maxWidth: 56 }}
    >
      {/* Replay button */}
      <button
        type="button"
        onClick={onReplayClick}
        disabled={isReplaySelectionMode}
        className={`flex h-11 w-full flex-shrink-0 items-center justify-center border-b border-gray-700 transition-colors ${
          isReplayActive
            ? "bg-blue-600 text-white"
            : "text-gray-400 hover:text-white hover:bg-gray-800"
        } ${isReplaySelectionMode ? "opacity-50 cursor-not-allowed" : ""}`}
        title={t("replay")}
      >
        <Play size={20} />
      </button>

      {/* Drawing tools */}
      <div className="flex min-h-0 flex-1 flex-col justify-start overflow-y-auto py-2">
        {DRAWING_TOOLS.map(({ id, icon: Icon, labelKey }) => (
          <button
            key={id}
            type="button"
            onClick={() => onToolChange(id)}
            className={`flex h-11 w-full flex-shrink-0 items-center justify-center transition-colors ${
              activeTool === id
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
            title={t(labelKey)}
          >
            <Icon size={20} />
          </button>
        ))}

        <button
          type="button"
          onClick={onMagnetToggle}
          className={`flex h-11 w-full flex-shrink-0 items-center justify-center transition-colors ${
            magnetEnabled
              ? "bg-blue-600 text-white"
              : "text-gray-400 hover:text-white hover:bg-gray-800"
          }`}
          title={t("magnetMode")}
        >
          <Settings size={20} />
        </button>
        <button
          type="button"
          onClick={onLockAll}
          className="flex h-11 w-full flex-shrink-0 items-center justify-center text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
          title={t("lockAll")}
        >
          <Lock size={20} />
        </button>
        <button
          type="button"
          onClick={onHideAll}
          className="flex h-11 w-full flex-shrink-0 items-center justify-center text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
          title={t("hideAll")}
        >
          <EyeOff size={20} />
        </button>
        <button
          type="button"
          onClick={onClearAll}
          className="flex h-11 w-full flex-shrink-0 items-center justify-center text-gray-400 transition-colors hover:bg-gray-800 hover:text-red-400"
          title={t("clearAll")}
        >
          <Trash2 size={20} />
        </button>
      </div>
    </div>
  );
};

export default LeftSidebar;
