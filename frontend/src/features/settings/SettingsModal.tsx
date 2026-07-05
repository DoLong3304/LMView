import React, { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Bell,
  Bot,
  Bug,
  CheckCircle2,
  Info,
  KeyRound,
  Loader2,
  Lock,
  Plus,
  RefreshCcw,
  Save,
  SlidersHorizontal,
  Trash2,
  UserRound,
  Users,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { BACKEND_VERSION, DATA_SOURCE, FRONTEND_VERSION } from "@/constants/env";
import { TIMEFRAMES } from "@/constants/timeframes";
import { useAuth } from "@/features/auth/AuthContext";
import { selectAiSession } from "@/features/ai/aiSessionSelection";
import {
  deleteLocalAiSession,
  loadLocalAiSessions,
} from "@/features/ai/localAiSessions";
import {
  aiHealth,
  aiGetSessionMessages,
  aiListSessions,
  aiValidateActions,
  type AIMessageResponse,
  type AISessionResponse,
} from "@/services/aiService";
import { fetchHealthStatus } from "@/services/healthService";
import {
  DEFAULT_USER_SETTINGS,
  DEFAULT_CHART_PREFERENCES,
  fetchAdminUsers,
  fetchAppSettings,
  fetchUserSettings,
  forceAdminPasswordChange,
  normalizeChartPreferences,
  saveAiSettings,
  saveAlertSettings,
  saveCustomizationDefaults,
  saveNotificationPreferences,
  updateAdminUser,
  type AdminUsersResponse,
  type ChartPreferenceSettings,
  type ChartThemePreset,
  type CrosshairStyle,
  type GridLineStyle,
  type LayoutPreference,
  type UserSettings,
} from "@/services/settingsService";
import type { UserResponse } from "@/services/authService";
import { formatNormalizedError, getRoleAwareErrorMessage, normalizeError } from "@/utils/errors";
import { useI18n } from "@/i18n";
import type { TranslationKey } from "@/i18n/translations";
import { CHART_TYPES as CHART_TYPE_CONFIGS } from "@/types";
import type {
  ChartType,
  HealthData,
  LocalAiHelpSession,
  SettingsTab,
  TimeframeKey,
} from "@/types";

interface SettingsModalProps {
  isOpen: boolean;
  initialTab: SettingsTab;
  themeMode: "dark" | "light";
  timeframe: TimeframeKey;
  chartType: ChartType;
  onClose: () => void;
  onLoginClick: () => void;
  onThemeChange: (mode: "dark" | "light") => void;
  onTimeframeChange: (timeframe: TimeframeKey) => void;
  onChartTypeChange: (chartType: ChartType) => void;
}

const CHART_TYPE_OPTIONS: ChartType[] = CHART_TYPE_CONFIGS.map((chartType) => chartType.id);
const CHART_TYPE_LABEL_KEYS = Object.fromEntries(
  CHART_TYPE_CONFIGS.map((chartType) => [chartType.id, chartType.labelKey]),
) as Record<ChartType, TranslationKey>;
const INDICATOR_PRESETS: Array<{ id: string; labelKey: TranslationKey; indicators: string[] }> = [
  { id: "core-trend", labelKey: "presetCoreTrend", indicators: ["sma20", "sma50", "ema12", "ema26", "volumeMa"] },
  { id: "momentum", labelKey: "presetMomentum", indicators: ["rsi", "macd", "stochastic", "mfi"] },
  { id: "volatility", labelKey: "presetVolatility", indicators: ["bb", "atr", "supertrend", "psar"] },
];
const TOOL_PRESETS: Array<{ id: string; labelKey: TranslationKey }> = [
  { id: "precision", labelKey: "toolPresetPrecision" },
  { id: "annotation", labelKey: "toolPresetAnnotation" },
  { id: "clean", labelKey: "toolPresetClean" },
];
const LAYOUT_PRESETS: Array<{ id: string; labelKey: TranslationKey }> = [
  { id: "balanced", labelKey: "layoutPresetBalanced" },
  { id: "focus", labelKey: "layoutPresetFocus" },
  { id: "research", labelKey: "layoutPresetResearch" },
];

const AI_RESPONSE_STYLE_LABEL_KEYS: Record<string, TranslationKey> = {
  concise: "aiResponseConcise",
  balanced: "aiResponseBalanced",
  detailed: "aiResponseDetailed",
};
const CHART_THEME_PRESETS: Array<{ id: ChartThemePreset; labelKey: TranslationKey }> = [
  { id: "dark", labelKey: "dark" },
  { id: "light", labelKey: "light" },
  { id: "highContrast", labelKey: "highContrast" },
  { id: "custom", labelKey: "custom" },
];
const GRID_LINE_STYLE_OPTIONS: Array<{ id: GridLineStyle; labelKey: TranslationKey }> = [
  { id: "solid", labelKey: "solid" },
  { id: "dashed", labelKey: "dashed" },
];
const CROSSHAIR_STYLE_OPTIONS: Array<{ id: CrosshairStyle; labelKey: TranslationKey }> = [
  { id: "standard", labelKey: "standard" },
  { id: "magnet", labelKey: "magnet" },
];
const LAYOUT_PREFERENCE_OPTIONS: Array<{ id: LayoutPreference; labelKey: TranslationKey }> = [
  { id: "compact", labelKey: "compact" },
  { id: "comfortable", labelKey: "comfortable" },
];
const FAVORITE_DRAWING_TOOL_OPTIONS: Array<{ id: string; labelKey: TranslationKey }> = [
  { id: "trendline", labelKey: "trendline" },
  { id: "horizontalRay", labelKey: "horizontalRay" },
  { id: "vertical", labelKey: "verticalLine" },
  { id: "rectangle", labelKey: "rectangle" },
  { id: "parallelChannel", labelKey: "parallelChannel" },
  { id: "fibRetracement", labelKey: "fibRetracement" },
  { id: "text", labelKey: "textNotes" },
  { id: "ruler", labelKey: "ruler" },
];
const TAB_DESCRIPTION_KEYS: Partial<Record<SettingsTab, TranslationKey>> = {
  account: "settingsAccountDescription",
  notifications: "settingsNotificationsDescription",
  customization: "settingsCustomizationDescription",
  aiHelper: "settingsAiHelperDescription",
  about: "settingsAboutDescription",
  debug: "settingsDebugDescription",
  adminAccounts: "settingsAdminAccountsDescription",
};
type StatusTone = "success" | "error" | "info";
type SettingsStatus = {
  tone: StatusTone;
  message: string;
  details?: string;
};
const DEFAULT_ACTION_TEST = JSON.stringify(
  [
    {
      action_type: "highlight_area",
      params: {
        time_start: 1717200000,
        time_end: 1717286400,
        price_top: 70000,
        price_bottom: 68000,
      },
      reason: "Debug validation sample",
      requires_approval: true,
    },
  ],
  null,
  2,
);

function stringifyDebug(data: unknown): string {
  return JSON.stringify(data, null, 2);
}

function metadataNumber(metadata: Record<string, unknown>, key: string): number | undefined {
  const value = metadata[key];
  return typeof value === "number" ? value : undefined;
}

function formatAccountDate(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(date);
}

function getUserInitials(user: UserResponse): string {
  const source = user.display_name || user.username || user.email || "";
  const words = source
    .replace(/@.*/, "")
    .split(/\s|\.|_/)
    .filter(Boolean);
  const initials = words.length > 1
    ? `${words[0][0]}${words[1][0]}`
    : source.slice(0, 2);
  return initials.toUpperCase() || "LM";
}

function apiMessageToSettingsMessage(message: AIMessageResponse): LocalAiHelpSession["messages"][number] {
  const metadata = message.metadata || {};
  return {
    id: message.id,
    role: message.role === "user" || message.role === "system" ? message.role : "assistant",
    content: message.content,
    created_at: message.created_at,
    token_input: message.token_input ?? metadataNumber(metadata, "token_input"),
    token_output: message.token_output ?? metadataNumber(metadata, "token_output"),
    estimated_cost_usd: metadataNumber(metadata, "estimated_cost_usd"),
  };
}

function apiSessionToSettingsSession(userId: string, session: AISessionResponse): LocalAiHelpSession {
  const fallbackTitle = [session.symbol, session.timeframe?.toUpperCase()]
    .filter(Boolean)
    .join(" ");
  return {
    id: session.id,
    userId,
    title: session.title || fallbackTitle || "LMView AI session",
    mode: session.mode === "interact" ? "interact" : "ask",
    messages: [],
    message_count: session.message_count,
    symbol: session.symbol ?? undefined,
    timeframe: session.timeframe ?? undefined,
    exchange: session.exchange ?? undefined,
    source: "api",
    created_at: session.created_at || new Date().toISOString(),
    updated_at: session.updated_at || session.created_at || new Date().toISOString(),
  };
}

const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  initialTab,
  onClose,
  onLoginClick,
}) => {
  const { t } = useI18n();
  const {
    user,
    loading: authLoading,
    error: authError,
    isAuthenticated,
    updateProfile,
    changePassword,
    deleteAccount,
    refreshUser,
  } = useAuth();
  const isAdmin = user?.role === "admin";
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [sessions, setSessions] = useState<LocalAiHelpSession[]>([]);
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_USER_SETTINGS);
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [debugLoading, setDebugLoading] = useState<string | null>(null);
  const [debugResult, setDebugResult] = useState("");
  const [chartActionJson, setChartActionJson] = useState(DEFAULT_ACTION_TEST);
  const [modelsByTier, setModelsByTier] = useState<Record<string, string[]> | null>(null);

  // Sync selected model to module-level state for useAiChat hook
  const syncSelectedModel = React.useCallback(() => {
    const { selected_model, model_tier } = settings.ai_settings;
    if (selected_model || model_tier) {
      import("@/services/aiService").then(({ setSelectedModel }) => {
        setSelectedModel(selected_model || null, model_tier || null);
      });
    }
  }, [settings.ai_settings]);
  const [adminQuery, setAdminQuery] = useState("");
  const [adminUsers, setAdminUsers] = useState<AdminUsersResponse>({
    users: [],
    total: 0,
    limit: 50,
    offset: 0,
  });
  const [adminUsersLoading, setAdminUsersLoading] = useState(false);
  const [appSettings, setAppSettings] = useState<Record<string, unknown>>({});
  const [aboutHealth, setAboutHealth] = useState<HealthData | null>(null);
  const [aboutHealthLoading, setAboutHealthLoading] = useState(false);
  const [aboutHealthError, setAboutHealthError] = useState("");
  const [profileDraft, setProfileDraft] = useState({
    display_name: "",
    username: "",
    avatar_url: "",
    date_of_birth: "",
    bio: "",
    timezone: "",
  });
  const [passwordDraft, setPasswordDraft] = useState({
    current: "",
    next: "",
    confirm: "",
  });
  const [deleteStep, setDeleteStep] = useState(0);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const chartPreferences = useMemo(
    () => normalizeChartPreferences(settings.customization_defaults),
    [settings.customization_defaults],
  );

  useEffect(() => {
    if (!isOpen) return;
    const adminOnly = initialTab === "adminAccounts" || initialTab === "debug";
    setActiveTab(!isAdmin && adminOnly ? "account" : initialTab);
    setStatus(null);
  }, [initialTab, isAdmin, isOpen]);

  useEffect(() => {
    if (!isAdmin && (activeTab === "adminAccounts" || activeTab === "debug")) {
      setActiveTab("account");
    }
  }, [activeTab, isAdmin]);

  // Fetch available models by tier for model selector
  useEffect(() => {
    if (!isOpen || activeTab !== "aiHelper" || !isAuthenticated) return;
    let cancelled = false;
    import("@/services/aiService").then(({ aiHealth }) => {
      aiHealth().then((health) => {
        if (!cancelled && health.models_by_tier) {
          setModelsByTier(health.models_by_tier);
        }
      }).catch(() => {
        if (!cancelled) setModelsByTier(null);
      });
    });
    return () => { cancelled = true; };
  }, [isOpen, activeTab, isAuthenticated]);

  useEffect(() => {
    if (!isOpen || !user) {
      setSessions([]);
      setSettingsLoading(false);
      return;
    }
    let cancelled = false;
    setProfileDraft({
      display_name: user.display_name || "",
      username: user.username || "",
      avatar_url: user.avatar_url || "",
      date_of_birth: user.date_of_birth || "",
      bio: user.bio || "",
      timezone: user.timezone || "",
    });
    if (DATA_SOURCE === "api") {
      aiListSessions()
        .then(async (payload) => {
          const apiSessions = payload.sessions.map((session) => apiSessionToSettingsSession(user.id, session));
          if (!isAdmin) {
            setSessions(apiSessions);
            return;
          }
          const sessionsWithMessages = await Promise.all(
            apiSessions.map(async (session) => {
              try {
                const history = await aiGetSessionMessages(session.id);
                return {
                  ...session,
                  messages: history.messages.map(apiMessageToSettingsMessage),
                };
              } catch {
                return session;
              }
            }),
          );
          setSessions(sessionsWithMessages);
        })
        .catch(() => setSessions([]));
    } else {
      setSessions(loadLocalAiSessions(user.id));
    }
    setSettingsLoading(true);
    fetchUserSettings()
      .then((nextSettings) => {
        if (!cancelled) setSettings(nextSettings);
      })
      .catch((error) => {
        if (!cancelled) setStatusError(error, t("settingsLoadFailed"));
      })
      .finally(() => {
        if (!cancelled) setSettingsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isAdmin, isOpen, user]);

  useEffect(() => {
    if (!isOpen || !isAdmin || activeTab !== "adminAccounts") return;
    let cancelled = false;
    setAdminUsersLoading(true);
    fetchAdminUsers(adminQuery)
      .then((nextUsers) => {
        if (!cancelled) setAdminUsers(nextUsers);
      })
      .catch((error) => {
        if (!cancelled) setStatusError(error, t("settingsLoadFailed"));
      })
      .finally(() => {
        if (!cancelled) setAdminUsersLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeTab, adminQuery, isAdmin, isOpen]);

  useEffect(() => {
    if (!isOpen || !isAdmin || activeTab !== "debug") return;
    fetchAppSettings()
      .then(setAppSettings)
      .catch(() => setAppSettings({}));
  }, [activeTab, isAdmin, isOpen]);

  useEffect(() => {
    if (!isOpen || activeTab !== "about") return;
    let cancelled = false;
    setAboutHealthLoading(true);
    setAboutHealthError("");
    fetchHealthStatus()
      .then((data) => {
        if (cancelled) return;
        setAboutHealth(data);
      })
      .catch((error) => {
        if (cancelled) return;
        setAboutHealthError(getRoleAwareErrorMessage(error, { isAdmin, fallback: t("systemStatusUnavailable") }));
      })
      .finally(() => {
        if (!cancelled) setAboutHealthLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeTab, isOpen, t]);

  const tabs = useMemo(() => {
    const base: Array<{
      id: SettingsTab;
      label: string;
      icon: LucideIcon;
      locked: boolean;
    }> = [
      { id: "account" as const, label: t("settingsAccount"), icon: UserRound, locked: !isAuthenticated },
      { id: "notifications" as const, label: t("settingsNotifications"), icon: Bell, locked: !isAuthenticated },
      { id: "customization" as const, label: t("settingsCustomization"), icon: SlidersHorizontal, locked: !isAuthenticated },
      { id: "aiHelper" as const, label: t("settingsAiHelper"), icon: Bot, locked: !isAuthenticated },
      { id: "about" as const, label: t("settingsAbout"), icon: Info, locked: false },
    ];
    if (isAdmin) {
      base.push(
        { id: "debug" as const, label: t("settingsDebug"), icon: Bug, locked: false },
        { id: "adminAccounts" as const, label: t("settingsAdminAccounts"), icon: Users, locked: false },
      );
    }
    return base;
  }, [isAdmin, isAuthenticated, t]);
  const activeTabLabel = tabs.find((tab) => tab.id === activeTab)?.label || t("settings");
  const activeTabDescriptionKey = TAB_DESCRIPTION_KEYS[activeTab];
  const activeTabDescription = activeTabDescriptionKey ? t(activeTabDescriptionKey) : "";
  const setStatusMessage = (tone: StatusTone, message: string) => {
    setStatus({ tone, message });
  };
  const setStatusError = (error: unknown, fallback: string) => {
    const normalized = normalizeError(error, { area: "settings", fallbackMessage: fallback });
    setStatus({
      tone: "error",
      message: formatNormalizedError(normalized, false),
      details: isAdmin ? normalized.adminMessage : undefined,
    });
  };

  const saveProfile = async () => {
    setSaving(true);
    const result = await updateProfile({
      display_name: profileDraft.display_name,
      username: profileDraft.username || null,
      avatar_url: profileDraft.avatar_url || null,
      date_of_birth: profileDraft.date_of_birth || null,
      bio: profileDraft.bio || null,
      timezone: profileDraft.timezone || null,
    });
    setSaving(false);
    setStatusMessage(result.success ? "success" : "error", result.success ? t("profileSaved") : result.error || t("error"));
  };

  const submitPassword = async () => {
    if (passwordDraft.next !== passwordDraft.confirm) {
      setStatusMessage("error", t("passwordsMismatch"));
      return;
    }
    setSaving(true);
    const result = await changePassword(passwordDraft.current, passwordDraft.next);
    setSaving(false);
    if (result.success) {
      setPasswordDraft({ current: "", next: "", confirm: "" });
      setStatusMessage("success", t("passwordChanged"));
    } else {
      setStatusMessage("error", result.error || t("error"));
    }
  };

  const submitDeleteAccount = async () => {
    setSaving(true);
    const result = await deleteAccount(deleteConfirmation);
    setSaving(false);
    setStatusMessage(result.success ? "success" : "error", result.success ? t("accountDeleted") : result.error || t("error"));
  };

  const saveSettingsPatch = async (next: Promise<UserSettings>) => {
    setSaving(true);
    try {
      const updated = await next;
      setSettings(updated);
      setStatusMessage("success", t("settingsSaved"));
      syncSelectedModel();
    } catch (error) {
      setStatusError(error, t("error"));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSession = (sessionId: string) => {
    if (!user?.id) return;
    deleteLocalAiSession(user.id, sessionId);
    setSessions(loadLocalAiSessions(user.id));
  };

  const [deleteSessionTarget, setDeleteSessionTarget] = useState<{
    id: string;
    title: string;
  } | null>(null);

  const confirmDeleteSession = async (sessionId: string, sessionTitle: string) => {
    if (!user?.id) return;
    const confirmed = window.confirm(
      t("confirmDeleteAiSession").replace("{title}", sessionTitle),
    );
    if (!confirmed) return;
    setDeleteSessionTarget({ id: sessionId, title: sessionTitle });
    try {
      const session = sessions.find((s) => s.id === sessionId);
      const isApi = session?.source === "api";
      if (isApi) {
        const { aiDeleteSession } = await import("@/services/aiService");
        await aiDeleteSession(sessionId);
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      } else {
        handleDeleteSession(sessionId);
      }
    } catch (error) {
      setStatusError(error, t("deleteSessionFailed"));
    } finally {
      setDeleteSessionTarget(null);
    }
  };

  const handleLoadSession = (targetSessionId: string) => {
    if (!user?.id) return;
    selectAiSession(user.id, targetSessionId);
    setStatusMessage("success", t("aiSessionLoaded"));
    onClose();
  };

  // Start a brand-new AI Helper conversation: drop any active session
  // pointer and clear the chat so the next `sendMessage` creates a
  // fresh session. This is the escape hatch when the current session
  // is stuck (e.g. tour lockup, missing from list, etc.) and the user
  // cannot otherwise recover.
  const handleNewSession = () => {
    if (!user?.id) return;
    selectAiSession(user.id, null);
    window.dispatchEvent(new CustomEvent("lmview:ai-clear-chat"));
    setStatusMessage("success", t("aiSessionStarted"));
    onClose();
  };

  const setCustomizationDefaults = (patch: Partial<UserSettings["customization_defaults"]>) => {
    setSettings((draft) => ({
      ...draft,
      customization_defaults: {
        ...draft.customization_defaults,
        ...patch,
      },
    }));
  };

  const setDrawingDefaults = (patch: Record<string, unknown>) => {
    setSettings((draft) => ({
      ...draft,
      customization_defaults: {
        ...draft.customization_defaults,
        drawing_defaults: {
          ...draft.customization_defaults.drawing_defaults,
          ...patch,
        },
      },
    }));
  };

  const setChartPreferences = (patch: Partial<ChartPreferenceSettings>) => {
    setSettings((draft) => {
      const current = normalizeChartPreferences(draft.customization_defaults);
      const next: ChartPreferenceSettings = {
        ...current,
        ...patch,
        candle_style: {
          ...current.candle_style,
          ...patch.candle_style,
        },
        grid_crosshair: {
          ...current.grid_crosshair,
          ...patch.grid_crosshair,
        },
        scale: {
          ...current.scale,
          ...patch.scale,
        },
        favorite_drawing_tools: patch.favorite_drawing_tools ?? current.favorite_drawing_tools,
      };
      return {
        ...draft,
        customization_defaults: {
          ...draft.customization_defaults,
          theme: next.chart_theme_preset,
          drawing_defaults: {
            ...draft.customization_defaults.drawing_defaults,
            chart_preferences: next,
            compact_panels: next.layout_preference === "compact",
          },
        },
      };
    });
  };

  const resetCustomization = () => {
    setSettings((draft) => ({
      ...draft,
      customization_defaults: {
        ...DEFAULT_USER_SETTINGS.customization_defaults,
        drawing_defaults: {
          ...DEFAULT_USER_SETTINGS.customization_defaults.drawing_defaults,
          chart_preferences: DEFAULT_CHART_PREFERENCES,
        },
      },
    }));
    setStatusMessage("info", t("customizationReset"));
  };

  const aiUsage = useMemo(() => {
    let tokenInput = 0;
    let tokenOutput = 0;
    let cost = 0;
    for (const session of sessions) {
      for (const message of session.messages) {
        tokenInput += message.token_input || 0;
        tokenOutput += message.token_output || 0;
        cost += message.estimated_cost_usd || 0;
      }
    }
    return { tokenInput, tokenOutput, cost };
  }, [sessions]);

  const runHealthCheck = async () => {
    setDebugLoading("health");
    try {
      const data: HealthData = await fetchHealthStatus();
      setDebugResult(stringifyDebug(data));
    } catch (error) {
      setDebugResult(getRoleAwareErrorMessage(error, { isAdmin: true, fallback: "Health check failed" }));
    } finally {
      setDebugLoading(null);
    }
  };

  const runAiHealthCheck = async () => {
    setDebugLoading("ai");
    try {
      const data = await aiHealth();
      setDebugResult(stringifyDebug(data));
    } catch (error) {
      setDebugResult(getRoleAwareErrorMessage(error, { isAdmin: true, fallback: "AI health check failed" }));
    } finally {
      setDebugLoading(null);
    }
  };

  const runChartActionValidation = async () => {
    setDebugLoading("chartAction");
    try {
      const parsed = JSON.parse(chartActionJson);
      const actions = Array.isArray(parsed) ? parsed : [parsed];
      const result = await aiValidateActions(actions);
      setDebugResult(stringifyDebug(result));
    } catch (error) {
      setDebugResult(getRoleAwareErrorMessage(error, { isAdmin: true, fallback: "Chart action validation failed" }));
    } finally {
      setDebugLoading(null);
    }
  };

  const openAiActionTester = () => {
    onClose();
    window.dispatchEvent(new CustomEvent("lmview:open-ai-action-debug"));
  };

  const updateAdminUsers = async (nextQuery = adminQuery) => {
    setAdminUsersLoading(true);
    try {
      setAdminUsers(await fetchAdminUsers(nextQuery));
    } catch (error) {
      setStatusError(error, t("settingsLoadFailed"));
    } finally {
      setAdminUsersLoading(false);
    }
  };

  if (!isOpen) return null;

  const loginRequired = (
    <LockedState
      icon={<Lock size={22} />}
      title={t("loginRequiredTitle")}
      body={t("loginRequiredSettings")}
      actionLabel={t("login")}
      onAction={onLoginClick}
    />
  );

  return (
    <div data-ai-section="settings-modal" className="fixed inset-0 z-[600] flex items-end justify-center bg-black/60 px-0 py-0 backdrop-blur-sm sm:items-center sm:px-3 sm:py-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="flex h-[min(900px,calc(100dvh-0.75rem))] w-full max-w-7xl flex-col overflow-hidden rounded-t border border-gray-700 bg-gray-900 text-gray-100 shadow-2xl sm:h-[min(860px,92vh)] sm:rounded sm:flex-row"
      >
        <aside className="max-h-32 w-full flex-shrink-0 overflow-x-auto overscroll-contain border-b border-gray-800 bg-gray-950 sm:max-h-none sm:w-52 sm:overflow-visible sm:border-b-0 sm:border-r">
          <div className="flex items-center justify-between border-b border-gray-800 px-3 py-3">
            <h2 id="settings-title" className="text-sm font-semibold text-white">
              {t("settings")}
            </h2>
          </div>
          <nav className="flex gap-1 p-2 sm:block sm:space-y-1">
            {tabs.map(({ id, label, icon: Icon, locked }) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveTab(id)}
                className={`flex min-w-[9.5rem] items-center gap-2 rounded px-2 py-2 text-left text-xs font-semibold transition-colors sm:min-w-0 sm:w-full ${
                  activeTab === id
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                }`}
              >
                <Icon size={15} />
                <span className="min-w-0 flex-1 truncate">{label}</span>
                {locked && <Lock size={12} className="text-gray-500" />}
              </button>
            ))}
          </nav>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-start justify-between gap-3 border-b border-gray-800 px-3 py-3 sm:px-4">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-white">
                {activeTabLabel}
              </h3>
              {activeTabDescription && (
                <p className="mt-0.5 max-w-2xl text-xs leading-5 text-gray-500">
                  {activeTabDescription}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex-shrink-0 rounded p-1.5 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
              title={t("close")}
              aria-label={t("close")}
            >
              <X size={18} />
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-3 sm:p-4">
            {status && <StatusBanner tone={status.tone} message={status.message} details={status.details} />}
            {settingsLoading && isAuthenticated && activeTab !== "about" && activeTab !== "debug" && activeTab !== "adminAccounts" && (
              <InlineLoading text={t("settingsLoading")} />
            )}
            {activeTab === "account" && (
              authLoading ? (
                <Panel title={t("accountOverview")}>
                  <div className="flex min-h-40 items-center justify-center gap-2 text-sm text-gray-400">
                    <Loader2 size={16} className="animate-spin text-blue-300" />
                    {t("loadingAccount")}
                  </div>
                </Panel>
              ) : isAuthenticated && user ? (
                <div className="space-y-4">
                  {authError && (
                    <div className="rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs leading-5 text-red-200">
                      {t("accountLoadError")}: {authError}
                    </div>
                  )}

                  <section className="rounded border border-gray-800 bg-gray-850 p-4">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div className="flex min-w-0 items-center gap-3">
                        <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full border border-blue-500/40 bg-blue-500/15 text-sm font-bold text-blue-100">
                          {getUserInitials(user)}
                        </div>
                        <div className="min-w-0">
                          <h4 className="truncate text-base font-semibold text-white">
                            {user.display_name || user.username || user.email}
                          </h4>
                          <p className="truncate text-xs text-gray-400">{user.email}</p>
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            <StatusPill tone={user.is_active ? "success" : "muted"} label={user.is_active ? t("active") : t("inactive")} />
                            <StatusPill tone={user.must_change_password ? "warning" : "muted"} label={user.must_change_password ? t("passwordChangeRequired") : t("accountProtectedData")} />
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={refreshUser}
                        className="inline-flex w-full items-center justify-center gap-2 rounded border border-gray-700 bg-gray-950 px-3 py-1.5 text-xs font-semibold text-gray-200 transition-colors hover:border-blue-500 hover:text-white sm:w-auto"
                      >
                        <RefreshCcw size={13} />
                        {t("refresh")}
                      </button>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                      <AccountDetail label={t("displayName")} value={user.display_name || t("unavailable")} />
                      <AccountDetail label={t("username")} value={user.username || t("unavailable")} />
                      <AccountDetail label={t("role")} value={user.role === "admin" ? t("admin") : user.role === "moderator" ? t("moderator") : user.role === "user" ? t("userRole") : user.role} />
                      <AccountDetail label={t("accountStatus")} value={user.is_active ? t("active") : t("inactive")} />
                      <AccountDetail label={t("memberSince")} value={formatAccountDate(user.created_at) || t("unavailable")} />
                      <AccountDetail label={t("lastLogin")} value={formatAccountDate(user.last_login_at) || t("unavailable")} />
                    </div>
                  </section>

                  <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                    <Panel title={t("profileDetails")}>
                      <p className="text-xs leading-5 text-gray-500">{t("profileDetailsHint")}</p>
                      <TextInput label={t("email")} value={user.email} disabled />
                      <TextInput
                        label={t("displayName")}
                        value={profileDraft.display_name}
                        onChange={(value) => setProfileDraft((draft) => ({ ...draft, display_name: value }))}
                      />
                      <TextInput
                        label={t("username")}
                        value={profileDraft.username}
                        onChange={(value) => setProfileDraft((draft) => ({ ...draft, username: value }))}
                      />
                      <TextInput
                        label={t("avatarUrl")}
                        value={profileDraft.avatar_url}
                        onChange={(value) => setProfileDraft((draft) => ({ ...draft, avatar_url: value }))}
                      />
                      <div className="grid gap-3 sm:grid-cols-2">
                        <TextInput
                          label={t("dateOfBirth")}
                          type="date"
                          value={profileDraft.date_of_birth}
                          onChange={(value) => setProfileDraft((draft) => ({ ...draft, date_of_birth: value }))}
                        />
                        <TextInput
                          label={t("timezone")}
                          value={profileDraft.timezone}
                          onChange={(value) => setProfileDraft((draft) => ({ ...draft, timezone: value }))}
                        />
                      </div>
                      <label className="block text-xs text-gray-400">
                        {t("bio")}
                        <textarea
                          value={profileDraft.bio}
                          onChange={(event) => setProfileDraft((draft) => ({ ...draft, bio: event.target.value }))}
                          className="mt-1 min-h-24 w-full resize-y rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-sm text-white outline-none focus:border-blue-500"
                        />
                      </label>
                      <ActionButton label={t("saveChanges")} icon={<Save size={14} />} loading={saving} onClick={saveProfile} />
                    </Panel>

                    <div className="space-y-4">
                      <Panel title={t("security")}>
                        <p className="text-xs leading-5 text-gray-500">{t("securityHint")}</p>
                        <InfoRow label={t("passwordChangeRequired")} value={user.must_change_password ? t("yes") : t("no")} />
                        <InfoRow label={t("lastPasswordChange")} value={formatAccountDate(user.password_changed_at) || t("unavailable")} />
                      </Panel>
                      <Panel title={t("changePassword")}>
                        <PasswordInput label={t("currentPassword")} value={passwordDraft.current} onChange={(value) => setPasswordDraft((draft) => ({ ...draft, current: value }))} />
                        <PasswordInput label={t("newPassword")} value={passwordDraft.next} onChange={(value) => setPasswordDraft((draft) => ({ ...draft, next: value }))} />
                        <PasswordInput label={t("confirmPassword")} value={passwordDraft.confirm} onChange={(value) => setPasswordDraft((draft) => ({ ...draft, confirm: value }))} />
                        <ActionButton label={t("updatePassword")} icon={<KeyRound size={14} />} loading={saving} onClick={submitPassword} />
                      </Panel>
                      <Panel title={t("dangerZone")}>
                        <p className="text-xs leading-5 text-gray-500">{t("dangerZoneHint")}</p>
                        {deleteStep === 0 ? (
                          <ActionButton label={t("deleteAccount")} icon={<Trash2 size={14} />} danger onClick={() => setDeleteStep(1)} />
                        ) : (
                          <>
                            <p className="text-xs leading-5 text-gray-400">{t("deleteAccountConfirmBody")}</p>
                            <TextInput label={t("confirmation")} value={deleteConfirmation} onChange={setDeleteConfirmation} />
                            <ActionButton label={t("deleteAccount")} icon={<Trash2 size={14} />} danger loading={saving} onClick={submitDeleteAccount} />
                          </>
                        )}
                      </Panel>
                    </div>
                  </div>
                </div>
              ) : loginRequired
            )}

            {activeTab === "notifications" && (
              isAuthenticated ? (
                <div className="grid gap-4 lg:grid-cols-2">
                  <Panel title={t("settingsNotifications")}>
                    <Toggle label={t("notificationSystem")} checked={settings.notification_preferences.system} onChange={(value) => setSettings((draft) => ({ ...draft, notification_preferences: { ...draft.notification_preferences, system: value } }))} />
                    <Toggle label={t("notificationAlerts")} checked={settings.notification_preferences.alerts} onChange={(value) => setSettings((draft) => ({ ...draft, notification_preferences: { ...draft.notification_preferences, alerts: value } }))} />
                    <Toggle label={t("notificationNews")} checked={settings.notification_preferences.news} onChange={(value) => setSettings((draft) => ({ ...draft, notification_preferences: { ...draft.notification_preferences, news: value } }))} />
                    <Toggle label={t("notificationAi")} checked={settings.notification_preferences.ai} onChange={(value) => setSettings((draft) => ({ ...draft, notification_preferences: { ...draft.notification_preferences, ai: value } }))} />
                    <Toggle label={t("notificationSound")} checked={settings.notification_preferences.sound} onChange={(value) => setSettings((draft) => ({ ...draft, notification_preferences: { ...draft.notification_preferences, sound: value } }))} />
                    <Toggle label={t("notificationDesktop")} checked={settings.notification_preferences.desktop} onChange={(value) => setSettings((draft) => ({ ...draft, notification_preferences: { ...draft.notification_preferences, desktop: value } }))} />
                    <Toggle label={t("notificationEmail")} checked={settings.notification_preferences.email} onChange={(value) => setSettings((draft) => ({ ...draft, notification_preferences: { ...draft.notification_preferences, email: value } }))} />
                    <ActionButton label={t("saveChanges")} icon={<Save size={14} />} loading={saving} onClick={() => saveSettingsPatch(saveNotificationPreferences(settings.notification_preferences))} />
                  </Panel>
                  <Panel title={t("alertSettings")}>
                    <Toggle label={t("priceAlerts")} checked={settings.alert_settings.price_alerts} onChange={(value) => setSettings((draft) => ({ ...draft, alert_settings: { ...draft.alert_settings, price_alerts: value } }))} />
                    <Toggle label={t("volumeAlerts")} checked={settings.alert_settings.volume_alerts} onChange={(value) => setSettings((draft) => ({ ...draft, alert_settings: { ...draft.alert_settings, volume_alerts: value } }))} />
                    <Toggle label={t("indicatorAlerts")} checked={settings.alert_settings.indicator_alerts} onChange={(value) => setSettings((draft) => ({ ...draft, alert_settings: { ...draft.alert_settings, indicator_alerts: value } }))} />
                    <Toggle label={t("whaleAlerts")} checked={settings.alert_settings.whale_alerts} onChange={(value) => setSettings((draft) => ({ ...draft, alert_settings: { ...draft.alert_settings, whale_alerts: value } }))} />
                    <Toggle label={t("quietHours")} checked={settings.alert_settings.quiet_hours_enabled} onChange={(value) => setSettings((draft) => ({ ...draft, alert_settings: { ...draft.alert_settings, quiet_hours_enabled: value } }))} />
                    <ActionButton label={t("saveChanges")} icon={<Save size={14} />} loading={saving} onClick={() => saveSettingsPatch(saveAlertSettings(settings.alert_settings))} />
                  </Panel>
                </div>
              ) : loginRequired
            )}

            {activeTab === "customization" && (
              isAuthenticated ? (
                <div className="space-y-4">
                  <section className="flex flex-col gap-3 rounded border border-gray-800 bg-gray-850 p-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-white">{t("chartPresets")}</h4>
                      <p className="mt-1 text-xs leading-5 text-gray-500">{t("chartPresetsHint")}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={resetCustomization}
                        className="inline-flex items-center gap-2 rounded border border-gray-700 bg-gray-950 px-3 py-1.5 text-xs font-semibold text-gray-200 transition-colors hover:border-blue-500 hover:text-white"
                      >
                        <RefreshCcw size={14} />
                        {t("reset")}
                      </button>
                      <ActionButton label={t("saveChanges")} icon={<Save size={14} />} loading={saving} onClick={() => saveSettingsPatch(saveCustomizationDefaults(settings.customization_defaults))} />
                    </div>
                  </section>

                  <div className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(22rem,0.85fr)]">
                    <div className="space-y-4">
                      <Panel title={t("chartThemePreset")}>
                        <PresetButtons
                          items={CHART_THEME_PRESETS.map((preset) => ({ id: preset.id, label: t(preset.labelKey) }))}
                          activeId={chartPreferences.chart_theme_preset}
                          onSelect={(id) => setChartPreferences({ chart_theme_preset: id as ChartThemePreset })}
                        />
                        <p className="text-xs leading-5 text-gray-500">{t("chartThemePresetHint")}</p>
                      </Panel>

                      <Panel title={t("candleStyle")}>
                        <div className="grid gap-3 sm:grid-cols-2">
                          <ColorInput label={t("upColor")} value={chartPreferences.candle_style.up_color} onChange={(value) => setChartPreferences({ candle_style: { ...chartPreferences.candle_style, up_color: value } })} />
                          <ColorInput label={t("downColor")} value={chartPreferences.candle_style.down_color} onChange={(value) => setChartPreferences({ candle_style: { ...chartPreferences.candle_style, down_color: value } })} />
                        </div>
                        <Toggle label={t("showWicks")} checked={chartPreferences.candle_style.wick_visible} onChange={(value) => setChartPreferences({ candle_style: { ...chartPreferences.candle_style, wick_visible: value } })} />
                        <Toggle label={t("showBorders")} checked={chartPreferences.candle_style.border_visible} onChange={(value) => setChartPreferences({ candle_style: { ...chartPreferences.candle_style, border_visible: value } })} />
                      </Panel>

                      <Panel title={t("gridCrosshair")}>
                        <Toggle label={t("showGrid")} checked={chartPreferences.grid_crosshair.grid_visible} onChange={(value) => setChartPreferences({ grid_crosshair: { ...chartPreferences.grid_crosshair, grid_visible: value } })} />
                        <SelectRow label={t("gridLineStyle")} value={chartPreferences.grid_crosshair.grid_style} options={GRID_LINE_STYLE_OPTIONS.map((item) => item.id)} getOptionLabel={(value) => t(GRID_LINE_STYLE_OPTIONS.find((item) => item.id === value)?.labelKey ?? "solid")} onChange={(value) => setChartPreferences({ grid_crosshair: { ...chartPreferences.grid_crosshair, grid_style: value as GridLineStyle } })} />
                        <SelectRow label={t("crosshairStyle")} value={chartPreferences.grid_crosshair.crosshair_style} options={CROSSHAIR_STYLE_OPTIONS.map((item) => item.id)} getOptionLabel={(value) => t(CROSSHAIR_STYLE_OPTIONS.find((item) => item.id === value)?.labelKey ?? "standard")} onChange={(value) => setChartPreferences({ grid_crosshair: { ...chartPreferences.grid_crosshair, crosshair_style: value as CrosshairStyle } })} />
                      </Panel>
                    </div>

                    <div className="space-y-4">
                      <Panel title={t("savedDefaults")}>
                        <div className="space-y-3">
                          <SelectRow label={t("defaultTimeframe")} value={settings.customization_defaults.default_timeframe} options={Object.keys(TIMEFRAMES)} onChange={(value) => setCustomizationDefaults({ default_timeframe: value })} />
                          <SelectRow label={t("defaultChartType")} value={settings.customization_defaults.default_chart_type} options={CHART_TYPE_OPTIONS} getOptionLabel={(value) => t(CHART_TYPE_LABEL_KEYS[value as ChartType])} onChange={(value) => setCustomizationDefaults({ default_chart_type: value })} />
                          <TextInput label={t("defaultSymbol")} value={settings.customization_defaults.default_symbol} onChange={(value) => setCustomizationDefaults({ default_symbol: value.toUpperCase() })} />
                          <SelectRow label={t("defaultExchange")} value={settings.customization_defaults.default_exchange} options={["binance", "okx"]} onChange={(value) => setCustomizationDefaults({ default_exchange: value })} />
                        </div>
                        <p className="text-xs leading-5 text-gray-500">{t("savedDefaultsHint")}</p>
                      </Panel>

                      <Panel title={t("scaleSettings")}>
                        <Toggle label={t("priceLabels")} checked={chartPreferences.scale.price_labels_visible} onChange={(value) => setChartPreferences({ scale: { ...chartPreferences.scale, price_labels_visible: value } })} />
                        <Toggle label={t("timeLabels")} checked={chartPreferences.scale.time_labels_visible} onChange={(value) => setChartPreferences({ scale: { ...chartPreferences.scale, time_labels_visible: value } })} />
                        <Toggle label={t("secondsVisibility")} checked={chartPreferences.scale.seconds_visible} onChange={(value) => setChartPreferences({ scale: { ...chartPreferences.scale, seconds_visible: value } })} />
                        <RangeInput label={t("barSpacing")} value={chartPreferences.scale.bar_spacing} min={4} max={18} onChange={(value) => setChartPreferences({ scale: { ...chartPreferences.scale, bar_spacing: value } })} />
                      </Panel>

                      <Panel title={t("layoutPreference")}>
                        <PresetButtons
                          items={LAYOUT_PREFERENCE_OPTIONS.map((preset) => ({ id: preset.id, label: t(preset.labelKey) }))}
                          activeId={chartPreferences.layout_preference}
                          onSelect={(id) => setChartPreferences({ layout_preference: id as LayoutPreference })}
                        />
                        <p className="text-xs leading-5 text-gray-500">{t("layoutPreferenceHint")}</p>
                      </Panel>

                      <Panel title={t("favoriteDrawingTools")}>
                        <div className="grid gap-2 sm:grid-cols-2">
                          {FAVORITE_DRAWING_TOOL_OPTIONS.map((tool) => {
                            const selected = chartPreferences.favorite_drawing_tools.includes(tool.id);
                            return (
                              <ChipToggle
                                key={tool.id}
                                label={t(tool.labelKey)}
                                selected={selected}
                                onClick={() => {
                                  const next = selected
                                    ? chartPreferences.favorite_drawing_tools.filter((id) => id !== tool.id)
                                    : [...chartPreferences.favorite_drawing_tools, tool.id];
                                  setChartPreferences({ favorite_drawing_tools: next });
                                }}
                              />
                            );
                          })}
                        </div>
                        <p className="text-xs leading-5 text-gray-500">{t("favoriteDrawingToolsHint")}</p>
                      </Panel>

                      <Panel title={t("indicatorTemplates")}>
                        <PresetButtons
                          items={INDICATOR_PRESETS.map((preset) => ({ id: preset.id, label: t(preset.labelKey) }))}
                          activeId={settings.customization_defaults.drawing_defaults.indicator_preset as string | undefined}
                          onSelect={(id) => {
                            const preset = INDICATOR_PRESETS.find((item) => item.id === id);
                            if (!preset) return;
                            setCustomizationDefaults({ visible_indicators: [...preset.indicators] });
                            setDrawingDefaults({ indicator_preset: id });
                          }}
                        />
                        <div className="flex flex-wrap gap-1.5">
                          {settings.customization_defaults.visible_indicators.map((indicator) => (
                            <span key={indicator} className="rounded border border-gray-700 bg-gray-950 px-2 py-1 text-[11px] text-gray-300">
                              {indicator}
                            </span>
                          ))}
                        </div>
                        <Toggle label={t("showVolume")} checked={settings.customization_defaults.drawing_defaults.show_volume !== false} onChange={(value) => setDrawingDefaults({ show_volume: value })} />
                      </Panel>
                    </div>

                    <div className="space-y-4 xl:col-span-2 2xl:col-span-1">
                      <Panel title={t("chartPreview")}>
                        <ChartPresetPreview preferences={chartPreferences} />
                        <InfoRow label={t("chartThemePreset")} value={t(CHART_THEME_PRESETS.find((item) => item.id === chartPreferences.chart_theme_preset)?.labelKey ?? "dark")} />
                        <InfoRow label={t("layoutPreference")} value={t(LAYOUT_PREFERENCE_OPTIONS.find((item) => item.id === chartPreferences.layout_preference)?.labelKey ?? "comfortable")} />
                        <InfoRow label={t("defaultChartType")} value={t(CHART_TYPE_LABEL_KEYS[settings.customization_defaults.default_chart_type as ChartType] ?? "candlestick")} />
                      </Panel>

                      <Panel title={t("toolPresets")}>
                        <PresetButtons
                          items={TOOL_PRESETS.map((preset) => ({ id: preset.id, label: t(preset.labelKey) }))}
                          activeId={settings.customization_defaults.drawing_defaults.tool_preset as string | undefined}
                          onSelect={(id) => setDrawingDefaults({ tool_preset: id })}
                        />
                        <Toggle label={t("magnetDefault")} checked={settings.customization_defaults.drawing_defaults.magnet_default === true} onChange={(value) => setDrawingDefaults({ magnet_default: value })} />
                      </Panel>

                      <Panel title={t("layoutPresets")}>
                        <PresetButtons
                          items={LAYOUT_PRESETS.map((preset) => ({ id: preset.id, label: t(preset.labelKey) }))}
                          activeId={settings.customization_defaults.drawing_defaults.layout_preset as string | undefined}
                          onSelect={(id) => setDrawingDefaults({ layout_preset: id })}
                        />
                        <p className="text-xs leading-5 text-gray-500">{t("layoutPresetsHint")}</p>
                      </Panel>
                    </div>
                  </div>
                </div>
              ) : loginRequired
            )}

            {activeTab === "aiHelper" && (
              isAuthenticated ? (
                <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
                  <Panel title={t("aiAgentSettings")}>
                    {/* Model selector — fetch available models from health endpoint */}
      {(() => {
        const sel = settings.ai_settings.selected_model;
        const allModels = modelsByTier
          ? Object.values(modelsByTier).flat()
          : [];
        const hasAnyModel = allModels.length > 0;

        return hasAnyModel ? (
          <SelectRow
            label={t("aiModel")}
            value={sel || ""}
            options={["", ...allModels]}
            getOptionLabel={(value) => {
              if (!value) return t("aiModelAuto") || "Auto (Default)";
              // Find which tier this model belongs to
              let modelTier = "";
              if (modelsByTier) {
                for (const [t, models] of Object.entries(modelsByTier)) {
                  if (models.includes(value)) {
                    modelTier = t;
                    break;
                  }
                }
              }
              const suffix = modelTier ? ` (${modelTier})` : "";
              return `${value}${suffix}`;
            }}
            onChange={(value) => {
              // Remove tier suffix if present
              const modelName = value.includes(" (") ? value.split(" (")[0] : value;
              setSettings((draft) => ({
                ...draft,
                ai_settings: {
                  ...draft.ai_settings,
                  selected_model: modelName || null,
                  model_tier: modelName && modelsByTier
                    ? (Object.entries(modelsByTier).find(([, models]) => models.includes(modelName))?.[0] || null)
                    : null,
                },
              }));
            }}
          />
        ) : null;
      })()}

      <SelectRow
        label={t("aiResponseStyle")}
        value={settings.ai_settings.response_style}
        options={["concise", "balanced", "detailed"]}
        getOptionLabel={(value) => t(AI_RESPONSE_STYLE_LABEL_KEYS[value] ?? "aiResponseBalanced")}
        onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, response_style: value } }))}
      />
                    <Toggle label={t("riskReminders")} checked={settings.ai_settings.risk_reminders} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, risk_reminders: value } }))} />
                    <Toggle label={t("includeChartContext")} checked={settings.ai_settings.auto_include_chart_context} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, auto_include_chart_context: value } }))} />
                    <Toggle label={t("allowChartActions")} checked={settings.ai_settings.allow_chart_actions} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, allow_chart_actions: value } }))} />
                    <Toggle label={t("actionConfirmation")} checked={settings.ai_settings.require_action_confirmation} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, require_action_confirmation: value } }))} />
                    <NumberInput label={t("maxContextCandles")} value={settings.ai_settings.max_context_candles} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, max_context_candles: value } }))} />
                    <NumberInput label={t("memoryRetentionDays")} value={settings.ai_settings.memory_retention_days} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, memory_retention_days: value } }))} />
                    <ActionButton label={t("saveChanges")} icon={<Save size={14} />} loading={saving} onClick={() => saveSettingsPatch(saveAiSettings(settings.ai_settings))} />
                  </Panel>
                  <Panel title={t("savedAiSessions")}>
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="text-[10px] text-gray-500">
                        {sessions.length} {t("savedAiSessionsCount")}
                      </span>
                      <button
                        type="button"
                        onClick={handleNewSession}
                        className="flex items-center gap-1 rounded border border-blue-500/40 bg-blue-500/10 px-2 py-1 text-[11px] font-semibold text-blue-200 hover:bg-blue-500/20"
                        data-testid="ai-new-session"
                      >
                        <Plus size={11} /> {t("newChat")}
                      </button>
                    </div>
                    {sessions.length > 0 ? sessions.map((session) => (
                      <div key={session.id} className="flex items-center gap-3 border-b border-gray-800 py-2 last:border-b-0">
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-xs font-semibold text-white">{session.title}</div>
                          <div className="text-[11px] text-gray-500">
                            {session.message_count ?? session.messages.length} {t("messages")}
                            {session.symbol && session.timeframe ? ` - ${session.symbol} ${session.timeframe.toUpperCase()}` : ""}
                          </div>
                        </div>
                        <button type="button" onClick={() => handleLoadSession(session.id)} className="rounded border border-gray-700 px-2 py-1 text-[11px] font-semibold text-gray-300 hover:border-blue-500 hover:text-white" title={t("loadSession")}>
                          {t("loadSession")}
                        </button>
                        <button
                          type="button"
                          onClick={() => void confirmDeleteSession(session.id, session.title)}
                          disabled={deleteSessionTarget?.id === session.id}
                          className="flex h-7 w-7 items-center justify-center rounded p-1 text-gray-500 hover:bg-red-500/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
                          title={t("deleteSession")}
                          aria-label={t("deleteSession")}
                          data-testid={`ai-delete-session-${session.id}`}
                        >
                          {deleteSessionTarget?.id === session.id ? (
                            <Loader2 size={12} className="animate-spin" />
                          ) : (
                            <Trash2 size={14} />
                          )}
                        </button>
                      </div>
                    )) : (
                      <EmptyState text={t("noSavedAiSessions")} />
                    )}
                  </Panel>
                  {isAdmin && (
                    <Panel title={t("aiTokenUsage")}>
                      <InfoRow label={t("totalInputTokens")} value={aiUsage.tokenInput.toLocaleString()} />
                      <InfoRow label={t("totalOutputTokens")} value={aiUsage.tokenOutput.toLocaleString()} />
                      <InfoRow label={t("estimatedCost")} value={`$${aiUsage.cost.toFixed(4)}`} />
                    </Panel>
                  )}
                </div>
              ) : loginRequired
            )}

            {activeTab === "about" && (
              <div className="space-y-4">
                <section className="rounded border border-blue-500/30 bg-blue-500/10 p-5">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded bg-blue-600 text-white">
                        <Info size={21} />
                      </div>
                      <h4 className="text-xl font-semibold text-white">LMView</h4>
                      <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-300">{t("aboutProductDescription")}</p>
                    </div>
                    <div className="grid min-w-48 gap-2 text-xs">
                      <AboutMetric label={t("frontendVersion")} value={FRONTEND_VERSION || t("unavailable")} />
                      <AboutMetric label={t("backendVersion")} value={BACKEND_VERSION || t("unavailable")} />
                    </div>
                  </div>
                </section>

                <div className="grid gap-4 lg:grid-cols-[1fr_0.85fr]">
                  <div className="space-y-4">
                    <Panel title={t("coreFeatures")}>
                      <div className="flex flex-wrap gap-2">
                        {[
                          "featureRealtimeChart",
                          "featureDrawingTools",
                          "featureIndicators",
                          "featureMarketOverview",
                          "featureNews",
                          "featureScreener",
                          "featureAiAskInteract",
                        ].map((key) => (
                          <FeaturePill key={key} label={t(key as TranslationKey)} />
                        ))}
                      </div>
                    </Panel>

                    <section className="rounded border border-amber-500/30 bg-amber-500/10 p-4">
                      <h5 className="text-xs font-semibold uppercase text-amber-200">{t("dataDisclaimer")}</h5>
                      <p className="mt-2 text-sm leading-6 text-amber-50/90">{t("dataDisclaimerBody")}</p>
                    </section>
                  </div>

                  <div className="space-y-4">
                    <Panel title={t("systemStatus")}>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-gray-300">{t("backendStatus")}</span>
                        <StatusPill
                          tone={aboutHealth?.status === "ok" ? "success" : aboutHealth ? "warning" : "muted"}
                          label={aboutHealthLoading ? t("loading") : aboutHealth?.status || t("unavailable")}
                        />
                      </div>
                      {aboutHealth?.total_latency_ms != null && (
                        <InfoRow label={t("totalLatency")} value={`${aboutHealth.total_latency_ms} ms`} />
                      )}
                      {aboutHealth?.checked_at && (
                        <InfoRow label={t("lastChecked")} value={new Date(aboutHealth.checked_at).toLocaleString()} />
                      )}
                      {aboutHealthError && (
                        <p className="text-xs leading-5 text-gray-500">{t("systemStatusUnavailable")}</p>
                      )}
                      <DebugButton loading={aboutHealthLoading} label={t("refresh")} onClick={async () => {
                        setAboutHealthLoading(true);
                        setAboutHealthError("");
                        try {
                          setAboutHealth(await fetchHealthStatus());
                        } catch (error) {
                          setAboutHealthError(getRoleAwareErrorMessage(error, { isAdmin, fallback: t("systemStatusUnavailable") }));
                        } finally {
                          setAboutHealthLoading(false);
                        }
                      }} />
                    </Panel>

                    <Panel title={t("resources")}>
                      <AboutResource title={t("documentation")} detail={t("productGuide")} />
                      <AboutResource title={t("changelog")} detail={t("releaseHistory")} />
                      <AboutResource title={t("systemHealthInfo")} detail={t("systemStatusApi")} />
                    </Panel>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "debug" && isAdmin && (
              <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
                <div className="space-y-4">
                  <Panel title={t("systemHealthInfo")}>
                    <div className="flex flex-wrap gap-2">
                      <DebugButton loading={debugLoading === "health"} label={t("runHealthCheck")} onClick={runHealthCheck} />
                      <DebugButton loading={debugLoading === "ai"} label={t("runAiHealthCheck")} onClick={runAiHealthCheck} />
                    </div>
                  </Panel>
                  <Panel title={t("appSettings")}>
                    <pre className="max-h-48 overflow-auto rounded border border-gray-800 bg-gray-950 p-3 text-xs text-gray-300">{stringifyDebug(appSettings)}</pre>
                  </Panel>
                  <Panel title={t("chartActionTest")}>
                    <DebugButton loading={false} label={t("aiActionDebug")} onClick={openAiActionTester} />
                    <textarea value={chartActionJson} onChange={(event) => setChartActionJson(event.target.value)} className="h-48 w-full rounded border border-gray-700 bg-gray-950 p-2 font-mono text-xs text-gray-200 outline-none focus:border-blue-500" />
                    <DebugButton loading={debugLoading === "chartAction"} label={t("validate")} onClick={runChartActionValidation} />
                  </Panel>
                </div>
                <pre className="min-h-72 overflow-auto rounded border border-gray-800 bg-gray-950 p-3 text-xs leading-5 text-gray-300">
                  {debugResult || t("debugNoResult")}
                </pre>
              </div>
            )}

            {activeTab === "adminAccounts" && isAdmin && (
              <Panel title={t("settingsAdminAccounts")}>
                <div className="mb-3 flex flex-col gap-2 sm:flex-row">
                  <input
                    value={adminQuery}
                    onChange={(event) => setAdminQuery(event.target.value)}
                    placeholder={t("searchUsers")}
                    className="min-w-0 flex-1 rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-sm text-white outline-none focus:border-blue-500"
                  />
                  <ActionButton label={t("refresh")} icon={<RefreshCcw size={14} />} onClick={() => updateAdminUsers()} />
                </div>
                <div className="overflow-hidden rounded border border-gray-800">
                  {adminUsersLoading ? <InlineLoading text={t("adminUsersLoading")} /> : adminUsers.users.length === 0 ? <EmptyState text={t("noUsers")} /> : adminUsers.users.map((item) => (
                    <div key={item.id} className="grid gap-2 border-b border-gray-800 p-3 last:border-b-0 lg:grid-cols-[1fr_auto]">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-white">{item.display_name || item.email}</div>
                        <div className="truncate text-xs text-gray-500">{item.email}</div>
                        <div className="mt-1 flex flex-wrap gap-1 text-[10px] uppercase tracking-wide">
                          <span className="rounded border border-gray-700 px-1.5 py-0.5 text-gray-300">{item.role}</span>
                          <span className={`rounded border px-1.5 py-0.5 ${item.is_active ? "border-emerald-500/30 text-emerald-300" : "border-red-500/30 text-red-300"}`}>{item.is_active ? t("active") : t("inactive")}</span>
                          {item.must_change_password && <span className="rounded border border-amber-500/30 px-1.5 py-0.5 text-amber-300">{t("passwordChangeRequired")}</span>}
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5 sm:justify-end">
                        <select
                          value={item.role}
                          onChange={async (event) => {
                            await updateAdminUser(item.id, { role: event.target.value });
                            await refreshUser();
                            await updateAdminUsers();
                          }}
                          className="rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-xs text-white"
                        >
                          <option value="user">{t("userRole")}</option>
                          <option value="moderator">{t("moderator")}</option>
                          <option value="admin">{t("admin")}</option>
                        </select>
                        <button type="button" onClick={async () => { await updateAdminUser(item.id, { is_active: !item.is_active }); await updateAdminUsers(); }} className="rounded border border-gray-700 px-2 py-1.5 text-xs text-gray-200 hover:border-blue-500 hover:text-white">
                          {item.is_active ? t("deactivate") : t("activate")}
                        </button>
                        <button type="button" onClick={async () => { await forceAdminPasswordChange(item.id); await updateAdminUsers(); }} className="rounded border border-amber-500/30 px-2 py-1.5 text-xs text-amber-200 hover:bg-amber-500/10">
                          {t("forcePassword")}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </Panel>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="min-w-0 rounded border border-gray-800 bg-gray-850">
      <div className="border-b border-gray-800 px-3 py-2 text-xs font-semibold uppercase text-gray-400">
        {title}
      </div>
      <div className="space-y-3 p-3">{children}</div>
    </section>
  );
}

function StatusBanner({ tone, message, details }: { tone: StatusTone; message: string; details?: string }) {
  const toneClass = {
    success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-100",
    error: "border-red-500/30 bg-red-500/10 text-red-100",
    info: "border-blue-500/30 bg-blue-500/10 text-blue-100",
  }[tone];
  const Icon = tone === "success" ? CheckCircle2 : tone === "error" ? AlertCircle : Info;

  return (
    <div className={`mb-4 flex items-start gap-2 rounded border px-3 py-2 text-sm ${toneClass}`}>
      <Icon size={16} className="mt-0.5 flex-shrink-0" />
      <div className="min-w-0 flex-1">
        <span>{message}</span>
        {details && (
          <details className="mt-2 rounded border border-gray-700/70 bg-gray-950/70 p-2 text-xs text-gray-300">
            <summary className="cursor-pointer font-semibold">Technical details</summary>
            <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap leading-5">{details}</pre>
          </details>
        )}
      </div>
    </div>
  );
}

function InlineLoading({ text }: { text: string }) {
  return (
    <div className="mb-4 flex min-h-16 items-center justify-center gap-2 rounded border border-gray-800 bg-gray-950/70 px-3 py-3 text-sm text-gray-400">
      <Loader2 size={16} className="animate-spin text-blue-300" />
      <span>{text}</span>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1.5 text-sm sm:grid-cols-[minmax(9rem,1fr)_minmax(7rem,auto)] sm:items-center sm:gap-4">
      <span className="min-w-0 text-gray-500">{label}</span>
      <span className="min-w-0 break-words font-medium text-gray-200 sm:text-right">{value}</span>
    </div>
  );
}

function AccountDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 border-t border-gray-800 pt-3">
      <div className="text-[11px] font-semibold uppercase text-gray-500">{label}</div>
      <div className="mt-1 min-w-0 truncate text-sm font-medium text-gray-100">{value}</div>
    </div>
  );
}

function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: "success" | "warning" | "muted";
}) {
  const toneClass = {
    success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
    warning: "border-amber-500/30 bg-amber-500/10 text-amber-200",
    muted: "border-gray-700 bg-gray-950 text-gray-300",
  }[tone];

  return (
    <span className={`rounded border px-2 py-0.5 text-[11px] font-semibold ${toneClass}`}>
      {label}
    </span>
  );
}

