import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Move, Play, RotateCcw, X } from "lucide-react";
import { INDICATORS } from "@/features/chart/IndicatorPanel";
import { TOOL_GROUPS } from "@/features/drawing/components/DrawingToolbar";
import { useI18n } from "@/i18n";
import type { Drawing, IndicatorSettings, TimeframeKey } from "@/types";

export interface AiActionCall {
  name: string;
  arguments?: Record<string, unknown>;
  reason?: string | null;
  requires_approval?: boolean;
}

export interface AiActionDefinition {
  name: string;
  description: string;
  parameters: {
    type: "object";
    properties: Record<string, AiActionParameter>;
    required?: string[];
  };
}

interface AiActionParameter {
  type: "string" | "number" | "integer" | "boolean" | "array" | "object";
  enum?: string[];
  default?: unknown;
  description?: string;
}

export interface AiChartActionController {
  setIndicatorVisible: (indicator: string, visible: boolean) => void;
  toggleIndicator: (indicator: string) => void;
}

interface AiActionRuntime {
  setDrawingTool?: (tool: string) => void;
  addDrawing?: (drawing: Drawing) => void;
  clearDrawings?: () => void;
  setTimeframe?: (timeframe: TimeframeKey) => void;
  setSymbol?: (symbol: string) => void;
  chartController?: AiChartActionController | null;
}

interface AiActionContextValue {
  definitions: AiActionDefinition[];
  executeAction: (call: AiActionCall) => Promise<{ ok: boolean; detail: string }>;
  openDebugWindow: () => void;
  setRuntime: (runtime: Partial<AiActionRuntime>) => void;
}

const AiActionContext = createContext<AiActionContextValue | null>(null);

const SECTION_SELECTORS: Record<string, string> = {
  chart: "[data-ai-section='chart']",
  ai: "[data-ai-section='ai-panel']",
  rightPanel: "[data-ai-section='right-panel']",
  watchlist: "[data-ai-section='right-panel']",
  drawingTools: "[data-ai-section='drawing-toolbar']",
  settings: "[data-ai-section='settings-modal']",
};

function drawingTools(): string[] {
  return TOOL_GROUPS.flatMap((group) => group.tools.map((tool) => tool.id));
}

function actionDefinitions(): AiActionDefinition[] {
  const indicators = INDICATORS.map((item) => item.key);
  const tools = drawingTools();
  return [
    {
      name: "add_indicator",
      description: "Show a supported chart indicator.",
      parameters: {
        type: "object",
        properties: { indicator: { type: "string", enum: indicators } },
        required: ["indicator"],
      },
    },
    {
      name: "remove_indicator",
      description: "Hide a supported chart indicator.",
      parameters: {
        type: "object",
        properties: { indicator: { type: "string", enum: indicators } },
        required: ["indicator"],
      },
    },
    {
      name: "toggle_indicator",
      description: "Toggle a supported chart indicator.",
      parameters: {
        type: "object",
        properties: { indicator: { type: "string", enum: indicators } },
        required: ["indicator"],
      },
    },
    {
      name: "draw_tool",
      description: "Select a drawing tool and optionally place a drawing.",
      parameters: {
        type: "object",
        properties: {
          tool: { type: "string", enum: tools },
          points: { type: "array", description: "JSON array of data points." },
          text: { type: "string" },
        },
        required: ["tool"],
      },
    },
    {
      name: "highlight_section",
      description: "Dim the UI except the target section and AI response area.",
      parameters: {
        type: "object",
        properties: {
          target: { type: "string", enum: Object.keys(SECTION_SELECTORS) },
          label: { type: "string" },
          message: { type: "string" },
        },
        required: ["target"],
      },
    },
    {
      name: "start_tour",
      description: "Start a user-paced LMView tour.",
      parameters: {
        type: "object",
        properties: {
          tour_id: { type: "string", default: "lmview-overview" },
          start_step: { type: "integer", default: 0 },
        },
      },
    },
    {
      name: "clear_ai_annotations",
      description: "Clear AI highlights and action overlays.",
      parameters: { type: "object", properties: {} },
    },
  ];
}

