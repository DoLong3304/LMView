import type { DataPoint } from "@/types";

export interface PixelPointLike {
  x: number;
  y: number;
}

export const MIN_TWO_POINT_DRAWING_DISTANCE_PX = 4;
export const MIN_BOX_DRAWING_SIDE_PX = 4;
export const MIN_PARALLEL_CHANNEL_OFFSET_PX = 4;
const ONE_POINT_DRAWING_TOOLS = new Set(["anchoredText", "horizontalRay", "note", "vertical"]);

export function pixelDistance(start: PixelPointLike, end: PixelPointLike): number {
  return Math.hypot(end.x - start.x, end.y - start.y);
}

export function isRenderableTwoPointDrawing(
  start: PixelPointLike | null,
  end: PixelPointLike | null,
  minDistancePx = MIN_TWO_POINT_DRAWING_DISTANCE_PX
): boolean {
  if (!start || !end) {
    return false;
  }

  return pixelDistance(start, end) >= minDistancePx;
}

export function isRenderableBoxDrawing(
  start: PixelPointLike | null,
  end: PixelPointLike | null,
  minSidePx = MIN_BOX_DRAWING_SIDE_PX
): boolean {
  if (!start || !end) {
    return false;
  }

  return Math.abs(end.x - start.x) >= minSidePx && Math.abs(end.y - start.y) >= minSidePx;
}

export function isRenderableParallelChannel(
  points: Array<PixelPointLike | null>,
  minBaseDistancePx = MIN_TWO_POINT_DRAWING_DISTANCE_PX,
  minOffsetPx = MIN_PARALLEL_CHANNEL_OFFSET_PX
): boolean {
  const [p1, p2, p3] = points;
  if (!p1 || !p2 || !p3) {
    return false;
  }

  if (!isRenderableTwoPointDrawing(p1, p2, minBaseDistancePx)) {
    return false;
  }

  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const length = Math.hypot(dx, dy);
  if (length === 0) {
    return false;
  }

  const normalX = -dy / length;
  const normalY = dx / length;
  const offset = Math.abs((p3.x - p1.x) * normalX + (p3.y - p1.y) * normalY);

  return offset >= minOffsetPx;
}

export function getCommittedDrawingDataPoints(
  tool: string,
  start: DataPoint,
  end: DataPoint
): DataPoint[] {
  if (ONE_POINT_DRAWING_TOOLS.has(tool)) {
    return [start];
  }

  return [start, end];
}
