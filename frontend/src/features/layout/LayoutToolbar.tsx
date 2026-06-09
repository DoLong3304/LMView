import React from "react";
import { LayoutType } from "./LayoutContext";
import { useI18n } from "@/i18n";
import type { TranslationKey } from "@/i18n/translations";

interface LayoutToolbarProps {
  currentLayout: LayoutType;
  onLayoutChange: (layout: LayoutType) => void;
}

const LAYOUT_OPTIONS: { type: LayoutType; labelKey: TranslationKey; icon: React.ReactNode }[] = [
  {
    type: "single",
    labelKey: "singleChart",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
        <rect x="2" y="2" width="16" height="16" rx="1" />
      </svg>
    ),
  },
  {
    type: "split-v",
    labelKey: "splitVertical",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
        <rect x="1" y="2" width="8" height="16" rx="1" />
        <rect x="11" y="2" width="8" height="16" rx="1" />
      </svg>
    ),
  },
  {
    type: "split-h",
    labelKey: "splitHorizontal",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
        <rect x="2" y="1" width="16" height="8" rx="1" />
        <rect x="2" y="11" width="16" height="8" rx="1" />
      </svg>
    ),
  },
  {
    type: "quad",
    labelKey: "quadChart",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
        <rect x="1" y="1" width="8" height="8" rx="1" />
        <rect x="11" y="1" width="8" height="8" rx="1" />
        <rect x="1" y="11" width="8" height="8" rx="1" />
        <rect x="11" y="11" width="8" height="8" rx="1" />
      </svg>
    ),
  },
  {
    type: "three-v",
    labelKey: "threeVertical",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
        <rect x="1" y="2" width="5" height="16" rx="1" />
        <rect x="7.5" y="2" width="5" height="16" rx="1" />
        <rect x="14" y="2" width="5" height="16" rx="1" />
      </svg>
    ),
  },
];

export function LayoutToolbar({ currentLayout, onLayoutChange }: LayoutToolbarProps) {
  const { t } = useI18n();

  return (
    <div className="flex items-center gap-1 p-1 bg-gray-800 rounded">
      {LAYOUT_OPTIONS.map((opt) => (
        <button
          key={opt.type}
          onClick={() => onLayoutChange(opt.type)}
          title={t(opt.labelKey)}
          className={`p-1.5 rounded transition-colors ${
            currentLayout === opt.type
              ? "bg-blue-600 text-white"
              : "text-gray-400 hover:bg-gray-700 hover:text-white"
          }`}
        >
          {opt.icon}
        </button>
      ))}
    </div>
  );
}