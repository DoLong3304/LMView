import React, {
    useState,
    useCallback,
    useEffect,
    useLayoutEffect,
    useRef,
} from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Header from "@/components/layout/Header";
import LeftSidebar from "@/components/layout/LeftSidebar";
import AuthModal from "@/features/auth/AuthModal";
import { useAuth } from "@/features/auth/AuthContext";
import SettingsModal from "@/features/settings/SettingsModal";
import {
    AiActionProvider,
    useAiActions,
    type AiChartActionController,
} from "@/features/ai/actions/AiActionProvider";
import { CandlestickChart } from "@/features/chart";
import ChartOverlay from "@/features/drawing/components/ChartOverlay";
import DrawingContextToolbar from "@/features/drawing/components/DrawingContextToolbar";
import { ReplayControls } from "@/features/replay/components/ReplayControls";
import RightPanel, {
    type RightPanelTab,
    type RightPanelTopTab,
} from "@/features/watchlist/components/RightPanel";
import NewsPage from "@/pages/NewsPage";
import ScreenerPage from "@/pages/ScreenerPage";
import { FALLBACK_SYMBOLS } from "@/constants/market";
import { fetchTickers, fetchSymbols, getLivePrices } from "@/services/marketDataService";
import { fetchLatestNews } from "@/services/newsService";
import {
    DEFAULT_CHART_PREFERENCES,
    fetchUserSettings,
    normalizeChartPreferences,
    type ChartPreferenceSettings,
} from "@/services/settingsService";
import { loadFromStorage, saveToStorage } from "@/utils/storageHelpers";
import {
    loadDrawings,
    saveDrawings,
    deleteDrawings,
} from "@/services/chartStorageService";
import { useChartKeyboardShortcuts } from "@/hooks/useChartKeyboardShortcuts";
import { useDrawingToolbarPosition } from "@/hooks/useDrawingToolbarPosition";
import { useReplayMode } from "@/hooks/useReplayMode";
import { useI18n } from "@/i18n";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { CHART_TYPES as CHART_TYPE_CONFIGS } from "@/types";
import type {
    Candle,
    ChartType,
    Drawing,
    NewsArticle,
    SettingsTab,
    SymbolInfo,
    Ticker,
    TimeframeKey,
} from "@/types";

interface WatchlistItemData {
    symbol: string;
    price: number;
    change: number;
    activityScore?: number;
    volume?: number;
    color: "green" | "red" | "gray";
}

type ThemeMode = "dark" | "light";
type AppView = "charts" | "marketsNews" | "screener";

const DESKTOP_LAYOUT_QUERY = "(min-width: 1024px)";
const DEFAULT_TIMEFRAME_STORAGE_KEY = "app_defaultTimeframe";
const DEFAULT_CHART_TYPE_STORAGE_KEY = "app_defaultChartType";
const VALID_TIMEFRAMES: TimeframeKey[] = [
    "1s",
    "1m",
    "5m",
    "15m",
    "1h",
    "4h",
    "1d",
    "1w",
];
const VALID_CHART_TYPES: ChartType[] = CHART_TYPE_CONFIGS.map(
    (chartType) => chartType.id,
);

function getInitialTheme(): ThemeMode {
    if (typeof window === "undefined") return "dark";
    const stored = window.localStorage.getItem("app_theme");
    if (stored === "dark" || stored === "light") return stored;
    return window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark";
}

function getInitialTimeframe(): TimeframeKey {
    const stored = loadFromStorage<TimeframeKey>(
        DEFAULT_TIMEFRAME_STORAGE_KEY,
        "1m",
    );
    return VALID_TIMEFRAMES.includes(stored) ? stored : "1m";
}

