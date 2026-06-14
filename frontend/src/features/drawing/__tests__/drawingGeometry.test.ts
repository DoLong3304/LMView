import { describe, expect, it } from 'vitest';

import {
  MIN_BOX_DRAWING_SIDE_PX,
  MIN_PARALLEL_CHANNEL_OFFSET_PX,
  MIN_TWO_POINT_DRAWING_DISTANCE_PX,
  getCommittedDrawingDataPoints,
  isRenderableBoxDrawing,
  isRenderableParallelChannel,
  isRenderableTwoPointDrawing,
  pixelDistance,
} from '../drawingGeometry';

describe('drawingGeometry', () => {
  it('calculates pixel distance between two drawing points', () => {
    expect(pixelDistance({ x: 10, y: 20 }, { x: 13, y: 24 })).toBe(5);
  });

  it('rejects zero-length or tiny two-point drawings', () => {
    expect(isRenderableTwoPointDrawing({ x: 10, y: 10 }, { x: 10, y: 10 })).toBe(false);
    expect(
      isRenderableTwoPointDrawing(
        { x: 10, y: 10 },
        { x: 10 + MIN_TWO_POINT_DRAWING_DISTANCE_PX - 1, y: 10 }
      )
    ).toBe(false);
  });

  it('accepts a two-point drawing once it reaches the minimum pixel distance', () => {
    expect(
      isRenderableTwoPointDrawing(
        { x: 10, y: 10 },
        { x: 10 + MIN_TWO_POINT_DRAWING_DISTANCE_PX, y: 10 }
      )
    ).toBe(true);
  });

  it('rejects box drawings without a minimum width and height', () => {
    expect(isRenderableBoxDrawing({ x: 10, y: 10 }, { x: 10, y: 20 })).toBe(false);
    expect(
      isRenderableBoxDrawing(
        { x: 10, y: 10 },
        { x: 10 + MIN_BOX_DRAWING_SIDE_PX, y: 10 + MIN_BOX_DRAWING_SIDE_PX - 1 }
      )
    ).toBe(false);
  });

  it('accepts box drawings once width and height reach the minimum', () => {
    expect(
      isRenderableBoxDrawing(
        { x: 10, y: 10 },
        { x: 10 + MIN_BOX_DRAWING_SIDE_PX, y: 10 + MIN_BOX_DRAWING_SIDE_PX }
      )
    ).toBe(true);
  });

  it('rejects parallel channels with a tiny base or offset', () => {
    expect(
      isRenderableParallelChannel([
        { x: 10, y: 10 },
        { x: 10 + MIN_TWO_POINT_DRAWING_DISTANCE_PX - 1, y: 10 },
        { x: 40, y: 30 },
      ])
    ).toBe(false);

    expect(
      isRenderableParallelChannel([
        { x: 10, y: 10 },
        { x: 40, y: 10 },
        { x: 25, y: 10 + MIN_PARALLEL_CHANNEL_OFFSET_PX - 1 },
      ])
    ).toBe(false);
  });

  it('accepts parallel channels with a valid base and perpendicular offset', () => {
    expect(
      isRenderableParallelChannel([
        { x: 10, y: 10 },
        { x: 40, y: 10 },
        { x: 25, y: 10 + MIN_PARALLEL_CHANNEL_OFFSET_PX },
      ])
    ).toBe(true);
  });

  it('commits one-anchor drawings with a single data point', () => {
    const start = { time: 1_700_000_000, price: 100 };
    const end = { time: 1_700_000_060, price: 104 };

    expect(getCommittedDrawingDataPoints('anchoredText', start, end)).toEqual([start]);
    expect(getCommittedDrawingDataPoints('vertical', start, end)).toEqual([start]);
    expect(getCommittedDrawingDataPoints('horizontalRay', start, end)).toEqual([start]);
    expect(getCommittedDrawingDataPoints('note', start, end)).toEqual([start]);
  });

  it('keeps two points for regular drag drawings', () => {
    const start = { time: 1_700_000_000, price: 100 };
    const end = { time: 1_700_000_060, price: 104 };

    expect(getCommittedDrawingDataPoints('trendline', start, end)).toEqual([start, end]);
    expect(getCommittedDrawingDataPoints('fibRetracement', start, end)).toEqual([start, end]);
    expect(getCommittedDrawingDataPoints('ruler', start, end)).toEqual([start, end]);
    expect(getCommittedDrawingDataPoints('longPosition', start, end)).toEqual([start, end]);
    expect(getCommittedDrawingDataPoints('shortPosition', start, end)).toEqual([start, end]);
  });
});
