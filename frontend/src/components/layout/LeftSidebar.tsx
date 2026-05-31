import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpRight,
  BarChart3,
  Circle,
  EyeOff,
  Eraser,
  GitBranch,
  Lock,
  Magnet,
  MousePointer2,
  Play,
  Ruler,
  Shapes,
  Square,
  TextCursorInput,
  Trash2,
  TrendingUp,
  Triangle,
  Unlock,
  Waves,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { useI18n } from "@/i18n";
import type { TranslationKey } from "@/i18n/translations";

interface LeftSidebarProps {
  activeTool: string;
  onToolChange: (tool: string) => void;
  onClearAll: () => void;
  onLockAll: () => void;
  onHideAll: () => void;
  magnetEnabled: boolean;
  onMagnetToggle: () => void;
  onReplayClick: () => void;
  isReplayActive: boolean;
  isReplaySelectionMode: boolean;
  drawingsLocked?: boolean;
}

interface ToolItem {
  id: string;
  icon: LucideIcon;
  labelKey: TranslationKey;
}

interface ToolGroup {
  id: string;
  icon: LucideIcon;
  labelKey: TranslationKey;
  tools: ToolItem[];
}

const DIRECT_TOOLS: ToolItem[] = [
  { id: "cursor", icon: MousePointer2, labelKey: "cursor" },
  { id: "text", icon: TextCursorInput, labelKey: "textNotes" },
  { id: "ruler", icon: Ruler, labelKey: "ruler" },
];

const TOOL_GROUPS: ToolGroup[] = [
  {
    id: "lineTools",
    icon: TrendingUp,
    labelKey: "lineTools",
    tools: [
      { id: "trendline", icon: TrendingUp, labelKey: "trendline" },
      { id: "ray", icon: ArrowUpRight, labelKey: "ray" },
      { id: "extendedLine", icon: GitBranch, labelKey: "extendedLine" },
      { id: "horizontal", icon: BarChart3, labelKey: "horizontalLine" },
      { id: "vertical", icon: BarChart3, labelKey: "verticalLine" },
      { id: "arrow", icon: ArrowUpRight, labelKey: "arrow" },
    ],
  },
  {
    id: "shapeTools",
    icon: Shapes,
    labelKey: "shapeTools",
    tools: [
      { id: "rectangle", icon: Square, labelKey: "rectangle" },
      { id: "circle", icon: Circle, labelKey: "circle" },
      { id: "triangle", icon: Triangle, labelKey: "triangle" },
    ],
  },
  {
    id: "fibonacciTools",
    icon: GitBranch,
    labelKey: "fibonacciTools",
    tools: [
      { id: "fibRetracement", icon: GitBranch, labelKey: "fibRetracement" },
    ],
  },
  {
    id: "patternTools",
    icon: Triangle,
    labelKey: "patternTools",
    tools: [
      { id: "harmonicABCD", icon: Triangle, labelKey: "abcdPattern" },
      { id: "xabcdPattern", icon: Triangle, labelKey: "xabcdPattern" },
    ],
  },
  {
    id: "elliottTools",
    icon: Waves,
    labelKey: "elliottTools",
    tools: [
      { id: "elliottWave", icon: Waves, labelKey: "elliottImpulseWave" },
    ],
  },
  {
    id: "positionTools",
    icon: Zap,
    labelKey: "positionTools",
    tools: [
      { id: "longPosition", icon: TrendingUp, labelKey: "longPosition" },
      { id: "shortPosition", icon: TrendingUp, labelKey: "shortPosition" },
      { id: "forecast", icon: Zap, labelKey: "forecast" },
    ],
  },
];