function getInitialChartType(): ChartType {
    const stored = loadFromStorage<ChartType>(
        DEFAULT_CHART_TYPE_STORAGE_KEY,
        "candles",
    );
    return VALID_CHART_TYPES.includes(stored) ? stored : "candles";
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

function isEditableTarget(target: EventTarget | null): boolean {
    if (!target || !(target instanceof HTMLElement)) return false;

    const tagName = target.tagName.toLowerCase();
    return (
        target.isContentEditable ||
        ["input", "textarea", "select"].includes(tagName)
    );
}

const TradingDashboard: React.FC = () => {
    const { t } = useI18n();
    const { user, changePassword, logout } = useAuth();
    const chartContainerRef = useRef<HTMLDivElement | null>(null);
    const [themeMode, setThemeMode] = useState<ThemeMode>(getInitialTheme);
    const [isDesktop, setIsDesktop] = useState(isDesktopLayout);
    const [isRightPanelOpen, setIsRightPanelOpen] = useState(isDesktopLayout);
    const [rightPanelTopTab, setRightPanelTopTab] =
        useState<RightPanelTopTab>("overview");
    const [rightPanelTab, setRightPanelTab] =
        useState<RightPanelTab>("watchlist");
    const [isDrawingToolbarOpen, setIsDrawingToolbarOpen] =
        useState(isDesktopLayout);
    const [appView, setAppView] = useState<AppView>("charts");
    const [activeTool, setActiveTool] = useState("cursor");
    const [drawings, setDrawings] = useState<Drawing[]>([]);
    const [selectedDrawingIds, setSelectedDrawingIds] = useState<
        (string | number)[]
    >([]);
    const [isClearDrawingsConfirmOpen, setIsClearDrawingsConfirmOpen] =
        useState(false);
    const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
    const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
    const [settingsInitialTab, setSettingsInitialTab] =
        useState<SettingsTab>("account");
    const [magnetEnabled, setMagnetEnabled] = useState(false);
    const [chartPreferences, setChartPreferences] =
        useState<ChartPreferenceSettings>(DEFAULT_CHART_PREFERENCES);
    const [currentTimeframe, setCurrentTimeframe] =
        useState<TimeframeKey>(getInitialTimeframe);
    const [chartType, setChartType] = useState<ChartType>(getInitialChartType);
    const [aiChartController, setAiChartController] =
        useState<AiChartActionController | null>(null);
    // True while a guided analysis is freezing the chart. Used to pause
    // non-chart UI updates (RightPanel price/change%, fast ticker poll)
    // so the user sees a stable screen while the AI walks them through
    // a multi-step analysis.
    const [chartFrozen, setChartFrozen] = useState(false);
    const [isDrawing, setIsDrawing] = useState(false);
    const [selectedSymbol, setSelectedSymbol] = useState<string>(() => {
        const stored = loadFromStorage("app_selectedSymbol", "BTCUSDT");
        if (stored && !stored.endsWith("USDT")) return "BTCUSDT";
        return stored;
    });
    const [starredSymbols, setStarredSymbols] = useState<string[]>(() =>
        loadFromStorage("app_starred", []),
    );
    const [symbols, setSymbols] = useState<string[]>(() => [
        ...FALLBACK_SYMBOLS,
    ]);
    const [watchlistItems, setWatchlistItems] = useState<WatchlistItemData[]>(
        () => buildWatchlist([...FALLBACK_SYMBOLS]),
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

    // Fetch news articles for chart overlay markers
    useEffect(() => {
        let cancelled = false;
        const refreshNews = async () => {
            try {
                const articles = await fetchLatestNews({
                    limit: 200,
                    hours: 72,
                });
                if (!cancelled) setNewsArticles(articles);
            } catch {
                // silently ignore news fetch errors in chart context
            }
        };
        refreshNews();
        const id = setInterval(refreshNews, 5 * 60_000); // refresh every 5 min
        return () => {
            cancelled = true;
            clearInterval(id);
        };
    }, []);

    // Fetch live ticker prices for the watchlist.
    // Live price from chart WS is available for selectedSymbol via _livePriceMap.
    // Use poll fallback (30s) for non-selected watchlist symbols + initial load.
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
                    const livePrices = getLivePrices();
                    setWatchlistItems((prev) =>
                        prev.map((item) => {
                            const tick = map[item.symbol];
                            const live = livePrices[item.symbol];

                            // Prefer live WS price for selected symbol, ticker for others
                            if (item.symbol === selectedSymbol && live) {
                                return {
                                    ...item,
                                    price: live.price,
                                    change: live.change24h,
                                    activityScore: live.activity_score,
                                    volume: live.volume,
                                    color: live.change24h >= 0 ? "green" : "red",
                                };
                            }

                            if (!tick) return item;
                            return {
                                ...item,
                                price: tick.price,
                                change:
                                    tick.change24h != null
                                        ? tick.change24h
                                        : item.change,
                                activityScore:
                                    tick.activity_score ??
                                    (tick.volume ?? item.volume ?? 0) *
                                        (1 +
                                            Math.abs(
                                                tick.change24h ??
                                                    item.change ??
                                                    0,
                                            ) /
                                                100),
                                volume: tick.volume ?? item.volume,
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
        // Poll every 30s — selected symbol price comes from WS via _livePriceMap
        const id = setInterval(refresh, 30_000);
        return () => {
            cancelled = true;
            clearInterval(id);
        };
    }, [selectedSymbol]);

    // ─── Fast live price update for selected symbol from WS _livePriceMap ───
    // Updates every 2s, no API call — keeps price/change% in RightPanel synced
    // with the forming candle moving on chart.
    // Preserves previous change% if WS doesn't send change24h.
    useEffect(() => {
        const fastRefresh = () => {
            // Pause the live price tick while a guided analysis freezes
            // the chart, so the user sees a stable UI.
            if (chartFrozen) return;
            const livePrices = getLivePrices();
            setWatchlistItems((prev) =>
                prev.map((item) => {
                    if (item.symbol !== selectedSymbol) return item;
                    const live = livePrices[selectedSymbol];
                    if (!live) return item;
                    return {
                        ...item,
                        price: live.price,
                        change: live.change24h !== 0 ? live.change24h : item.change,
                        activityScore: live.activity_score ?? item.activityScore,
                        volume: live.volume > 0 ? live.volume : item.volume,
                        color: live.change24h >= 0 ? "green" : "red",
                    };
                }),
            );
        };
        const id = setInterval(fastRefresh, 2_000);
        return () => clearInterval(id);
    }, [selectedSymbol, chartFrozen]);

    // Mirror the chart-freeze custom event into App-level state so we
    // can pause non-chart UI updates (RightPanel price tick, etc.).
    useEffect(() => {
        const handler = (event: Event) => {
            const detail = (event as CustomEvent<{ frozen: boolean }>).detail;
            if (detail && typeof detail.frozen === "boolean") {
                setChartFrozen(detail.frozen);
            }
        };
        window.addEventListener("lmview:chart-freeze", handler);
        return () => window.removeEventListener("lmview:chart-freeze", handler);
    }, []);

    // Persist settings to localStorage
    useEffect(() => {
        saveToStorage("app_starred", starredSymbols);
    }, [starredSymbols]);
    useEffect(() => {
        saveToStorage("app_selectedSymbol", selectedSymbol);
    }, [selectedSymbol]);
    useEffect(() => {
        saveToStorage(DEFAULT_TIMEFRAME_STORAGE_KEY, currentTimeframe);
    }, [currentTimeframe]);
    useEffect(() => {
        saveToStorage(DEFAULT_CHART_TYPE_STORAGE_KEY, chartType);
    }, [chartType]);

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
                console.error("[App] Failed to load drawings:", error);
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
                    drawings,
                );
            } catch (error) {
                console.error("[App] Failed to save drawings:", error);
            }
        }, 500); // Debounce 500ms

        return () => clearTimeout(timeoutId);
    }, [drawings, selectedSymbol, currentTimeframe]);

    // Keyboard shortcuts with command history - initialize early
    const handleCancelDrawing = useCallback(() => {
        setIsDrawing(false);
    }, []);

    const handleToolChange = useCallback((tool: string) => {
        setActiveTool((current) =>
            tool === "eraser" && current === "eraser" ? "cursor" : tool,
        );
        setSelectedDrawingIds([]);
    }, []);

    const handleDeleteDrawingsInternal = useCallback(
        (ids: (string | number)[]) => {
            setDrawings((prev) =>
                prev.filter((d) => d.locked || !ids.includes(d.id)),
            );
            setSelectedDrawingIds([]);
        },
        [],
    );

    const handleSaveDrawings = useCallback(async () => {
        try {
            await saveDrawings(
                {
                    symbol: selectedSymbol,
                    timeframe: currentTimeframe,
                    storageVersion: 1,
                },
                drawings,
            );
            console.log("[App] Drawings saved successfully");
        } catch (error) {
            console.error("[App] Failed to save drawings:", error);
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
                type: "add",
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
                const oldDrawing = prev.find((d) => d.id === id);
                if (!oldDrawing || oldDrawing.locked) return prev;
                const newDrawings = prev.map((d) =>
                    d.id === id ? { ...d, ...updates } : d,
                );

                // Record update command
                const newDrawing = newDrawings.find((d) => d.id === id);
                addCommand({
                    type: "update",
                    timestamp: Date.now(),
                    drawingId: id,
                    before: oldDrawing,
                    after: newDrawing,
                    description: `Update ${oldDrawing.tool}`,
                });

                return newDrawings;
            });
        },
        [addCommand],
    );

    const handleDeleteDrawing = useCallback(
        (id: string | number) => {
            setDrawings((prev) => {
                const deletedDrawing = prev.find((d) => d.id === id);
                if (!deletedDrawing || deletedDrawing.locked) return prev;

                // Record delete command
                addCommand({
                    type: "delete",
                    timestamp: Date.now(),
                    drawingId: id,
                    before: deletedDrawing,
                    description: `Delete ${deletedDrawing.tool}`,
                });

                return prev.filter((d) => d.id !== id);
            });
            setSelectedDrawingIds((prev) => prev.filter((sid) => sid !== id));
            if (activeTool === "eraser") {
                setActiveTool("cursor");
            }
        },
        [activeTool, addCommand],
    );

    const handleClearAll = useCallback(async () => {
        setDrawings([]);
        setSelectedDrawingIds([]);
        setActiveTool("cursor");
        setIsClearDrawingsConfirmOpen(false);
        try {
            await deleteDrawings({
                symbol: selectedSymbol,
                timeframe: currentTimeframe,
                storageVersion: 1,
            });
        } catch (error) {
            console.error("[App] Failed to delete drawings:", error);
        }
    }, [selectedSymbol, currentTimeframe]);

    const handleRequestClearAllDrawings = useCallback(() => {
        setIsClearDrawingsConfirmOpen(true);
    }, []);

    const handleLockAll = useCallback(() => {
        setDrawings((prev) => {
            const shouldLock = prev.some((d) => !d.locked);
            return prev.map((d) => ({ ...d, locked: shouldLock }));
        });
        setSelectedDrawingIds([]);
        setActiveTool("cursor");
    }, []);

    const handleHideAll = useCallback(() => {
        setDrawings((prev) => {
            const shouldHide = prev.some((d) => !d.hidden);
            return prev.map((d) => ({ ...d, hidden: shouldHide }));
        });
        setSelectedDrawingIds([]);
        setActiveTool("cursor");
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

    useEffect(() => {
        if (!user?.id || user.must_change_password) return;
        let cancelled = false;
        fetchUserSettings()
            .then((payload) => {
                if (cancelled) return;
                const defaults = payload.customization_defaults;
                if (defaults.theme === "dark" || defaults.theme === "light") {
                    setThemeMode(defaults.theme);
                }
                if (
                    VALID_TIMEFRAMES.includes(
                        defaults.default_timeframe as TimeframeKey,
                    )
                ) {
                    setCurrentTimeframe(
                        defaults.default_timeframe as TimeframeKey,
                    );
                }
                if (
                    VALID_CHART_TYPES.includes(
                        defaults.default_chart_type as ChartType,
                    )
                ) {
                    setChartType(defaults.default_chart_type as ChartType);
                }
                if (defaults.default_symbol.endsWith("USDT")) {
                    setSelectedSymbol(defaults.default_symbol);
                }
                setChartPreferences(normalizeChartPreferences(defaults));
            })
            .catch(() => {
                // User defaults are optional; local storage still provides anonymous defaults.
            });
        return () => {
            cancelled = true;
        };
    }, [user?.id, user?.must_change_password]);

    const handleThemeModeChange = useCallback((mode: ThemeMode) => {
        setThemeMode(mode);
    }, []);

    const handleOpenSettings = useCallback((tab: SettingsTab = "account") => {
        setSettingsInitialTab(tab);
        setIsSettingsModalOpen(true);
    }, []);

    const handleToggleDrawingToolbar = useCallback(() => {
        setIsDrawingToolbarOpen((open) => !open);
    }, []);

    useEffect(() => {
        const handleEscape = (event: KeyboardEvent) => {
            if (event.key !== "Escape" || isEditableTarget(event.target))
                return;
            setActiveTool((current) =>
                current === "cursor" ? current : "cursor",
            );
        };

        document.addEventListener("keydown", handleEscape);
        return () => document.removeEventListener("keydown", handleEscape);
    }, []);

    // State lifted from CandlestickChart for Overview + DrawingToolbar data.
    const [chartCandles, setChartCandles] = useState<Candle[]>([]);
    // Indicator settings + visible indicator list, mirrored from
    // CandlestickChart so the AI panel can build the chart context
    // (indicator_values + selected_indicators) without needing to live
    // inside the chart.
    const [chartIndSettings, setChartIndSettings] = useState<Record<string, import("@/types").IndicatorSettings>>({});
    const [chartSelectedIndicators, setChartSelectedIndicators] = useState<string[]>([]);

    // Chart API refs for floating toolbar positioning
    const [chartApi, setChartApi] = useState<any>(null);
    const [candleSeries, setCandleSeries] = useState<any>(null);

    // News items for chart overlay markers
    const [newsArticles, setNewsArticles] = useState<NewsArticle[]>([]);

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
        onCandleUpdate: useCallback(
            (candle: Candle) => {
                // Update chart with replay candle
                if (candleSeries) {
                    candleSeries.update(candle);
                }
            },
            [candleSeries],
        ),
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
            setActiveTool("cursor"); // Switch to cursor for selection
        }
    }, [isReplayActive, isReplaySelectionMode, exitReplay]);

    // Handle candle click in selection mode
    const handleReplayStartSelect = useCallback(
        (timestamp: number) => {
            if (isReplaySelectionMode && chartCandles.length > 0) {
                // Find the nearest candle to the clicked chart coordinate.
                const clickedIndex = chartCandles.reduce(
                    (bestIndex, candle, index) => {
                        const bestDistance = Math.abs(
                            chartCandles[bestIndex].time - timestamp,
                        );
                        const currentDistance = Math.abs(
                            candle.time - timestamp,
                        );
                        return currentDistance < bestDistance
                            ? index
                            : bestIndex;
                    },
                    0,
                );
                if (clickedIndex >= 0) {
                    const visibleHistory = chartCandles.slice(
                        0,
                        clickedIndex + 1,
                    );

                    // Hide future candles; replay will append them back one by one.
                    if (candleSeries) {
                        candleSeries.setData(visibleHistory);
                    }

                    // Start replay from this point
                    startReplay(chartCandles, clickedIndex);
                    setIsReplaySelectionMode(false);
                }
            }
        },
        [isReplaySelectionMode, chartCandles, startReplay, candleSeries],
    );

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
    }, [isReplayActive, candleSeries]);

    const drawingsLocked =
        drawings.length > 0 && drawings.every((drawing) => drawing.locked);
    useEffect(() => {
        if (
            activeTool === "eraser" &&
            (drawings.length === 0 || drawingsLocked)
        ) {
            setActiveTool("cursor");
        }
    }, [activeTool, drawings.length, drawingsLocked]);

    // Get selected drawing for context toolbar
    const selectedDrawing =
        selectedDrawingIds.length === 1
            ? drawings.find((d) => d.id === selectedDrawingIds[0]) || null
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
        console.log("[App] Add alert for drawing:", selectedDrawing?.id);
        alert(t("alertFeatureSoon"));
    }, [selectedDrawing, t]);

    // Resizable right sidebar
    const SIDEBAR_MIN = 280;
    const SIDEBAR_MAX = 520;
    const SIDEBAR_DEFAULT = 360;
    const SIDEBAR_MAX_VIEWPORT_RATIO = 0.36;
    const CHART_MIN_WIDTH_WITH_PANEL = 560;
    const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
    const dragging = useRef(false);
    const clampSidebarWidth = useCallback((width: number) => {
        if (typeof window === "undefined") {
            return Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, width));
        }

        const viewportMax = Math.floor(
            window.innerWidth * SIDEBAR_MAX_VIEWPORT_RATIO,
        );
        const chartSafeMax = window.innerWidth - CHART_MIN_WIDTH_WITH_PANEL;
        const maxWidth = Math.max(
            SIDEBAR_MIN,
            Math.min(SIDEBAR_MAX, viewportMax, chartSafeMax),
        );
        return Math.max(SIDEBAR_MIN, Math.min(maxWidth, width));
    }, []);

    useEffect(() => {
        const onTopTab = (event: Event) => {
            const tab = (event as CustomEvent<{ tab?: RightPanelTopTab }>)
                .detail?.tab;
            if (tab === "aiHelper" && !user) return;
            if (tab === "overview" || tab === "aiHelper") {
                setRightPanelTopTab(tab);
            }
        };
        const onPanelTab = (event: Event) => {
            const tab = (event as CustomEvent<{ tab?: RightPanelTab }>)
                .detail?.tab;
            if (
                tab === "watchlist" ||
                tab === "orderBook" ||
                tab === "recentTrades"
            ) {
                setRightPanelTopTab("overview");
                setRightPanelTab(tab);
            }
        };
        window.addEventListener("lmview:right-panel-top-tab", onTopTab);
        window.addEventListener("lmview:right-panel-tab", onPanelTab);
        return () => {
            window.removeEventListener("lmview:right-panel-top-tab", onTopTab);
            window.removeEventListener("lmview:right-panel-tab", onPanelTab);
        };
    }, [user]);

    useEffect(() => {
        const onResize = () => {
            setSidebarWidth((width) => clampSidebarWidth(width));
        };
        onResize();
        window.addEventListener("resize", onResize);
        return () => window.removeEventListener("resize", onResize);
    }, [clampSidebarWidth]);

    const onDragStart = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        dragging.current = true;
        const onMove = (ev: MouseEvent) => {
            if (!dragging.current) return;
            const newW = window.innerWidth - ev.clientX;
            setSidebarWidth(clampSidebarWidth(newW));
        };
        const onUp = () => {
            dragging.current = false;
            document.removeEventListener("mousemove", onMove);
            document.removeEventListener("mouseup", onUp);
        };
        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
    }, [clampSidebarWidth]);

    const isChartsView = appView === "charts";
    const showDrawingToolbar = isChartsView;
    const showRightPanel = isChartsView && isRightPanelOpen;
    const compactRightPanelWidth =
        typeof window === "undefined"
            ? 420
            : Math.min(420, Math.floor(window.innerWidth * 0.92));

    const clearDrawingsConfirmModal = isClearDrawingsConfirmOpen ? (
        <div className="fixed inset-0 z-[500] flex items-center justify-center bg-black/60 px-4">
            <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="clear-drawings-title"
                className="w-full max-w-sm rounded border border-[var(--lm-border)] bg-[var(--lm-bg-secondary)] shadow-2xl"
            >
                <div className="border-b border-[var(--lm-border)] px-4 py-3">
                    <h2
                        id="clear-drawings-title"
                        className="text-sm font-semibold text-[var(--lm-text-primary)]"
                    >
                        {t("clearAllDrawings")}
                    </h2>
                </div>
                <div className="space-y-2 px-4 py-4">
                    <p className="text-sm text-[var(--lm-text-secondary)]">
                        {t("confirmClearDrawings")}
                    </p>
                    <p className="text-xs text-[var(--lm-text-muted)]">
                        {t("actionCannotBeUndone")}
                    </p>
                </div>
                <div className="flex items-center justify-end gap-2 border-t border-[var(--lm-border)] px-4 py-3">
                    <button
                        type="button"
                        onClick={() => setIsClearDrawingsConfirmOpen(false)}
                        className="rounded border border-[var(--lm-border)] px-3 py-1.5 text-xs font-medium text-[var(--lm-text-secondary)] transition-colors hover:bg-[var(--lm-bg-tertiary)] hover:text-[var(--lm-text-primary)]"
                    >
                        {t("cancel")}
                    </button>
                    <button
                        type="button"
                        onClick={handleClearAll}
                        className="rounded bg-red-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-red-500"
                    >
                        {t("deleteAll")}
                    </button>
                </div>
            </div>
        </div>
    ) : null;

    return (
        <ErrorBoundary isAdmin={user?.role === "admin"}>
            <AiActionProvider>
            <AiActionRuntimeBridge
                setDrawingTool={handleToolChange}
                addDrawing={handleAddDrawing}
                setTimeframe={handleTimeframeChange}
                setSymbol={handleSymbolSelect}
                setChartType={setChartType}
                setView={setAppView}
                setRightPanelOpen={setIsRightPanelOpen}
                setRightPanelTopTab={setRightPanelTopTab}
                setRightPanelTab={setRightPanelTab}
                openSettings={() => handleOpenSettings()}
                closeSettings={() => setIsSettingsModalOpen(false)}
                currentView={appView}
                rightPanelOpen={isRightPanelOpen}
                rightPanelTopTab={rightPanelTopTab}
                rightPanelTab={rightPanelTab}
                currentTimeframe={currentTimeframe}
                selectedSymbol={selectedSymbol}
                chartType={chartType}
                chartController={aiChartController}
            />
            <div data-ai-section="app-shell" className="bg-gray-900 text-white h-dvh flex flex-col overflow-hidden">
                <div data-ai-section="header">
                    <Header
                    themeMode={themeMode}
                    onThemeToggle={handleToggleTheme}
                    isRightPanelOpen={isRightPanelOpen}
                    onToggleRightPanel={() =>
                        setIsRightPanelOpen((open) => !open)
                    }
                    activeView={appView}
                    onViewChange={setAppView}
                    onLoginClick={() => setIsAuthModalOpen(true)}
                    onSettingsClick={() => handleOpenSettings("account")}
                />
                </div>

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
                                            setWatchlistItems(
                                                buildWatchlist(names),
                                            );
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
                    {appView === "marketsNews" ? (
                        <div data-ai-section="markets-news-page" className="flex-1 min-w-0 overflow-hidden">
                            <NewsPage />
                        </div>
                    ) : appView === "screener" ? (
                        <div data-ai-section="screener-page" className="flex-1 min-w-0 overflow-hidden">
                            <ScreenerPage
                                onBack={() => setAppView("charts")}
                                onSymbolSelect={(symbol) => {
                                    handleSymbolSelect(symbol);
                                    setAppView("charts");
                                }}
                            />
                        </div>
                    ) : (
                        <>
                            {/* Chart area */}
                            <div
                                data-ai-section="chart"
                                className="flex-1 flex flex-col overflow-hidden min-w-0"
                                ref={chartContainerRef}
                            >
                                <div className="relative flex min-h-0 flex-1 bg-gray-900">
                                    <CandlestickChart
                                        symbol={selectedSymbol}
                                        symbols={symbols}
                                        starredSymbols={starredSymbols}
                                        timeframe={currentTimeframe}
                                        onCandlesChange={setChartCandles}
                                        onTimeframeChange={
                                            handleTimeframeChange
                                        }
                                        onSymbolChange={handleSymbolSelect}
                                        onToggleStar={handleToggleStar}
                                        themeMode={themeMode}
                                        chartType={chartType}
                                        onChartTypeChange={setChartType}
                                        chartPreferences={chartPreferences}
                                        isReplayActive={isReplayActive}
                                        newsItems={newsArticles}
                                        showNewsMarkers={true}
                                        onAiActionControllerReady={
                                            setAiChartController
                                        }
                                        onIndicatorSettingsChange={setChartIndSettings}
                                        onSelectedIndicatorsChange={setChartSelectedIndicators}
                                    >
                                        {(chartApiRef, candleSeriesRef) => {
                                            if (chartApiRef !== chartApi)
                                                setChartApi(chartApiRef);
                                            if (
                                                candleSeriesRef !== candleSeries
                                            )
                                                setCandleSeries(
                                                    candleSeriesRef,
                                                );

                                            return (
                                                <>
                                                    {showDrawingToolbar && (
                                                        <div
                                                            data-ai-section="drawing-toolbar"
                                                            className="pointer-events-none absolute left-3 top-3 z-[130] max-h-[calc(100%-1.5rem)] overflow-visible"
                                                            style={{
                                                                width: 56,
                                                                minWidth: 56,
                                                                maxWidth: 56,
                                                            }}
                                                        >
                                                            <div
                                                                className={`transition-all duration-200 ease-out ${
                                                                    isDrawingToolbarOpen
                                                                        ? "pointer-events-auto opacity-100"
                                                                        : "pointer-events-none opacity-0"
                                                                }`}
                                                                style={{
                                                                    transform:
                                                                        isDrawingToolbarOpen
                                                                            ? "translateX(0)"
                                                                            : "translateX(calc(-100% - 12px))",
                                                                }}
                                                            >
                                                                <LeftSidebar
                                                                    activeTool={
                                                                        activeTool
                                                                    }
                                                                    onToolChange={
                                                                        handleToolChange
                                                                    }
                                                                    onClearAll={
                                                                        handleRequestClearAllDrawings
                                                                    }
                                                                    onLockAll={
                                                                        handleLockAll
                                                                    }
                                                                    onHideAll={
                                                                        handleHideAll
                                                                    }
                                                                    magnetEnabled={
                                                                        magnetEnabled
                                                                    }
                                                                    onMagnetToggle={() =>
                                                                        setMagnetEnabled(
                                                                            (
                                                                                prev,
                                                                            ) =>
                                                                                !prev,
                                                                        )
                                                                    }
                                                                    onReplayClick={
                                                                        handleReplayButtonClick
                                                                    }
                                                                    isReplayActive={
                                                                        isReplayActive
                                                                    }
                                                                    isReplaySelectionMode={
                                                                        isReplaySelectionMode
                                                                    }
                                                                    drawingsLocked={
                                                                        drawingsLocked
                                                                    }
                                                                    favoriteTools={
                                                                        chartPreferences.favorite_drawing_tools
                                                                    }
                                                                />
                                                            </div>
                                                            <button
                                                                type="button"
                                                                onClick={
                                                                    handleToggleDrawingToolbar
                                                                }
                                                                className={`pointer-events-auto absolute top-1/2 z-[150] flex -translate-y-1/2 items-center justify-center border border-[var(--lm-border-strong)] bg-[var(--lm-bg-secondary)] text-[var(--lm-text-secondary)] shadow-lg outline-none transition-all duration-200 hover:border-[var(--lm-blue-border)] hover:bg-[var(--lm-blue-soft)] hover:text-[var(--lm-blue)] hover:opacity-95 focus-visible:border-blue-500 focus-visible:opacity-95 ${
                                                                    isDrawingToolbarOpen
                                                                        ? "-right-2 h-14 w-5 rounded-full opacity-40"
                                                                        : "-left-3 h-16 w-5 rounded-r-full border-l-0 opacity-45"
                                                                }`}
                                                                title={
                                                                    isDrawingToolbarOpen
                                                                        ? t(
                                                                              "collapseDrawingToolbar",
                                                                          )
                                                                        : t(
                                                                              "expandDrawingToolbar",
                                                                          )
                                                                }
                                                                aria-label={
                                                                    isDrawingToolbarOpen
                                                                        ? t(
                                                                              "collapseDrawingToolbar",
                                                                          )
                                                                        : t(
                                                                              "expandDrawingToolbar",
                                                                          )
                                                                }
                                                            >
                                                                {isDrawingToolbarOpen ? (
                                                                    <ChevronLeft
                                                                        size={
                                                                            14
                                                                        }
                                                                    />
                                                                ) : (
                                                                    <ChevronRight
                                                                        size={
                                                                            14
                                                                        }
                                                                    />
                                                                )}
                                                            </button>
                                                        </div>
                                                    )}
                                                    <ChartOverlay
                                                        activeTool={activeTool}
                                                        drawings={drawings}
                                                        onAddDrawing={
                                                            handleAddDrawing
                                                        }
                                                        onUpdateDrawing={
                                                            handleUpdateDrawing
                                                        }
                                                        onDeleteDrawing={
                                                            handleDeleteDrawing
                                                        }
                                                        chartApi={chartApiRef}
                                                        candleSeries={
                                                            candleSeriesRef
                                                        }
                                                        magnetEnabled={
                                                            magnetEnabled
                                                        }
                                                        selectedDrawingIds={
                                                            selectedDrawingIds
                                                        }
                                                        onSetSelectedDrawingIds={
                                                            setSelectedDrawingIds
                                                        }
                                                        isReplaySelectionMode={
                                                            isReplaySelectionMode
                                                        }
                                                        onReplayStartSelect={
                                                            handleReplayStartSelect
                                                        }
                                                    />
                                                    {selectedDrawing &&
                                                        !selectedDrawing.locked && (
                                                            <DrawingContextToolbar
                                                                drawing={
                                                                    selectedDrawing
                                                                }
                                                                position={
                                                                    toolbarPosition
                                                                }
                                                                onUpdateDrawing={(
                                                                    updates,
                                                                ) =>
                                                                    handleUpdateDrawing(
                                                                        selectedDrawing.id,
                                                                        updates,
                                                                    )
                                                                }
                                                                onDelete={() =>
                                                                    handleDeleteDrawing(
                                                                        selectedDrawing.id,
                                                                    )
                                                                }
                                                                onAddAlert={
                                                                    handleAddAlert
                                                                }
                                                                onClose={() =>
                                                                    setSelectedDrawingIds(
                                                                        [],
                                                                    )
                                                                }
                                                            />
                                                        )}
                                                    {isReplayActive && (
                                                        <ReplayControls
                                                            isPlaying={
                                                                isPlaying
                                                            }
                                                            playbackSpeed={
                                                                playbackSpeed
                                                            }
                                                            currentIndex={
                                                                currentIndex
                                                            }
                                                            totalCandles={
                                                                totalCandles
                                                            }
                                                            onPlayPause={
                                                                togglePlayPause
                                                            }
                                                            onStepForward={
                                                                stepForward
                                                            }
                                                            onSpeedChange={
                                                                changeSpeed
                                                            }
                                                            onExit={exitReplay}
                                                        />
                                                    )}
                                                    {clearDrawingsConfirmModal}
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
                                            onClick={() =>
                                                setIsRightPanelOpen(false)
                                            }
                                        />
                                    )}
                                    <div
                                        className={
                                            isDesktop
                                                ? "flex-shrink-0"
                                            : "fixed right-0 top-0 z-[190] h-screen max-w-[92vw] shadow-2xl"
                                        }
                                        data-ai-section="right-panel"
                                    >
                                        <RightPanel
                                            items={watchlistItems}
                                            selectedSymbol={selectedSymbol}
                                            starredSymbols={starredSymbols}
                                            onSymbolSelect={(symbol) => {
                                                handleSymbolSelect(symbol);
                                                if (!isDesktop)
                                                    setIsRightPanelOpen(false);
                                            }}
                                            onToggleStar={handleToggleStar}
                                            width={
                                                isDesktop
                                                    ? sidebarWidth
                                                    : compactRightPanelWidth
                                            }
                                            candles={chartCandles}
                                            timeframe={currentTimeframe}
                                            indSettings={chartIndSettings}
                                            selectedIndicators={chartSelectedIndicators}
                                            onOpenSettings={handleOpenSettings}
                                            activeTopTab={rightPanelTopTab}
                                            activeTab={rightPanelTab}
                                            onTopTabChange={setRightPanelTopTab}
                                            onTabChange={setRightPanelTab}
                                        />
                                    </div>
                                </>
                            )}
                        </>
                    )}
                </main>

                <AuthModal
                    isOpen={isAuthModalOpen}
                    onClose={() => setIsAuthModalOpen(false)}
                />
                {user?.must_change_password && (
                    <ForcedPasswordChangeModal
                        onSubmit={changePassword}
                        onLogout={logout}
                    />
                )}
                <SettingsModal
                    isOpen={isSettingsModalOpen}
                    initialTab={settingsInitialTab}
                    themeMode={themeMode}
                    timeframe={currentTimeframe}
                    chartType={chartType}
                    onClose={() => setIsSettingsModalOpen(false)}
                    onLoginClick={() => {
                        setIsSettingsModalOpen(false);
                        setIsAuthModalOpen(true);
                    }}
                    onThemeChange={handleThemeModeChange}
                    onTimeframeChange={handleTimeframeChange}
                    onChartTypeChange={setChartType}
                />
            </div>
            </AiActionProvider>
        </ErrorBoundary>
    );
};

