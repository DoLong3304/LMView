import { API_BASE_URL, DATA_SOURCE } from "@/constants/env";
import { getAuthHeaders } from "@/services/authService";
import { createApiError } from "@/utils/errors";
import type { UserResponse } from "@/services/authService";

export interface NotificationPreferences {
  system: boolean;
  alerts: boolean;
  news: boolean;
  ai: boolean;
  sound: boolean;
  desktop: boolean;
  email: boolean;
  position: string;
}

export type ChartThemePreset = "dark" | "light" | "highContrast" | "custom";
export type GridLineStyle = "solid" | "dashed";
export type CrosshairStyle = "standard" | "magnet";
export type LayoutPreference = "compact" | "comfortable";

export interface CandleStyleSettings {
  up_color: string;
  down_color: string;
  wick_visible: boolean;
  border_visible: boolean;
}

export interface GridCrosshairSettings {
  grid_visible: boolean;
  grid_style: GridLineStyle;
  crosshair_style: CrosshairStyle;
}

export interface ScaleSettings {
  price_labels_visible: boolean;
  time_labels_visible: boolean;
  seconds_visible: boolean;
  bar_spacing: number;
}

export interface ChartPreferenceSettings {
  chart_theme_preset: ChartThemePreset;
  candle_style: CandleStyleSettings;
  grid_crosshair: GridCrosshairSettings;
  scale: ScaleSettings;
  favorite_drawing_tools: string[];
  layout_preference: LayoutPreference;
}

export interface CustomizationDefaults {
  theme: ChartThemePreset;
  default_timeframe: string;
  default_chart_type: string;
  default_symbol: string;
  default_exchange: string;
  visible_indicators: string[];
  drawing_defaults: Record<string, unknown>;
}

export interface AiHelperSettings {
  response_style: string;
  risk_reminders: boolean;
  auto_include_chart_context: boolean;
  allow_chart_actions: boolean;
  require_action_confirmation: boolean;
  max_context_candles: number;
  memory_retention_days: number;
}

export interface AlertSettings {
  price_alerts: boolean;
  volume_alerts: boolean;
  indicator_alerts: boolean;
  whale_alerts: boolean;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

export interface UserSettings {
  notification_preferences: NotificationPreferences;
  customization_defaults: CustomizationDefaults;
  ai_settings: AiHelperSettings;
  alert_settings: AlertSettings;
}

export interface UserNotification {
  id: string;
  category: "system" | "alert" | "news" | "ai";
  severity: "info" | "success" | "warning" | "error";
  title: string;
  body?: string | null;
  payload: Record<string, unknown>;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationList {
  notifications: UserNotification[];
  unread_count: number;
}

export interface AdminUsersResponse {
  users: UserResponse[];
  total: number;
  limit: number;
  offset: number;
}

const MOCK_SETTINGS_KEY = "lmview_mock_settings";
const MOCK_NOTIFICATIONS_KEY = "lmview_mock_notifications";

export const DEFAULT_CHART_PREFERENCES: ChartPreferenceSettings = {
  chart_theme_preset: "dark",
  candle_style: {
    up_color: "#22c55e",
    down_color: "#ef4444",
    wick_visible: true,
    border_visible: true,
  },
  grid_crosshair: {
    grid_visible: true,
    grid_style: "solid",
    crosshair_style: "standard",
  },
  scale: {
    price_labels_visible: true,
    time_labels_visible: true,
    seconds_visible: true,
    bar_spacing: 8,
  },
  favorite_drawing_tools: [
    "trendline",
    "horizontalRay",
    "rectangle",
    "fibRetracement",
    "ruler",
  ],
  layout_preference: "comfortable",
};

export const DEFAULT_USER_SETTINGS: UserSettings = {
  notification_preferences: {
    system: true,
    alerts: true,
    news: true,
    ai: true,
    sound: false,
    desktop: false,
    email: false,
    position: "top-right",
  },
  customization_defaults: {
    theme: "dark",
    default_timeframe: "1m",
    default_chart_type: "candles",
    default_symbol: "BTCUSDT",
    default_exchange: "binance",
    visible_indicators: [],
    drawing_defaults: {
      chart_preferences: DEFAULT_CHART_PREFERENCES,
    },
  },
  ai_settings: {
    response_style: "concise",
    risk_reminders: true,
    auto_include_chart_context: true,
    allow_chart_actions: false,
    require_action_confirmation: true,
    max_context_candles: 300,
    memory_retention_days: 30,
  },
  alert_settings: {
    price_alerts: true,
    volume_alerts: true,
    indicator_alerts: true,
    whale_alerts: true,
    quiet_hours_enabled: false,
    quiet_hours_start: "22:00",
    quiet_hours_end: "07:00",
  },
};

async function settingsFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...(options.headers as Record<string, string> | undefined),
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw createApiError("settings", response.status, payload, { endpoint: path });
  }
  return response.json() as Promise<T>;
}