function FeaturePill({ label }: { label: string }) {
  return (
    <span className="rounded border border-gray-700 bg-gray-950 px-2.5 py-1.5 text-xs font-semibold text-gray-200">
      {label}
    </span>
  );
}

function AboutMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-blue-500/20 bg-gray-950/70 px-3 py-2">
      <div className="text-[11px] font-semibold uppercase text-gray-500">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold text-gray-100">{value}</div>
    </div>
  );
}

function AboutResource({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="grid gap-1.5 border-b border-gray-800 py-2 last:border-b-0 sm:grid-cols-[minmax(8rem,0.9fr)_minmax(10rem,1.1fr)] sm:items-center sm:gap-4">
      <span className="min-w-0 text-sm font-medium text-gray-200">{title}</span>
      <span className="min-w-0 break-words text-xs leading-5 text-gray-500 sm:text-right">{detail}</span>
    </div>
  );
}

function TextInput({
  label,
  value,
  type = "text",
  disabled = false,
  onChange,
}: {
  label: string;
  value: string;
  type?: string;
  disabled?: boolean;
  onChange?: (value: string) => void;
}) {
  return (
    <label className="block text-xs text-gray-400">
      {label}
      <input
        type={type}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange?.(event.target.value)}
        className="mt-1 w-full rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-sm text-white outline-none transition-colors focus:border-blue-500 disabled:opacity-60"
      />
    </label>
  );
}

