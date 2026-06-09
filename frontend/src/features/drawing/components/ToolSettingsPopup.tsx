/**
 * ToolSettingsPopup.tsx
 * Settings pop-up for drawing tools.
 */
import React, { useRef, useEffect } from "react";
import { X } from "lucide-react";
import { useI18n } from "@/i18n";
import type { TranslationKey } from "@/i18n/translations";

export interface BaseToolSettings {
  color: string;
  lineWidth: number;
  showLabel?: boolean;
  dashArray?: string;
  fillOpacity?: number;
  waveType?: string;
  fiboLevels?: number[];
  // Extended settings
  lineStyle?: "solid" | "dashed" | "dotted";
  showPrices?: boolean;
  showTimes?: boolean;
  fill?: boolean;
  fillColor?: string;
  fontSize?: number;
  fontFamily?: string;
  textColor?: string;
  backgroundColor?: string;
  // Fibonacci/Gann specific
  levels?: number[];
  angles?: number[];
  showGrid?: boolean;
  showMidlines?: boolean;
  showArcs?: boolean;
  showFans?: boolean;
  // Pitchfork specific
  showMedian?: boolean;
  showExtensions?: boolean;
  showChannels?: boolean;
  // Text specific
  bold?: boolean;
  italic?: boolean;
  alignment?: "left" | "center" | "right";
  [key: string]: unknown;
}

export type ToolSettings = BaseToolSettings;

