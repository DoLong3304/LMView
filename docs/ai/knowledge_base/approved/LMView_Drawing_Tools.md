# LMView Drawing Tools — Complete Reference

> **Document Type**: Feature Reference
> **Audience**: AI Assistant, End Users
> **Version**: 0.25.42+

---

## Overview

LMView provides **40+ drawing tools** for technical analysis directly on the chart. All drawings use **data-space coordinates**, meaning they remain anchored to price and time even when you zoom, pan, or change timeframes.

### Key Concepts

- **Data-Space Anchoring**: Drawings store `(time, price)` coordinates, not pixel positions. This ensures they stay aligned with candles.
- **Persistence**: Drawings are saved to your account and restored across sessions.
- **Undo/Redo**: Full history support (Ctrl+Z / Ctrl+Y).
- **Editability**: Click any drawing to select it, then drag anchors or press Delete to remove.
- **Visibility Toggle**: Hide/show individual drawings or lock them to prevent accidental edits.

---

## Toolbar Organization

The drawing toolbar is organized into categories:

| Category | Tools |
|----------|-------|
| **Lines** | Cursor, Crosshair, Trendline, Ray, Extended Line, Horizontal Ray, Horizontal, Vertical, Angle Line, Disjoint Angle |
| **Shapes** | Rectangle, Rotated Rectangle, Triangle, Ellipse, Arrow, Polyline, Parallel Channel, Price Range |
| **Fibonacci** | Retracement, Extension, Channel, Arcs, Spiral, Time Zones |
| **Gann** | Gann Box, Gann Fan, Gann Square, Gann Line |
| **Elliott** | Elliott Wave, Harmonic ABCD, XABCD Pattern |
| **Pitchfork** | Pitchfork, Schiff Pitchfork, Modified Pitchfork, Inside Pitchfork |
| **Text** | Text, Callout, Note, Balloon, Anchored Text |
| **Measurement** | Ruler, Crossline, Date Range, Price Range Tool, Risk/Reward |
| **Position** | Long Position, Short Position, Forecast |
| **Utility** | Magnet, Lock, Hide, Eraser, Clear All |

---

## Drawing Interaction Model

### Anchor Points

Tools require a specific number of clicks (anchor points):

| Anchor Count | Tools (examples) |
|--------------|------------------|
| 1 click | Horizontal, Vertical, Horizontal Ray, Text, Note |
| 2 clicks | Trendline, Ray, Rectangle, Fibonacci Retracement, Risk/Reward |
| 3 clicks | Parallel Channel, Pitchfork, Gann Fan |
| 4+ clicks | Polyline, Elliott Wave, Harmonic ABCD |

### Editing Workflow

1. **Select** — Click a drawing to show its anchor handles
2. **Drag** — Move any anchor to reshape
3. **Delete** — Press `Delete` key or click trash icon
4. **Lock** — Toggle lock to prevent edits
5. **Hide** — Toggle visibility without deleting

---

## Complete Tool Reference

### Lines Category

#### `cursor`
- **Display Name**: Cursor
- **Purpose**: Crosshair cursor for precise price/time reading
- **Anchors**: 0 (cursor mode only)
- **Behavior**: Follows mouse; shows exact price and time in labels
- **Settings**: None
- **Note**: This is the default tool when selecting other tools doesn't apply

#### `crosshair`
- **Display Name**: Crosshair
- **Purpose**: Precise crosshair with price/time labels
- **Anchors**: 0 (cursor mode)
- **Behavior**: Vertical and horizontal lines extend across chart; labels show price and timestamp
- **Settings**: `lineColor`, `lineWidth`, `showLabels`
- **Example Use**: Reading exact values at a specific candle

#### `trendline`
- **Display Name**: Trend Line
- **Purpose**: Draw a straight line between two points to identify trend direction and potential support/resistance
- **Anchors**: 2 (start point, end point)
- **Settings**:
  - `color` (hex)
  - `lineWidth` (1-5)
  - `lineStyle` (`solid`, `dashed`, `dotted`)
  - `extendLeft` (boolean) — Extend line leftward indefinitely
  - `extendRight` (boolean) — Extend line rightward indefinitely
