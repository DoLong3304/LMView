import React from "react";
import {
  CandlestickChart as CandleIcon,
  Moon,
  Newspaper,
  PanelRight,
  Settings,
  Sun,
  UserRound,
} from "lucide-react";
import { getDataSourceLabel, DATA_SOURCE } from "@/constants/env";
import LanguageSwitcher from "@/components/ui/LanguageSwitcher";
import SystemHealthCard from "@/components/ui/SystemHealthCard";
import { useI18n } from "@/i18n";

const SHOW_DEVELOPER_TOOLS = false;

type AppView = "charts" | "marketsNews";

interface HeaderProps {
  themeMode: "dark" | "light";
  onThemeToggle: () => void;
  isRightPanelOpen: boolean;
  onToggleRightPanel: () => void;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
}

const Header: React.FC<HeaderProps> = ({
  themeMode,
  onThemeToggle,
  isRightPanelOpen,
  onToggleRightPanel,
  activeView,
  onViewChange,
}) => {
  const { t } = useI18n();

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

        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
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
          <button
            type="button"
            className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-gray-800 transition-colors"
            title={t("settings")}
          >
            <Settings className="w-5 h-5" />
          </button>
          <button
            type="button"
            className="flex items-center gap-1.5 rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-gray-700 hover:text-white"
            title={t("login")}
          >
            <UserRound className="w-4 h-4" />
            <span className="hidden md:inline">{t("login")}</span>
          </button>
        </div>
      </header>
    </>
  );
};

export default Header;
