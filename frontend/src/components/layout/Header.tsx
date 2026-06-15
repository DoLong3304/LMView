import React from "react";
import {
  Bell,
  CandlestickChart as CandleIcon,
  Loader2,
  LogOut,
  Moon,
  Newspaper,
  PanelRight,
  Settings,
  Sun,
  UserRound,
  Filter,
} from "lucide-react";
import { getDataSourceLabel, DATA_SOURCE } from "@/constants/env";
import LanguageSwitcher from "@/components/ui/LanguageSwitcher";
import SystemHealthCard from "@/components/ui/SystemHealthCard";
import { useAuth } from "@/features/auth/AuthContext";
import { useI18n } from "@/i18n";
import {
  fetchNotifications,
  fetchUserSettings,
  markNotificationsRead,
  type NotificationPreferences,
  type UserNotification,
} from "@/services/settingsService";

const SHOW_DEVELOPER_TOOLS = false;

type AppView = "charts" | "marketsNews" | "screener";

interface HeaderProps {
  themeMode: "dark" | "light";
  onThemeToggle: () => void;
  isRightPanelOpen: boolean;
  onToggleRightPanel: () => void;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
  onLoginClick: () => void;
  onSettingsClick: () => void;
}

const Header: React.FC<HeaderProps> = ({
  themeMode,
  onThemeToggle,
  isRightPanelOpen,
  onToggleRightPanel,
  activeView,
  onViewChange,
  onLoginClick,
  onSettingsClick,
}) => {
  const { t } = useI18n();
  const { user, loading, isAuthenticated, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = React.useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = React.useState(false);
  const [notifications, setNotifications] = React.useState<UserNotification[]>([]);
  const [unreadCount, setUnreadCount] = React.useState(0);
  const notifiedIdsRef = React.useRef<Set<string>>(new Set());
  const notificationPreferencesRef = React.useRef<NotificationPreferences | null>(null);

  const loadNotifications = React.useCallback(async () => {
    if (!isAuthenticated) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }
    try {
      const payload = await fetchNotifications(10);
      setNotifications(payload.notifications);
      setUnreadCount(payload.unread_count);
      const prefs = notificationPreferencesRef.current;
      if (prefs?.desktop && typeof Notification !== "undefined" && Notification.permission === "granted") {
        for (const item of payload.notifications) {
          if (item.read_at || notifiedIdsRef.current.has(item.id)) continue;
          notifiedIdsRef.current.add(item.id);
          new Notification(item.title, { body: item.body || undefined });
        }
      }
    } catch {
      setNotifications([]);
      setUnreadCount(0);
    }
  }, [isAuthenticated]);

  React.useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  React.useEffect(() => {
    if (!isAuthenticated) return;
    fetchUserSettings()
      .then((settings) => {
        notificationPreferencesRef.current = settings.notification_preferences;
      })
      .catch(() => {
        notificationPreferencesRef.current = null;
      });
  }, [isAuthenticated]);

  React.useEffect(() => {
    if (!isAuthenticated) return;
    const intervalId = window.setInterval(() => void loadNotifications(), 30_000);
    return () => window.clearInterval(intervalId);
  }, [isAuthenticated, loadNotifications]);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <>
      <header className="bg-gray-900 border-b border-gray-700 px-2 sm:px-3 py-2 flex flex-wrap lg:flex-nowrap items-center gap-2 lg:gap-3">
        <div className="flex items-center gap-2 min-w-0 flex-shrink-0">
          <span className="text-lg sm:text-xl font-bold text-blue-500 leading-none">LMView</span>
          <span className="hidden xl:block max-w-72 truncate text-xs text-gray-500">
            {t("appTagline")}
          </span>
          {SHOW_DEVELOPER_TOOLS && <SystemHealthCard />}
        </div>

        <div className="hidden lg:block w-px h-6 bg-gray-700" />

        <div className="flex min-w-0 basis-full flex-wrap items-center justify-start gap-1.5 sm:ml-auto sm:basis-auto sm:justify-end sm:gap-2">
          <div className="flex items-center gap-1 rounded border border-gray-700 bg-gray-800 p-0.5">
            <button
              onClick={() => onViewChange("charts")}
              className={`flex items-center gap-1 rounded px-2 py-1 text-xs font-medium transition-colors ${
                activeView === "charts"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:bg-gray-700 hover:text-white"
              }`}
              title={t("charts")}
            >
              <CandleIcon size={14} />
              <span className="hidden sm:inline">{t("charts")}</span>
            </button>
            <button
              onClick={() => onViewChange("marketsNews")}
              className={`flex items-center gap-1 rounded px-2 py-1 text-xs font-medium transition-colors ${
                activeView === "marketsNews"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:bg-gray-700 hover:text-white"
              }`}
              title={t("marketsAndNews")}
            >
              <Newspaper size={14} />
              <span className="hidden sm:inline">{t("marketsAndNews")}</span>
            </button>
            <button
              onClick={() => onViewChange("screener")}
              className={`flex items-center gap-1 rounded px-2 py-1 text-xs font-medium transition-colors ${
                activeView === "screener"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:bg-gray-700 hover:text-white"
              }`}
              title={t("screener")}
            >
              <Filter size={14} />
              <span className="hidden sm:inline">{t("screener")}</span>
            </button>
          </div>
          {SHOW_DEVELOPER_TOOLS && (
            <div
              className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                DATA_SOURCE === "mock"
                  ? "bg-amber-500/20 text-amber-500 border border-amber-500/30"
                  : "bg-emerald-500/20 text-emerald-500 border border-emerald-500/30"
              }`}
              title={t("dataSource")}
            >
              {getDataSourceLabel()}
            </div>
          )}
          <button
            onClick={onThemeToggle}
            className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-gray-800 transition-colors"
            title={themeMode === "dark" ? t("switchToLightMode") : t("switchToDarkMode")}
          >
            {themeMode === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
          {activeView === "charts" && (
            <button
              onClick={onToggleRightPanel}
              className={`p-1.5 rounded transition-colors ${
                isRightPanelOpen
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
              title={t("toggleOverviewPanel")}
            >
              <PanelRight className="w-5 h-5" />
            </button>
          )}
          <LanguageSwitcher />
          {isAuthenticated && (
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  const prefs = notificationPreferencesRef.current;
                  if (
                    prefs?.desktop &&
                    typeof Notification !== "undefined" &&
                    Notification.permission === "default"
                  ) {
                    void Notification.requestPermission();
                  }
                  setIsNotificationsOpen((open) => !open);
                  void loadNotifications();
                }}
                className="relative rounded p-1.5 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
                title={t("notifications")}
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute -right-0.5 -top-0.5 min-w-4 rounded-full bg-red-600 px-1 text-[10px] font-bold leading-4 text-white">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>
              {isNotificationsOpen && (
                <div className="absolute right-0 top-full z-[500] mt-2 w-[calc(100vw-1rem)] max-w-80 overflow-hidden rounded border border-gray-700 bg-gray-900 shadow-2xl">
                  <div className="flex items-center justify-between border-b border-gray-800 px-3 py-2">
                    <span className="text-xs font-semibold text-white">{t("notifications")}</span>
                    <button
                      type="button"
                      onClick={async () => {
                        await markNotificationsRead();
                        await loadNotifications();
                      }}
                      className="text-[11px] font-medium text-blue-300 hover:text-blue-200"
                    >
                      {t("markAllRead")}
                    </button>
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <div className="px-3 py-8 text-center text-xs text-gray-500">
                        {t("noNotifications")}
                      </div>
                    ) : (
                      notifications.map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          onClick={async () => {
                            await markNotificationsRead(item.id);
                            await loadNotifications();
                          }}
                          className={`block w-full border-b border-gray-800 px-3 py-2 text-left last:border-b-0 hover:bg-gray-800 ${
                            item.read_at ? "opacity-70" : ""
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="truncate text-xs font-semibold text-white">{item.title}</span>
                            <span className="rounded border border-gray-700 px-1.5 py-0.5 text-[10px] uppercase text-gray-400">
                              {item.category}
                            </span>
                          </div>
                          {item.body && <p className="mt-1 line-clamp-2 text-xs leading-5 text-gray-400">{item.body}</p>}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
          <button
            type="button"
            onClick={onSettingsClick}
            className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-gray-800 transition-colors"
            title={t("settings")}
          >
            <Settings className="w-5 h-5" />
          </button>
          {isAuthenticated && user ? (
            <div className="flex min-w-0 max-w-[9.5rem] items-center gap-1 rounded border border-gray-700 bg-gray-800 px-1 py-1 sm:max-w-[13rem]">
              <div
                className="flex min-w-0 items-center gap-1.5 px-1 text-xs font-medium text-gray-300"
                title={user.email}
              >
                <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-blue-500/30 bg-blue-500/15 text-[10px] font-bold text-blue-100">
                  {getHeaderUserInitials(user.display_name || user.email)}
                </span>
                <span className="hidden min-w-0 max-w-24 truncate md:inline lg:max-w-32">
                  {user.display_name || user.email}
                </span>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white disabled:cursor-wait disabled:opacity-60"
                title={t("logout")}
                aria-label={t("logout")}
              >
                {isLoggingOut ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <LogOut className="h-4 w-4" />
                )}
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={onLoginClick}
              disabled={loading}
              className="flex items-center gap-1.5 rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-gray-700 hover:text-white disabled:cursor-wait disabled:opacity-60"
              title={t("login")}
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <UserRound className="h-4 w-4" />
              )}
              <span className="hidden md:inline">{t("login")}</span>
            </button>
          )}
        </div>
      </header>
    </>
  );
};

function getHeaderUserInitials(value: string): string {
  const words = value
    .replace(/@.*/, "")
    .split(/\s|\.|_/)
    .filter(Boolean);
  const initials = words.length > 1
    ? `${words[0][0]}${words[1][0]}`
    : value.slice(0, 2);
  return initials.toUpperCase() || "LM";
}

export default Header;
