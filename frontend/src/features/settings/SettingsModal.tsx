import React, { useEffect, useMemo, useState } from "react";
import {
  Bot,
  Bug,
  Info,
  Loader2,
  Lock,
  RefreshCcw,
  Shield,
  SlidersHorizontal,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { DATA_SOURCE, getDataSourceLabel } from "@/constants/env";
import { TIMEFRAMES } from "@/constants/timeframes";
import { useAuth } from "@/features/auth/AuthContext";
import {
  deleteLocalAiSession,
  loadLocalAiSessions,
} from "@/features/ai/localAiSessions";
import { aiHealth } from "@/services/aiService";
import { fetchHealthStatus } from "@/services/healthService";
import { useI18n } from "@/i18n";
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

const CHART_TYPES: ChartType[] = ["candles", "bars", "line", "area"];

function stringifyDebug(data: unknown): string {
  return JSON.stringify(data, null, 2);
}

const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  initialTab,
  themeMode,
  timeframe,
  chartType,
  onClose,
  onLoginClick,
  onThemeChange,
  onTimeframeChange,
  onChartTypeChange,
}) => {
  const { t } = useI18n();
  const { user, isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [sessions, setSessions] = useState<LocalAiHelpSession[]>([]);
  const [debugLoading, setDebugLoading] = useState<string | null>(null);
  const [debugResult, setDebugResult] = useState<string>("");

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    if (isOpen) setActiveTab(initialTab);
  }, [initialTab, isOpen]);

  useEffect(() => {
    if (!isOpen || !user?.id) {
      setSessions([]);
      return;
    }
    setSessions(loadLocalAiSessions(user.id));
  }, [isOpen, user?.id]);

  const tabs = useMemo(
    () => [
      { id: "account" as const, label: t("settingsAccount"), icon: UserRound, locked: !isAuthenticated },
      { id: "customization" as const, label: t("settingsCustomization"), icon: SlidersHorizontal, locked: !isAuthenticated },
      { id: "aiHelper" as const, label: t("settingsAiHelper"), icon: Bot, locked: !isAuthenticated },
      { id: "about" as const, label: t("settingsAbout"), icon: Info, locked: false },
      { id: "debug" as const, label: t("settingsDebug"), icon: Bug, locked: !isAdmin },
    ],
    [isAdmin, isAuthenticated, t],
  );

  const handleDeleteSession = (sessionId: string) => {
    if (!user?.id) return;
    deleteLocalAiSession(user.id, sessionId);
    setSessions(loadLocalAiSessions(user.id));
  };

  const runHealthCheck = async () => {
    setDebugLoading("health");
    try {
      const data: HealthData = await fetchHealthStatus();
      setDebugResult(stringifyDebug(data));
    } catch (error) {
      setDebugResult(error instanceof Error ? error.message : "Health check failed");
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
      setDebugResult(error instanceof Error ? error.message : "AI health check failed");
    } finally {
      setDebugLoading(null);
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

  const adminRequired = (
    <LockedState
      icon={<Shield size={22} />}
      title={t("adminRequiredTitle")}
      body={t("adminRequiredSettings")}
    />
  );

  return (
    <div className="fixed inset-0 z-[600] flex items-center justify-center bg-black/60 px-3 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="flex h-[min(760px,90vh)] w-full max-w-4xl overflow-hidden rounded border border-gray-700 bg-gray-900 text-gray-100 shadow-2xl"
      >
        <aside className="w-48 flex-shrink-0 border-r border-gray-800 bg-gray-950">
          <div className="flex items-center justify-between border-b border-gray-800 px-3 py-3">
            <h2 id="settings-title" className="text-sm font-semibold text-white">
              {t("settings")}
            </h2>
          </div>
          <nav className="space-y-1 p-2">
            {tabs.map(({ id, label, icon: Icon, locked }) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveTab(id)}
                className={`flex w-full items-center gap-2 rounded px-2 py-2 text-left text-xs font-semibold transition-colors ${
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
          <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
            <div>
              <h3 className="text-sm font-semibold text-white">
                {tabs.find((tab) => tab.id === activeTab)?.label}
              </h3>
              <p className="text-xs text-gray-500">
                {t("dataSource")}: {getDataSourceLabel()}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1.5 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
              title={t("close")}
            >
              <X size={18} />
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            {activeTab === "account" && (
              isAuthenticated && user ? (
                <div className="space-y-4">
                  <Panel title={t("userInfo")}>
                    <InfoRow label={t("email")} value={user.email} />
                    <InfoRow label={t("name")} value={user.display_name || "-"} />
                    <InfoRow label={t("role")} value={user.role} />
                    <InfoRow label={t("status")} value={user.is_active ? t("active") : t("inactive")} />
                  </Panel>
                  <Panel title={t("changePassword")}>
                    <UnavailableRow label={t("changePassword")} detail={t("unavailableNoBackendRoute")} />
                  </Panel>
                </div>
              ) : loginRequired
            )}

            {activeTab === "customization" && (
              isAuthenticated ? (
                <div className="space-y-4">
                  <Panel title={t("realControls")}>
                    <ControlRow label={t("theme")}>
                      <select
                        value={themeMode}
                        onChange={(event) => onThemeChange(event.target.value as "dark" | "light")}
                        className="rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-xs text-white outline-none focus:border-blue-500"
                      >
                        <option value="dark">{t("dark")}</option>
                        <option value="light">{t("light")}</option>
                      </select>
                    </ControlRow>
                    <ControlRow label={t("defaultTimeframe")}>
                      <select
                        value={timeframe}
                        onChange={(event) => onTimeframeChange(event.target.value as TimeframeKey)}
                        className="rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-xs text-white outline-none focus:border-blue-500"
                      >
                        {Object.keys(TIMEFRAMES).map((tf) => (
                          <option key={tf} value={tf}>{tf.toUpperCase()}</option>
                        ))}
                      </select>
                    </ControlRow>
                    <ControlRow label={t("defaultChartType")}>
                      <select
                        value={chartType}
                        onChange={(event) => onChartTypeChange(event.target.value as ChartType)}
                        className="rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-xs text-white outline-none focus:border-blue-500"
                      >
                        {CHART_TYPES.map((type) => (
                          <option key={type} value={type}>{t(type)}</option>
                        ))}
                      </select>
                    </ControlRow>
                  </Panel>
                  <Panel title={t("unavailableControls")}>
                    <UnavailableRow label={t("visibleIndicatorSet")} detail={t("unavailableNeedsChartWiring")} />
                    <UnavailableRow label={t("drawingToolArrangement")} detail={t("unavailableNeedsChartWiring")} />
                    <UnavailableRow label={t("indicatorTemplates")} detail={t("unavailableNeedsChartWiring")} />
                  </Panel>
                </div>
              ) : loginRequired
            )}

            {activeTab === "aiHelper" && (
              isAuthenticated ? (
                <div className="space-y-4">
                  <Panel title={t("aiHelperAvailability")}>
                    <InfoRow label={t("askMode")} value={DATA_SOURCE === "mock" ? t("mockMode") : t("lmviewHelpMode")} />
                    <InfoRow label={t("interactMode")} value={t("aiInteractUnavailable")} />
                    <InfoRow label={t("marketAnalysisMode")} value={t("aiMarketAnalysisUnavailable")} />
                  </Panel>
                  <Panel title={t("savedAiSessions")}>
                    {sessions.length > 0 ? (
                      <div className="divide-y divide-gray-800">
                        {sessions.map((session) => (
                          <div key={session.id} className="flex items-center gap-3 py-2">
                            <div className="min-w-0 flex-1">
                              <div className="truncate text-xs font-semibold text-white">{session.title}</div>
                              <div className="text-[11px] text-gray-500">
                                {session.messages.length} {t("messages")} - {new Date(session.updated_at).toLocaleString()}
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleDeleteSession(session.id)}
                              className="rounded p-1.5 text-gray-500 transition-colors hover:bg-red-500/10 hover:text-red-300"
                              title={t("deleteSession")}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded border border-dashed border-gray-800 px-3 py-6 text-center text-xs text-gray-500">
                        {t("noSavedAiSessions")}
                      </div>
                    )}
                  </Panel>
                </div>
              ) : loginRequired
            )}

            {activeTab === "about" && (
              <div className="space-y-4">
                <Panel title={t("aboutLmview")}>
                  <p className="text-sm leading-6 text-gray-300">{t("aboutLmviewBody")}</p>
                </Panel>
                <Panel title={t("featurePolicy")}>
                  <p className="text-sm leading-6 text-gray-300">{t("featurePolicyBody")}</p>
                </Panel>
              </div>
            )}

            {activeTab === "debug" && (
              isAdmin ? (
                <div className="space-y-4">
                  <Panel title={t("systemHealthInfo")}>
                    <div className="flex flex-wrap gap-2">
                      <DebugButton
                        loading={debugLoading === "health"}
                        label={t("runHealthCheck")}
                        onClick={runHealthCheck}
                      />
                      <DebugButton
                        loading={debugLoading === "ai"}
                        label={t("runAiHealthCheck")}
                        onClick={runAiHealthCheck}
                      />
                    </div>
                  </Panel>
                  <pre className="min-h-48 overflow-auto rounded border border-gray-800 bg-gray-950 p-3 text-xs leading-5 text-gray-300">
                    {debugResult || t("debugNoResult")}
                  </pre>
                </div>
              ) : adminRequired
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded border border-gray-800 bg-gray-850">
      <div className="border-b border-gray-800 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
        {title}
      </div>
      <div className="space-y-3 p-3">{children}</div>
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="min-w-0 truncate text-right font-medium text-gray-200">{value}</span>
    </div>
  );
}

function ControlRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex items-center justify-between gap-3 text-sm">
      <span className="text-gray-300">{label}</span>
      {children}
    </label>
  );
}

function UnavailableRow({ label, detail }: { label: string; detail: string }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center justify-between gap-3 rounded border border-gray-800 bg-gray-950 px-3 py-2">
      <div className="min-w-0">
        <div className="text-sm font-medium text-gray-400">{label}</div>
        <div className="text-[11px] text-gray-600">{detail}</div>
      </div>
      <span className="rounded border border-amber-500/25 bg-amber-500/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
        {t("unavailable")}
      </span>
    </div>
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
        <button
          type="button"
          onClick={onAction}
          className="mt-4 rounded bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-blue-500"
        >
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

export default SettingsModal;