- **Usage Scenarios**:
  - Connect swing lows (support) or swing highs (resistance)
  - Identify trend breaks when price crosses the line
  - Channel boundaries with parallel lines
- **Example**:
  - Click at swing low (time: 1700000000, price: 49000)
  - Click at next swing low (time: 1700018000, price: 50000)
  - Line indicates ascending support

#### `ray`
- **Display Name**: Ray
- **Purpose**: A line that extends infinitely from the first anchor through the second
- **Anchors**: 2 (origin point, direction point)
- **Settings**: `color`, `lineWidth`, `lineStyle`
- **Usage**: Trend lines that project into the future; Gann angles
- **Difference from `extendedLine`**: Ray extends only in one direction (from first anchor)

#### `extendedLine`
- **Display Name**: Extended Line
- **Purpose**: A line that extends infinitely in both directions
- **Anchors**: 2 (any two points define the infinite line)
- **Settings**: `color`, `lineWidth`, `lineStyle`
- **Usage**: Support/resistance lines that span entire chart history

#### `horizontalRay`
- **Display Name**: Horizontal Ray
- **Purpose**: A horizontal line starting from anchor and extending right indefinitely
- **Anchors**: 1 (price level)
- **Settings**: `color`, `lineWidth`, `lineStyle`, `showLabel`
- **Usage**: Mark a specific price level (support/resistance, psychological levels)
- **Example**: Click at price 50000 → horizontal line at $50,000 extending right

#### `horizontal`
- **Display Name**: Horizontal Line
- **Purpose**: A horizontal line segment between left and right chart edges at a fixed price
- **Anchors**: 1 (price level)
- **Settings**: `color`, `lineWidth`, `lineStyle`, `showLabel`
- **Usage**: Static price level markers
- **Difference from `horizontalRay`**: Does not extend; finite segment

#### `vertical`
- **Display Name**: Vertical Line
- **Purpose**: Mark a specific time point
- **Anchors**: 1 (timestamp)
- **Settings**: `color`, `lineWidth`, `lineStyle`, `showLabel`
- **Usage**: Highlight significant dates (earnings, news events, candle patterns)

#### `angleLine`
- **Display Name**: Angle Line
- **Purpose**: Draw a line at a specific angle from an anchor point
- **Anchors**: 2 (origin point, angle defined by second point direction)
- **Settings**: `color`, `lineWidth`, `lineStyle`, `angle` (computed), `extendRight`
- **Usage**: Gann angle approximations; measuring slope
- **Note**: The angle is calculated from the two points; the line can be extended

#### `disjointAngle`
- **Display Name**: Disjoint Angle
- **Purpose**: Two separate angle measurements from a common origin
- **Anchors**: 3 (origin, angle1 direction, angle2 direction)
- **Settings**: `color`, `lineWidth`, `showAngles`
- **Usage**: Compare two trend angles; measure wedge patterns

---

### Shapes Category

#### `rectangle`
- **Display Name**: Rectangle
- **Purpose**: Highlight a price/time zone (consolidation, breakout area)
- **Anchors**: 2 (top-left/bottom-right or opposite corners)
- **Settings**:
  - `color` (border)
  - `lineWidth`
  - `fill` (boolean)
  - `fillColor` (with opacity)
  - `fillOpacity` (0-1)
- **Usage**:
  - Box consolidation periods
  - Mark support/resistance zones
  - Highlight chart patterns (flags, wedges)
- **Example**: Drag from consolidation start to end → shaded box

#### `rotatedRectangle`
- **Display Name**: Rotated Rectangle
- **Purpose**: Rectangle that can be rotated (parallelogram with 90° angles preserved)
- **Anchors**: 3 (three corners to define rotation)
- **Settings**: `color`, `lineWidth`, `fill`, `fillColor`, `fillOpacity`
- **Usage**: Diagonal support/resistance zones; rotated channel approximations