export function AiActionProvider({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const definitions = useMemo(actionDefinitions, []);
  const runtimeRef = useRef<AiActionRuntime>({});
  const [debugOpen, setDebugOpen] = useState(false);
  const [highlight, setHighlight] = useState<{ target: string; label?: string; message?: string } | null>(null);
  const [tourIndex, setTourIndex] = useState<number | null>(null);
  const [tourDone, setTourDone] = useState(false);

  const setRuntime = useCallback((runtime: Partial<AiActionRuntime>) => {
    runtimeRef.current = { ...runtimeRef.current, ...runtime };
  }, []);

  const executeAction = useCallback(async (call: AiActionCall) => {
    const args = call.arguments || {};
    const runtime = runtimeRef.current;
    switch (call.name) {
      case "add_indicator":
        runtime.chartController?.setIndicatorVisible(String(args.indicator), true);
        return { ok: true, detail: `Added indicator ${String(args.indicator)}` };
      case "remove_indicator":
        runtime.chartController?.setIndicatorVisible(String(args.indicator), false);
        return { ok: true, detail: `Removed indicator ${String(args.indicator)}` };
      case "toggle_indicator":
        runtime.chartController?.toggleIndicator(String(args.indicator));
        return { ok: true, detail: `Toggled indicator ${String(args.indicator)}` };
      case "draw_tool": {
        const tool = String(args.tool || "cursor");
        runtime.setDrawingTool?.(tool);
        const points = Array.isArray(args.points) ? args.points : [];
        if (points.length && runtime.addDrawing) {
          runtime.addDrawing({
            id: `ai-${Date.now()}`,
            tool,
            dataPoints: points as Drawing["dataPoints"],
            text: typeof args.text === "string" ? args.text : undefined,
            settings: { color: "#38bdf8", lineWidth: 2 },
          });
        }
        return { ok: true, detail: `Selected drawing tool ${tool}` };
      }
      case "highlight_section":
        setHighlight({
          target: String(args.target || "chart"),
          label: typeof args.label === "string" ? args.label : undefined,
          message: typeof args.message === "string" ? args.message : undefined,
        });
        return { ok: true, detail: `Highlighted ${String(args.target || "chart")}` };
      case "start_tour":
        setTourDone(false);
        setTourIndex(Number(args.start_step || 0));
        return { ok: true, detail: "Started tour" };
      case "clear_ai_annotations":
        setHighlight(null);
        setTourIndex(null);
        setTourDone(false);
        return { ok: true, detail: "Cleared AI annotations" };
      default:
        return { ok: false, detail: `Unsupported action: ${call.name}` };
    }
  }, []);

  useEffect(() => {
    const openDebug = () => setDebugOpen(true);
    window.addEventListener("lmview:open-ai-action-debug", openDebug);
    return () => window.removeEventListener("lmview:open-ai-action-debug", openDebug);
  }, []);

  const tourSteps = useMemo(
    () => [
      { target: "chart", label: t("tourChartTitle"), message: t("tourChartBody") },
      { target: "drawingTools", label: t("tourDrawingTitle"), message: t("tourDrawingBody") },
      { target: "rightPanel", label: t("tourRightPanelTitle"), message: t("tourRightPanelBody") },
      { target: "ai", label: t("tourAiTitle"), message: t("tourAiBody") },
    ],
    [t],
  );
  const activeTourStep = tourIndex !== null ? tourSteps[Math.min(tourIndex, tourSteps.length - 1)] : null;
  const activeHighlight = activeTourStep || highlight;

  return (
    <AiActionContext.Provider value={{ definitions, executeAction, openDebugWindow: () => setDebugOpen(true), setRuntime }}>
      {children}
      {activeHighlight && (
        <HighlightOverlay
          target={activeHighlight.target}
          label={activeHighlight.label}
          message={activeHighlight.message}
          onClose={() => {
            setHighlight(null);
            setTourIndex(null);
          }}
        />
      )}
      {tourIndex !== null && (
        <TourControls
          index={tourIndex}
          count={tourSteps.length}
          onPrev={() => setTourIndex((value) => Math.max(0, (value || 0) - 1))}
          onNext={() => {
            if (tourIndex >= tourSteps.length - 1) {
              setTourIndex(null);
              setHighlight(null);
              setTourDone(true);
            } else {
              setTourIndex(tourIndex + 1);
            }
          }}
          onClose={() => setTourIndex(null)}
        />
      )}
      {tourDone && (
        <TourRecap
          onReplay={() => {
            setTourDone(false);
            setTourIndex(0);
          }}
          onClose={() => setTourDone(false)}
        />
      )}
      {debugOpen && (
        <AiActionDebugWindow
          definitions={definitions}
          onRun={(call) => executeAction(call)}
          onClose={() => setDebugOpen(false)}
        />
      )}
    </AiActionContext.Provider>
  );
}

export function useAiActions(): AiActionContextValue {
  const context = useContext(AiActionContext);
  if (!context) {
    throw new Error("useAiActions must be used inside AiActionProvider");
  }
  return context;
}

function HighlightOverlay({
  target,
  label,
  message,
  onClose,
}: {
  target: string;
  label?: string;
  message?: string;
  onClose: () => void;
}) {
  const [rects, setRects] = useState<DOMRect[]>([]);
  const selector = SECTION_SELECTORS[target] || target;

  useEffect(() => {
    const update = () => {
      const targetEl = document.querySelector(selector);
      const aiEl = document.querySelector(SECTION_SELECTORS.ai);
      const next = [targetEl, aiEl]
        .filter((item): item is Element => Boolean(item))
        .map((item) => item.getBoundingClientRect())
        .filter((rect) => rect.width > 0 && rect.height > 0);
      setRects(next);
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [selector]);

  const cells = useMemo(() => dimCells(rects), [rects]);
  const primary = rects[0];

  return (
    <div className="pointer-events-none fixed inset-0 z-[680]">
      {cells.map((cell) => (
        <div
          key={cell.key}
          className="absolute bg-black/65 backdrop-blur-[1px]"
          style={{ left: cell.left, top: cell.top, width: cell.width, height: cell.height }}
        />
      ))}
      {rects.map((rect, index) => (
        <div
          key={`${rect.left}-${rect.top}-${index}`}
          className="absolute rounded border-2 border-sky-400 shadow-[0_0_0_1px_rgba(14,165,233,0.35)]"
          style={{
            left: rect.left - 4,
            top: rect.top - 4,
            width: rect.width + 8,
            height: rect.height + 8,
          }}
        />
      ))}
      {primary && (
        <div
          className="pointer-events-auto absolute max-w-xs rounded border border-sky-500/50 bg-gray-950 px-3 py-2 text-xs text-gray-100 shadow-2xl"
          style={{ left: Math.min(primary.left, window.innerWidth - 280), top: Math.min(primary.bottom + 10, window.innerHeight - 120) }}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              {label && <div className="font-semibold text-white">{label}</div>}
              {message && <div className="mt-1 leading-5 text-gray-300">{message}</div>}
            </div>
            <button type="button" onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white">
              <X size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function dimCells(holes: DOMRect[]) {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const xs = [0, width];
  const ys = [0, height];
  holes.forEach((rect) => {
    xs.push(Math.max(0, rect.left - 6), Math.min(width, rect.right + 6));
    ys.push(Math.max(0, rect.top - 6), Math.min(height, rect.bottom + 6));
  });
  const sx = [...new Set(xs)].sort((a, b) => a - b);
  const sy = [...new Set(ys)].sort((a, b) => a - b);
  const cells: Array<{ key: string; left: number; top: number; width: number; height: number }> = [];
  for (let xi = 0; xi < sx.length - 1; xi += 1) {
    for (let yi = 0; yi < sy.length - 1; yi += 1) {
      const left = sx[xi];
      const right = sx[xi + 1];
      const top = sy[yi];
      const bottom = sy[yi + 1];
      const cx = (left + right) / 2;
      const cy = (top + bottom) / 2;
      const insideHole = holes.some((rect) => cx >= rect.left - 6 && cx <= rect.right + 6 && cy >= rect.top - 6 && cy <= rect.bottom + 6);
      if (!insideHole) cells.push({ key: `${xi}-${yi}`, left, top, width: right - left, height: bottom - top });
    }
  }
  return cells;
}

function TourControls({
  index,
  count,
  onPrev,
  onNext,
  onClose,
}: {
  index: number;
  count: number;
  onPrev: () => void;
  onNext: () => void;
  onClose: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="fixed bottom-5 left-1/2 z-[700] flex -translate-x-1/2 items-center gap-2 rounded border border-gray-700 bg-gray-950 px-3 py-2 shadow-2xl">
      <span className="text-xs text-gray-400">{index + 1} / {count}</span>
      <button type="button" onClick={onPrev} disabled={index === 0} className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-200 disabled:opacity-40">{t("previous")}</button>
      <button type="button" onClick={onNext} className="rounded bg-blue-600 px-2 py-1 text-xs font-semibold text-white">{index === count - 1 ? t("finish") : t("next")}</button>
      <button type="button" onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white"><X size={14} /></button>
    </div>
  );
}

function TourRecap({ onReplay, onClose }: { onReplay: () => void; onClose: () => void }) {
  const { t } = useI18n();
  return (
    <div className="fixed bottom-5 right-5 z-[690] w-80 rounded border border-gray-700 bg-gray-950 p-3 text-sm text-gray-100 shadow-2xl">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-white">{t("tourRecapTitle")}</h3>
          <p className="mt-1 text-xs leading-5 text-gray-400">{t("tourRecapBody")}</p>
        </div>
        <button type="button" onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white"><X size={14} /></button>
      </div>
      <button type="button" onClick={onReplay} className="mt-3 inline-flex items-center gap-2 rounded bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white">
        <RotateCcw size={13} /> {t("replay")}
      </button>
    </div>
  );
}

function AiActionDebugWindow({
  definitions,
  onRun,
  onClose,
}: {
  definitions: AiActionDefinition[];
  onRun: (call: AiActionCall) => Promise<{ ok: boolean; detail: string }>;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const [selected, setSelected] = useState(definitions[0]?.name || "");
  const [params, setParams] = useState<Record<string, string>>({});
  const [result, setResult] = useState("");
  const [running, setRunning] = useState(false);
  const [pos, setPos] = useState({ x: 80, y: 80 });
  const dragRef = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  const definition = definitions.find((item) => item.name === selected) || definitions[0];

  const run = async () => {
    setRunning(true);
    try {
      const parsed = parseParams(definition, params);
      const output = await onRun({ name: definition.name, arguments: parsed });
      setResult(`${output.ok ? "success" : "error"}: ${output.detail}`);
    } catch (error) {
      setResult(`error: ${error instanceof Error ? error.message : "unknown"}`);
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    const onMove = (event: MouseEvent) => {
      if (!dragRef.current) return;
      setPos({
        x: dragRef.current.ox + event.clientX - dragRef.current.x,
        y: dragRef.current.oy + event.clientY - dragRef.current.y,
      });
    };
    const onUp = () => {
      dragRef.current = null;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  return (
    <div className="fixed z-[720] w-[min(460px,92vw)] rounded border border-gray-700 bg-gray-950 text-gray-100 shadow-2xl" style={{ left: pos.x, top: pos.y }}>
      <div
        className="flex cursor-move items-center justify-between border-b border-gray-800 px-3 py-2"
        onMouseDown={(event) => {
          dragRef.current = { x: event.clientX, y: event.clientY, ox: pos.x, oy: pos.y };
        }}
      >
        <div className="flex items-center gap-2 text-xs font-semibold"><Move size={14} /> {t("aiActionDebug")}</div>
        <button type="button" onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white"><X size={14} /></button>
      </div>
      <div className="space-y-3 p-3">
        <label className="block text-xs text-gray-400">
          {t("functionCall")}
          <select
            value={selected}
            onChange={(event) => {
              setSelected(event.target.value);
              setParams({});
              setResult("");
            }}
            className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-xs text-white"
          >
            {definitions.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}
          </select>
        </label>
        <div className="grid gap-2">
          {Object.entries(definition.parameters.properties).map(([key, schema]) => (
            <label key={key} className="block text-xs text-gray-400">
              {key}{definition.parameters.required?.includes(key) ? " *" : ""}
              {schema.enum ? (
                <select
                  value={params[key] ?? String(schema.default ?? schema.enum[0] ?? "")}
                  onChange={(event) => setParams((draft) => ({ ...draft, [key]: event.target.value }))}
                  className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-xs text-white"
                >
                  {schema.enum.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              ) : (
                <input
                  value={params[key] ?? String(schema.default ?? "")}
                  onChange={(event) => setParams((draft) => ({ ...draft, [key]: event.target.value }))}
                  className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-xs text-white"
                  placeholder={schema.type === "array" || schema.type === "object" ? "JSON" : schema.type}
                />
              )}
            </label>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={run} disabled={running} className="inline-flex items-center gap-2 rounded bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-60">
            <Play size={13} /> {t("run")}
          </button>
          <button type="button" onClick={() => { setParams({}); setResult(""); }} className="rounded border border-gray-700 px-2.5 py-1.5 text-xs text-gray-200">
            {t("reset")}
          </button>
        </div>
        <div className="min-h-8 rounded border border-gray-800 bg-gray-900 px-2 py-1.5 text-xs text-gray-300">
          {result || t("debugNoResult")}
        </div>
      </div>
    </div>
  );
}

function parseParams(definition: AiActionDefinition, params: Record<string, string>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, schema] of Object.entries(definition.parameters.properties)) {
    const raw = params[key] ?? schema.default;
    if (raw === undefined || raw === "") continue;
    if (schema.type === "number" || schema.type === "integer") out[key] = Number(raw);
    else if (schema.type === "boolean") out[key] = raw === "true";
    else if (schema.type === "array" || schema.type === "object") out[key] = typeof raw === "string" ? JSON.parse(raw || (schema.type === "array" ? "[]" : "{}")) : raw;
    else out[key] = String(raw);
  }
  for (const key of definition.parameters.required || []) {
    if (out[key] === undefined) throw new Error(`${key} required`);
  }
  return out;
}

export function buildIndicatorSettingsPatch(
  settings: Record<string, IndicatorSettings>,
  indicator: string,
  visible: boolean,
) {
  return {
    ...settings,
    [indicator]: {
      ...settings[indicator],
      visible,
    },
  };
}
