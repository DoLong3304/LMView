import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

export type LayoutType = "single" | "split-v" | "split-h" | "quad" | "three-v" | "three-h" | "six";

export interface ChartInstance {
  id: string;
  symbol: string;
  timeframe: string;
  chartType?: string;
}

interface LayoutState {
  type: LayoutType;
  charts: ChartInstance[];
  activeChartId: string | null;
  syncTimeScale: boolean;
}

interface LayoutContextValue {
  state: LayoutState;
  setType: (type: LayoutType) => void;
  addChart: (chart: Partial<ChartInstance>) => void;
  removeChart: (id: string) => void;
  updateChart: (id: string, updates: Partial<ChartInstance>) => void;
  setActiveChart: (id: string) => void;
  setSyncTimeScale: (sync: boolean) => void;
}

const LayoutContext = createContext<LayoutContextValue | null>(null);

export function LayoutProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<LayoutState>({
    type: "single",
    charts: [{ id: "main", symbol: "BTCUSDT", timeframe: "1h" }],
    activeChartId: "main",
    syncTimeScale: false,
  });

  const setType = useCallback((type: LayoutType) => {
    setState((prev) => {
      const maxCharts = getMaxCharts(type);
      const charts = prev.charts.slice(0, maxCharts);
      return { ...prev, type, charts };
    });
  }, []);

  const addChart = useCallback((chart: Partial<ChartInstance>) => {
    setState((prev) => {
      const id = `chart-${Date.now()}`;
      const newChart: ChartInstance = {
        id,
        symbol: chart.symbol ?? "BTCUSDT",
        timeframe: chart.timeframe ?? "1h",
        chartType: chart.chartType,
      };
      return { ...prev, charts: [...prev.charts, newChart], activeChartId: id };
    });
  }, []);

  const removeChart = useCallback((id: string) => {
    setState((prev) => {
      const charts = prev.charts.filter((c) => c.id !== id);
      const activeChartId = prev.activeChartId === id
        ? (charts[0]?.id ?? null)
        : prev.activeChartId;
      return { ...prev, charts, activeChartId };
    });
  }, []);

  const updateChart = useCallback((id: string, updates: Partial<ChartInstance>) => {
    setState((prev) => ({
      ...prev,
      charts: prev.charts.map((c) => (c.id === id ? { ...c, ...updates } : c)),
    }));
  }, []);

  const setActiveChart = useCallback((id: string) => {
    setState((prev) => ({ ...prev, activeChartId: id }));
  }, []);

  const setSyncTimeScale = useCallback((sync: boolean) => {
    setState((prev) => ({ ...prev, syncTimeScale: sync }));
  }, []);

  return (
    <LayoutContext.Provider value={{ state, setType, addChart, removeChart, updateChart, setActiveChart, setSyncTimeScale }}>
      {children}
    </LayoutContext.Provider>
  );
}

export function useLayout(): LayoutContextValue {
  const ctx = useContext(LayoutContext);
  if (!ctx) throw new Error("useLayout must be used within LayoutProvider");
  return ctx;
}

function getMaxCharts(type: LayoutType): number {
  switch (type) {
    case "single": return 1;
    case "split-v": case "split-h": return 2;
    case "quad": case "three-v": case "three-h": return 3;
    case "six": return 6;
    default: return 1;
  }
}