#### `triangle`
- **Display Name**: Triangle
- **Purpose**: Draw a triangular shape
- **Anchors**: 3 (three vertices)
- **Settings**: `color`, `lineWidth`, `fill`, `fillColor`, `fillOpacity`
- **Usage**: Triangle patterns (ascending/descending); visual marker

#### `ellipse`
- **Display Name**: Ellipse
- **Purpose**: Draw an ellipse/oval shape
- **Anchors**: 2 (bounding box corners)
- **Settings**: `color`, `lineWidth`, `fill`, `fillColor`, `fillOpacity`
- **Usage**: Highlight zones; rarely used in TA

#### `arrow`
- **Display Name**: Arrow
- **Purpose**: Point to a specific event or direction
- **Anchors**: 2 (tail, head)
- **Settings**:
  - `color`
  - `lineWidth`
  - `arrowSize` (head size)
  - `fill` (boolean)
- **Usage**: Mark breakout directions; indicate expected movement

#### `polyline`
- **Display Name**: Polyline
- **Purpose**: Connect multiple points with line segments
- **Anchors**: 4+ (as many as needed)
- **Settings**: `color`, `lineWidth`, `lineStyle`, `showPoints`
- **Usage**: Complex pattern outlines; custom shape annotations
- **Note**: Double-click or press Enter to finish

#### `parallelChannel`
- **Display Name**: Parallel Channel
- **Purpose**: Draw a channel with two parallel trendlines
- **Anchors**: 3 (first: anchor point on main line; second: another point on main line; third: offset point to define channel width)
- **Settings**:
  - `color`
  - `lineWidth`
  - `lineStyle`
  - `extendLeft`
  - `extendRight`
- **Usage**:
  - Price channels (parallel support/resistance)
  - Measure channel width for breakout targets
- **Example**:
  1. Click lower trendline point 1
  2. Click lower trendline point 2
  3. Click a point above to set channel height

#### `priceRange`
- **Display Name**: Price Range
- **Purpose**: Highlight a horizontal price zone between two levels
- **Anchors**: 2 (price level 1, price level 2) — clicks on horizontal axis define range
- **Settings**: `color`, `fillColor`, `fillOpacity`, `showLabels`
- **Usage**: Mark consolidation zones; supply/demand areas

---

### Fibonacci Tools

All Fibonacci tools use the standard Fibonacci ratios:
`0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%, 127.2%, 161.8%, 261.8%`

#### `fibRetracement`
- **Display Name**: Fibonacci Retracement
- **Purpose**: Draw retracement levels between a swing high and swing low (or vice versa)
- **Anchors**: 2 (point A, point B)
- **Settings**:
  - `levels` (array of ratios to display, default: `[0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.618]`)
  - `colors` (per level, can use defaults)
  - `lineWidth`
  - `showLabels`
  - `backgroundFill` (boolean)
- **Default Level Colors**:
  - 0%, 100% — `#787B86` (gray, thick)
  - 23.6%, 78.6% — `#787B86` (dashed)
  - 38.2% — `#7E8A93` (dashed)
  - 50% — `#9E8C6D` (gold, thick dashed)
  - 61.8% — `#E7863D` (orange, **thick solid** — key level)
  - 127.2%, 161.8% — `#3D793D` (green)
- **Usage**:
  - Uptrend: anchor 1 = swing low, anchor 2 = swing high → retracement levels show potential support
  - Downtrend: anchor 1 = swing high, anchor 2 = swing low → retracement levels show potential resistance
- **Interpretation**: Price often retraces to 38.2%, 50%, or 61.8% before resuming trend

#### `fibExtension`
- **Display Name**: Fibonacci Extension
- **Purpose**: Project price targets beyond the swing points
- **Anchors**: 3 (swing low, swing high, extension anchor)
- **Settings**: `levels`, `colors`, `lineWidth`, `showLabels`
- **Common Extension Levels**: 161.8%, 261.8%, 423.6%
- **Usage**: Set profit targets; measure impulse wave lengths
- **Example**:
  1. Click swing low (A)
  2. Click swing high (B)
  3. Click retracement low (C) → extensions project from B through C

