import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useI18n } from '../i18n';
import type { Drawing, DataPoint } from '../types';
import type { ToolSettings } from './ToolSettingsPopup';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';

const MULTI_CLICK_NEEDED: Record<string, boolean> = {
  elliottWave: true,
  harmonicABCD: true
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

  // Anchor dragging state
  const [draggingAnchor, setDraggingAnchor] = useState<{
    drawingId: string | number;
    pointIndex: number;
  } | null>(null);

  const isMultiClick = MULTI_CLICK_NEEDED[activeTool] || false;

  const activeSettings = useCallback((): ToolSettings => {
    return (toolSettings && toolSettings[activeTool]) || { color: '#3b82f6', lineWidth: 2 };
  }, [toolSettings, activeTool]);

  const requiredPoints = useCallback((): number => {
    if (activeTool === 'elliottWave') {
      const wt = activeSettings().waveType || 'impulse';
      return wt === 'corrective' ? 4 : 6;
    }
    if (activeTool === 'harmonicABCD') return 4;
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

      case 'rectangle': {
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

        for (let i = 0; i < validPixels.length - 1; i++) {
          const dist = distanceToLine(mousePixel, validPixels[i], validPixels[i + 1]);
          if (dist <= DRAWING_HIT_TOLERANCE) return true;
        }
        return false;
      }
    }
  }, [dataToPixel, distanceToLine]);

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
    } else {
      setMultiDataPoints(next);
    }
  }, [multiDataPoints, requiredPoints, activeTool, getSVGPoint, pixelToData, magneticSnap, onAddDrawing, activeSettings]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const pixel = getSVGPoint(e);

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
      for (const d of drawings) {
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

      for (const d of drawings) {
        if (hitTestDrawing(d, pixel)) {
          clickedDrawingId = d.id;
          break;
        }
      }

      if (clickedDrawingId && onSetSelectedDrawingIds) {
        onSetSelectedDrawingIds([clickedDrawingId]);
      } else if (onSetSelectedDrawingIds) {
        onSetSelectedDrawingIds([]);
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
  }, [activeTool, getSVGPoint, pixelToData, magneticSnap, isMultiClick, handleMultiClick, drawings, hitTestDrawing, onDeleteDrawing, onSetSelectedDrawingIds, isReplaySelectionMode, onReplayStartSelect]);

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
    if (!drawing || !drawing.dataPoints) return;

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

    // Handle anchor dragging
    if (draggingAnchor) {
      handleAnchorDrag(e);
      return;
    }

    // Eraser mode: highlight drawing on hover
    if (activeTool === 'eraser') {
      let foundId: string | number | null = null;
      for (const d of drawings) {
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
  }, [isDrawing, isMultiClick, multiDataPoints.length, getSVGPoint, pixelToData, magneticSnap, activeTool, drawings, hitTestDrawing, draggingAnchor, handleAnchorDrag]);

  const handleMouseUp = useCallback(() => {
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
  }, [isDrawing, startDataPoint, currentDataPoint, activeTool, onAddDrawing, activeSettings, draggingAnchor, handleAnchorMouseUp]);

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
        if (pixels.length < 1 || !pixels[0]) return null;
        const y = pixels[0].y;
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
        if (pixels.length < 1 || !pixels[0]) return null;
        const x = pixels[0].x;
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

      default: {
        // For other tools, skip if any point is off-screen
        const validPixels = pixels.filter(p => p !== null) as PixelPoint[];
        if (validPixels.length !== pixels.length) return null; // Some points off-screen, don't render

        if (validPixels.length < 2) return null;

        // Render based on tool type (simplified for now)
        const [p1, p2] = validPixels;

        return (
          <g key={key} opacity={opacity}>
            <line
              x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
            />
            {/* Render anchors when selected */}
            {isSelected && !isPreview && (
              <>
                <circle
                  cx={p1.x}
                  cy={p1.y}
                  r="6"
                  fill={strokeColor}
                  stroke="white"
                  strokeWidth="2"
                  style={{ cursor: 'move' }}
                  onMouseDown={(e) => handleAnchorMouseDown(e, d.id, 0)}
                />
                <circle
                  cx={p2.x}
                  cy={p2.y}
                  r="6"
                  fill={strokeColor}
                  stroke="white"
                  strokeWidth="2"
                  style={{ cursor: 'move' }}
                  onMouseDown={(e) => handleAnchorMouseDown(e, d.id, 1)}
                />
              </>
            )}
          </g>
        );
      }
    }
  }, [dataToPixel, selectedDrawingIds, hoveredDrawingId]);

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

  const isInteractive = activeTool !== 'cursor';
  const isEraser = activeTool === 'eraser';
  const cursor = isEraser ? 'not-allowed' : (!isInteractive ? 'default' : isMultiClick ? 'cell' : 'crosshair');

  return (
    <div className="absolute inset-0 z-10" style={{ pointerEvents: isInteractive || isEraser ? 'auto' : 'none' }}>
      <svg
        ref={svgRef}
        className="w-full h-full"
        style={{ cursor }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
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