const MENU_WIDTH = 216;
const MENU_ITEM_HEIGHT = 36;
const MENU_MARGIN = 12;

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
  drawingsLocked = false,
}) => {
  const { t } = useI18n();
  const [openGroupId, setOpenGroupId] = useState<string | null>(null);
  const [pinnedGroupId, setPinnedGroupId] = useState<string | null>(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const closeTimerRef = useRef<number | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  const activeGroupId = useMemo(() => {
    return TOOL_GROUPS.find((group) => group.tools.some((tool) => tool.id === activeTool))?.id ?? null;
  }, [activeTool]);

  const clearCloseTimer = useCallback(() => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);

  const scheduleClose = useCallback(() => {
    if (pinnedGroupId) return;
    clearCloseTimer();
    closeTimerRef.current = window.setTimeout(() => setOpenGroupId(null), 140);
  }, [clearCloseTimer, pinnedGroupId]);

  const showGroupMenu = useCallback((group: ToolGroup, anchor: HTMLElement) => {
    clearCloseTimer();
    const root = rootRef.current;
    if (!root) return;

    const rect = anchor.getBoundingClientRect();
    const rootRect = root.getBoundingClientRect();
    const menuHeight = group.tools.length * MENU_ITEM_HEIGHT + 16;
    const preferredTop = rect.top - rootRect.top;
    const maxTop = window.innerHeight - rootRect.top - menuHeight - MENU_MARGIN;
    const top = Math.min(
      Math.max(0, preferredTop),
      Math.max(0, maxTop),
    );
    const preferredLeft = rect.right - rootRect.left + 8;
    const maxLeft = window.innerWidth - rootRect.left - MENU_WIDTH - MENU_MARGIN;
    const left = Math.min(preferredLeft, Math.max(MENU_MARGIN, maxLeft));
    setMenuPosition({ top, left });
    setOpenGroupId(group.id);
  }, [clearCloseTimer]);

  const selectTool = useCallback((toolId: string) => {
    onToolChange(toolId);
    setOpenGroupId(null);
    setPinnedGroupId(null);
  }, [onToolChange]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (rootRef.current?.contains(event.target as Node)) return;
      setOpenGroupId(null);
      setPinnedGroupId(null);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpenGroupId(null);
      setPinnedGroupId(null);
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  useEffect(() => () => clearCloseTimer(), [clearCloseTimer]);

  const sidebarButtonClass = (active: boolean, disabled = false) =>
    [
      "lm-tool-button flex h-11 w-full flex-shrink-0 items-center justify-center transition-colors",
      active ? "is-active" : "",
      disabled ? "is-disabled cursor-not-allowed" : "",
    ].filter(Boolean).join(" ");

  const openGroup = openGroupId ? TOOL_GROUPS.find((group) => group.id === openGroupId) ?? null : null;

  return (
    <div ref={rootRef} className="relative overflow-visible">
      <div
        className="lm-left-toolbar flex max-h-[calc(100vh-9rem)] flex-shrink-0 flex-col justify-start overflow-visible rounded-lg border shadow-2xl"
        style={{ width: 56, minWidth: 56, maxWidth: 56 }}
      >
        <button
          type="button"
          onClick={onReplayClick}
          disabled={isReplaySelectionMode}
          className={sidebarButtonClass(isReplayActive, isReplaySelectionMode)}
          title={t("replay")}
        >
          <Play size={20} />
        </button>

        <div className="flex min-h-0 flex-col justify-start gap-0 overflow-y-auto overflow-x-visible py-2">
          {DIRECT_TOOLS.map(({ id, icon: Icon, labelKey }) => (
            <button
              key={id}
              type="button"
              onClick={() => selectTool(id)}
              className={sidebarButtonClass(activeTool === id)}
              title={t(labelKey)}
            >
              <Icon size={20} />
            </button>
          ))}

          <div className="lm-tool-separator" />

          {TOOL_GROUPS.map((group) => {
            const GroupIcon = group.icon;
            const active = activeGroupId === group.id || openGroupId === group.id;
            const selectedTool = group.tools.find((tool) => tool.id === activeTool);
            const DisplayIcon = selectedTool?.icon ?? GroupIcon;
            return (
              <button
                key={group.id}
                type="button"
                onMouseEnter={(event) => showGroupMenu(group, event.currentTarget)}
                onMouseLeave={scheduleClose}
                onClick={(event) => {
                  if (group.tools.length === 1) {
                    selectTool(group.tools[0].id);
                    return;
                  }
                  showGroupMenu(group, event.currentTarget);
                  setPinnedGroupId((current) => (current === group.id ? null : group.id));
                }}
                className={sidebarButtonClass(active)}
                title={t(group.labelKey)}
                aria-haspopup="menu"
                aria-expanded={openGroupId === group.id}
              >
                <DisplayIcon size={20} />
              </button>
            );
          })}

          <div className="lm-tool-separator" />

          <button
            type="button"
            onClick={onMagnetToggle}
            className={sidebarButtonClass(magnetEnabled)}
            title={t("magnetMode")}
          >
            <Magnet size={20} />
          </button>
          <button
            type="button"
            onClick={onLockAll}
            className={sidebarButtonClass(drawingsLocked)}
            title={drawingsLocked ? t("unlockAll") : t("lockAll")}
          >
            {drawingsLocked ? <Unlock size={20} /> : <Lock size={20} />}
          </button>
          <button
            type="button"
            onClick={onHideAll}
            className={sidebarButtonClass(false)}
            title={t("hideAll")}
          >
            <EyeOff size={20} />
          </button>
          <button
            type="button"
            onClick={() => selectTool("eraser")}
            disabled={drawingsLocked}
            className={sidebarButtonClass(activeTool === "eraser", drawingsLocked)}
            title={t("eraser")}
          >
            <Eraser size={20} />
          </button>
          <button
            type="button"
            onClick={onClearAll}
            className="lm-tool-button flex h-11 w-full flex-shrink-0 items-center justify-center transition-colors hover:text-red-500"
            title={t("deleteAllDrawings")}
          >
            <Trash2 size={20} />
          </button>
        </div>
      </div>

      {openGroup && (
        <div
          role="menu"
          aria-label={t(openGroup.labelKey)}
          className="lm-tool-flyout absolute z-[220] w-[216px] rounded-lg border p-2 shadow-2xl"
          style={{ top: menuPosition.top, left: menuPosition.left }}
          onMouseEnter={clearCloseTimer}
          onMouseLeave={scheduleClose}
        >
          <div className="mb-1 px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--lm-text-muted)]">
            {t(openGroup.labelKey)}
          </div>
          {openGroup.tools.map((tool) => {
            const Icon = tool.icon;
            const active = activeTool === tool.id;
            return (
              <button
                key={tool.id}
                type="button"
                role="menuitem"
                onClick={() => selectTool(tool.id)}
                className={`lm-tool-menu-item flex h-9 w-full items-center gap-2 rounded-md px-2 text-left text-xs font-medium transition-colors ${
                  active ? "is-active" : ""
                }`}
              >
                <Icon size={15} />
                <span className="min-w-0 truncate">{t(tool.labelKey)}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default LeftSidebar;
