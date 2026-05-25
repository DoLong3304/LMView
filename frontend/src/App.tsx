import React, { useState, useCallback, useEffect, useLayoutEffect, useRef } from "react";
import Header from "@/components/layout/Header";
import LeftSidebar from "@/components/layout/LeftSidebar";
import { CandlestickChart } from "@/features/chart";
import ChartOverlay from "@/features/drawing/components/ChartOverlay";
import DrawingContextToolbar from "@/features/drawing/components/DrawingContextToolbar";
import { ReplayControls } from "@/features/replay/components/ReplayControls";
import RightPanel from "@/features/watchlist/components/RightPanel";
import NewsPage from "@/pages/NewsPage";
import { FALLBACK_SYMBOLS } from "@/constants/market";
import { fetchTickers, fetchSymbols } from "@/services/marketDataService";
import { loadFromStorage, saveToStorage } from "@/utils/storageHelpers";
import { loadDrawings, saveDrawings, deleteDrawings } from "@/services/chartStorageService";
import { useChartKeyboardShortcuts } from "@/hooks/useChartKeyboardShortcuts";
import { useDrawingToolbarPosition } from "@/hooks/useDrawingToolbarPosition";
import { useReplayMode } from "@/hooks/useReplayMode";
import { useI18n } from "@/i18n";
import type { Candle, ChartType, Drawing, SymbolInfo, Ticker, TimeframeKey } from "@/types";

interface WatchlistItemData {
  symbol: string;
  price: number;
  change: number;
  color: "green" | "red" | "gray";
}

type ThemeMode = "dark" | "light";
type AppView = "charts" | "marketsNews";

const DESKTOP_LAYOUT_QUERY = "(min-width: 1024px)";