#### `fibChannel`
- **Display Name**: Fibonacci Channel
- **Purpose**: Channel based on Fibonacci retracement parallel to trend
- **Anchors**: 3 (trend start, trend end, channel width anchor)
- **Settings**: `levels`, `colors`, `extendLeft`, `extendRight`
- **Usage**: Dynamic support/resistance channels in trending markets

#### `fibArcs`
- **Display Name**: Fibonacci Arcs
- **Purpose**: Draw arcs at Fibonacci price levels emanating from a point
- **Anchors**: 2 (center point, radius endpoint)
- **Settings**: `levels`, `colors`, `lineWidth`
- **Usage**: Time-based price projections; less common but useful for cyclical analysis
- **Note**: Arcs are circular in price-time space

#### `fibSpiral`
- **Display Name**: Fibonacci Spiral
- **Purpose**: Draw a logarithmic spiral based on Fibonacci ratios
- **Anchors**: 2 (center, outer point)
- **Settings**: `levels`, `colors`, `showGrid`
- **Usage**: Advanced pattern analysis; Elliott wave expansions
- **Note**: Complex visualization; primarily for educational/advanced use

#### `fibTimeZone`
- **Display Name**: Fibonacci Time Zones
- **Purpose**: Vertical lines at Fibonacci time intervals from a starting point
- **Anchors**: 2 (start point, interval unit)
- **Settings**: `levels`, `colors`, `lineWidth`, `extend`
- **Usage**: Predict significant time periods (1, 2, 3, 5, 8, 13, 21... periods from anchor)
- **Example**: Start at major bottom → vertical lines at 1 week, 2 weeks, 3 weeks, 5 weeks, etc.

---

### Gann Tools

Based on W.D. Gann's geometric analysis. Angles represent price/time relationships.