export async function fetchUserSettings(): Promise<UserSettings> {
  if (DATA_SOURCE === "mock") return getMockSettings();
  return settingsFetch<UserSettings>("/settings");
}

export async function saveNotificationPreferences(
  value: NotificationPreferences,
): Promise<UserSettings> {
  if (DATA_SOURCE === "mock") return saveMockSettings({ notification_preferences: value });
  return settingsFetch<UserSettings>("/settings/notifications", {
    method: "PATCH",
    body: JSON.stringify(value),
  });
}

export async function saveCustomizationDefaults(
  value: CustomizationDefaults,
): Promise<UserSettings> {
  if (DATA_SOURCE === "mock") return saveMockSettings({ customization_defaults: value });
  return settingsFetch<UserSettings>("/settings/customization", {
    method: "PATCH",
    body: JSON.stringify(value),
  });
}

export async function saveAiSettings(value: AiHelperSettings): Promise<UserSettings> {
  if (DATA_SOURCE === "mock") return saveMockSettings({ ai_settings: value });
  return settingsFetch<UserSettings>("/settings/ai", {
    method: "PATCH",
    body: JSON.stringify(value),
  });
}

export async function saveAlertSettings(value: AlertSettings): Promise<UserSettings> {
  if (DATA_SOURCE === "mock") return saveMockSettings({ alert_settings: value });
  return settingsFetch<UserSettings>("/settings/alerts", {
    method: "PATCH",
    body: JSON.stringify(value),
  });
}

export async function fetchNotifications(limit = 20): Promise<NotificationList> {
  if (DATA_SOURCE === "mock") return getMockNotifications();
  return settingsFetch<NotificationList>(`/notifications?limit=${limit}`);
}

export async function markNotificationsRead(notificationId?: string): Promise<void> {
  if (DATA_SOURCE === "mock") {
    const payload = getMockNotifications();
    const notifications = payload.notifications.map((item) =>
      !notificationId || item.id === notificationId
        ? { ...item, read_at: item.read_at || new Date().toISOString() }
        : item,
    );
    localStorage.setItem(MOCK_NOTIFICATIONS_KEY, JSON.stringify(notifications));
    return;
  }
  const suffix = notificationId ? `?notification_id=${encodeURIComponent(notificationId)}` : "";
  await settingsFetch(`/notifications/read${suffix}`, { method: "POST" });
}

export async function fetchAdminUsers(query = ""): Promise<AdminUsersResponse> {
  if (DATA_SOURCE === "mock") return getMockAdminUsers(query);
  const suffix = query ? `?query=${encodeURIComponent(query)}` : "";
  return settingsFetch<AdminUsersResponse>(`/admin/users${suffix}`);
}