function getInitialTheme(): ThemeMode {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem("app_theme");
  if (stored === "dark" || stored === "light") return stored;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function isDesktopLayout(): boolean {
  if (typeof window === "undefined") return true;
  return window.matchMedia(DESKTOP_LAYOUT_QUERY).matches;
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
  const [themeMode, setThemeMode] = useState<ThemeMode>(getInitialTheme);
  const [isDesktop, setIsDesktop] = useState(isDesktopLayout);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(isDesktopLayout);
  const [isDrawingToolbarOpen, setIsDrawingToolbarOpen] = useState(isDesktopLayout);
  const [appView, setAppView] = useState<AppView>("charts");
  const [activeTool, setActiveTool] = useState("cursor");
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [selectedDrawingIds, setSelectedDrawingIds] = useState<(string | number)[]>([]);
  const [magnetEnabled, setMagnetEnabled] = useState(false);
  const [currentTimeframe, setCurrentTimeframe] = useState<TimeframeKey>("1m");
  const [chartType, setChartType] = useState<ChartType>("candles");
  const [isDrawing, setIsDrawing] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string>(() => {
    const stored = loadFromStorage("app_selectedSymbol", "BTCUSDT");
    if (stored && !stored.endsWith("USDT")) return "BTCUSDT";
    return stored;
  });
  const [starredSymbols, setStarredSymbols] = useState<string[]>(() =>
    loadFromStorage("app_starred", []),
  );
  const [symbols, setSymbols] = useState<string[]>([...FALLBACK_SYMBOLS]);
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItemData[]>(() =>
    buildWatchlist([...FALLBACK_SYMBOLS]),
  );
  const [connError, setConnError] = useState(false);

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = themeMode;
    document.documentElement.style.colorScheme = themeMode;
    saveToStorage("app_theme", themeMode);
  }, [themeMode]);

  useEffect(() => {
    const mediaQuery = window.matchMedia(DESKTOP_LAYOUT_QUERY);
    const syncLayout = () => {
      const desktop = mediaQuery.matches;
      setIsDesktop(desktop);
      setIsRightPanelOpen(desktop);
      setIsDrawingToolbarOpen(desktop);
    };

    syncLayout();
    mediaQuery.addEventListener("change", syncLayout);
    return () => mediaQuery.removeEventListener("change", syncLayout);
  }, []);

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

  const handleDeleteDrawings = useCallback(
    (ids: (string | number)[]) => {
      if (ids.length === 0) return;
      const deletedDrawings = drawings.filter((d) => ids.includes(d.id));
      addCommand({
        type: 'delete',
        timestamp: Date.now(),
        drawingIds: ids,
        before: deletedDrawings,
        description: `Delete ${ids.length} drawing(s)`,
      });
      handleDeleteDrawingsInternal(ids);
    },
    [addCommand, drawings, handleDeleteDrawingsInternal],
  );

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

  const handleTimeframeChange = useCallback((timeframe: TimeframeKey) => {
    setCurrentTimeframe(timeframe);
    // Drawings will be loaded by useEffect
  }, []);

  const handleToggleStar = useCallback((symbol: string) => {
    setStarredSymbols((prev) =>
      prev.includes(symbol)
        ? prev.filter((s) => s !== symbol)
        : [...prev, symbol],
    );
  }, []);

  const handleToggleTheme = useCallback(() => {
    setThemeMode((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  // State lifted from CandlestickChart for Overview + DrawingToolbar data.
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
    if (isReplaySelectionMode) {
      setIsReplaySelectionMode(false);
    } else if (isReplayActive) {
      // Already in replay mode, exit it
      exitReplay();
    } else {
      // Enter selection mode
      setIsReplaySelectionMode(true);
      setActiveTool('cursor'); // Switch to cursor for selection
    }
  }, [isReplayActive, isReplaySelectionMode, exitReplay]);

  // Handle candle click in selection mode
  const handleReplayStartSelect = useCallback((timestamp: number) => {
    if (isReplaySelectionMode && chartCandles.length > 0) {
      // Find the nearest candle to the clicked chart coordinate.
      const clickedIndex = chartCandles.reduce((bestIndex, candle, index) => {
        const bestDistance = Math.abs(chartCandles[bestIndex].time - timestamp);
        const currentDistance = Math.abs(candle.time - timestamp);
        return currentDistance < bestDistance ? index : bestIndex;
      }, 0);
      if (clickedIndex >= 0) {
        const visibleHistory = chartCandles.slice(0, clickedIndex + 1);

        // Hide future candles; replay will append them back one by one.
        if (candleSeries) {
          candleSeries.setData(visibleHistory);
        }

        // Start replay from this point
        startReplay(chartCandles, clickedIndex);
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
    alert(t("alertFeatureSoon"));
  }, [selectedDrawing, t]);

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

  const isChartsView = appView === "charts";
  const showDrawingToolbar = isChartsView && (isDesktop || isDrawingToolbarOpen);
  const showRightPanel = isChartsView && isRightPanelOpen;
  const compactRightPanelWidth = typeof window === "undefined"
    ? 340
    : Math.min(360, Math.floor(window.innerWidth * 0.92));

  return (
    <div className="bg-gray-900 text-white h-screen flex flex-col overflow-hidden">
      <Header
        selectedSymbol={selectedSymbol}
        symbols={symbols}
        onSymbolChange={handleSymbolSelect}
        timeframe={currentTimeframe}
        onTimeframeChange={handleTimeframeChange}
        chartType={chartType}
        onChartTypeChange={setChartType}
        themeMode={themeMode}
        onThemeToggle={handleToggleTheme}
        isCompactLayout={!isDesktop}
        isDrawingToolbarOpen={isDrawingToolbarOpen}
        onToggleDrawingToolbar={() => setIsDrawingToolbarOpen((open) => !open)}
        isRightPanelOpen={isRightPanelOpen}
        onToggleRightPanel={() => setIsRightPanelOpen((open) => !open)}
        activeView={appView}
        onViewChange={setAppView}
      />

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

      {/* Main content area */}
      <main className="relative flex-1 flex overflow-hidden min-h-0">
        {!isChartsView ? (
          <div className="flex-1 min-w-0 overflow-hidden">
            <NewsPage />
          </div>
        ) : (
          <>
        {/* Chart area */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0" ref={chartContainerRef}>
          <div className="flex-1 bg-gray-900">
            <CandlestickChart
              symbol={selectedSymbol}
              timeframe={currentTimeframe}
              symbols={symbols}
              starredSymbols={starredSymbols}
              onToggleStar={handleToggleStar}
              onSymbolChange={handleSymbolSelect}
              onCandlesChange={setChartCandles}
              onTimeframeChange={handleTimeframeChange}
              themeMode={themeMode}
              chartType={chartType}
              isReplayActive={isReplayActive}
            >
              {(chartApiRef, candleSeriesRef) => {
                if (chartApiRef !== chartApi) setChartApi(chartApiRef);
                if (candleSeriesRef !== candleSeries) setCandleSeries(candleSeriesRef);

                return (
                  <>
                    {showDrawingToolbar && (
                      <div className="absolute left-2 top-2 z-[120] max-h-[calc(100%-1rem)] rounded-lg overflow-hidden border border-gray-700 shadow-2xl">
                        <LeftSidebar
                          activeTool={activeTool as any}
                          onToolChange={setActiveTool as any}
                          onClearAll={handleClearAll}
                          onDeleteSelected={() => handleDeleteDrawings(selectedDrawingIds)}
                          selectedDrawingIds={selectedDrawingIds.map(String)}
                          onLockAll={handleLockAll}
                          onHideAll={handleHideAll}
                          magnetEnabled={magnetEnabled}
                          onMagnetToggle={() => setMagnetEnabled((prev) => !prev)}
                          onReplayClick={handleReplayButtonClick}
                          isReplayActive={isReplayActive}
                          isReplaySelectionMode={isReplaySelectionMode}
                        />
                      </div>
                    )}
                    <ChartOverlay
                      activeTool={activeTool}
                      drawings={drawings}
                      onAddDrawing={handleAddDrawing}
                      onUpdateDrawing={handleUpdateDrawing}
                      onDeleteDrawing={handleDeleteDrawing}
                      chartApi={chartApiRef}
                      candleSeries={candleSeriesRef}
                      magnetEnabled={magnetEnabled}
                      selectedDrawingIds={selectedDrawingIds}
                      onSetSelectedDrawingIds={setSelectedDrawingIds}
                      isReplaySelectionMode={isReplaySelectionMode}
                      onReplayStartSelect={handleReplayStartSelect}
                    />
                    {selectedDrawing && (
                      <DrawingContextToolbar
                        drawing={selectedDrawing}
                        position={toolbarPosition}
                        onUpdateDrawing={(updates) => handleUpdateDrawing(selectedDrawing.id, updates)}
                        onDelete={() => handleDeleteDrawing(selectedDrawing.id)}
                        onAddAlert={handleAddAlert}
                        onClose={() => setSelectedDrawingIds([])}
                      />
                    )}
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
        {isDesktop && showRightPanel && (
          <div
            onMouseDown={onDragStart}
            className="flex-shrink-0 cursor-col-resize flex items-center justify-center group"
            style={{ width: 6, margin: "0 2px" }}
          >
            <div className="w-[3px] h-10 rounded-full bg-gray-700 group-hover:bg-blue-500 transition-colors" />
          </div>
        )}

        {/* Right Panel */}
        {showRightPanel && (
          <>
            {!isDesktop && (
              <button
                className="fixed inset-0 z-[180] bg-black bg-opacity-40"
                aria-label={t("closePanel")}
                onClick={() => setIsRightPanelOpen(false)}
              />
            )}
            <div
              className={
                isDesktop
                  ? "flex-shrink-0"
                  : "fixed right-0 top-0 z-[190] h-screen max-w-[92vw] shadow-2xl"
              }
            >
              <RightPanel
                items={watchlistItems}
                selectedSymbol={selectedSymbol}
                starredSymbols={starredSymbols}
                onSymbolSelect={(symbol) => {
                  handleSymbolSelect(symbol);
                  if (!isDesktop) setIsRightPanelOpen(false);
                }}
                onToggleStar={handleToggleStar}
                width={isDesktop ? sidebarWidth : compactRightPanelWidth}
                candles={chartCandles}
              />
            </div>
          </>
        )}
          </>
        )}
      </main>
    </div>
  );
};

export default TradingDashboard;
