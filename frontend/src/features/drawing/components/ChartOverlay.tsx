import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useI18n } from "@/i18n";
import type { Drawing, DataPoint } from "@/types";
import { DEFAULT_TOOL_SETTINGS, type ToolSettings } from './ToolSettingsPopup';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';

const MULTI_CLICK_NEEDED: Record<string, boolean> = {
  elliottWave: true,
  harmonicABCD: true,
  xabcdPattern: true,
  parallelChannel: true,
  pitchfork: true,
  schiffPitchfork: true,
  modifiedPitchfork: true,
  insidePitchfork: true,
};

const DRAWING_HIT_TOLERANCE = 8; // pixels

interface ChartOverlayProps {
  activeTool: string;
  drawings: Drawing[];
  onAddDrawing: (drawing: Drawing) => void;
  onUpdateDrawing?: (id: string | number, updates: Partial<Drawing>) => void;
  onDeleteDrawing: (id: string | number) => void;
  toolSettings?: Record<string, ToolSettings>;
  chartApi: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
  magnetEnabled?: boolean;
  selectedDrawingIds?: (string | number)[];
  onSetSelectedDrawingIds?: (ids: (string | number)[]) => void;
  // Replay mode props
  isReplaySelectionMode?: boolean;
  onReplayStartSelect?: (timestamp: number) => void;
}

interface PixelPoint { x: number; y: number; }

const PATTERN_TOOLS = new Set(["harmonicABCD", "xabcdPattern", "elliottWave"]);
const PITCHFORK_TOOLS = new Set(["pitchfork", "schiffPitchfork", "modifiedPitchfork", "insidePitchfork"]);
const GANN_BOX_TOOLS = new Set(["gannBox", "gannSquare"]);
const DEFAULT_GANN_ANGLES = [45, 26.565, 18.435, 14.036, 7.125, 63.75, 71.565, 75.964, 82.875];

function getGannAngles(settings: Record<string, any>): number[] {
  const configured = settings.angles;
  if (!Array.isArray(configured)) return DEFAULT_GANN_ANGLES;
  const angles = configured.filter((value) => typeof value === "number" && Number.isFinite(value));
  return angles.length > 0 ? angles : DEFAULT_GANN_ANGLES;
}

function buildGannFanSegments(origin: PixelPoint, target: PixelPoint, settings: Record<string, any>) {
  const length = Math.max(Math.hypot(target.x - origin.x, target.y - origin.y), 120);
  const signX = target.x >= origin.x ? 1 : -1;
  const signY = target.y >= origin.y ? 1 : -1;
  return getGannAngles(settings).map((angle) => {
    const radians = (angle * Math.PI) / 180;
    return {
      start: origin,
      end: {
        x: origin.x + signX * Math.cos(radians) * length,
        y: origin.y + signY * Math.sin(radians) * length,
      },
      angle,
    };
  });
}

const getPatternLabels = (tool: string, settings: Record<string, any>): string[] => {
  if (tool === "xabcdPattern") return ["X", "A", "B", "C", "D"];
  if (tool === "harmonicABCD") return ["A", "B", "C", "D"];
  return (settings.waveType || "impulse") === "corrective"
    ? ["A", "B", "C", "D"]
    : ["0", "1", "2", "3", "4", "5"];
};

