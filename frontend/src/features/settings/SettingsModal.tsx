import React, { useEffect, useMemo, useState } from "react";
import {
  Bell,
  Bot,
  Bug,
  Info,
  KeyRound,
  Loader2,
  Lock,
  RefreshCcw,
  Save,
  SlidersHorizontal,
  Trash2,
  UserRound,
  Users,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { TIMEFRAMES } from "@/constants/timeframes";
import { useAuth } from "@/features/auth/AuthContext";
import {
  deleteLocalAiSession,
  loadLocalAiSessions,
} from "@/features/ai/localAiSessions";
import { aiHealth, aiValidateActions } from "@/services/aiService";
import { fetchHealthStatus } from "@/services/healthService";
import {
  DEFAULT_USER_SETTINGS,
  fetchAdminUsers,
  fetchAppSettings,
  fetchUserSettings,
  forceAdminPasswordChange,
  saveAiSettings,
  saveAlertSettings,
  saveCustomizationDefaults,
  saveNotificationPreferences,
  updateAdminUser,
  type AdminUsersResponse,
  type UserSettings,
} from "@/services/settingsService";
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

const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  initialTab,
  onClose,
  onLoginClick,
}) => {
  const { t } = useI18n();
  const {
    user,
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
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [debugLoading, setDebugLoading] = useState<string | null>(null);
  const [debugResult, setDebugResult] = useState("");
  const [chartActionJson, setChartActionJson] = useState(DEFAULT_ACTION_TEST);
  const [adminQuery, setAdminQuery] = useState("");
  const [adminUsers, setAdminUsers] = useState<AdminUsersResponse>({
    users: [],
    total: 0,
    limit: 50,
    offset: 0,
  });
  const [appSettings, setAppSettings] = useState<Record<string, unknown>>({});
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

  useEffect(() => {
    if (!isOpen) return;
    const adminOnly = initialTab === "adminAccounts" || initialTab === "debug";
    setActiveTab(!isAdmin && adminOnly ? "account" : initialTab);
    setStatus("");
  }, [initialTab, isAdmin, isOpen]);

  useEffect(() => {
    if (!isOpen || !user) {
      setSessions([]);
      return;
    }
    setProfileDraft({
      display_name: user.display_name || "",
      username: user.username || "",
      avatar_url: user.avatar_url || "",
      date_of_birth: user.date_of_birth || "",
      bio: user.bio || "",
      timezone: user.timezone || "",
    });
    setSessions(loadLocalAiSessions(user.id));
    fetchUserSettings()
      .then(setSettings)
      .catch((error) => setStatus(error instanceof Error ? error.message : "Settings failed"));
  }, [isOpen, user]);

  useEffect(() => {
    if (!isOpen || !isAdmin || activeTab !== "adminAccounts") return;
    fetchAdminUsers(adminQuery)
      .then(setAdminUsers)
      .catch((error) => setStatus(error instanceof Error ? error.message : "Admin users failed"));
  }, [activeTab, adminQuery, isAdmin, isOpen]);

  useEffect(() => {
    if (!isOpen || !isAdmin || activeTab !== "debug") return;
    fetchAppSettings()
      .then(setAppSettings)
      .catch(() => setAppSettings({}));
  }, [activeTab, isAdmin, isOpen]);

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
    setStatus(result.success ? t("profileSaved") : result.error || t("error"));
  };

  const submitPassword = async () => {
    if (passwordDraft.next !== passwordDraft.confirm) {
      setStatus(t("passwordsMismatch"));
      return;
    }
    setSaving(true);
    const result = await changePassword(passwordDraft.current, passwordDraft.next);
    setSaving(false);
    if (result.success) {
      setPasswordDraft({ current: "", next: "", confirm: "" });
      setStatus(t("passwordChanged"));
    } else {
      setStatus(result.error || t("error"));
    }
  };

  const submitDeleteAccount = async () => {
    setSaving(true);
    const result = await deleteAccount(deleteConfirmation);
    setSaving(false);
    setStatus(result.success ? t("accountDeleted") : result.error || t("error"));
  };

  const saveSettingsPatch = async (next: Promise<UserSettings>) => {
    setSaving(true);
    try {
      const updated = await next;
      setSettings(updated);
      setStatus(t("settingsSaved"));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("error"));
    } finally {
      setSaving(false);
    }
  };

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

  const runChartActionValidation = async () => {
    setDebugLoading("chartAction");
    try {
      const parsed = JSON.parse(chartActionJson);
      const actions = Array.isArray(parsed) ? parsed : [parsed];
      const result = await aiValidateActions(actions);
      setDebugResult(stringifyDebug(result));
    } catch (error) {
      setDebugResult(error instanceof Error ? error.message : "Chart action validation failed");
    } finally {
      setDebugLoading(null);
    }
  };

  const updateAdminUsers = async (nextQuery = adminQuery) => {
    setAdminUsers(await fetchAdminUsers(nextQuery));
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
    <div className="fixed inset-0 z-[600] flex items-center justify-center bg-black/60 px-3 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="flex h-[min(820px,92vh)] w-full max-w-5xl overflow-hidden rounded border border-gray-700 bg-gray-900 text-gray-100 shadow-2xl"
      >
        <aside className="w-52 flex-shrink-0 border-r border-gray-800 bg-gray-950">
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
              {status && <p className="mt-0.5 text-xs text-blue-300">{status}</p>}
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
                <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                  <Panel title={t("profile")}>
                    <TextInput label={t("email")} value={user.email} disabled />
                    <TextInput
                      label={t("name")}
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
                    <label className="block text-xs text-gray-400">
                      {t("bio")}
                      <textarea
                        value={profileDraft.bio}
                        onChange={(event) => setProfileDraft((draft) => ({ ...draft, bio: event.target.value }))}
                        className="mt-1 min-h-20 w-full rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-sm text-white outline-none focus:border-blue-500"
                      />
                    </label>
                    <ActionButton label={t("saveChanges")} icon={<Save size={14} />} loading={saving} onClick={saveProfile} />
                  </Panel>

                  <div className="space-y-4">
                    <Panel title={t("accountStatus")}>
                      <InfoRow label={t("role")} value={user.role} />
                      <InfoRow label={t("status")} value={user.is_active ? t("active") : t("inactive")} />
                      <InfoRow label={t("passwordChangeRequired")} value={user.must_change_password ? t("yes") : t("no")} />
                    </Panel>
                    <Panel title={t("changePassword")}>
                      <PasswordInput label={t("currentPassword")} value={passwordDraft.current} onChange={(value) => setPasswordDraft((draft) => ({ ...draft, current: value }))} />
                      <PasswordInput label={t("newPassword")} value={passwordDraft.next} onChange={(value) => setPasswordDraft((draft) => ({ ...draft, next: value }))} />
                      <PasswordInput label={t("confirmPassword")} value={passwordDraft.confirm} onChange={(value) => setPasswordDraft((draft) => ({ ...draft, confirm: value }))} />
                      <ActionButton label={t("updatePassword")} icon={<KeyRound size={14} />} loading={saving} onClick={submitPassword} />
                    </Panel>
                    <Panel title={t("dangerZone")}>
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
                <Panel title={t("savedDefaults")}>
                  <SelectRow label={t("theme")} value={settings.customization_defaults.theme} options={["dark", "light"]} onChange={(value) => setSettings((draft) => ({ ...draft, customization_defaults: { ...draft.customization_defaults, theme: value as "dark" | "light" } }))} />
                  <SelectRow label={t("defaultTimeframe")} value={settings.customization_defaults.default_timeframe} options={Object.keys(TIMEFRAMES)} onChange={(value) => setSettings((draft) => ({ ...draft, customization_defaults: { ...draft.customization_defaults, default_timeframe: value } }))} />
                  <SelectRow label={t("defaultChartType")} value={settings.customization_defaults.default_chart_type} options={CHART_TYPES} onChange={(value) => setSettings((draft) => ({ ...draft, customization_defaults: { ...draft.customization_defaults, default_chart_type: value } }))} />
                  <TextInput label={t("defaultSymbol")} value={settings.customization_defaults.default_symbol} onChange={(value) => setSettings((draft) => ({ ...draft, customization_defaults: { ...draft.customization_defaults, default_symbol: value.toUpperCase() } }))} />
                  <p className="text-xs leading-5 text-gray-500">{t("savedDefaultsHint")}</p>
                  <ActionButton label={t("saveChanges")} icon={<Save size={14} />} loading={saving} onClick={() => saveSettingsPatch(saveCustomizationDefaults(settings.customization_defaults))} />
                </Panel>
              ) : loginRequired
            )}

            {activeTab === "aiHelper" && (
              isAuthenticated ? (
                <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
                  <Panel title={t("aiAgentSettings")}>
                    <SelectRow label={t("aiResponseStyle")} value={settings.ai_settings.response_style} options={["concise", "balanced", "detailed"]} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, response_style: value } }))} />
                    <Toggle label={t("riskReminders")} checked={settings.ai_settings.risk_reminders} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, risk_reminders: value } }))} />
                    <Toggle label={t("includeChartContext")} checked={settings.ai_settings.auto_include_chart_context} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, auto_include_chart_context: value } }))} />
                    <Toggle label={t("allowChartActions")} checked={settings.ai_settings.allow_chart_actions} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, allow_chart_actions: value } }))} />
                    <Toggle label={t("actionConfirmation")} checked={settings.ai_settings.require_action_confirmation} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, require_action_confirmation: value } }))} />
                    <NumberInput label={t("maxContextCandles")} value={settings.ai_settings.max_context_candles} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, max_context_candles: value } }))} />
                    <NumberInput label={t("memoryRetentionDays")} value={settings.ai_settings.memory_retention_days} onChange={(value) => setSettings((draft) => ({ ...draft, ai_settings: { ...draft.ai_settings, memory_retention_days: value } }))} />
                    <ActionButton label={t("saveChanges")} icon={<Save size={14} />} loading={saving} onClick={() => saveSettingsPatch(saveAiSettings(settings.ai_settings))} />
                  </Panel>
                  <Panel title={t("savedAiSessions")}>
                    {sessions.length > 0 ? sessions.map((session) => (
                      <div key={session.id} className="flex items-center gap-3 border-b border-gray-800 py-2 last:border-b-0">
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-xs font-semibold text-white">{session.title}</div>
                          <div className="text-[11px] text-gray-500">{session.messages.length} {t("messages")}</div>
                        </div>
                        <button type="button" onClick={() => handleDeleteSession(session.id)} className="rounded p-1.5 text-gray-500 hover:bg-red-500/10 hover:text-red-300" title={t("deleteSession")}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    )) : (
                      <EmptyState text={t("noSavedAiSessions")} />
                    )}
                  </Panel>
                </div>
              ) : loginRequired
            )}

            {activeTab === "about" && (
              <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
                <section className="rounded border border-blue-500/30 bg-blue-500/10 p-5">
                  <div className="mb-3 flex h-10 w-10 items-center justify-center rounded bg-blue-600 text-white">
                    <Info size={20} />
                  </div>
                  <h4 className="text-lg font-semibold text-white">LMView</h4>
                  <p className="mt-2 text-sm leading-6 text-gray-300">{t("aboutLmviewBody")}</p>
                </section>
                <Panel title={t("aboutCapabilities")}>
                  <InfoRow label={t("charts")} value={t("technicalIndicators")} />
                  <InfoRow label={t("marketNews")} value={t("latestNews")} />
                  <InfoRow label={t("settings")} value={t("profile")} />
                  <InfoRow label={t("aiHelper")} value={t("aiAgentSettings")} />
                </Panel>
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
                <div className="mb-3 flex gap-2">
                  <input
                    value={adminQuery}
                    onChange={(event) => setAdminQuery(event.target.value)}
                    placeholder={t("searchUsers")}
                    className="min-w-0 flex-1 rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-sm text-white outline-none focus:border-blue-500"
                  />
                  <ActionButton label={t("refresh")} icon={<RefreshCcw size={14} />} onClick={() => updateAdminUsers()} />
                </div>
                <div className="overflow-hidden rounded border border-gray-800">
                  {adminUsers.users.length === 0 ? <EmptyState text={t("noUsers")} /> : adminUsers.users.map((item) => (
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
                      <div className="flex flex-wrap items-center gap-1.5">
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
    <section className="rounded border border-gray-800 bg-gray-850">
      <div className="border-b border-gray-800 px-3 py-2 text-xs font-semibold uppercase text-gray-400">
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

function SelectRow({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-3 text-sm">
      <span className="text-gray-300">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-xs text-white outline-none focus:border-blue-500"
      >
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </label>
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
    <label className="flex items-center justify-between gap-3 text-sm">
      <span className="text-gray-300">{label}</span>
      <input
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-28 rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-xs text-white outline-none focus:border-blue-500"
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
    <label className="flex items-center justify-between gap-3 text-sm">
      <span className="text-gray-300">{label}</span>
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
      className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-xs font-semibold text-white transition-colors disabled:cursor-wait disabled:opacity-70 ${
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
