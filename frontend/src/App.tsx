import React, { useState, useCallback, useEffect, useRef } from "react";
import CandlestickChart from "./components/CandlestickChart";
import DrawingToolbar from "./components/DrawingToolbar";
import ChartOverlay from "./components/ChartOverlay";
import DrawingContextToolbar from "./components/DrawingContextToolbar";
import { ReplayControls } from "./components/ReplayControls";
import { ReplayButton } from "./components/ReplayButton";
import Header from "./components/Header";
import Watchlist from "./components/Watchlist";
import OverviewChart from "./components/OverviewChart";
import { DEFAULT_TOOL_SETTINGS, type ToolSettings } from "./components/ToolSettingsPopup";
import { fetchTickers, fetchSymbols } from "./services/marketDataService";
import { loadFromStorage, saveToStorage } from "./utils/storageHelpers";
import { loadDrawings, saveDrawings, deleteDrawings } from "./services/chartStorageService";
import { useChartKeyboardShortcuts } from "./hooks/useChartKeyboardShortcuts";
import { useDrawingToolbarPosition } from "./hooks/useDrawingToolbarPosition";
import { useReplayMode } from "./hooks/useReplayMode";
import { useI18n } from "./i18n";
import type { Candle, Drawing, SymbolInfo, Ticker, WatchlistFilter } from "./types";

const FALLBACK_SYMBOLS = [
  "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
  "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT",
];

interface WatchlistItemData {
  symbol: string;
  price: number;
  change: number;
  color: "green" | "red" | "gray";
}

function buildWatchlist(symbolNames: string[]): WatchlistItemData[] {
  return symbolNames.map((s) => ({
    symbol: s,
    price: 0,
    change: 0,
    color: "gray" as const,
  }));
}