function AiActionRuntimeBridge({
    setDrawingTool,
    addDrawing,
    setTimeframe,
    setSymbol,
    setChartType,
    setView,
    setRightPanelOpen,
    setRightPanelTopTab,
    setRightPanelTab,
    openSettings,
    closeSettings,
    currentView,
    rightPanelOpen,
    rightPanelTopTab,
    rightPanelTab,
    currentTimeframe,
    selectedSymbol,
    chartType,
    chartController,
}: {
    setDrawingTool: (tool: string) => void;
    addDrawing: (drawing: Drawing) => void;
    setTimeframe: (timeframe: TimeframeKey) => void;
    setSymbol: (symbol: string) => void;
    setChartType: (chartType: ChartType) => void;
    setView: (view: AppView) => void;
    setRightPanelOpen: (open: boolean) => void;
    setRightPanelTopTab: (tab: RightPanelTopTab) => void;
    setRightPanelTab: (tab: RightPanelTab) => void;
    openSettings: () => void;
    closeSettings: () => void;
    currentView: AppView;
    rightPanelOpen: boolean;
    rightPanelTopTab: RightPanelTopTab;
    rightPanelTab: RightPanelTab;
    currentTimeframe: TimeframeKey;
    selectedSymbol: string;
    chartType: ChartType;
    chartController: AiChartActionController | null;
}) {
    const { setRuntime } = useAiActions();
    useEffect(() => {
        setRuntime({
            setDrawingTool,
            addDrawing,
            setTimeframe,
            setSymbol,
            setChartType,
            setView,
            setRightPanelOpen,
            setRightPanelTopTab,
            setRightPanelTab,
            openSettings,
            closeSettings,
            currentView,
            rightPanelOpen,
            rightPanelTopTab,
            rightPanelTab,
            currentTimeframe,
            selectedSymbol,
            chartType,
            chartController,
        });
    }, [
        addDrawing,
        chartController,
        chartType,
        closeSettings,
        currentView,
        currentTimeframe,
        openSettings,
        rightPanelOpen,
        selectedSymbol,
        setChartType,
        setDrawingTool,
        setRightPanelOpen,
        setRightPanelTab,
        setRightPanelTopTab,
        setRuntime,
        setSymbol,
        setTimeframe,
        setView,
        rightPanelTab,
        rightPanelTopTab,
    ]);
    return null;
}