const ChartOverlay: React.FC<ChartOverlayProps> = ({
  activeTool,
  drawings,
  onAddDrawing,
  onUpdateDrawing,
  onDeleteDrawing, // Used in keyboard shortcuts via parent
  toolSettings,
  chartApi,
  candleSeries,
  magnetEnabled = false,
  selectedDrawingIds = [],
  onSetSelectedDrawingIds,
  isReplaySelectionMode = false,
  onReplayStartSelect,
}) => {
  void onUpdateDrawing;
  void onDeleteDrawing; // Used via keyboard shortcuts in parent
  const { t } = useI18n();
  void t; // May be used in future for tooltips
  const svgRef = useRef<SVGSVGElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startDataPoint, setStartDataPoint] = useState<DataPoint | null>(null);
  const [currentDataPoint, setCurrentDataPoint] = useState<DataPoint | null>(null);
  const [multiDataPoints, setMultiDataPoints] = useState<DataPoint[]>([]);
  const [textInput, setTextInput] = useState<PixelPoint | null>(null);
  const [hoveredDrawingId, setHoveredDrawingId] = useState<string | number | null>(null);
  const [, setRedrawCounter] = useState(0);
  const [panState, setPanState] = useState<{
    startX: number;
    range: { from: number; to: number };
  } | null>(null);

  // Anchor dragging state
  const [draggingAnchor, setDraggingAnchor] = useState<{
    drawingId: string | number;
    pointIndex: number;
  } | null>(null);

  const isMultiClick = MULTI_CLICK_NEEDED[activeTool] || false;

  const activeSettings = useCallback((): ToolSettings => {
    return (toolSettings && toolSettings[activeTool]) || DEFAULT_TOOL_SETTINGS[activeTool] || { color: '#3b82f6', lineWidth: 2 };
  }, [toolSettings, activeTool]);

  const requiredPoints = useCallback((): number => {
    if (activeTool === 'elliottWave') {
      const wt = activeSettings().waveType || 'impulse';
      return wt === 'corrective' ? 4 : 6;
    }
    if (activeTool === 'harmonicABCD') return 4;
    if (activeTool === 'xabcdPattern') return 5;
    if (activeTool === 'parallelChannel') return 3;
    if (PITCHFORK_TOOLS.has(activeTool)) return 3;
    return 0;
  }, [activeTool, activeSettings]);

  // ══════════════════════════════════════════════════════════════
  // COORDINATE CONVERSION (Data-space ↔ Pixel-space)
  // CRITICAL: Never fallback to old pixel values. Return null if conversion fails.
  // ══════════════════════════════════════════════════════════════

  const dataToPixel = useCallback((dataPoint: DataPoint): PixelPoint | null => {
    if (!chartApi || !candleSeries) return null;

    const x = chartApi.timeScale().timeToCoordinate(dataPoint.time as any);
    const y = candleSeries.priceToCoordinate(dataPoint.price);

    // CRITICAL: If either coordinate is null, return null (drawing is off-screen)
    // DO NOT fallback to previous pixel values
    if (x === null || y === null) return null;

    return { x, y };
  }, [chartApi, candleSeries]);

  const pixelToData = useCallback((pixel: PixelPoint): DataPoint | null => {
    if (!chartApi || !candleSeries) return null;

    const time = chartApi.timeScale().coordinateToTime(pixel.x);
    const price = candleSeries.coordinateToPrice(pixel.y);

    if (time === null || price === null) return null;

    return { time: time as number, price };
  }, [chartApi, candleSeries]);

  const priceToY = useCallback((price: number): number | null => {
    if (!candleSeries) return null;
    return candleSeries.priceToCoordinate(price);
  }, [candleSeries]);

  const timeToX = useCallback((time: number): number | null => {
    if (!chartApi) return null;
    return chartApi.timeScale().timeToCoordinate(time as any);
  }, [chartApi]);

  // ══════════════════════════════════════════════════════════════
  // HIT TESTING FOR ERASER
  // ══════════════════════════════════════════════════════════════

  const distanceToLine = useCallback((point: PixelPoint, p1: PixelPoint, p2: PixelPoint): number => {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const lengthSquared = dx * dx + dy * dy;

    if (lengthSquared === 0) {
      // p1 and p2 are the same point
      return Math.sqrt((point.x - p1.x) ** 2 + (point.y - p1.y) ** 2);
    }

    // Calculate projection parameter
    let t = ((point.x - p1.x) * dx + (point.y - p1.y) * dy) / lengthSquared;
    t = Math.max(0, Math.min(1, t));

    // Find closest point on line segment
    const closestX = p1.x + t * dx;
    const closestY = p1.y + t * dy;

    return Math.sqrt((point.x - closestX) ** 2 + (point.y - closestY) ** 2);
  }, []);

  const distanceToInfiniteLine = useCallback((point: PixelPoint, p1: PixelPoint, p2: PixelPoint): number => {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const length = Math.sqrt(dx * dx + dy * dy);

    if (length === 0) {
      return Math.sqrt((point.x - p1.x) ** 2 + (point.y - p1.y) ** 2);
    }

    return Math.abs(dy * point.x - dx * point.y + p2.x * p1.y - p2.y * p1.x) / length;
  }, []);

  const distanceToRay = useCallback((point: PixelPoint, p1: PixelPoint, p2: PixelPoint): number => {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const lengthSquared = dx * dx + dy * dy;

    if (lengthSquared === 0) {
      return Math.sqrt((point.x - p1.x) ** 2 + (point.y - p1.y) ** 2);
    }

    const t = ((point.x - p1.x) * dx + (point.y - p1.y) * dy) / lengthSquared;
    if (t < 0) {
      return Math.sqrt((point.x - p1.x) ** 2 + (point.y - p1.y) ** 2);
    }

    const projected = { x: p1.x + t * dx, y: p1.y + t * dy };
    return Math.sqrt((point.x - projected.x) ** 2 + (point.y - projected.y) ** 2);
  }, []);

  const hitTestDrawing = useCallback((drawing: Drawing, mousePixel: PixelPoint): boolean => {
    if (!drawing.dataPoints || drawing.dataPoints.length === 0) return false;

    const pixels = drawing.dataPoints.map(dp => dataToPixel(dp));

    switch (drawing.tool) {
      case 'horizontal': {
        // Horizontal line: check Y distance
        if (!pixels[0]) return false;
        return Math.abs(mousePixel.y - pixels[0].y) <= DRAWING_HIT_TOLERANCE;
      }

      case 'vertical': {
        // Vertical line: check X distance
        if (!pixels[0]) return false;
        return Math.abs(mousePixel.x - pixels[0].x) <= DRAWING_HIT_TOLERANCE;
      }

      case 'rectangle':
      case 'gannBox':
      case 'gannSquare': {
        // Rectangle: check if near border or inside
        if (pixels.length < 2 || !pixels[0] || !pixels[1]) return false;
        const [p1, p2] = pixels;
        const left = Math.min(p1.x, p2.x);
        const right = Math.max(p1.x, p2.x);
        const top = Math.min(p1.y, p2.y);
        const bottom = Math.max(p1.y, p2.y);

        // Check if inside
        const inside = mousePixel.x >= left && mousePixel.x <= right &&
                      mousePixel.y >= top && mousePixel.y <= bottom;

        if (inside) return true;

        // Check borders
        const nearLeft = Math.abs(mousePixel.x - left) <= DRAWING_HIT_TOLERANCE &&
                        mousePixel.y >= top - DRAWING_HIT_TOLERANCE &&
                        mousePixel.y <= bottom + DRAWING_HIT_TOLERANCE;
        const nearRight = Math.abs(mousePixel.x - right) <= DRAWING_HIT_TOLERANCE &&
                         mousePixel.y >= top - DRAWING_HIT_TOLERANCE &&
                         mousePixel.y <= bottom + DRAWING_HIT_TOLERANCE;
        const nearTop = Math.abs(mousePixel.y - top) <= DRAWING_HIT_TOLERANCE &&
                       mousePixel.x >= left - DRAWING_HIT_TOLERANCE &&
                       mousePixel.x <= right + DRAWING_HIT_TOLERANCE;
        const nearBottom = Math.abs(mousePixel.y - bottom) <= DRAWING_HIT_TOLERANCE &&
                          mousePixel.x >= left - DRAWING_HIT_TOLERANCE &&
                          mousePixel.x <= right + DRAWING_HIT_TOLERANCE;

        return nearLeft || nearRight || nearTop || nearBottom;
      }

      case 'circle': {
        if (pixels.length < 2 || !pixels[0] || !pixels[1]) return false;
        const [p1, p2] = pixels;
        const cx = (p1.x + p2.x) / 2;
        const cy = (p1.y + p2.y) / 2;
        const rx = Math.abs(p2.x - p1.x) / 2 || 1;
        const ry = Math.abs(p2.y - p1.y) / 2 || 1;
        const normalized = ((mousePixel.x - cx) ** 2) / (rx ** 2) + ((mousePixel.y - cy) ** 2) / (ry ** 2);
        return normalized <= 1.15;
      }

      case 'triangle': {
        if (pixels.length < 2 || !pixels[0] || !pixels[1]) return false;
        const [p1, p2] = pixels;
        const left = Math.min(p1.x, p2.x);
        const right = Math.max(p1.x, p2.x);
        const top = Math.min(p1.y, p2.y);
        const bottom = Math.max(p1.y, p2.y);
        return mousePixel.x >= left - DRAWING_HIT_TOLERANCE &&
          mousePixel.x <= right + DRAWING_HIT_TOLERANCE &&
          mousePixel.y >= top - DRAWING_HIT_TOLERANCE &&
          mousePixel.y <= bottom + DRAWING_HIT_TOLERANCE;
      }

      case 'longPosition':
      case 'shortPosition': {
        if (pixels.length < 2 || !pixels[0] || !pixels[1]) return false;
        const [p1, p2] = pixels;
        const left = Math.min(p1.x, p2.x);
        const right = Math.max(p1.x, p2.x);
        const top = Math.min(p1.y, p2.y);
        const bottom = Math.max(p1.y, p2.y);
        return mousePixel.x >= left - DRAWING_HIT_TOLERANCE &&
          mousePixel.x <= right + DRAWING_HIT_TOLERANCE &&
          mousePixel.y >= top - DRAWING_HIT_TOLERANCE &&
          mousePixel.y <= bottom + DRAWING_HIT_TOLERANCE;
      }

      case 'text': {
        // Text: check bounding box
        if (!pixels[0]) return false;
        const text = drawing.text || '';
        const width = text.length * 7 + 8;
        const height = 20;
        return mousePixel.x >= pixels[0].x - 2 &&
               mousePixel.x <= pixels[0].x + width &&
               mousePixel.y >= pixels[0].y - 14 &&
               mousePixel.y <= pixels[0].y + height - 14;
      }

      default: {
        // Trendline, ray, arrow, etc: check distance to line
        const validPixels = pixels.filter(p => p !== null) as PixelPoint[];
        if (validPixels.length < 2) return false;

        if (PATTERN_TOOLS.has(drawing.tool)) {
          const nearAnchor = validPixels.some((point) =>
            Math.sqrt((mousePixel.x - point.x) ** 2 + (mousePixel.y - point.y) ** 2) <= DRAWING_HIT_TOLERANCE,
          );
          if (nearAnchor) return true;
        }

        if (drawing.tool === 'extendedLine') {
          return distanceToInfiniteLine(mousePixel, validPixels[0], validPixels[1]) <= DRAWING_HIT_TOLERANCE;
        }

        if (drawing.tool === 'ray') {
          return distanceToRay(mousePixel, validPixels[0], validPixels[1]) <= DRAWING_HIT_TOLERANCE;
        }

        if (drawing.tool === 'parallelChannel') {
          if (validPixels.length < 3) return false;
          const [p1, p2, p3] = validPixels;
          // Hit test both lines of the channel
          const hit1 = distanceToLine(mousePixel, p1, p2) <= DRAWING_HIT_TOLERANCE;
          // Calculate parallel line from p3 offset
          const dx = p2.x - p1.x, dy = p2.y - p1.y;
          const len = Math.sqrt(dx * dx + dy * dy);
          if (len === 0) return false;
          const nx = -dy / len, ny = dx / len;
          const dot = (p3.x - p1.x) * nx + (p3.y - p1.y) * ny;
          const q1 = { x: p1.x + nx * dot, y: p1.y + ny * dot };
          const q2 = { x: p2.x + nx * dot, y: p2.y + ny * dot };
          const hit2 = distanceToLine(mousePixel, q1, q2) <= DRAWING_HIT_TOLERANCE;
          return hit1 || hit2;
        }

        if (PITCHFORK_TOOLS.has(drawing.tool)) {
          if (validPixels.length < 3) return false;
          const [pA, pB, pC] = validPixels;
          const mid = { x: (pB.x + pC.x) / 2, y: (pB.y + pC.y) / 2 };
          const hitMedian = distanceToInfiniteLine(mousePixel, pA, mid) <= DRAWING_HIT_TOLERANCE;
          const hitFork1 = distanceToInfiniteLine(mousePixel, pB, pC) <= DRAWING_HIT_TOLERANCE;
          const hitAnchors = validPixels.some(p =>
            Math.sqrt((mousePixel.x - p.x) ** 2 + (mousePixel.y - p.y) ** 2) <= DRAWING_HIT_TOLERANCE
          );
          return hitMedian || hitFork1 || hitAnchors;
        }

        if (drawing.tool === 'gannFan') {
          const segments = buildGannFanSegments(validPixels[0], validPixels[1], drawing.settings || {});
          const hitFan = segments.some((segment) =>
            distanceToRay(mousePixel, segment.start, segment.end) <= DRAWING_HIT_TOLERANCE,
          );
          const hitAnchors = validPixels.some(p =>
            Math.sqrt((mousePixel.x - p.x) ** 2 + (mousePixel.y - p.y) ** 2) <= DRAWING_HIT_TOLERANCE
          );
          return hitFan || hitAnchors;
        }

        for (let i = 0; i < validPixels.length - 1; i++) {
          const dist = distanceToLine(mousePixel, validPixels[i], validPixels[i + 1]);
          if (dist <= DRAWING_HIT_TOLERANCE) return true;
        }
        return false;
      }
    }
  }, [dataToPixel, distanceToInfiniteLine, distanceToLine, distanceToRay]);

  // ══════════════════════════════════════════════════════════════
  // MAGNET SNAP
  // ══════════════════════════════════════════════════════════════

  const magneticSnap = useCallback((dataPoint: DataPoint): DataPoint => {
    if (!magnetEnabled) return dataPoint;
    // TODO: Implement snap to OHLC
    return dataPoint;
  }, [magnetEnabled]);

  // ══════════════════════════════════════════════════════════════
  // MOUSE EVENT HANDLERS
  // ══════════════════════════════════════════════════════════════

  const getSVGPoint = useCallback((e: React.MouseEvent): PixelPoint => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const beginOverlayPan = useCallback((pixel: PixelPoint) => {
    if (!chartApi) return false;
    const range = chartApi.timeScale().getVisibleLogicalRange();
    if (!range) return false;

    setPanState({
      startX: pixel.x,
      range: { from: range.from, to: range.to },
    });
    return true;
  }, [chartApi]);

  const handleOverlayPan = useCallback((e: React.MouseEvent) => {
    if (!panState || !chartApi || !svgRef.current) return;

    const pixel = getSVGPoint(e);
    const width = Math.max(svgRef.current.clientWidth, 1);
    const visibleBars = panState.range.to - panState.range.from;
    const logicalShift = -((pixel.x - panState.startX) / width) * visibleBars;

    chartApi.timeScale().setVisibleLogicalRange({
      from: panState.range.from + logicalShift,
      to: panState.range.to + logicalShift,
    });
  }, [chartApi, getSVGPoint, panState]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (!chartApi || !svgRef.current) return;

    const timeScale = chartApi.timeScale();
    const range = timeScale.getVisibleLogicalRange();
    if (!range) return;

    e.preventDefault();
    e.stopPropagation();

    const width = Math.max(svgRef.current.clientWidth, 1);
    const span = Math.max(range.to - range.from, 1);

    if (e.ctrlKey || e.metaKey) {
      const rect = svgRef.current.getBoundingClientRect();
      const anchorRatio = Math.max(0, Math.min(1, (e.clientX - rect.left) / width));
      const anchor = range.from + span * anchorRatio;
      const scale = e.deltaY > 0 ? 1.15 : 0.85;

      timeScale.setVisibleLogicalRange({
        from: anchor - (anchor - range.from) * scale,
        to: anchor + (range.to - anchor) * scale,
      });
      return;
    }

    const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (delta === 0) return;

    const logicalShift = (delta / width) * span;
    timeScale.setVisibleLogicalRange({
      from: range.from + logicalShift,
      to: range.to + logicalShift,
    });
  }, [chartApi]);

  const handleMultiClick = useCallback((e: React.MouseEvent) => {
    const pixel = getSVGPoint(e);
    const dataPoint = pixelToData(pixel);
    if (!dataPoint) return;

    const snapped = magneticSnap(dataPoint);
    const needed = requiredPoints();
    const next = [...multiDataPoints, snapped];

    if (next.length >= needed) {
      onAddDrawing({
        id: Date.now(),
        tool: activeTool,
        dataPoints: next,
        settings: activeSettings(),
      });
      setMultiDataPoints([]);
      setCurrentDataPoint(null);
    } else {
      setMultiDataPoints(next);
      setCurrentDataPoint(snapped);
    }
  }, [multiDataPoints, requiredPoints, activeTool, getSVGPoint, pixelToData, magneticSnap, onAddDrawing, activeSettings]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const pixel = getSVGPoint(e);

    if (e.button === 1 || e.button === 2 || e.shiftKey) {
      e.preventDefault();
      beginOverlayPan(pixel);
      return;
    }

    // Replay selection mode: click on candle to start replay from that point
    if (isReplaySelectionMode && onReplayStartSelect) {
      const dataPoint = pixelToData(pixel);
      if (dataPoint) {
        onReplayStartSelect(dataPoint.time);
      }
      return;
    }

    // Eraser mode: delete drawing on click
    if (activeTool === 'eraser') {
      for (const d of [...drawings].reverse()) {
        if (d.hidden || d.locked) continue;
        if (hitTestDrawing(d, pixel)) {
          onDeleteDrawing(d.id);
          return;
        }
      }
      return;
    }

    if (activeTool === 'cursor') {
      // Check if clicking on a drawing for selection
      let clickedDrawingId: string | number | null = null;

      for (const d of [...drawings].reverse()) {
        if (d.hidden || d.locked) continue;
        if (hitTestDrawing(d, pixel)) {
          clickedDrawingId = d.id;
          break;
        }
      }

      if (clickedDrawingId && onSetSelectedDrawingIds) {
        onSetSelectedDrawingIds([clickedDrawingId]);
      } else if (onSetSelectedDrawingIds) {
        onSetSelectedDrawingIds([]);
        beginOverlayPan(pixel);
      }
      return;
    }

    if (activeTool === 'text') {
      setTextInput(getSVGPoint(e));
      return;
    }

    if (isMultiClick) {
      handleMultiClick(e);
      return;
    }

    const dataPoint = pixelToData(pixel);
    if (!dataPoint) return;

    const snapped = magneticSnap(dataPoint);
    setStartDataPoint(snapped);
    setCurrentDataPoint(snapped);
    setIsDrawing(true);
  }, [activeTool, getSVGPoint, pixelToData, magneticSnap, isMultiClick, handleMultiClick, drawings, hitTestDrawing, onDeleteDrawing, onSetSelectedDrawingIds, isReplaySelectionMode, onReplayStartSelect, beginOverlayPan]);

  // ══════════════════════════════════════════════════════════════
  // ANCHOR DRAGGING HANDLERS
  // ══════════════════════════════════════════════════════════════

  const handleAnchorMouseDown = useCallback((e: React.MouseEvent, drawingId: string | number, pointIndex: number) => {
    e.stopPropagation();
    setDraggingAnchor({ drawingId, pointIndex });
  }, []);

  const handleAnchorDrag = useCallback((e: React.MouseEvent) => {
    if (!draggingAnchor || !onUpdateDrawing) return;

    const pixel = getSVGPoint(e);
    const dataPoint = pixelToData(pixel);
    if (!dataPoint) return;

    const drawing = drawings.find(d => d.id === draggingAnchor.drawingId);
    if (!drawing || drawing.locked || !drawing.dataPoints) return;

    // Update the specific data point
    const newDataPoints = [...drawing.dataPoints];
    newDataPoints[draggingAnchor.pointIndex] = magneticSnap(dataPoint);

    onUpdateDrawing(drawing.id, { dataPoints: newDataPoints });
  }, [draggingAnchor, drawings, getSVGPoint, pixelToData, magneticSnap, onUpdateDrawing]);

  const handleAnchorMouseUp = useCallback(() => {
    setDraggingAnchor(null);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const pixel = getSVGPoint(e);

    if (panState) {
      handleOverlayPan(e);
      return;
    }

    // Handle anchor dragging
    if (draggingAnchor) {
      handleAnchorDrag(e);
      return;
    }

    // Eraser mode: highlight drawing on hover
    if (activeTool === 'eraser') {
      let foundId: string | number | null = null;
      for (const d of [...drawings].reverse()) {
        if (d.hidden || d.locked) continue;
        if (hitTestDrawing(d, pixel)) {
          foundId = d.id;
          break;
        }
      }
      setHoveredDrawingId(foundId);
      return;
    }

    const dataPoint = pixelToData(pixel);
    if (!dataPoint) return;

    const snapped = magneticSnap(dataPoint);

    if (isMultiClick && multiDataPoints.length > 0) {
      setCurrentDataPoint(snapped);
      return;
    }

    if (!isDrawing) return;
    setCurrentDataPoint(snapped);
  }, [isDrawing, isMultiClick, multiDataPoints.length, getSVGPoint, pixelToData, magneticSnap, activeTool, drawings, hitTestDrawing, draggingAnchor, handleAnchorDrag, panState, handleOverlayPan]);

  const handleMouseUp = useCallback(() => {
    if (panState) {
      setPanState(null);
      return;
    }

    // Handle anchor drag end
    if (draggingAnchor) {
      handleAnchorMouseUp();
      return;
    }

    if (!isDrawing || !startDataPoint || !currentDataPoint) return;

    onAddDrawing({
      id: Date.now(),
      tool: activeTool,
      dataPoints: [startDataPoint, currentDataPoint],
      settings: activeSettings(),
    });

    setIsDrawing(false);
    setStartDataPoint(null);
    setCurrentDataPoint(null);
  }, [isDrawing, startDataPoint, currentDataPoint, activeTool, onAddDrawing, activeSettings, draggingAnchor, handleAnchorMouseUp, panState]);

  const handleTextSubmit = useCallback((text: string) => {
    if (!textInput || !text) {
      setTextInput(null);
      return;
    }

    const dataPoint = pixelToData(textInput);
    if (!dataPoint) {
      setTextInput(null);
      return;
    }

    onAddDrawing({
      id: Date.now(),
      tool: 'text',
      dataPoints: [dataPoint],
      text,
      settings: activeSettings(),
    });
    setTextInput(null);
  }, [textInput, pixelToData, onAddDrawing, activeSettings]);

  // ══════════════════════════════════════════════════════════════
  // REDRAW ON CHART CHANGES (zoom, pan, resize)
  // ══════════════════════════════════════════════════════════════

  useEffect(() => {
    if (!chartApi) return;

    const handleVisibleRangeChange = () => {
      setRedrawCounter(prev => prev + 1);
    };

    const timeScale = chartApi.timeScale();
    timeScale.subscribeVisibleLogicalRangeChange(handleVisibleRangeChange);

    return () => {
      timeScale.unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange);
    };
  }, [chartApi]);

  useEffect(() => {
    if (!svgRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      setRedrawCounter(prev => prev + 1);
    });

    resizeObserver.observe(svgRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  useEffect(() => {
    setIsDrawing(false);
    setStartDataPoint(null);
    setCurrentDataPoint(null);
    setMultiDataPoints([]);
    setTextInput(null);
    setHoveredDrawingId(null);
    setDraggingAnchor(null);
    setPanState(null);
  }, [activeTool]);

  // ══════════════════════════════════════════════════════════════
  // RENDERING FUNCTIONS
  // ══════════════════════════════════════════════════════════════

  const renderDrawing = useCallback((d: Drawing, isPreview = false) => {
    if (!d.dataPoints || d.dataPoints.length === 0) return null;

    // Convert data points to pixels
    // CRITICAL: If any point is off-screen (null), handle appropriately per tool type
    const pixels = d.dataPoints.map(dp => dataToPixel(dp));

    const opacity = isPreview ? 0.6 : (d.hidden ? 0.3 : 1);
    const key = isPreview ? 'preview' : d.id;
    const s = d.settings || {};
    const lw = s.lineWidth || 2;
    const color = s.color || '#3b82f6';
    const isSelected = selectedDrawingIds.includes(d.id);
    const isHovered = hoveredDrawingId === d.id;

    // Highlight if hovered in eraser mode
    const strokeWidth = isSelected ? lw + 1 : (isHovered ? lw + 2 : lw);
    const strokeColor = isSelected ? '#60a5fa' : (isHovered ? '#ef4444' : color);

    switch (d.tool) {
      case 'horizontal': {
        // Horizontal line: only needs price (y), can render even if time is off-screen
        const y = priceToY(d.dataPoints[0].price);
        if (y === null) return null;
        const price = d.dataPoints[0].price;

        return (
          <g key={key} opacity={opacity}>
            <line
              x1={0} y1={y} x2="100%" y2={y}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeDasharray="8 4"
            />
            {s.showLabel !== false && (
              <>
                <rect x={10} y={y - 18} width="60" height="16" rx="3" fill={`${color}30`} />
                <text x={40} y={y - 6} textAnchor="middle" fontSize="10" fill={color}>
                  {price.toFixed(2)}
                </text>
              </>
            )}
          </g>
        );
      }

      case 'vertical': {
        // Vertical line: only needs time (x), skip if off-screen
        const x = timeToX(d.dataPoints[0].time);
        if (x === null) return null;
        const time = d.dataPoints[0].time;
        const dateStr = new Date(time * 1000).toLocaleDateString();

        return (
          <g key={key} opacity={opacity}>
            <line
              x1={x} y1={0} x2={x} y2="100%"
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeDasharray="8 4"
            />
            {s.showLabel !== false && (
              <>
                <rect x={x - 40} y={10} width="80" height="16" rx="3" fill={`${color}30`} />
                <text x={x} y={22} textAnchor="middle" fontSize="10" fill={color}>
                  {dateStr}
                </text>
              </>
            )}
          </g>
        );
      }

      case 'text': {
        if (pixels.length < 1 || !pixels[0]) return null;
        const p = pixels[0];
        const text = d.text || '';
        const width = Math.max(44, text.length * 7 + 12);

        return (
          <g key={key} opacity={opacity}>
            <rect
              x={p.x - 4}
              y={p.y - 18}
              width={width}
              height={22}
              rx={4}
              fill={`${color}26`}
              stroke={isSelected ? strokeColor : `${color}80`}
              strokeWidth={isSelected ? 1.5 : 1}
            />
            <text x={p.x + 2} y={p.y - 3} fontSize="12" fill={strokeColor}>
              {text}
            </text>
            {isSelected && !isPreview && !d.locked && (
              <circle
                cx={p.x}
                cy={p.y}
                r="6"
                fill={strokeColor}
                stroke="white"
                strokeWidth="2"
                style={{ cursor: 'move' }}
                onMouseDown={(e) => handleAnchorMouseDown(e, d.id, 0)}
              />
            )}
          </g>
        );
      }

      default: {
        // Horizontal ray with arrows both sides
        if (d.tool === 'horizontalRay') {
          const y = priceToY(d.dataPoints[0].price);
          if (y === null) return null;
          return (
            <g key={key} opacity={opacity}>
              <line x1={0} y1={y} x2="100%" y2={y} stroke={strokeColor} strokeWidth={strokeWidth} strokeDasharray="8 4" />
              <polygon points={`8,${y - 6} 0,${y} 8,${y + 6}`} fill={strokeColor} />
              <polygon points={`16,${y - 6} 24,${y} 16,${y + 6}`} fill={strokeColor} transform="translate(-24,0)" />
              {s.showLabel !== false && (
                <>
                  <rect x={10} y={y - 18} width="60" height="16" rx="3" fill={`${color}30`} />
                  <text x={40} y={y - 6} textAnchor="middle" fontSize="10" fill={color}>{d.dataPoints[0].price.toFixed(2)}</text>
                </>
              )}
            </g>
          );
        }

        // Parallel channel (3-point)
        if (d.tool === 'parallelChannel') {
          if (pixels.length < 3 || !pixels[0] || !pixels[1] || !pixels[2]) return null;
          const [p1, p2, p3] = pixels;
          const dx = p2.x - p1.x, dy = p2.y - p1.y;
          const len = Math.sqrt(dx * dx + dy * dy);
          if (len === 0) return null;
          const nx = -dy / len, ny = dx / len;
          const dot = (p3.x - p1.x) * nx + (p3.y - p1.y) * ny;
          const q1 = { x: p1.x + nx * dot, y: p1.y + ny * dot };
          const q2 = { x: p2.x + nx * dot, y: p2.y + ny * dot };
          const fillAlpha = Math.round((s.fillOpacity || 0.08) * 255).toString(16).padStart(2, '0');
          const channelAnchors = isSelected && !isPreview && !d.locked ? [p1, p2, p3].map((p, index) => (
            <circle key={`${d.id}-anchor-${index}`} cx={p.x} cy={p.y} r="6" fill={strokeColor} stroke="white" strokeWidth="2" style={{ cursor: 'move' }} onMouseDown={(e) => handleAnchorMouseDown(e, d.id, index)} />
          )) : null;
          return (
            <g key={key} opacity={opacity}>
              <polygon points={`${p1.x},${p1.y} ${p2.x},${p2.y} ${q2.x},${q2.y} ${q1.x},${q1.y}`} fill={`${color}${fillAlpha}`} stroke="none" />
              <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke={strokeColor} strokeWidth={strokeWidth} />
              <line x1={q1.x} y1={q1.y} x2={q2.x} y2={q2.y} stroke={strokeColor} strokeWidth={strokeWidth} strokeDasharray="6 3" opacity={0.6} />
              {channelAnchors}
            </g>
          );
        }

        // Andrews Pitchfork (3-point)
        if (PITCHFORK_TOOLS.has(d.tool)) {
          if (pixels.length < 3 || !pixels[0] || !pixels[1] || !pixels[2]) return null;
          const [pA, pB, pC] = pixels;
          const mid = { x: (pB.x + pC.x) / 2, y: (pB.y + pC.y) / 2 };
          const W = svgRef.current?.clientWidth || 800;
          const H = svgRef.current?.clientHeight || 600;
          const extendLine = (x1: number, y1: number, x2: number, y2: number) => {
            const dx = x2 - x1, dy = y2 - y1;
            if (Math.abs(dx) < 0.001) return [{ x: x1, y: 0 }, { x: x1, y: H }];
            if (Math.abs(dy) < 0.001) return [{ x: 0, y: y1 }, { x: W, y: y1 }];
            const slope = dy / dx;
            const pts = [];
            const yAtX0 = y1 + slope * (0 - x1);
            if (yAtX0 >= 0 && yAtX0 <= H) pts.push({ x: 0, y: yAtX0 });
            const yAtXW = y1 + slope * (W - x1);
            if (yAtXW >= 0 && yAtXW <= H) pts.push({ x: W, y: yAtXW });
            const xAtY0 = x1 + (0 - y1) / slope;
            if (xAtY0 >= 0 && xAtY0 <= W) pts.push({ x: xAtY0, y: 0 });
            const xAtYH = x1 + (H - y1) / slope;
            if (xAtYH >= 0 && xAtYH <= W) pts.push({ x: xAtYH, y: H });
            return pts.length >= 2 ? pts.sort((a, b) => a.x - b.x) : [{ x: x1, y: y1 }, { x: x2, y: y2 }];
          };
          const medExt = extendLine(pA.x, pA.y, mid.x, mid.y);
          const fDx = mid.x - pA.x, fDy = mid.y - pA.y;
          const f1End = { x: pB.x + fDx * 10, y: pB.y + fDy * 10 };
          const f2End = { x: pC.x + fDx * 10, y: pC.y + fDy * 10 };
          const fork1Ext = extendLine(pB.x, pB.y, f1End.x, f1End.y);
          const fork2Ext = extendLine(pC.x, pC.y, f2End.x, f2End.y);
          const pitchforkAnchors = isSelected && !isPreview && !d.locked ? [pA, pB, pC].map((p, index) => (
            <circle key={`${d.id}-anchor-${index}`} cx={p.x} cy={p.y} r="6" fill={strokeColor} stroke="white" strokeWidth="2" style={{ cursor: 'move' }} onMouseDown={(e) => handleAnchorMouseDown(e, d.id, index)} />
          )) : null;
          return (
            <g key={key} opacity={opacity}>
              <line x1={medExt[0].x} y1={medExt[0].y} x2={medExt[1].x} y2={medExt[1].y} stroke={strokeColor} strokeWidth={strokeWidth} />
              <line x1={pA.x} y1={pA.y} x2={mid.x} y2={mid.y} stroke={strokeColor} strokeWidth={strokeWidth * 0.5} strokeDasharray="4 2" />
              <line x1={fork1Ext[0].x} y1={fork1Ext[0].y} x2={fork1Ext[1].x} y2={fork1Ext[1].y} stroke={strokeColor} strokeWidth={strokeWidth} strokeDasharray="5 3" />
              <line x1={fork2Ext[0].x} y1={fork2Ext[0].y} x2={fork2Ext[1].x} y2={fork2Ext[1].y} stroke={strokeColor} strokeWidth={strokeWidth} strokeDasharray="5 3" />
              {pitchforkAnchors}
            </g>
          );
        }

        // For other tools, skip if any point is off-screen
        const validPixels = pixels.filter(p => p !== null) as PixelPoint[];
        if (validPixels.length !== pixels.length) return null; // Some points off-screen, don't render

        const anchors = isSelected && !isPreview && !d.locked ? validPixels.map((p, index) => (
          <circle
            key={`${d.id}-anchor-${index}`}
            cx={p.x}
            cy={p.y}
            r="6"
            fill={strokeColor}
            stroke="white"
            strokeWidth="2"
            style={{ cursor: 'move' }}
            onMouseDown={(e) => handleAnchorMouseDown(e, d.id, index)}
          />
        )) : null;

        if (PATTERN_TOOLS.has(d.tool)) {
          const labels = getPatternLabels(d.tool, s);
          const pointList = validPixels.map((point) => `${point.x},${point.y}`).join(' ');
          const canFill = validPixels.length >= 3;

          return (
            <g key={key} opacity={opacity}>
              {canFill && (
                <polygon
                  points={pointList}
                  fill={`${color}16`}
                  stroke={`${color}66`}
                  strokeWidth={Math.max(1, strokeWidth - 0.5)}
                  strokeLinejoin="round"
                />
              )}
              {validPixels.length >= 2 && (
                <polyline
                  points={pointList}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  strokeLinejoin="round"
                />
              )}
              {validPixels.map((point, index) => {
                const label = labels[index] ?? `${index + 1}`;
                const isPreviewPoint = isPreview && index === validPixels.length - 1;
                return (
                  <g key={`${d.id}-point-${index}`} opacity={isPreviewPoint ? 0.82 : 1}>
                    <circle
                      cx={point.x}
                      cy={point.y}
                      r={isPreviewPoint ? 3.5 : 4.5}
                      fill={strokeColor}
                      stroke="white"
                      strokeWidth="1.5"
                    />
                    {s.showLabel !== false && (
                      <>
                        <rect
                          x={point.x + 7}
                          y={point.y - 19}
                          width={Math.max(18, label.length * 8 + 10)}
                          height={17}
                          rx={4}
                          fill={`${color}34`}
                          stroke={`${color}80`}
                          strokeWidth="1"
                        />
                        <text
                          x={point.x + 16}
                          y={point.y - 7}
                          textAnchor="middle"
                          fontSize="10"
                          fontWeight="600"
                          fill={strokeColor}
                        >
                          {label}
                        </text>
                      </>
                    )}
                  </g>
                );
              })}
              {anchors}
            </g>
          );
        }

        if (validPixels.length < 2) return null;

        const [p1, p2] = validPixels;

        if (GANN_BOX_TOOLS.has(d.tool)) {
          let endX = p2.x;
          let endY = p2.y;
          if (d.tool === 'gannSquare') {
            const size = Math.max(Math.abs(p2.x - p1.x), Math.abs(p2.y - p1.y));
            endX = p1.x + (p2.x >= p1.x ? size : -size);
            endY = p1.y + (p2.y >= p1.y ? size : -size);
          }

          const left = Math.min(p1.x, endX);
          const right = Math.max(p1.x, endX);
          const top = Math.min(p1.y, endY);
          const bottom = Math.max(p1.y, endY);
          const width = right - left;
          const height = bottom - top;
          const gridFractions = [0.25, 0.5, 0.75];

          return (
            <g key={key} opacity={opacity}>
              <rect
                x={left}
                y={top}
                width={width}
                height={height}
                fill={`${color}10`}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
              />
              <line x1={left} y1={top} x2={right} y2={bottom} stroke={strokeColor} strokeWidth={Math.max(1, strokeWidth - 0.5)} opacity={0.55} />
              <line x1={left} y1={bottom} x2={right} y2={top} stroke={strokeColor} strokeWidth={Math.max(1, strokeWidth - 0.5)} opacity={0.55} />
              {s.showGrid !== false && gridFractions.map((fraction) => (
                <React.Fragment key={`${d.id}-gann-grid-${fraction}`}>
                  <line x1={left + width * fraction} y1={top} x2={left + width * fraction} y2={bottom} stroke={strokeColor} strokeWidth="1" opacity={0.28} />
                  <line x1={left} y1={top + height * fraction} x2={right} y2={top + height * fraction} stroke={strokeColor} strokeWidth="1" opacity={0.28} />
                </React.Fragment>
              ))}
              {anchors}
            </g>
          );
        }

        if (d.tool === 'gannFan') {
          const segments = buildGannFanSegments(p1, p2, s);

          return (
            <g key={key} opacity={opacity}>
              {segments.map((segment) => (
                <line
                  key={`${d.id}-gann-fan-${segment.angle}`}
                  x1={segment.start.x}
                  y1={segment.start.y}
                  x2={segment.end.x}
                  y2={segment.end.y}
                  stroke={strokeColor}
                  strokeWidth={segment.angle === 45 ? strokeWidth : Math.max(1, strokeWidth - 0.5)}
                  opacity={segment.angle === 45 ? 1 : 0.55}
                />
              ))}
              {s.showLabel !== false && (
                <text x={p1.x + 8} y={p1.y - 8} fontSize="11" fill={strokeColor}>
                  Gann Fan
                </text>
              )}
              {anchors}
            </g>
          );
        }

        if (d.tool === 'rectangle') {
          const left = Math.min(p1.x, p2.x);
          const top = Math.min(p1.y, p2.y);
          const width = Math.abs(p2.x - p1.x);
          const height = Math.abs(p2.y - p1.y);

          return (
            <g key={key} opacity={opacity}>
              <rect
                x={left}
                y={top}
                width={width}
                height={height}
                fill={`${color}20`}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
              />
              {anchors}
            </g>
          );
        }

        if (d.tool === 'circle') {
          const cx = (p1.x + p2.x) / 2;
          const cy = (p1.y + p2.y) / 2;
          const rx = Math.abs(p2.x - p1.x) / 2;
          const ry = Math.abs(p2.y - p1.y) / 2;

          return (
            <g key={key} opacity={opacity}>
              <ellipse
                cx={cx}
                cy={cy}
                rx={rx}
                ry={ry}
                fill={`${color}16`}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
              />
              {anchors}
            </g>
          );
        }

        if (d.tool === 'triangle') {
          const left = Math.min(p1.x, p2.x);
          const right = Math.max(p1.x, p2.x);
          const top = Math.min(p1.y, p2.y);
          const bottom = Math.max(p1.y, p2.y);
          const points = `${(left + right) / 2},${top} ${right},${bottom} ${left},${bottom}`;

          return (
            <g key={key} opacity={opacity}>
              <polygon
                points={points}
                fill={`${color}18`}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
              />
              {anchors}
            </g>
          );
        }

        if (d.tool === 'ruler') {
          const start = d.dataPoints[0];
          const end = d.dataPoints[1];
          const pct = start.price ? ((end.price - start.price) / start.price) * 100 : 0;
          const seconds = Math.abs(end.time - start.time);
          const duration = seconds >= 86400
            ? `${(seconds / 86400).toFixed(1)}d`
            : seconds >= 3600
              ? `${(seconds / 3600).toFixed(1)}h`
              : `${Math.round(seconds / 60)}m`;
          const midX = (p1.x + p2.x) / 2;
          const midY = (p1.y + p2.y) / 2;
          const label = `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}% / ${duration}`;

          return (
            <g key={key} opacity={opacity}>
              <line
                x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
                strokeDasharray="6 4"
              />
              <rect
                x={midX - 54}
                y={midY - 26}
                width={108}
                height={20}
                rx={4}
                fill={`${color}30`}
                stroke={`${color}80`}
              />
              <text x={midX} y={midY - 12} textAnchor="middle" fontSize="11" fill={strokeColor}>
                {label}
              </text>
              {anchors}
            </g>
          );
        }

        if (d.tool === 'fibRetracement') {
          const start = d.dataPoints[0];
          const end = d.dataPoints[1];
          const levels = (s.levels as number[] | undefined) ?? [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
          const left = Math.min(p1.x, p2.x);
          const right = Math.max(p1.x, p2.x);
          const top = Math.min(p1.y, p2.y);
          const bottom = Math.max(p1.y, p2.y);

          return (
            <g key={key} opacity={opacity}>
              <line
                x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
                strokeDasharray="4 4"
              />
              {levels.map((level) => {
                const price = start.price + (end.price - start.price) * level;
                const y = p1.y + (p2.y - p1.y) * level;
                return (
                  <g key={`${d.id}-fib-${level}`}>
                    <line
                      x1={left}
                      y1={y}
                      x2={right}
                      y2={y}
                      stroke={strokeColor}
                      strokeWidth={Math.max(1, strokeWidth - 0.5)}
                      opacity={0.82}
                    />
                    {s.showLabel !== false && (
                      <>
                        <rect
                          x={right + 4}
                          y={y - 8}
                          width={86}
                          height={16}
                          rx={3}
                          fill={`${color}24`}
                        />
                        <text x={right + 8} y={y + 4} fontSize="10" fill={strokeColor}>
                          {(level * 100).toFixed(1)}% {price.toFixed(2)}
                        </text>
                      </>
                    )}
                  </g>
                );
              })}
              <rect
                x={left}
                y={top}
                width={right - left}
                height={bottom - top}
                fill={`${color}08`}
                stroke="none"
              />
              {anchors}
            </g>
          );
        }

        if (d.tool === 'longPosition' || d.tool === 'shortPosition') {
          const left = Math.min(p1.x, p2.x);
          const top = Math.min(p1.y, p2.y);
          const width = Math.abs(p2.x - p1.x);
          const entryY = p1.y;
          const targetY = d.tool === 'longPosition' ? top : Math.max(p1.y, p2.y);
          const riskY = d.tool === 'longPosition' ? Math.max(p1.y, p2.y) : top;
          const targetHeight = Math.abs(entryY - targetY);
          const riskHeight = Math.abs(riskY - entryY);
          const priceMove = d.tool === 'longPosition'
            ? d.dataPoints[1].price - d.dataPoints[0].price
            : d.dataPoints[0].price - d.dataPoints[1].price;
          const pct = d.dataPoints[0].price ? (priceMove / d.dataPoints[0].price) * 100 : 0;

          return (
            <g key={key} opacity={opacity}>
              <rect
                x={left}
                y={targetY}
                width={width}
                height={targetHeight}
                fill="#16a34a22"
                stroke="#16a34a"
                strokeWidth={strokeWidth}
              />
              <rect
                x={left}
                y={Math.min(entryY, riskY)}
                width={width}
                height={riskHeight}
                fill="#dc262622"
                stroke="#dc2626"
                strokeWidth={strokeWidth}
              />
              <line x1={left} y1={entryY} x2={left + width} y2={entryY} stroke={strokeColor} strokeWidth={strokeWidth} />
              {s.showLabel !== false && (
                <text x={left + width / 2} y={top - 6} textAnchor="middle" fontSize="11" fill={strokeColor}>
                  {d.tool === 'longPosition' ? 'Long' : 'Short'} {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
                </text>
              )}
              {anchors}
            </g>
          );
        }

        if (d.tool === 'forecast') {
          const pct = d.dataPoints[0].price ? ((d.dataPoints[1].price - d.dataPoints[0].price) / d.dataPoints[0].price) * 100 : 0;
          const midX = (p1.x + p2.x) / 2;
          const midY = (p1.y + p2.y) / 2;

          return (
            <g key={key} opacity={opacity}>
              <line
                x1={p1.x}
                y1={p1.y}
                x2={p2.x}
                y2={p2.y}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
                strokeDasharray="6 4"
              />
              <circle cx={p2.x} cy={p2.y} r={4} fill={strokeColor} />
              {s.showLabel !== false && (
                <text x={midX} y={midY - 8} textAnchor="middle" fontSize="11" fill={strokeColor}>
                  Forecast {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
                </text>
              )}
              {anchors}
            </g>
          );
        }

        if (d.tool === 'ray' || d.tool === 'extendedLine') {
          const width = svgRef.current?.clientWidth || 0;
          const height = svgRef.current?.clientHeight || 0;
          const dx = p2.x - p1.x;
          const dy = p2.y - p1.y;
          const candidates: PixelPoint[] = [];

          if (width > 0 && height > 0 && (dx !== 0 || dy !== 0)) {
            if (dx !== 0) {
              const yAtLeft = p1.y + ((0 - p1.x) * dy) / dx;
              const yAtRight = p1.y + ((width - p1.x) * dy) / dx;
              if (yAtLeft >= 0 && yAtLeft <= height) candidates.push({ x: 0, y: yAtLeft });
              if (yAtRight >= 0 && yAtRight <= height) candidates.push({ x: width, y: yAtRight });
            }
            if (dy !== 0) {
              const xAtTop = p1.x + ((0 - p1.y) * dx) / dy;
              const xAtBottom = p1.x + ((height - p1.y) * dx) / dy;
              if (xAtTop >= 0 && xAtTop <= width) candidates.push({ x: xAtTop, y: 0 });
              if (xAtBottom >= 0 && xAtBottom <= width) candidates.push({ x: xAtBottom, y: height });
            }
          }

          const uniqueCandidates = candidates.filter((candidate, index) =>
            candidates.findIndex((other) =>
              Math.abs(other.x - candidate.x) < 0.5 && Math.abs(other.y - candidate.y) < 0.5,
            ) === index,
          );

          let lineStart = p1;
          let lineEnd = p2;

          if (d.tool === 'extendedLine' && uniqueCandidates.length >= 2) {
            const [startCandidate, endCandidate] = uniqueCandidates
              .sort((a, b) => (a.x - b.x) || (a.y - b.y))
              .slice(0, 2);
            if (startCandidate && endCandidate) {
              lineStart = startCandidate;
              lineEnd = endCandidate;
            }
          }

          if (d.tool === 'ray' && uniqueCandidates.length > 0) {
            const forwardCandidates = uniqueCandidates.filter((candidate) =>
              (candidate.x - p1.x) * dx + (candidate.y - p1.y) * dy >= 0,
            );
            const endpoint = forwardCandidates
              .sort((a, b) =>
                ((b.x - p1.x) ** 2 + (b.y - p1.y) ** 2) -
                ((a.x - p1.x) ** 2 + (a.y - p1.y) ** 2),
              )[0];
            if (endpoint) lineEnd = endpoint;
          }

          return (
            <g key={key} opacity={opacity}>
              <line
                x1={lineStart.x} y1={lineStart.y} x2={lineEnd.x} y2={lineEnd.y}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
              />
              {anchors}
            </g>
          );
        }

        if (d.tool === 'arrow') {
          const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
          const size = 10;
          const left = {
            x: p2.x - size * Math.cos(angle - Math.PI / 6),
            y: p2.y - size * Math.sin(angle - Math.PI / 6),
          };
          const right = {
            x: p2.x - size * Math.cos(angle + Math.PI / 6),
            y: p2.y - size * Math.sin(angle + Math.PI / 6),
          };

        return (
          <g key={key} opacity={opacity}>
            <line
              x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
            />
            <polygon
              points={`${p2.x},${p2.y} ${left.x},${left.y} ${right.x},${right.y}`}
              fill={strokeColor}
            />
            {anchors}
          </g>
        );
        }

        return (
          <g key={key} opacity={opacity}>
            <line
              x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
            />
            {anchors}
          </g>
        );
      }
    }
  }, [dataToPixel, handleAnchorMouseDown, hoveredDrawingId, priceToY, selectedDrawingIds, timeToX]);

  const renderPreview = useCallback(() => {
    if (!isDrawing || !startDataPoint || !currentDataPoint) return null;

    const previewDrawing: Drawing = {
      id: 'preview',
      tool: activeTool,
      dataPoints: [startDataPoint, currentDataPoint],
      settings: activeSettings(),
    };

    return renderDrawing(previewDrawing, true);
  }, [isDrawing, startDataPoint, currentDataPoint, activeTool, activeSettings, renderDrawing]);

  const renderMultiClickPreview = useCallback(() => {
    if (!isMultiClick || multiDataPoints.length === 0) return null;

    const previewPoints = currentDataPoint
      ? [...multiDataPoints, currentDataPoint]
      : multiDataPoints;

    const previewDrawing: Drawing = {
      id: 'multi-preview',
      tool: activeTool,
      dataPoints: previewPoints,
      settings: activeSettings(),
    };

    return renderDrawing(previewDrawing, true);
  }, [activeSettings, activeTool, currentDataPoint, isMultiClick, multiDataPoints, renderDrawing]);

  const isInteractive = activeTool !== 'cursor';
  const isEraser = activeTool === 'eraser';
  const shouldCapturePointer =
    isInteractive ||
    isReplaySelectionMode ||
    draggingAnchor !== null ||
    (activeTool === 'cursor' && drawings.length > 0);
  const cursor = isReplaySelectionMode
    ? 'crosshair'
    : panState
      ? 'grabbing'
      : isEraser
        ? 'cell'
        : activeTool === 'cursor'
          ? 'grab'
          : (!isInteractive ? 'default' : isMultiClick ? 'cell' : 'crosshair');

  return (
    <div className="absolute inset-0 z-10" style={{ pointerEvents: shouldCapturePointer ? 'auto' : 'none' }}>
      <svg
        ref={svgRef}
        className="w-full h-full"
        style={{ cursor }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        onContextMenu={(e) => {
          if (panState) e.preventDefault();
        }}
        onMouseLeave={() => {
          setPanState(null);
          if (isDrawing) {
            setIsDrawing(false);
            setStartDataPoint(null);
            setCurrentDataPoint(null);
          }
          setHoveredDrawingId(null);
        }}
      >
        {drawings.map((d) => renderDrawing(d))}
        {renderPreview()}
        {renderMultiClickPreview()}
      </svg>

      {textInput && (
        <TextInputPopup
          position={textInput}
          onSubmit={handleTextSubmit}
          onCancel={() => setTextInput(null)}
        />
      )}
    </div>
  );
};

interface TextInputPopupProps {
  position: PixelPoint;
  onSubmit: (text: string) => void;
  onCancel: () => void;
}

const TextInputPopup: React.FC<TextInputPopupProps> = ({ position, onSubmit, onCancel }) => {
  const { t } = useI18n();
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="absolute z-50 flex items-center gap-1" style={{ left: position.x, top: position.y }}>
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onSubmit(value);
          if (e.key === 'Escape') onCancel();
        }}
        className="bg-gray-700 text-white text-sm rounded px-2 py-1 w-40 border border-gray-500 focus:outline-none focus:border-blue-500"
        placeholder={t("enterNote")}
      />
      <button
        onClick={() => onSubmit(value)}
        className="bg-blue-600 text-white text-xs px-2 py-1 rounded hover:bg-blue-700"
      >
        OK
      </button>
    </div>
  );
};

export default ChartOverlay;