function PasswordInput(props: Omit<React.ComponentProps<typeof TextInput>, "type">) {
  return <TextInput {...props} type="password" />;
}

function ColorInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-xs text-gray-400">
      {label}
      <div className="mt-1 flex items-center gap-2">
        <input
          type="color"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="h-8 w-10 rounded border border-gray-700 bg-gray-950 p-1"
        />
        <input
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="min-w-0 flex-1 rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-xs text-white outline-none focus:border-blue-500"
        />
      </div>
    </label>
  );
}

function SelectRow({
  label,
  value,
  options,
  getOptionLabel,
  onChange,
}: {
  label: string;
  value: string;
  options: readonly string[];
  getOptionLabel?: (value: string) => string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1.5 text-sm sm:grid-cols-[minmax(10rem,1fr)_minmax(9rem,auto)] sm:items-center sm:gap-4">
      <span className="min-w-0 text-gray-300">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full min-w-0 rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-xs text-white outline-none focus:border-blue-500 sm:w-40"
      >
        {options.map((option) => (
          <option key={option} value={option}>{getOptionLabel?.(option) ?? option}</option>
        ))}
      </select>
    </label>
  );
}

function RangeInput({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 flex items-center justify-between gap-3">
        <span className="text-gray-300">{label}</span>
        <span className="text-xs font-semibold text-gray-400">{value}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full accent-blue-600"
      />
    </label>
  );
}

