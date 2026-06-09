import React, { useState, useRef, useCallback } from "react";
import { Settings, Eraser } from "lucide-react";
import ToolSettingsPopup, { DEFAULT_TOOL_SETTINGS, type ToolSettings } from "./ToolSettingsPopup";
import { useI18n } from "@/i18n";
import type { TranslationKey } from "@/i18n/translations";

const SETTINGS_TOOLS = new Set([
  "trendline", "ray", "extendedLine", "horizontal", "vertical",
  "rectangle", "arrow", "fibRetracement", "ruler",
  "elliottWave", "harmonicABCD",
  // NEW tools
  "gannBox", "gannFan", "gannSquare",
  "schiffPitchfork", "modifiedPitchfork", "insidePitchfork",
  "fibExtension", "fibChannel", "fibArcs", "fibSpiral", "fibTimeZone",
  "ellipse", "rotatedRectangle", "polyline",
  "callout", "note", "balloon",
  "priceRange", "dateRange", "riskReward",
]);

interface ToolDef {
  id: string;
  labelKey: TranslationKey;
  icon: React.ReactNode;
}

interface ToolGroup {
  labelKey: TranslationKey;
  tools: ToolDef[];
}

const TOOL_GROUPS: ToolGroup[] = [
  {
    labelKey: "basic",
    tools: [
      {
        id: "cursor",
        labelKey: "cursor",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M4 4l7 17 2.5-6.5L20 12z" />
          </svg>
        ),
      },
      {
        id: "crosshair",
        labelKey: "crosshair",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 3v18M3 12h18" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "lineTools",
    tools: [
      {
        id: "trendline",
        labelKey: "trendline",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 20L21 4" />
            <circle cx="3" cy="20" r="2" fill="currentColor" />
            <circle cx="21" cy="4" r="2" fill="currentColor" />
          </svg>
        ),
      },
      {
        id: "ray",
        labelKey: "ray",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 20L21 4" />
            <circle cx="3" cy="20" r="2" fill="currentColor" />
            <path d="M21 4l3-3" strokeWidth="1.5" />
          </svg>
        ),
      },
      {
        id: "extendedLine",
        labelKey: "extendedLine",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M1 22L23 2" />
            <path d="M1 22l-1-1M23 2l1-1" strokeWidth="1.5"/>
          </svg>
        ),
      },
      {
        id: "horizontalRay",
        labelKey: "horizontalRay",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M1 12h22" />
            <path d="M3 8l3 4-3 4" strokeWidth="1.5"/>
            <path d="M21 8l-3 4 3 4" strokeWidth="1.5"/>
          </svg>
        ),
      },
      {
        id: "horizontal",
        labelKey: "horizontalLine",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M2 12h20" strokeDasharray="4 2" />
          </svg>
        ),
      },
      {
        id: "vertical",
        labelKey: "verticalLine",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M12 2v20" strokeDasharray="4 2" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "shapes",
    tools: [
      {
        id: "rectangle",
        labelKey: "rectangle",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <rect x="3" y="5" width="18" height="14" rx="1" />
          </svg>
        ),
      },
      {
        id: "arrow",
        labelKey: "arrow",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 20L21 4" />
            <path d="M21 4l-6 2M21 4l-2 6" />
          </svg>
        ),
      },
      {
        id: "ellipse",
        labelKey: "ellipse",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <ellipse cx="12" cy="12" rx="9" ry="6" />
          </svg>
        ),
      },
      {
        id: "rotatedRectangle",
        labelKey: "rotatedRectangle",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M6 3L18 8L21 20L9 15Z" />
          </svg>
        ),
      },
      {
        id: "polyline",
        labelKey: "polyline",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M4 16L9 8L14 14L20 4" />
            <circle cx="4" cy="16" r="1.5" fill="currentColor" />
            <circle cx="9" cy="8" r="1.5" fill="currentColor" />
            <circle cx="14" cy="14" r="1.5" fill="currentColor" />
            <circle cx="20" cy="4" r="1.5" fill="currentColor" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "fibonacci",
    tools: [
      {
        id: "fibRetracement",
        labelKey: "fibonacci",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M2 4h20" />
            <path d="M2 9h20" opacity="0.7" />
            <path d="M2 14h20" opacity="0.5" />
            <path d="M2 20h20" opacity="0.3" />
          </svg>
        ),
      },
      {
        id: "fibExtension",
        labelKey: "fibExtension",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M2 20h16" />
            <path d="M2 12h16" opacity="0.6" />
            <path d="M18 4L22 4" strokeWidth="3" />
            <path d="M20 4L22 6" strokeWidth="2" opacity="0.7" />
          </svg>
        ),
      },
      {
        id: "fibChannel",
        labelKey: "fibChannel",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M2 18L22 10" />
            <path d="M2 14L22 6" opacity="0.6" />
            <path d="M2 10L22 2" opacity="0.3" />
          </svg>
        ),
      },
      {
        id: "fibArcs",
        labelKey: "fibArcs",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M4 20Q12 12 20 4" />
            <path d="M4 20Q16 12 20 4" opacity="0.6" strokeDasharray="3 2" />
            <path d="M4 20Q20 12 20 4" opacity="0.3" strokeDasharray="3 2" />
          </svg>
        ),
      },
      {
        id: "fibSpiral",
        labelKey: "fibSpiral",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M12 12c0-4 3-8 8-8s8 4 8 8-4 8-8 8-8-4-8-8" />
            <path d="M12 12c0 4-4 8-8 8s-8-4-8-8 4-8 8-8 8 4 8 8" opacity="0.5" />
          </svg>
        ),
      },
      {
        id: "fibTimeZone",
        labelKey: "fibTimeZone",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M4 4v16" />
            <path d="M10 4v16" opacity="0.6" />
            <path d="M16 4v16" opacity="0.3" />
            <path d="M22 4v16" opacity="0.2" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "annotation",
    tools: [
      {
        id: "text",
        labelKey: "textNotes",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M4 7V4h16v3" />
            <path d="M12 4v16" />
            <path d="M8 20h8" />
          </svg>
        ),
      },
      {
        id: "callout",
        labelKey: "callout",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M4 6h16v12H8l-4 4V6z" />
          </svg>
        ),
      },
      {
        id: "note",
        labelKey: "note",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6" />
            <path d="M8 13h8M8 17h5" />
          </svg>
        ),
      },
      {
        id: "balloon",
        labelKey: "balloon",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <ellipse cx="12" cy="8" rx="8" ry="5" />
            <path d="M12 13c2 2 3 4 4 6M12 13c-2 2-3 4-4 6" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "measure",
    tools: [
      {
        id: "ruler",
        labelKey: "ruler",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M2 22L22 2" />
            <path d="M6 18l2-2" />
            <path d="M10 14l2-2" />
            <path d="M14 10l2-2" />
            <path d="M18 6l2-2" />
          </svg>
        ),
      },
      {
        id: "priceRange",
        labelKey: "priceRange",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 6h18" />
            <path d="M3 18h18" />
            <path d="M3 6v12" />
            <path d="M21 6v12" />
          </svg>
        ),
      },
      {
        id: "dateRange",
        labelKey: "dateRangeTool",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <path d="M3 10h18" />
            <path d="M8 2v4M16 2v4" />
          </svg>
        ),
      },
      {
        id: "riskReward",
        labelKey: "riskReward",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 20L10 10L13 14L21 4" />
            <circle cx="10" cy="10" r="2" fill="currentColor" />
            <circle cx="13" cy="14" r="2" fill="currentColor" />
            <circle cx="21" cy="4" r="2" fill="currentColor" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "patterns",
    tools: [
      {
        id: "elliottWave",
        labelKey: "elliottWave",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M2 16 L5 8 L8 14 L11 6 L14 12 L17 5 L20 10" strokeLinejoin="round" />
            <circle cx="5" cy="8" r="1.5" fill="currentColor" />
            <circle cx="11" cy="6" r="1.5" fill="currentColor" />
            <circle cx="17" cy="5" r="1.5" fill="currentColor" />
          </svg>
        ),
      },
      {
        id: "harmonicABCD",
        labelKey: "harmonicABCD",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 18 L8 6 L13 14 L20 4" strokeLinejoin="round" />
            <circle cx="3" cy="18" r="1.5" fill="currentColor" />
            <circle cx="8" cy="6" r="1.5" fill="currentColor" />
            <circle cx="13" cy="14" r="1.5" fill="currentColor" />
            <circle cx="20" cy="4" r="1.5" fill="currentColor" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "channels",
    tools: [
      {
        id: "parallelChannel",
        labelKey: "parallelChannel",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 8L21 14" />
            <path d="M3 14L21 20" opacity="0.5" />
          </svg>
        ),
      },
      {
        id: "pitchfork",
        labelKey: "pitchfork",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 20L12 8L21 20" />
            <path d="M5 14L19 14" />
          </svg>
        ),
      },
      {
        id: "schiffPitchfork",
        labelKey: "schiffPitchfork",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 18L10 6L21 18" />
            <path d="M5 12L17 12" strokeDasharray="2 2" />
            <path d="M4 14L18 14" strokeDasharray="2 2" opacity="0.5" />
          </svg>
        ),
      },
      {
        id: "modifiedPitchfork",
        labelKey: "modifiedPitchfork",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 20L12 6L21 20" />
            <path d="M3 14L21 14" />
            <path d="M7 10L17 18" strokeDasharray="3 2" />
            <path d="M7 18L17 10" strokeDasharray="3 2" />
          </svg>
        ),
      },
      {
        id: "insidePitchfork",
        labelKey: "insidePitchfork",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M5 20L12 6L19 20" />
            <path d="M7 16L17 16" strokeDasharray="2 2" />
            <path d="M8 13L16 13" strokeDasharray="2 2" opacity="0.6" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "gann",
    tools: [
      {
        id: "gannBox",
        labelKey: "gannBox",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <rect x="3" y="5" width="18" height="14" rx="1" />
            <path d="M3 5L21 19" opacity="0.5" />
            <path d="M3 12L21 12" opacity="0.3" />
            <path d="M12 5L12 19" opacity="0.3" />
          </svg>
        ),
      },
      {
        id: "gannFan",
        labelKey: "gannFan",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M4 20L20 4" />
            <path d="M4 20L18 4" opacity="0.6" />
            <path d="M4 20L16 4" opacity="0.4" />
            <path d="M4 20L14 4" opacity="0.3" />
            <path d="M4 20L12 4" opacity="0.2" />
          </svg>
        ),
      },
      {
        id: "gannSquare",
        labelKey: "gannSquare",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <rect x="4" y="4" width="16" height="16" />
            <path d="M4 4L20 20" opacity="0.5" />
            <path d="M4 20L20 4" opacity="0.5" />
            <circle cx="12" cy="12" r="6" opacity="0.3" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "utility",
    tools: [
      {
        id: "magnet",
        labelKey: "magnet",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M6 15v-2a6 6 0 1 1 12 0v2" />
            <path d="M6 15v2a2 2 0 0 1-2 2H3a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h3z" />
            <path d="M18 15v2a2 2 0 0 0 2 2h1a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1h-3z" />
          </svg>
        ),
      },
      {
        id: "lock",
        labelKey: "lockAll",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <rect x="5" y="11" width="14" height="10" rx="2" />
            <path d="M12 17v-2" />
            <path d="M8 11V7a4 4 0 0 1 8 0v4" />
          </svg>
        ),
      },
      {
        id: "hide",
        labelKey: "hideAll",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
            <circle cx="12" cy="12" r="3" />
            <path d="M2 2l20 20" />
          </svg>
        ),
      },
    ],
  },
  {
    labelKey: "delete",
    tools: [
      {
        id: "eraser",
        labelKey: "eraser",
        icon: <Eraser className="w-5 h-5" />,
      },
      {
        id: "clearAll",
        labelKey: "clearAll",
        icon: (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <path d="M3 6h18" />
            <path d="M8 6V4h8v2" />
            <path d="M5 6l1 14h12l1-14" />
            <path d="M10 10v8" />
            <path d="M14 10v8" />
          </svg>
        ),
      },
    ],
  },
];

