# Drawing Tools Update Guide
// This file adds support for additional drawing tools

// Add to MULTI_CLICK_NEEDED in ChartOverlay.tsx:
const MULTI_CLICK_NEEDED: Record<string, boolean> = {
  elliottWave: true,
  harmonicABCD: true,
  xabcdPattern: true,
  pitchfork: true,
  gannFan: true,
  gannSquare: true,
  fibExtension: true,
  fibTimezone: true,
};

// Add to requiredPoints in ChartOverlay.tsx:
if (activeTool === 'pitchfork') return 3;
if (activeTool === 'gannFan') return 3;
if (activeTool === 'gannSquare') return 4;
if (activeTool === 'fibExtension') return 3;
if (activeTool === 'fibTimezone') return 3;

// Add new translations to en.ts and vi.ts:
pitchfork: "Andrews Pitchfork",
gannFan: "Gann Fan", 
gannSquare: "Gann Square",
fibExtension: "Fibonacci Extension",
fibTimezone: "Fibonacci Timezone",

// Add to DrawingToolbar.tsx labelKey translations (en.ts):
gann: "Gann Tools",
advancedShapes: "Advanced Shapes",
harmonicPatterns: "Harmonic Patterns",

// Vietnamese (vi.ts):
gann: "Công cụ Gann",
advancedShapes: "Hình dạng nâng cao",
harmonicPatterns: "Mẫu hài hòa",