#### `gannBox`
- **Display Name**: Gann Box
- **Purpose**: Draw a square of price and time (Gann's "square of 9")
- **Anchors**: 2 (bottom-left, top-right corners)
- **Settings**: `color`, `lineWidth`, `showGrid`, `showMidlines`
- **Usage**: Identify balanced price-time zones; support/resistance at box boundaries
- **Note**: Requires equal price and time scaling for full effect

#### `gannFan`
- **Display Name**: Gann Fan
- **Purpose**: Draw multiple Gann angles from a single origin
- **Anchors**: 2 (origin point, angle reference point) — fan extends from origin
- **Settings**:
  - `angles` (array of angles to draw, default: all)
  - `colors`
  - `lineWidth`
  - `extendRight`
- **Default Angles** (from horizontal):
  - 1x1: 45° (1 price unit = 1 time unit)
  - 1x2: 26.565° (1 price = 2 time)
  - 1x3: 18.435°
  - 1x4: 14.036°
  - 1x8: 7.125°
  - 2x1: 63.75° (2 price = 1 time)
  - 3x1: 71.565°
  - 4x1: 75.964°
  - 8x1: 82.875°
- **Usage**: Support/resistance at angle lines; trend strength assessment (steeper = stronger)
- **Interpretation**: Price bouncing off a Gann angle indicates trend continuation; breaking through may signal reversal

#### `gannSquare`
- **Display Name**: Gann Square
- **Purpose**: Draw a square grid from an origin point
- **Anchors**: 1 (origin)
- **Settings**:
  - `gridSize` (price and time units per square)
  - `showGrid` (boolean)
  - `showDiagonals` (boolean)
  - `showMidlines` (boolean)
- **Usage**: Master time-price square; identify major turning points at square boundaries

#### `gannLine`
- **Display Name**: Gann Line
- **Purpose**: Draw a single Gann angle line from an origin
- **Anchors**: 2 (origin, direction)
- **Settings**:
  - `angle` (specific angle like 45, 26.565, etc.)
  - `color`
  - `lineWidth`
  - `extendRight`
- **Usage**: Focus on one specific angle (e.g., 1x1 for balanced trend)

---

### Elliott Wave & Harmonics

#### `elliottWave`
- **Display Name**: Elliott Wave Labels
- **Purpose**: Label Elliott wave patterns (impulse and corrective)
- **Anchors**: 5 (for impulse: points 1, 2, 3, 4, 5) or more for corrections
- **Settings**:
  - `waveType` (`impulse` | `corrective`)
  - `waveLabels` (overrides default 1-2-3-4-5)
  - `color`
  - `fontSize`
  - `showWaveLines` (boolean)
- **Usage**:
  - Impulse wave: 5 waves in trend direction (1-2-3-4-5)
  - Corrective: 3 waves (A-B-C) or complex (W-X-Y)
- **Example**: Click successive pivot points to label waves; AI can suggest interpretations

#### `harmonicABCD`
- **Display Name**: Harmonic ABCD Pattern
- **Purpose**: Identify harmonic reversal patterns with Fibonacci relationships
- **Anchors**: 4 (points A, B, C, D)
- **Settings**:
  - `patternType` (`bat` | `butterfly` | `crab` | `gartley` | `deepCrab` | `shark` | `cypher`)
  - `showPotentialReversalZone` (boolean)
  - `przColor`
- **Fibonacci Ratios** (varies by pattern):
  - Bat: AB=0.382-0.5 BC, CD=1.618-2.618 AB, D=0.886 XA
  - Butterfly: AB=0.786 BC, CD=1.618-2.618 AB, D=1.272-1.618 XA
  - Crab: AB=0.382-0.618 BC, CD=1.618-2.618 AB, D=1.618 XA
- **Usage**: Find potential reversal points at D; trade entry at PRZ
- **Note**: Requires precise Fibonacci measurements; AI can validate ratios

#### `xabcdPattern`
- **Display Name**: XABCD Pattern
- **Purpose**: 5-point harmonic patterns (alternate bat, three drives, etc.)
- **Anchors**: 5 (X, A, B, C, D)
- **Settings**:
  - `patternType` (`alternateBat` | `threeDrives` | `fiveZero` | `shark`)
  - `showPRZ`
- **Usage**: Advanced harmonic patterns; D point is reversal zone

---

### Pitchfork Tools

Pitchforks (Andrews Pitchfork) create parallel channels from three points.

#### `pitchfork`
- **Display Name**: Pitchfork
- **Purpose**: Standard Andrews Pitchfork — three parallel lines
- **Anchors**: 3 (start point, middle point, end point)
- **Settings**:
  - `color`
  - `lineWidth`
  - `showMedian` (boolean) — show middle line
  - `showExtensions` (boolean) — extend lines beyond anchors
  - `extendLeft`
  - `extendRight`
- **Usage**:
  - Place middle line through median of price action
  - Upper and lower lines show reaction zones
  - Useful for channels and mean reversion
- **Placement**:
  1. Click significant high (or start of trend)
  2. Click significant low (or middle of channel)
  3. Click another high/low to complete fork

#### `schiffPitchfork`
- **Display Name**: Schiff Pitchfork
- **Purpose**: Modified pitchfork with adjusted parallelism
- **Anchors**: 3 (similar to standard pitchfork but offset)
- **Settings**: Same as pitchfork
- **Difference**: Parallel lines are calculated differently (Schiff method uses 0.5 factor)
- **Usage**: Often fits trends better than standard pitchfork

#### `modifiedPitchfork`
- **Display Name**: Modified Pitchfork
- **Purpose**: Another variant with different parallel calculation
- **Anchors**: 3
- **Settings**: Same as pitchfork
- **Difference**: Uses different midpoint calculation

#### `insidePitchfork`
- **Display Name**: Inside Pitchfork
- **Purpose**: Inverted pitchfork (median line through middle point)
- **Anchors**: 3
- **Settings**: Same as pitchfork
- **Usage**: Alternative channel drawing when standard pitchfork doesn't fit

---

### Text & Annotations

#### `text`
- **Display Name**: Text
- **Purpose**: Add plain text annotation at a point
- **Anchors**: 1 (position of text anchor)
- **Settings**:
  - `text` (string)
  - `color` (text color)
  - `backgroundColor`
  - `fontSize` (px)
  - `fontFamily`
  - `alignment` (`left`, `center`, `right`)
- **Usage**: Notes like "Bullish Divergence", "Support Held", "Earnings"
- **Editing**: Click to edit text inline

#### `callout`
- **Display Name**: Callout
- **Purpose**: Text with a leader line pointing to a chart point
- **Anchors**: 2 (text box position, anchor point on chart)
- **Settings**:
  - `text`
  - `color`
  - `backgroundColor`
  - `fontSize`
  - `arrowStyle` (`line` | `arrow`)
- **Usage**: Highlight specific candle with explanatory note

#### `note`
- **Display Name**: Note
- **Purpose**: Small sticky-note style annotation
- **Anchors**: 1 (position)
- **Settings**:
  - `text`
  - `color`
  - `backgroundColor`
  - `maxWidth`
- **Usage**: Quick memos; appears as small box with expandable content

#### `balloon`
- **Display Name**: Balloon
- **Purpose**: Text in a speech-bubble shape with pointer
- **Anchors**: 2 (anchor point, balloon position)
- **Settings**:
  - `text`
  - `color`
  - `backgroundColor`
  - `pointerDirection` (`up`, `down`, `left`, `right`)
- **Usage**: Informal annotations; highlight with description

#### `anchoredText`
- **Display Name**: Anchored Text
- **Purpose**: Text that stays anchored to a specific candle/price
- **Anchors**: 1 (anchor point)
- **Settings**: Same as `text`
- **Difference from `text`**: Moves with chart (data-space); regular `text` may be fixed to screen?

---

### Measurement Tools

#### `ruler`
- **Display Name**: Ruler / Measurement
- **Purpose**: Calculate price and time distance between two points
- **Anchors**: 2 (start, end)
- **Settings**:
  - `showPrice` (boolean)
  - `showTime` (boolean)
  - `showPercent` (boolean)
  - `color`
  - `lineWidth`
  - `textBackground`
- **Displayed Values**:
  - Price difference (absolute and %)
  - Time duration (in bars or actual time)
  - Angle/slope
- **Usage**: "This move was 25% in 48 hours"

#### `crossline`
- **Display Name**: Crossline
- **Purpose**: Perpendicular crosshairs at two points
- **Anchors**: 2
- **Settings**: `color`, `lineWidth`, `lineStyle`
- **Usage**: Measure vertical/horizontal distances simultaneously

#### `dateRange`
- **Display Name**: Date Range
- **Purpose**: Highlight a time period on the time axis
- **Anchors**: 2 (start time, end time)
- **Settings**:
  - `color`
  - `fillColor`
  - `fillOpacity`
  - `showLabel`
- **Usage**: Mark consolidation periods, time-based zones

#### `priceRangeTool`
- **Display Name**: Price Range Tool
- **Purpose**: Highlight a price zone across the full vertical range
- **Anchors**: 2 (upper price, lower price)
- **Settings**: `color`, `fillColor`, `fillOpacity`, `showLabels`
- **Usage**: Mark supply/demand zones; support/resistance bands

#### `riskReward`
- **Display Name**: Risk/Reward
- **Purpose**: Visualize risk-reward ratio for a potential trade
- **Anchors**: 3 (entry, stop loss, take profit)
- **Settings**:
  - `color`
  - `lineWidth`
  - `showRatio` (boolean)
  - `ratioTarget` (display desired RR, e.g., 2.0)
- **Display**:
  - Lines from entry to stop (risk) and entry to target (reward)
  - Ratio computed as reward/risk (absolute price distances)
- **Usage**: Evaluate trade setups; ensure RR meets criteria (e.g., 2:1)
- **Example**:
  - Entry at $50,000
  - Stop at $48,000 (risk = $2,000)
  - Target at $54,000 (reward = $4,000)
  - Ratio = 2.0

---

### Position Tools

#### `longPosition`
- **Display Name**: Long Position
- **Purpose**: Visualize a long trade setup (entry, stop, target)
- **Anchors**: 3 (entry point, stop loss point, take profit point)
- **Settings**:
  - `color` (usually green)
  - `lineWidth`
  - `showProfitLoss` (boolean)
  - `positionSize` (optional: for P&L calculation)
- **Display**:
  - Entry marker (dot)
  - Stop line below entry (red)
  - Target line above entry (green)
  - Box showing risk zone and profit zone
- **Usage**: Plan long entries; visualize risk/reward

#### `shortPosition`
- **Display Name**: Short Position
- **Purpose**: Visualize a short trade setup
- **Anchors**: 3 (entry, stop above entry, target below entry)
- **Settings**: Same as `longPosition`, default color red
- **Display**: Entry dot, stop above, target below
- **Usage**: Plan short entries

#### `forecast`
- **Display Name**: Forecast / Price Projection
- **Purpose**: Project future price based on recent trend
- **Anchors**: 2 (start point, recent point to define trend)
- **Settings**:
  - `projectionBars` (how many bars to project forward)
  - `color`
  - `lineWidth`
  - `lineStyle` (dashed for projection)
  - `confidence` (optional overlay)
- **Usage**: Linear extrapolation; not a trading signal but for visualization
- **Note**: Simple linear regression; should not be relied upon for actual predictions

---

### Utility Tools

#### `magnet`
- **Display Name**: Magnet
- **Purpose**: Toggle snapping to price/time grid when placing anchors
- **Mode**: Toggle (on/off)
- **Settings**:
  - `snapToPrice` (boolean)
  - `snapToTime` (boolean)
  - `priceGrid` (tick size, e.g., 0.5, 1, 5)
  - `timeGrid` (bar interval)
- **Usage**: Enable for precise alignment to candle OHLC; disable for freeform placement
- **Default**: Enabled

#### `lock`
- **Display Name**: Lock
- **Purpose**: Lock all drawings to prevent accidental edits
- **Mode**: Toggle
- **Behavior**: When locked, clicking drawings does nothing; no drag, no delete
- **Usage**: Freeze chart after analysis; prevent edits during presentation

#### `hide`
- **Display Name**: Hide Drawings
- **Purpose**: Toggle visibility of all drawings without deleting
- **Mode**: Toggle (show/hide all)
- **Usage**: Focus on price action without clutter

#### `eraser`
- **Display Name**: Eraser
- **Purpose**: Delete a single drawing by clicking it
- **Anchors**: 1 (click target drawing)
- **Settings**: None
- **Usage**: Remove specific drawing without selecting first

#### `clearAll`
- **Display Name**: Clear All
- **Purpose**: Remove all drawings from the current chart
- **Anchors**: 0 (instant action)
- **Confirmation**: May show confirmation dialog
- **Usage**: Start fresh; wipe clean
- **Warning**: Irreversible without undo

---

## Drawing Settings Reference

### Common Properties

| Property | Type | Description |
|----------|------|-------------|
| `color` | string (hex) | Line/border color (e.g., `#FF0000`) |
| `lineWidth` | number (1-10) | Stroke thickness in pixels |
| `lineStyle` | `solid` \| `dashed` \| `dotted` | Dash pattern |
| `fill` | boolean | Whether to fill shape interior |
| `fillColor` | string (hex) | Fill color (with opacity) |
| `fillOpacity` | number (0-1) | Fill transparency |
| `showLabel` | boolean | Display text labels on anchors/levels |

### Indicator-Specific

| Tool | Unique Settings |
|------|-----------------|
| Fibonacci tools | `levels` (number[]), `showBackground` |
| Gann Fan | `angles` (number[] — degrees) |
| Elliott Wave | `waveType`, `waveLabels`, `showWaveNumbers` |
| Pitchfork | `showMedian`, `showExtensions` |
| Risk/Reward | `showRatio`, `ratioTarget` |
| Text | `text`, `fontSize`, `alignment`, `backgroundColor` |

---

## Data Model

### Drawing Object Structure

```typescript
interface Drawing {
  id: string;                    // Unique identifier
  tool: DrawingTool;            // Tool ID string
  dataPoints: DataPoint[];      // SOURCE OF TRUTH: array of {time, price}
  settings: DrawingSettings;   // Appearance and tool-specific config
  text?: string;               // For text tools
  locked: boolean;             // Prevent edits
  hidden: boolean;             // Visibility toggle
  createdAt: string;           // ISO timestamp
  updatedAt: string;           // ISO timestamp
}
```

### DataPoint

```typescript
interface DataPoint {
  time: number;    // Unix timestamp in seconds
  price: number;   // Actual price value
}
```

---

## Best Practices

1. **Use appropriate tools** — Fibonacci for retracements, not rectangles; Risk/Reward for trade planning
2. **Consistent colors** — Use a color scheme (e.g., green for bullish, red for bearish, blue for neutral)
3. **Limit clutter** — Hide or delete old drawings; use layers if available
4. **Lock important drawings** — Once a key level is drawn, lock it to avoid accidental moves
5. **Leverage data-space** — Drawings survive timeframe changes; use this to mark levels that span multiple timeframes
6. **Combine tools** — Use Trendline + Fibonacci Retracement together for complete analysis

---

## Common Use Cases

### 1. Identifying Support/Resistance
- Draw `horizontalRay` at price levels where price reversed multiple times
- Use `trendline` connecting swing lows (support) or swing highs (resistance)
- Add `fibRetracement` from major swing high to low to see confluences

### 2. Channel Trading
- Use `parallelChannel` to fit price in a channel
- Or `pitchfork` for median-based channels
- Trade bounces off lower/upper boundaries

### 3. Breakout Confirmation
- Draw `rectangle` around consolidation
- When price breaks out with volume, the rectangle shows the explosion
- Use `fibExtension` to project targets from the breakout move

### 4. Elliott Wave Analysis
- Use `elliottWave` to label 5-wave impulse and 3-wave correction
- Identify wave 3 extensions with `fibExtension`
- Look for wave 5 ending at `fibExtension` 161.8% or `fibRetracement` 61.8% of waves 1-3

### 5. Harmonic Patterns
- Draw `harmonicABCD` or `xabcdPattern` to spot PRZ
- Wait for price reaction at PRZ for reversal trades
- Validate pattern ratios automatically (tool shows if valid)

### 6. Trade Planning with Risk/Reward
- Place `longPosition` or `shortPosition` tool
- Set entry, stop, target → see RR ratio
- Only take trades with RR ≥ 2:1

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Delete` / `Backspace` | Delete selected drawing |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Escape` | Deselect / cancel current tool |
| `L` | Lock/unlock selected |
| `H` | Hide/show selected |
| `1-9` | Quick-select favorite tools (configurable) |

---

## Persistence & Storage

Drawings are stored per user and per symbol/timeframe combination:
- **Key pattern**: `drawings:{userId}:{exchange}:{symbol}:{interval}`
- **Backend**: PostgreSQL `ai.user_drawings` table (or Redis with persistence)
- **Sync**: Saved automatically on change; fetched on chart load
- **Export/Import**: Possible via settings (JSON format)

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Drawing not appearing | Hidden or locked | Check visibility, unlock |
| Can't delete drawing | Locked | Unlock first |
| Drawing misplaced after timeframe change | Using pixel-space (legacy) | All new drawings use data-space; contact support if old drawings persist |
| Too many drawings slow chart | Performance | Hide or delete unused drawings |
| Cannot add more anchors | Tool already committed | Use undo and restart |

---

## References

- **Function Calling**: See `LMView_Function_Calling.md` for programmatic usage
- **Technical Indicators**: `LMView_Technical_Indicators.md`
- **Glossary**: `LMView_Glossary.md`