interface DrawingToolbarProps {
  activeTool: string;
  onToolChange: (toolId: string) => void;
  onClearAll: () => void;
  onLockAll?: () => void;
  onHideAll?: () => void;
  magnetEnabled?: boolean;
  onMagnetToggle?: () => void;
  toolSettings?: Record<string, ToolSettings>;
  onToolSettingsChange?: (toolId: string, settings: ToolSettings) => void;
}

const DrawingToolbar: React.FC<DrawingToolbarProps> = ({
  activeTool,
  onToolChange,
  onClearAll,
  onLockAll,
  onHideAll,
  magnetEnabled = false,
  onMagnetToggle,
  toolSettings,
  onToolSettingsChange,
}) => {
  const { t } = useI18n();
  const [openSettings, setOpenSettings] = useState<string | null>(null);
  const btnRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const handleToolClick = useCallback(
    (toolId: string) => {
      if (toolId === "clearAll") {
        // Show confirmation dialog
        if (window.confirm(t("confirmClearDrawings"))) {
          onClearAll();
        }
        return;
      }
      if (toolId === "magnet") {
        onMagnetToggle?.();
        return;
      }
      if (toolId === "lock") {
        onLockAll?.();
        return;
      }
      if (toolId === "hide") {
        onHideAll?.();
        return;
      }
      // For eraser and other tools, set as active tool
      onToolChange(toolId);
    },
    [onToolChange, onClearAll, onLockAll, onHideAll, onMagnetToggle, t]
  );

  const handleSettingsClick = useCallback((e: React.MouseEvent, toolId: string) => {
    e.stopPropagation();
    setOpenSettings((prev) => (prev === toolId ? null : toolId));
  }, []);

  return (
    <div className="flex flex-col items-center bg-gray-800 rounded-lg py-2 px-1 space-y-1 shadow-lg border border-gray-700 select-none">
      {TOOL_GROUPS.map((group, gi) => (
        <React.Fragment key={group.labelKey}>
          {gi > 0 && <div className="w-6 border-t border-gray-700 my-0.5" />}
          {group.tools.map((tool) => {
            const isActive = activeTool === tool.id || (tool.id === "magnet" && magnetEnabled);
            const hasSettings = SETTINGS_TOOLS.has(tool.id);
            return (
              <div
                key={tool.id}
                ref={(el) => {
                  btnRefs.current[tool.id] = el;
                }}
                className="relative group"
              >
                <button
                  title={t(tool.labelKey)}
                  onClick={() => handleToolClick(tool.id)}
                  className={`p-2 rounded-md transition-all duration-150 ${
                    isActive
                      ? "bg-blue-600 text-white shadow-md"
                      : "text-gray-400 hover:text-white hover:bg-gray-700"
                  }`}
                >
                  {tool.icon}
                </button>
                {hasSettings && (
                  <button
                    onClick={(e) => handleSettingsClick(e, tool.id)}
                    className={`absolute -right-1 -bottom-1 w-4 h-4 rounded-full flex items-center justify-center transition-all ${
                      openSettings === tool.id
                        ? "bg-blue-400 text-white opacity-100"
                        : "bg-gray-600 text-gray-300 opacity-0 group-hover:opacity-100"
                    }`}
                    title={t("settings")}
                  >
                    <Settings size={9} />
                  </button>
                )}
                <span className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 z-50 border border-gray-600">
                  {t(tool.labelKey)}
                </span>
                {openSettings === tool.id && hasSettings && (
                  <ToolSettingsPopup
                    tool={tool.id}
                    settings={toolSettings?.[tool.id] || DEFAULT_TOOL_SETTINGS[tool.id]}
                    onChange={(ns) => onToolSettingsChange?.(tool.id, ns)}
                    onClose={() => setOpenSettings(null)}
                    anchorRef={{ current: btnRefs.current[tool.id] ?? null }}
                  />
                )}
              </div>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
};

export default DrawingToolbar;