export const DEFAULT_TOOL_SETTINGS: Record<string, ToolSettings> = {
  // Lines
  trendline: { color: "#3b82f6", lineWidth: 2, showLabel: true, lineStyle: "solid" },
  ray: { color: "#3b82f6", lineWidth: 2, showLabel: true, lineStyle: "solid" },
  extendedLine: { color: "#3b82f6", lineWidth: 2, showLabel: false, lineStyle: "solid" },
  horizontalRay: { color: "#22c55e", lineWidth: 1.5, showLabel: true },
  horizontal: { color: "#22c55e", lineWidth: 1.5, showLabel: true, lineStyle: "dashed" },
  vertical: { color: "#22c55e", lineWidth: 1.5, showLabel: true, lineStyle: "dashed" },
  angleLine: { color: "#3b82f6", lineWidth: 2, showLabel: false },
  disjointAngle: { color: "#3b82f6", lineWidth: 2, showLabel: false },

  // Shapes
  rectangle: { color: "#8b5cf6", lineWidth: 1.5, showLabel: false, fillOpacity: 0.1 },
  rotatedRectangle: { color: "#8b5cf6", lineWidth: 1.5, showLabel: false, fillOpacity: 0.1 },
  triangle: { color: "#8b5cf6", lineWidth: 1.5, showLabel: false, fillOpacity: 0.1 },
  ellipse: { color: "#8b5cf6", lineWidth: 1.5, showLabel: false, fillOpacity: 0.1 },
  arrow: { color: "#3b82f6", lineWidth: 2, showLabel: false },
  polyline: { color: "#3b82f6", lineWidth: 2, showLabel: false },
  parallelChannel: { color: "#8b5cf6", lineWidth: 1.5, showLabel: false, fillOpacity: 0.08 },
  priceRange: { color: "#f97316", lineWidth: 1.5, showLabel: true },

  // Fibonacci
  fibRetracement: { color: "#facc15", lineWidth: 1, showLabel: true, showPrices: true, levels: [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.618] },
  fibExtension: { color: "#facc15", lineWidth: 1, showLabel: true, showPrices: true, levels: [0, 0.382, 0.618, 0.786, 1, 1.272, 1.618, 2.0] },
  fibChannel: { color: "#facc15", lineWidth: 1, showLabel: true, fillOpacity: 0.05 },
  fibArcs: { color: "#facc15", lineWidth: 1, showLabel: true, fillOpacity: 0.05 },
  fibSpiral: { color: "#facc15", lineWidth: 1, showLabel: true },
  fibTimeZone: { color: "#facc15", lineWidth: 1, showLabel: true },

  // Gann
  gannBox: { color: "#f97316", lineWidth: 1.5, showLabel: true, showGrid: true, showMidlines: true, showArcs: true, showFans: true },
  gannFan: { color: "#f97316", lineWidth: 1.5, showLabel: true, showFans: true, angles: [45, 26.565, 18.435, 14.036, 7.125, 63.75, 71.565, 75.964, 82.875] },
  gannSquare: { color: "#f97316", lineWidth: 1.5, showLabel: true, showGrid: true },
  gannLine: { color: "#f97316", lineWidth: 2, showLabel: true },

  // Elliott Wave
  elliottWave: { color: "#f97316", lineWidth: 2, showLabel: true, waveType: "impulse" },
  harmonicABCD: { color: "#a855f7", lineWidth: 2, showLabel: true, fiboLevels: [0.618, 1.272] },
  xabcdPattern: { color: "#a855f7", lineWidth: 2, showLabel: true, fiboLevels: [0.618, 0.786, 1.272] },

  // Pitchfork
  pitchfork: { color: "#f97316", lineWidth: 2, showLabel: false, showMedian: true, showExtensions: true },
  schiffPitchfork: { color: "#f97316", lineWidth: 2, showLabel: false, showMedian: true },
  modifiedPitchfork: { color: "#f97316", lineWidth: 2, showLabel: false, showMedian: true, showChannels: true },
  insidePitchfork: { color: "#f97316", lineWidth: 2, showLabel: false, showMedian: true },

  // Text & Notes
  text: { color: "#ffffff", lineWidth: 1, fontSize: 12, fontFamily: "Arial", textColor: "#ffffff", backgroundColor: "#3b82f640", bold: false, italic: false },
  callout: { color: "#f59e0b", lineWidth: 2, fontSize: 11, fontFamily: "Arial", textColor: "#ffffff", backgroundColor: "#f59e0b40", fillOpacity: 0.15 },
  note: { color: "#fbbf24", lineWidth: 1, fontSize: 10, fontFamily: "Arial", textColor: "#ffffff", backgroundColor: "#fbbf2440", fillOpacity: 0.1 },
  balloon: { color: "#ec4899", lineWidth: 1, fontSize: 11, fontFamily: "Arial", textColor: "#ffffff", backgroundColor: "#ec489940", fillOpacity: 0.1 },
  anchoredText: { color: "#ffffff", lineWidth: 1, fontSize: 12, fontFamily: "Arial", textColor: "#ffffff", bold: true },

  // Measurement
  ruler: { color: "#facc15", lineWidth: 2, showLabel: true, lineStyle: "dashed" },
  crossline: { color: "#6b7280", lineWidth: 1, showLabel: true },
  dateRange: { color: "#6b7280", lineWidth: 1, showLabel: true, showTimes: true },
  priceRangeTool: { color: "#f97316", lineWidth: 1, showLabel: true, showPrices: true },
  riskReward: { color: "#22c55e", lineWidth: 1.5, showLabel: true },

  // Position & Forecast
  longPosition: { color: "#16a34a", lineWidth: 1.5, showLabel: true, fillOpacity: 0.12 },
  shortPosition: { color: "#dc2626", lineWidth: 1.5, showLabel: true, fillOpacity: 0.12 },
  forecast: { color: "#2563eb", lineWidth: 2, showLabel: true, lineStyle: "dashed" },
};

const TOOL_TITLE_KEYS: Record<string, TranslationKey> = {
  trendline: "trendline",
  ray: "ray",
  extendedLine: "extendedLine",
  horizontalRay: "horizontalRay",
  horizontal: "horizontalLine",
  vertical: "verticalLine",
  angleLine: "trendAngle",
  disjointAngle: "disjointChannel",
  rectangle: "rectangle",
  rotatedRectangle: "rotatedRectangle",
  triangle: "triangle",
  ellipse: "ellipse",
  arrow: "arrow",
  polyline: "polyline",
  parallelChannel: "parallelChannel",
  fibRetracement: "fibRetracement",
  fibExtension: "fibExtension",
  fibChannel: "fibChannel",
  fibArcs: "fibArcs",
  fibSpiral: "fibSpiral",
  fibTimeZone: "fibTimeZone",
  gannBox: "gannBox",
  gannFan: "gannFan",
  gannSquare: "gannSquare",
  gannLine: "gann",
  elliottWave: "elliottWave",
  harmonicABCD: "harmonicABCD",
  xabcdPattern: "xabcdPattern",
  pitchfork: "pitchfork",
  schiffPitchfork: "schiffPitchfork",
  modifiedPitchfork: "modifiedPitchfork",
  insidePitchfork: "insidePitchfork",
  text: "textNotes",
  callout: "callout",
  note: "note",
  balloon: "balloon",
  anchoredText: "anchoredText",
  ruler: "ruler",
  crossline: "crossLine",
  dateRange: "dateRangeTool",
  priceRange: "priceRange",
  riskReward: "riskReward",
  longPosition: "longPosition",
  shortPosition: "shortPosition",
  forecast: "forecast",
};