const TradingDashboard: React.FC = () => {
  const { t } = useI18n();
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const [activeTool, setActiveTool] = useState("cursor");
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [selectedDrawingIds, setSelectedDrawingIds] = useState<(string | number)[]>([]);
  const [magnetEnabled, setMagnetEnabled] = useState(false);
  const [currentTimeframe, setCurrentTimeframe] = useState("1m");
  const [isDrawing, setIsDrawing] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string>(() => {
    const stored = loadFromStorage("app_selectedSymbol", "BTCUSDT");
    if (stored && !stored.endsWith("USDT")) return "BTCUSDT";
    return stored;
  });
  const [toolSettings, setToolSettings] = useState<Record<string, ToolSettings>>(() =>
    loadFromStorage(
      "app_toolSettings",
      JSON.parse(JSON.stringify(DEFAULT_TOOL_SETTINGS)),
    ),
  );
  const [starredSymbols, setStarredSymbols] = useState<string[]>(() =>
    loadFromStorage("app_starred", []),
  );
  const [watchlistFilter, setWatchlistFilter] = useState<WatchlistFilter>("all");
  const [symbols, setSymbols] = useState<string[]>(FALLBACK_SYMBOLS);
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItemData[]>(() =>
    buildWatchlist(FALLBACK_SYMBOLS),
  );
  const [showNavDrawer, setShowNavDrawer] = useState(false);
  const [connError, setConnError] = useState(false);

  // Load available symbols from backend on mount
  useEffect(() => {
    fetchSymbols()
      .then((list: SymbolInfo[]) => {
        const names = list.map((s) => s.symbol);
        if (names.length > 0) {
          setSymbols(names);
          setWatchlistItems(buildWatchlist(names));
        }
        setConnError(false);
      })
      .catch(() => {
        setConnError(true);
      });
  }, []);

  // Fetch live ticker prices for the watchlist
  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      fetchTickers()
        .then((tickers: Ticker[]) => {
          if (cancelled) return;
          const map: Record<string, Ticker> = {};
          tickers.forEach((tk) => {
            map[tk.symbol] = tk;
          });
          setWatchlistItems((prev) =>
            prev.map((item) => {
              const tick = map[item.symbol];
              if (!tick) return item;
              return {
                ...item,
                price: tick.price,
                change: tick.change24h != null ? tick.change24h : item.change,
                color:
                  tick.price > 0
                    ? (tick.change24h ?? 0) >= 0
                      ? "green"
                      : "red"
                    : item.color,
              };
            }),
          );
        })
        .catch(() => {
          if (!cancelled) setConnError(true);
        });
    };
    refresh();
    const id = setInterval(refresh, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  // Persist settings to localStorage
  useEffect(() => { saveToStorage("app_toolSettings", toolSettings); }, [toolSettings]);
  useEffect(() => { saveToStorage("app_starred", starredSymbols); }, [starredSymbols]);
  useEffect(() => { saveToStorage("app_selectedSymbol", selectedSymbol); }, [selectedSymbol]);

  // Load drawings when symbol or timeframe changes
  useEffect(() => {
    const loadDrawingsForChart = async () => {
      try {
        const loaded = await loadDrawings({
          symbol: selectedSymbol,
          timeframe: currentTimeframe,
          storageVersion: 1,
        });
        setDrawings(loaded);
      } catch (error) {
        console.error('[App] Failed to load drawings:', error);
        setDrawings([]);
      }
    };

    loadDrawingsForChart();
  }, [selectedSymbol, currentTimeframe]);

  // Save drawings when they change (debounced)
  useEffect(() => {
    const timeoutId = setTimeout(async () => {
      try {
        await saveDrawings(
          {
            symbol: selectedSymbol,
            timeframe: currentTimeframe,
            storageVersion: 1,
          },
          drawings
        );
      } catch (error) {
        console.error('[App] Failed to save drawings:', error);
      }
    }, 500); // Debounce 500ms

    return () => clearTimeout(timeoutId);
  }, [drawings, selectedSymbol, currentTimeframe]);

  // Keyboard shortcuts with command history - initialize early
  const handleCancelDrawing = useCallback(() => {
    setIsDrawing(false);
  }, []);

  const handleDeleteDrawingsInternal = useCallback(
    (ids: (string | number)[]) => {
      setDrawings((prev) => prev.filter((d) => !ids.includes(d.id)));
      setSelectedDrawingIds([]);
    },
    []
  );

  const handleSaveDrawings = useCallback(async () => {
    try {
      await saveDrawings(
        {
          symbol: selectedSymbol,
          timeframe: currentTimeframe,
          storageVersion: 1,
        },
        drawings
      );
      console.log('[App] Drawings saved successfully');
    } catch (error) {
      console.error('[App] Failed to save drawings:', error);
    }
  }, [selectedSymbol, currentTimeframe, drawings]);

  const { addCommand } = useChartKeyboardShortcuts({
    drawings,
    selectedDrawingIds,
    onSetDrawings: setDrawings,
    onSetSelectedDrawingIds: setSelectedDrawingIds,
    onDeleteDrawings: handleDeleteDrawingsInternal,
    onSaveDrawings: handleSaveDrawings,
    isDrawing,
    onCancelDrawing: handleCancelDrawing,
    chartContainerRef,
  });

  const handleAddDrawing = useCallback(
    (d: Drawing) => {
      setDrawings((prev) => [...prev, d]);

      // Record add command
      addCommand({
        type: 'add',
        timestamp: Date.now(),
        drawingId: d.id,
        after: d,
        description: `Add ${d.tool}`,
      });
    },
    [addCommand],
  );

  const handleUpdateDrawing = useCallback(
    (id: string | number, updates: Partial<Drawing>) => {
      setDrawings((prev) => {
        const oldDrawing = prev.find(d => d.id === id);
        const newDrawings = prev.map((d) => (d.id === id ? { ...d, ...updates } : d));

        // Record update command
        if (oldDrawing) {
          const newDrawing = newDrawings.find(d => d.id === id);
          addCommand({
            type: 'update',
            timestamp: Date.now(),
            drawingId: id,
            before: oldDrawing,
            after: newDrawing,
            description: `Update ${oldDrawing.tool}`,
          });
        }

        return newDrawings;
      });
    },
    [addCommand]
  );

  const handleDeleteDrawing = useCallback(
    (id: string | number) => {
      setDrawings((prev) => {
        const deletedDrawing = prev.find(d => d.id === id);

        // Record delete command
        if (deletedDrawing) {
          addCommand({
            type: 'delete',
            timestamp: Date.now(),
            drawingId: id,
            before: deletedDrawing,
            description: `Delete ${deletedDrawing.tool}`,
          });
        }

        return prev.filter((d) => d.id !== id);
      });
      setSelectedDrawingIds((prev) => prev.filter((sid) => sid !== id));
    },
    [addCommand]
  );

  const handleDeleteDrawings = handleDeleteDrawingsInternal;

  const handleClearAll = useCallback(async () => {
    setDrawings([]);
    setActiveTool("cursor");
    try {
      await deleteDrawings({
        symbol: selectedSymbol,
        timeframe: currentTimeframe,
        storageVersion: 1,
      });
    } catch (error) {
      console.error('[App] Failed to delete drawings:', error);
    }
  }, [selectedSymbol, currentTimeframe]);

  const handleLockAll = useCallback(() => {
    setDrawings((prev) =>
      prev.map((d) => ({ ...d, locked: !d.locked }))
    );
  }, []);

  const handleHideAll = useCallback(() => {
    setDrawings((prev) =>
      prev.map((d) => ({ ...d, hidden: !d.hidden }))
    );
  }, []);

  const handleSymbolSelect = useCallback((symbol: string) => {
    setSelectedSymbol(symbol);
    // Drawings will be loaded by useEffect
  }, []);

  const handleTimeframeChange = useCallback((timeframe: string) => {
    setCurrentTimeframe(timeframe);
    // Drawings will be loaded by useEffect
  }, []);
  const handleToolSettingsChange = useCallback((toolId: string, newSettings: ToolSettings) => {
    setToolSettings((prev) => ({ ...prev, [toolId]: newSettings }));
  }, []);

  const handleToggleStar = useCallback((symbol: string) => {
    setStarredSymbols((prev) =>
      prev.includes(symbol)
        ? prev.filter((s) => s !== symbol)
        : [...prev, symbol],
    );
  }, []);

  // State lifted from CandlestickChart for Overview + DrawingToolbar gating
  const [chartActiveTab, setChartActiveTab] = useState("chart");
  const [chartCandles, setChartCandles] = useState<Candle[]>([]);

  // Chart API refs for floating toolbar positioning
  const [chartApi, setChartApi] = useState<any>(null);
  const [candleSeries, setCandleSeries] = useState<any>(null);

  // Replay mode state and hook
  const {
    isReplayActive,
    isPlaying,
    playbackSpeed,
    currentIndex,
    totalCandles,
    startReplay,
    exitReplay,
    togglePlayPause,
    stepForward,
    changeSpeed,
  } = useReplayMode({
    onCandleUpdate: useCallback((candle: Candle) => {
      // Update chart with replay candle
      if (candleSeries) {
        candleSeries.update(candle);
      }
    }, [candleSeries]),
  });

  // Replay selection mode state
  const [isReplaySelectionMode, setIsReplaySelectionMode] = useState(false);

  // Handle replay button click - enter selection mode
  const handleReplayButtonClick = useCallback(() => {
    if (isReplayActive) {
      // Already in replay mode, exit it
      exitReplay();
    } else {
      // Enter selection mode
      setIsReplaySelectionMode(true);
      setActiveTool('cursor'); // Switch to cursor for selection
    }
  }, [isReplayActive, exitReplay]);

  // Handle candle click in selection mode
  const handleReplayStartSelect = useCallback((timestamp: number) => {
    if (isReplaySelectionMode && chartCandles.length > 0) {
      // Find the index of the clicked candle
      const clickedIndex = chartCandles.findIndex(c => c.time === timestamp);
      if (clickedIndex >= 0) {
        // Get candles from clicked point to current
        const replayBuffer = chartCandles.slice(clickedIndex);

        // Clear chart and set initial candle
        if (candleSeries) {
          candleSeries.setData([replayBuffer[0]]);
        }

        // Start replay from this point
        startReplay(replayBuffer, 0);
        setIsReplaySelectionMode(false);
      }
    }
  }, [isReplaySelectionMode, chartCandles, startReplay, candleSeries]);

  // Exit selection mode when replay starts or user cancels
  useEffect(() => {
    if (isReplayActive) {
      setIsReplaySelectionMode(false);
    }
  }, [isReplayActive]);

  // Restore chart data when exiting replay mode
  useEffect(() => {
    if (!isReplayActive && candleSeries && chartCandles.length > 0) {
      // Restore full chart data when exiting replay
      candleSeries.setData(chartCandles);
    }
  }, [isReplayActive, candleSeries, chartCandles]);

  // Get selected drawing for context toolbar
  const selectedDrawing = selectedDrawingIds.length === 1
    ? drawings.find(d => d.id === selectedDrawingIds[0]) || null
    : null;

  // Calculate toolbar position
  const toolbarPosition = useDrawingToolbarPosition({
    drawing: selectedDrawing,
    chartApi,
    candleSeries,
    offset: { x: 10, y: -60 },
  });

  // Handle alert creation (placeholder for now)
  const handleAddAlert = useCallback(() => {
    // TODO: Implement alert dialog in next session
    console.log('[App] Add alert for drawing:', selectedDrawing?.id);
    alert('Alert feature will be implemented in Step 5');
  }, [selectedDrawing]);

  // Resizable right sidebar
  const SIDEBAR_MIN = 280;
  const SIDEBAR_MAX = 520;
  const SIDEBAR_DEFAULT = 340;
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const dragging = useRef(false);

  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const newW = window.innerWidth - ev.clientX;
      setSidebarWidth(Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, newW)));
    };
    const onUp = () => {
      dragging.current = false;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, []);

  const isChartTab = chartActiveTab === "chart";

  return (
    <div className="bg-gray-900 text-white h-screen font-sans flex flex-col overflow-hidden">
      <Header showNavDrawer={showNavDrawer} onToggleDrawer={setShowNavDrawer} />

      {connError && (
        <div className="px-4 py-2 bg-red-900/50 border-b border-red-700/50 flex items-center justify-between">
          <span className="text-xs text-red-300">
            {t("connectionError")}
          </span>
          <button
            onClick={() => {
              setConnError(false);
              fetchSymbols()
                .then((list: SymbolInfo[]) => {
                  const names = list.map((s) => s.symbol);
                  if (names.length > 0) {
                    setSymbols(names);
                    setWatchlistItems(buildWatchlist(names));
                  }
                })
                .catch(() => setConnError(true));
            }}
            className="text-xs text-red-300 hover:text-white underline ml-4"
          >
            {t("retry")}
          </button>
        </div>
      )}

      <main
        className="flex-grow overflow-hidden flex"
        style={{ padding: "12px 16px" }}
      >
        {/* Drawing Toolbar — only visible on Chart tab */}
        {isChartTab && (
          <div className="mr-2 flex-shrink-0">
            {/* Replay Mode Button */}
            <ReplayButton
              onClick={handleReplayButtonClick}
              disabled={isReplaySelectionMode}
            />

            <DrawingToolbar
              activeTool={activeTool}
              onToolChange={setActiveTool}
              onClearAll={handleClearAll}
              onDeleteSelected={() => handleDeleteDrawings(selectedDrawingIds)}
              selectedDrawingIds={selectedDrawingIds}
              onLockAll={handleLockAll}
              onHideAll={handleHideAll}
              magnetEnabled={magnetEnabled}
              onMagnetToggle={() => setMagnetEnabled((prev) => !prev)}
              toolSettings={toolSettings}
              onToolSettingsChange={handleToolSettingsChange}
            />
          </div>
        )}

        {/* Chart area */}
        <div className="flex-grow flex flex-col" style={{ minWidth: 0 }} ref={chartContainerRef}>
          <div
            className="bg-gray-900 rounded-lg shadow-lg flex-grow"
            style={{ minHeight: 0 }}
          >
            <CandlestickChart
              symbol={selectedSymbol}
              symbols={symbols}
              starredSymbols={starredSymbols}
              onToggleStar={handleToggleStar}
              onSymbolChange={handleSymbolSelect}
              onActiveTabChange={setChartActiveTab}
              onCandlesChange={setChartCandles}
              onTimeframeChange={handleTimeframeChange}
              isReplayActive={isReplayActive}
            >
              {(chartApiRef, candleSeriesRef) => {
                // Store refs for toolbar positioning
                if (chartApiRef !== chartApi) setChartApi(chartApiRef);
                if (candleSeriesRef !== candleSeries) setCandleSeries(candleSeriesRef);

                return (
                  <>
                    <ChartOverlay
                      activeTool={isChartTab ? activeTool : "cursor"}
                      drawings={drawings}
                      onAddDrawing={handleAddDrawing}
                      onUpdateDrawing={handleUpdateDrawing}
                      onDeleteDrawing={handleDeleteDrawing}
                      toolSettings={toolSettings}
                      chartApi={chartApiRef}
                      candleSeries={candleSeriesRef}
                      magnetEnabled={magnetEnabled}
                      selectedDrawingIds={selectedDrawingIds}
                      onSetSelectedDrawingIds={setSelectedDrawingIds}
                      isReplaySelectionMode={isReplaySelectionMode}
                      onReplayStartSelect={handleReplayStartSelect}
                    />
                    {/* Floating Context Toolbar */}
                    {selectedDrawing && isChartTab && (
                      <DrawingContextToolbar
                        drawing={selectedDrawing}
                        position={toolbarPosition}
                        onUpdateDrawing={(updates) => handleUpdateDrawing(selectedDrawing.id, updates)}
                        onDelete={() => handleDeleteDrawing(selectedDrawing.id)}
                        onAddAlert={handleAddAlert}
                        onClose={() => setSelectedDrawingIds([])}
                      />
                    )}

                    {/* Replay Controls */}
                    {isReplayActive && (
                      <ReplayControls
                        isPlaying={isPlaying}
                        playbackSpeed={playbackSpeed}
                        currentIndex={currentIndex}
                        totalCandles={totalCandles}
                        onPlayPause={togglePlayPause}
                        onStepForward={stepForward}
                        onSpeedChange={changeSpeed}
                        onExit={exitReplay}
                      />
                    )}
                  </>
                );
              }}
            </CandlestickChart>
          </div>
        </div>

        {/* Drag handle */}
        <div
          onMouseDown={onDragStart}
          className="flex-shrink-0 cursor-col-resize flex items-center justify-center group"
          style={{ width: 6, margin: "0 2px" }}
        >
          <div className="w-[3px] h-10 rounded-full bg-gray-700 group-hover:bg-blue-500 transition-colors" />
        </div>

        {/* Right sidebar: Watchlist + Overview */}
        <aside
          className="flex-shrink-0 flex flex-col gap-2 overflow-hidden"
          style={{ width: sidebarWidth }}
        >
          <div className="min-h-0" style={{ flex: 6.5 }}>
            <Watchlist
              items={watchlistItems}
              selectedSymbol={selectedSymbol}
              starredSymbols={starredSymbols}
              filter={watchlistFilter}
              onFilterChange={setWatchlistFilter}
              onSymbolSelect={handleSymbolSelect}
              onToggleStar={handleToggleStar}
            />
          </div>
          <div
            className="min-h-0 bg-gray-800 rounded-lg overflow-y-auto"
            style={{ flex: 3.5 }}
          >
            <OverviewChart symbol={selectedSymbol} candles={chartCandles} />
          </div>
        </aside>
      </main>
    </div>
  );
};

export default TradingDashboard;