export async function updateAdminUser(
  userId: string,
  updates: { role?: string; is_active?: boolean },
): Promise<UserResponse> {
  if (DATA_SOURCE === "mock") return updateMockAdminUser(userId, updates);
  return settingsFetch<UserResponse>(`/admin/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function forceAdminPasswordChange(userId: string): Promise<UserResponse> {
  if (DATA_SOURCE === "mock") {
    return updateMockAdminUser(userId, { must_change_password: true });
  }
  return settingsFetch<UserResponse>(
    `/admin/users/${encodeURIComponent(userId)}/force-password-change`,
    { method: "POST" },
  );
}

export async function fetchAppSettings(): Promise<Record<string, unknown>> {
  if (DATA_SOURCE === "mock") {
    return {
      "frontend.show_internal_status": false,
      "frontend.notifications_enabled": true,
      "frontend.chart_action_testing": true,
    };
  }
  const payload = await settingsFetch<{ settings: Record<string, unknown> }>("/admin/app-settings");
  return payload.settings;
}

export function normalizeChartPreferences(
  defaults: CustomizationDefaults,
): ChartPreferenceSettings {
  const stored = defaults.drawing_defaults?.chart_preferences as Partial<ChartPreferenceSettings> | undefined;
  return {
    ...DEFAULT_CHART_PREFERENCES,
    ...stored,
    chart_theme_preset: stored?.chart_theme_preset || defaults.theme || DEFAULT_CHART_PREFERENCES.chart_theme_preset,
    candle_style: {
      ...DEFAULT_CHART_PREFERENCES.candle_style,
      ...stored?.candle_style,
    },
    grid_crosshair: {
      ...DEFAULT_CHART_PREFERENCES.grid_crosshair,
      ...stored?.grid_crosshair,
    },
    scale: {
      ...DEFAULT_CHART_PREFERENCES.scale,
      ...stored?.scale,
    },
    favorite_drawing_tools: Array.isArray(stored?.favorite_drawing_tools)
      ? stored.favorite_drawing_tools
      : DEFAULT_CHART_PREFERENCES.favorite_drawing_tools,
    layout_preference: stored?.layout_preference
      || (defaults.drawing_defaults?.compact_panels === true
        ? "compact"
        : DEFAULT_CHART_PREFERENCES.layout_preference),
  };
}

function getMockSettings(): UserSettings {
  try {
    const stored = localStorage.getItem(MOCK_SETTINGS_KEY);
    return normalizeUserSettings(stored ? JSON.parse(stored) : DEFAULT_USER_SETTINGS);
  } catch {
    return DEFAULT_USER_SETTINGS;
  }
}

function saveMockSettings(patch: Partial<UserSettings>): UserSettings {
  const current = getMockSettings();
  const next = normalizeUserSettings({
    ...current,
    ...patch,
    notification_preferences: {
      ...current.notification_preferences,
      ...patch.notification_preferences,
    },
    customization_defaults: {
      ...current.customization_defaults,
      ...patch.customization_defaults,
      drawing_defaults: {
        ...current.customization_defaults.drawing_defaults,
        ...patch.customization_defaults?.drawing_defaults,
      },
    },
    ai_settings: {
      ...current.ai_settings,
      ...patch.ai_settings,
    },
    alert_settings: {
      ...current.alert_settings,
      ...patch.alert_settings,
    },
  });
  localStorage.setItem(MOCK_SETTINGS_KEY, JSON.stringify(next));
  return next;
}

function normalizeUserSettings(value: Partial<UserSettings>): UserSettings {
  const customization = value.customization_defaults ?? DEFAULT_USER_SETTINGS.customization_defaults;
  const drawingDefaults = customization.drawing_defaults ?? {};
  return {
    ...DEFAULT_USER_SETTINGS,
    ...value,
    notification_preferences: {
      ...DEFAULT_USER_SETTINGS.notification_preferences,
      ...value.notification_preferences,
    },
    customization_defaults: {
      ...DEFAULT_USER_SETTINGS.customization_defaults,
      ...customization,
      drawing_defaults: {
        ...DEFAULT_USER_SETTINGS.customization_defaults.drawing_defaults,
        ...drawingDefaults,
        chart_preferences: normalizeChartPreferences({
          ...DEFAULT_USER_SETTINGS.customization_defaults,
          ...customization,
          drawing_defaults: {
            ...drawingDefaults,
          },
        }),
      },
    },
    ai_settings: {
      ...DEFAULT_USER_SETTINGS.ai_settings,
      ...value.ai_settings,
    },
    alert_settings: {
      ...DEFAULT_USER_SETTINGS.alert_settings,
      ...value.alert_settings,
    },
  };
}

function getMockNotifications(): NotificationList {
  try {
    const stored = localStorage.getItem(MOCK_NOTIFICATIONS_KEY);
    const notifications: UserNotification[] = stored
      ? JSON.parse(stored)
      : [
          {
            id: "mock-system-ready",
            category: "system",
            severity: "info",
            title: "Workspace ready",
            body: "Account settings and notifications are connected.",
            payload: {},
            read_at: null,
            created_at: new Date().toISOString(),
          },
          {
            id: "mock-whale-alert",
            category: "alert",
            severity: "warning",
            title: "Whale alert placeholder",
            body: "Large transfer alerts can be shown here when data is connected.",
            payload: { symbol: "BTCUSDT" },
            read_at: null,
            created_at: new Date().toISOString(),
          },
        ];
    if (!stored) localStorage.setItem(MOCK_NOTIFICATIONS_KEY, JSON.stringify(notifications));
    return {
      notifications,
      unread_count: notifications.filter((item) => !item.read_at).length,
    };
  } catch {
    return { notifications: [], unread_count: 0 };
  }
}

function getMockAdminUsers(query: string): AdminUsersResponse {
  const users = JSON.parse(localStorage.getItem("lmview_mock_users") || "[]") as UserResponse[];
  const needle = query.trim().toLowerCase();
  const filtered = needle
    ? users.filter((user) =>
        `${user.email} ${user.display_name} ${user.username || ""}`.toLowerCase().includes(needle),
      )
    : users;
  return { users: filtered, total: filtered.length, limit: 50, offset: 0 };
}

function updateMockAdminUser(
  userId: string,
  updates: Partial<UserResponse>,
): UserResponse {
  const users = JSON.parse(localStorage.getItem("lmview_mock_users") || "[]") as UserResponse[];
  const index = users.findIndex((user) => user.id === userId);
  if (index < 0) throw new Error("User not found");
  users[index] = { ...users[index], ...updates };
  localStorage.setItem("lmview_mock_users", JSON.stringify(users));
  return users[index];
}