const FieldRow = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div className="flex items-center justify-between gap-3 py-1.5">
    <span className="text-xs text-gray-400 whitespace-nowrap">{label}</span>
    {children}
  </div>
);

interface Props {
  tool: string;
  settings: ToolSettings;
  onChange: (s: ToolSettings) => void;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLElement | null>;
}

const ToolSettingsPopup: React.FC<Props> = ({ tool, settings, onChange, onClose, anchorRef }) => {
  const { t } = useI18n();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!anchorRef?.current || !panelRef.current) return;
    const btn = anchorRef.current.getBoundingClientRect();
    panelRef.current.style.top = `${btn.top}px`;
    panelRef.current.style.left = `${btn.right + 8}px`;
  }, [anchorRef]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node) &&
          anchorRef?.current && !anchorRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose, anchorRef]);

  if (!settings) return null;
  const set = (key: string, value: unknown) => onChange({ ...settings, [key]: value });
  const titleKey = TOOL_TITLE_KEYS[tool];

  return (
    <div ref={panelRef} className="fixed z-[200] w-64 bg-gray-800 border border-gray-600 rounded-lg shadow-2xl p-3" style={{ minWidth: 220 }}>
      <div className="flex items-center justify-between mb-2 pb-2 border-b border-gray-700">
        <span className="text-sm font-semibold text-white">{titleKey ? t(titleKey) : tool}</span>
        <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors"><X size={14} /></button>
      </div>

      <FieldRow label={t("lineColor")}>
        <input type="color" value={settings.color} onChange={(e) => set("color", e.target.value)} className="w-8 h-6 rounded cursor-pointer border-0 bg-transparent" />
      </FieldRow>

      <FieldRow label={t("lineWidthPx")}>
        <input type="range" min="0.5" max="5" step="0.5" value={settings.lineWidth} onChange={(e) => set("lineWidth", parseFloat(e.target.value))} className="w-28 accent-blue-500" />
        <span className="text-xs text-gray-300 w-5 text-right">{settings.lineWidth}</span>
      </FieldRow>

      {settings.dashArray !== undefined && (
        <FieldRow label={t("dashStyle")}>
          <select value={settings.dashArray} onChange={(e) => set("dashArray", e.target.value)} className="bg-gray-700 text-white text-xs rounded px-2 py-1 border border-gray-600 focus:outline-none">
            {(["solid", "dashed", "dotted"] as const).map((v) => (<option key={v} value={v}>{t(v)}</option>))}
          </select>
        </FieldRow>
      )}

      {settings.showLabel !== undefined && (
        <FieldRow label={t("showLabel")}>
          <button onClick={() => set("showLabel", !settings.showLabel)} className={`w-10 h-5 rounded-full transition-colors ${settings.showLabel ? "bg-blue-600" : "bg-gray-600"}`}>
            <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showLabel ? "translate-x-5" : "translate-x-0"}`} />
          </button>
        </FieldRow>
      )}

      {settings.fillOpacity !== undefined && (
        <FieldRow label={t("fillOpacity")}>
          <input type="range" min="0" max="0.5" step="0.05" value={settings.fillOpacity} onChange={(e) => set("fillOpacity", parseFloat(e.target.value))} className="w-28 accent-blue-500" />
          <span className="text-xs text-gray-300 w-8 text-right">{Math.round((settings.fillOpacity ?? 0) * 100)}%</span>
        </FieldRow>
      )}

      {tool === "elliottWave" && (
        <FieldRow label={t("waveType")}>
          <div className="flex gap-1">
            <button onClick={() => set("waveType", "impulse")} className={`text-xs px-2 py-0.5 rounded transition-colors ${settings.waveType === "impulse" ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-300"}`}>1-2-3-4-5</button>
            <button onClick={() => set("waveType", "corrective")} className={`text-xs px-2 py-0.5 rounded transition-colors ${settings.waveType === "corrective" ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-300"}`}>A-B-C</button>
          </div>
        </FieldRow>
      )}

      {tool === "harmonicABCD" && settings.fiboLevels && (
        <>
          <div className="mt-2 text-xs text-gray-400 mb-1">{t("fiboRatio")}</div>
          {settings.fiboLevels.map((lv, i) => (
            <FieldRow key={i} label={["AB", "BC", "CD", "AD"][i] || `L${i}`}>
              <input type="number" min="0.1" max="3" step="0.001" value={lv} onChange={(e) => { const nl = [...(settings.fiboLevels ?? [])]; nl[i] = parseFloat(e.target.value) || lv; set("fiboLevels", nl); }} className="w-16 bg-gray-700 text-white text-xs rounded px-2 py-1 border border-gray-600 focus:outline-none" />
            </FieldRow>
          ))}
        </>
      )}

      {tool === "fibRetracement" && settings.levels && (
        <>
          <div className="mt-2 text-xs text-gray-400 mb-1">{t("fiboLevels")}</div>
          <div className="grid grid-cols-5 gap-1">
            {[0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.618, 2.0].map((lv) => {
              const active = (settings.levels ?? []).includes(lv);
              return (
                <button key={lv} onClick={() => { const next = active ? (settings.levels ?? []).filter((x) => x !== lv) : [...(settings.levels ?? []), lv].sort((a, b) => a - b); set("levels", next); }}
                  className={`text-xs py-0.5 rounded transition-colors ${active ? "bg-yellow-600 text-white" : "bg-gray-700 text-gray-400"}`}>{(lv * 100).toFixed(1)}</button>
              );
            })}
          </div>
        </>
      )}

      {/* Gann Box settings */}
      {(tool === "gannBox" || tool === "gannSquare") && (
        <>
          {settings.showGrid !== undefined && (
            <FieldRow label={t("showGrid") || "Show Grid"}>
              <button onClick={() => set("showGrid", !settings.showGrid)} className={`w-10 h-5 rounded-full transition-colors ${settings.showGrid ? "bg-blue-600" : "bg-gray-600"}`}>
                <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showGrid ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </FieldRow>
          )}
          {settings.showMidlines !== undefined && (
            <FieldRow label={t("showMidlines") || "Show Midlines"}>
              <button onClick={() => set("showMidlines", !settings.showMidlines)} className={`w-10 h-5 rounded-full transition-colors ${settings.showMidlines ? "bg-blue-600" : "bg-gray-600"}`}>
                <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showMidlines ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </FieldRow>
          )}
          {settings.showArcs !== undefined && (
            <FieldRow label={t("showArcs") || "Show Arcs"}>
              <button onClick={() => set("showArcs", !settings.showArcs)} className={`w-10 h-5 rounded-full transition-colors ${settings.showArcs ? "bg-blue-600" : "bg-gray-600"}`}>
                <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showArcs ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </FieldRow>
          )}
          {settings.showFans !== undefined && (
            <FieldRow label={t("showFans") || "Show Fans"}>
              <button onClick={() => set("showFans", !settings.showFans)} className={`w-10 h-5 rounded-full transition-colors ${settings.showFans ? "bg-blue-600" : "bg-gray-600"}`}>
                <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showFans ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </FieldRow>
          )}
        </>
      )}

      {/* Gann Fan settings */}
      {tool === "gannFan" && settings.angles && (
        <>
          <div className="mt-2 text-xs text-gray-400 mb-1">{t("gannAngles") || "Gann Angles"}</div>
          <div className="grid grid-cols-3 gap-1">
            {[45, 26.565, 18.435, 14.036, 7.125, 63.75, 71.565, 75.964, 82.875].map((angle) => {
              const active = (settings.angles ?? []).includes(angle);
              return (
                <button key={angle} onClick={() => {
                  const next = active
                    ? (settings.angles ?? []).filter((x) => x !== angle)
                    : [...(settings.angles ?? []), angle].sort((a, b) => a - b);
                  set("angles", next);
                }}
                  className={`text-xs py-0.5 rounded transition-colors ${active ? "bg-orange-600 text-white" : "bg-gray-700 text-gray-400"}`}>
                  {angle.toFixed(1)}°
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* Pitchfork settings */}
      {tool === "pitchfork" || tool === "schiffPitchfork" || tool === "modifiedPitchfork" || tool === "insidePitchfork" ? (
        <>
          {settings.showMedian !== undefined && (
            <FieldRow label={t("showMedian") || "Show Median"}>
              <button onClick={() => set("showMedian", !settings.showMedian)} className={`w-10 h-5 rounded-full transition-colors ${settings.showMedian ? "bg-blue-600" : "bg-gray-600"}`}>
                <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showMedian ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </FieldRow>
          )}
          {settings.showExtensions !== undefined && (
            <FieldRow label={t("showExtensions") || "Show Extensions"}>
              <button onClick={() => set("showExtensions", !settings.showExtensions)} className={`w-10 h-5 rounded-full transition-colors ${settings.showExtensions ? "bg-blue-600" : "bg-gray-600"}`}>
                <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showExtensions ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </FieldRow>
          )}
          {settings.showChannels !== undefined && (
            <FieldRow label={t("showChannels") || "Show Channels"}>
              <button onClick={() => set("showChannels", !settings.showChannels)} className={`w-10 h-5 rounded-full transition-colors ${settings.showChannels ? "bg-blue-600" : "bg-gray-600"}`}>
                <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showChannels ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </FieldRow>
          )}
        </>
      ) : null}

      {/* Text tool settings */}
      {(tool === "text" || tool === "callout" || tool === "note" || tool === "balloon") && (
        <>
          {settings.fontSize !== undefined && (
            <FieldRow label={t("fontSize") || "Font Size"}>
              <input type="range" min="8" max="24" step="1" value={settings.fontSize} onChange={(e) => set("fontSize", parseInt(e.target.value))} className="w-28 accent-blue-500" />
              <span className="text-xs text-gray-300 w-6 text-right">{settings.fontSize}px</span>
            </FieldRow>
          )}
          {settings.textColor !== undefined && (
            <FieldRow label={t("textColor") || "Text Color"}>
              <input type="color" value={settings.textColor} onChange={(e) => set("textColor", e.target.value)} className="w-8 h-6 rounded cursor-pointer border-0 bg-transparent" />
            </FieldRow>
          )}
          {settings.backgroundColor !== undefined && (
            <FieldRow label={t("backgroundColor") || "Background"}>
              <input type="color" value={settings.backgroundColor} onChange={(e) => set("backgroundColor", e.target.value)} className="w-8 h-6 rounded cursor-pointer border-0 bg-transparent" />
            </FieldRow>
          )}
          {settings.bold !== undefined && (
            <FieldRow label={t("bold") || "Bold"}>
              <button onClick={() => set("bold", !settings.bold)} className={`w-10 h-5 rounded-full transition-colors ${settings.bold ? "bg-blue-600" : "bg-gray-600"}`}>
                <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.bold ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </FieldRow>
          )}
          {settings.italic !== undefined && (
            <FieldRow label={t("italic") || "Italic"}>
              <button onClick={() => set("italic", !settings.italic)} className={`w-10 h-5 rounded-full transition-colors ${settings.italic ? "bg-blue-600" : "bg-gray-600"}`}>
                <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.italic ? "translate-x-5" : "translate-x-0"}`} />
              </button>
            </FieldRow>
          )}
        </>
      )}

      {/* Show Prices toggle for Fibonacci tools */}
      {(tool === "fibRetracement" || tool === "fibExtension" || tool === "priceRangeTool") && settings.showPrices !== undefined && (
        <FieldRow label={t("showPrices") || "Show Prices"}>
          <button onClick={() => set("showPrices", !settings.showPrices)} className={`w-10 h-5 rounded-full transition-colors ${settings.showPrices ? "bg-blue-600" : "bg-gray-600"}`}>
            <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showPrices ? "translate-x-5" : "translate-x-0"}`} />
          </button>
        </FieldRow>
      )}

      {/* Show Times toggle for time-based tools */}
      {(tool === "dateRange" || tool === "fibTimeZone") && settings.showTimes !== undefined && (
        <FieldRow label={t("showTimes") || "Show Times"}>
          <button onClick={() => set("showTimes", !settings.showTimes)} className={`w-10 h-5 rounded-full transition-colors ${settings.showTimes ? "bg-blue-600" : "bg-gray-600"}`}>
            <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${settings.showTimes ? "translate-x-5" : "translate-x-0"}`} />
          </button>
        </FieldRow>
      )}
    </div>
  );
};

export default ToolSettingsPopup;