function ChipToggle({
  label,
  selected,
  onClick,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded border px-2 py-1.5 text-left text-xs font-semibold transition-colors ${
        selected
          ? "border-blue-500 bg-blue-600 text-white"
          : "border-gray-700 bg-gray-950 text-gray-300 hover:border-blue-500 hover:text-white"
      }`}
    >
      {label}
    </button>
  );
}

function ChartPresetPreview({ preferences }: { preferences: ChartPreferenceSettings }) {
  const light = preferences.chart_theme_preset === "light";
  const highContrast = preferences.chart_theme_preset === "highContrast";
  const background = light ? "#f8fafc" : highContrast ? "#050505" : "#0f172a";
  const gridColor = light ? "rgba(15, 23, 42, 0.16)" : highContrast ? "rgba(255,255,255,0.28)" : "rgba(148, 163, 184, 0.18)";
  const textColor = light ? "#334155" : "#cbd5e1";
  const gridImage = preferences.grid_crosshair.grid_visible
    ? `linear-gradient(${gridColor} 1px, transparent 1px), linear-gradient(90deg, ${gridColor} 1px, transparent 1px)`
    : "none";
  const gridSize = preferences.grid_crosshair.grid_style === "dashed" ? "24px 18px" : "18px 18px";

  return (
    <div
      className="relative h-44 overflow-hidden rounded border border-gray-800"
      style={{
        backgroundColor: background,
        backgroundImage: gridImage,
        backgroundSize: gridSize,
      }}
    >
      <div className="absolute inset-y-0 right-0 w-12 border-l border-gray-700/60" />
      {preferences.scale.price_labels_visible && (
        <div className="absolute right-2 top-3 space-y-8 text-[10px]" style={{ color: textColor }}>
          <div>68.4k</div>
          <div>67.8k</div>
          <div>67.2k</div>
        </div>
      )}
      {preferences.scale.time_labels_visible && (
        <div className="absolute bottom-2 left-4 right-14 flex justify-between text-[10px]" style={{ color: textColor }}>
          <span>10:15</span>
          <span>{preferences.scale.seconds_visible ? "10:30:15" : "10:30"}</span>
          <span>10:45</span>
        </div>
      )}
      <div className="absolute bottom-7 left-5 right-16 top-5 flex items-end gap-2">
        {[44, 72, 58, 96, 84, 112, 76, 100].map((height, index) => {
          const up = index % 3 !== 0;
          const color = up ? preferences.candle_style.up_color : preferences.candle_style.down_color;
          return (
            <div key={height + index} className="relative flex h-full items-end justify-center" style={{ width: preferences.scale.bar_spacing + 4 }}>
              {preferences.candle_style.wick_visible && (
                <div className="absolute bottom-2 w-px" style={{ height: height + 22, backgroundColor: color }} />
              )}
              <div
                className={preferences.candle_style.border_visible ? "border" : ""}
                style={{
                  width: Math.max(5, preferences.scale.bar_spacing),
                  height,
                  backgroundColor: preferences.candle_style.border_visible ? "transparent" : color,
                  borderColor: color,
                }}
              />
            </div>
          );
        })}
      </div>
      <div className="absolute left-1/2 top-0 h-full border-l border-blue-300/60" />
      <div className="absolute left-0 top-1/2 w-full border-t border-blue-300/60" />
    </div>
  );
}

function PresetButtons({
  items,
  activeId,
  onSelect,
}: {
  items: Array<{ id: string; label: string }>;
  activeId?: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onSelect(item.id)}
          className={`rounded border px-2 py-1 text-[11px] font-semibold transition-colors ${
            activeId === item.id
              ? "border-blue-500 bg-blue-600 text-white"
              : "border-gray-700 bg-gray-950 text-gray-300 hover:border-blue-500 hover:text-white"
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function NumberInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="grid gap-1.5 text-sm sm:grid-cols-[minmax(10rem,1fr)_minmax(7rem,auto)] sm:items-center sm:gap-4">
      <span className="min-w-0 text-gray-300">{label}</span>
      <input
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full min-w-0 rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-xs text-white outline-none focus:border-blue-500 sm:w-28"
      />
    </label>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 text-sm">
      <span className="min-w-0 text-gray-300">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-blue-600"
      />
    </label>
  );
}

function ActionButton({
  label,
  icon,
  loading = false,
  danger = false,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  loading?: boolean;
  danger?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className={`inline-flex items-center justify-center gap-2 rounded px-3 py-1.5 text-xs font-semibold text-white transition-colors disabled:cursor-wait disabled:opacity-70 ${
        danger ? "bg-red-600 hover:bg-red-500" : "bg-blue-600 hover:bg-blue-500"
      }`}
    >
      {loading ? <Loader2 size={14} className="animate-spin" /> : icon}
      {label}
    </button>
  );
}

function LockedState({
  icon,
  title,
  body,
  actionLabel,
  onAction,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="flex min-h-72 flex-col items-center justify-center rounded border border-dashed border-gray-800 bg-gray-950 px-6 text-center">
      <div className="mb-3 rounded bg-gray-900 p-3 text-gray-400">{icon}</div>
      <h4 className="mb-2 text-sm font-semibold text-white">{title}</h4>
      <p className="max-w-md text-sm leading-6 text-gray-500">{body}</p>
      {actionLabel && onAction && (
        <button type="button" onClick={onAction} className="mt-4 rounded bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-blue-500">
          {actionLabel}
        </button>
      )}
    </div>
  );
}

function DebugButton({
  loading,
  label,
  onClick,
}: {
  loading: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="flex items-center gap-2 rounded border border-gray-700 bg-gray-950 px-3 py-1.5 text-xs font-semibold text-gray-200 transition-colors hover:border-blue-500 hover:text-white disabled:cursor-wait disabled:opacity-70"
    >
      {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCcw size={14} />}
      {label}
    </button>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded border border-dashed border-gray-800 px-3 py-8 text-center text-xs text-gray-500">
      {text}
    </div>
  );
}

export default SettingsModal;