function ForcedPasswordChangeModal({
    onSubmit,
    onLogout,
}: {
    onSubmit: (
        currentPassword: string,
        newPassword: string,
    ) => Promise<{ success: boolean; error?: string }>;
    onLogout: () => Promise<void>;
}) {
    const { t } = useI18n();
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async () => {
        if (newPassword !== confirmPassword) {
            setError(t("passwordsMismatch"));
            return;
        }
        setLoading(true);
        const result = await onSubmit(currentPassword, newPassword);
        setLoading(false);
        setError(result.success ? "" : result.error || t("error"));
    };

    return (
        <div className="fixed inset-0 z-[700] flex items-center justify-center bg-black/75 px-4 backdrop-blur-sm">
            <div className="w-full max-w-sm rounded border border-gray-700 bg-gray-900 p-4 shadow-2xl">
                <h2 className="text-sm font-semibold text-white">
                    {t("forcePasswordChangeTitle")}
                </h2>
                <p className="mt-2 text-sm leading-6 text-gray-400">
                    {t("forcePasswordChangeBody")}
                </p>
                <div className="mt-4 space-y-3">
                    <input
                        type="password"
                        value={currentPassword}
                        onChange={(event) =>
                            setCurrentPassword(event.target.value)
                        }
                        placeholder={t("currentPassword")}
                        className="w-full rounded border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                    />
                    <input
                        type="password"
                        value={newPassword}
                        onChange={(event) => setNewPassword(event.target.value)}
                        placeholder={t("newPassword")}
                        className="w-full rounded border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                    />
                    <input
                        type="password"
                        value={confirmPassword}
                        onChange={(event) =>
                            setConfirmPassword(event.target.value)
                        }
                        placeholder={t("confirmPassword")}
                        className="w-full rounded border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                    />
                    {error && <p className="text-xs text-red-300">{error}</p>}
                    <div className="flex justify-between gap-2 pt-1">
                        <button
                            type="button"
                            onClick={() => void onLogout()}
                            className="rounded border border-gray-700 px-3 py-1.5 text-xs font-medium text-gray-300 hover:bg-gray-800 hover:text-white"
                        >
                            {t("logout")}
                        </button>
                        <button
                            type="button"
                            disabled={loading}
                            onClick={submit}
                            className="rounded bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:cursor-wait disabled:opacity-70"
                        >
                            {loading ? t("loading") : t("updatePassword")}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default TradingDashboard;
