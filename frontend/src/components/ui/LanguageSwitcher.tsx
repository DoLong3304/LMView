import React, { useEffect, useRef, useState } from "react";
import { Globe } from "lucide-react";
import { useI18n } from "@/i18n";
import type { TranslationKey } from "@/i18n/translations";

interface LangOption {
  code: string;
  labelKey: TranslationKey;
  shortLabel: string;
}

const LANGS: LangOption[] = [
  { code: "en", labelKey: "english", shortLabel: "EN" },
  { code: "vi", labelKey: "vietnamese", shortLabel: "VI" },
];

const LanguageSwitcher: React.FC = () => {
  const { lang, switchLang, t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const current = LANGS.find((option) => option.code === lang) || LANGS[0];

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2 py-1.5 rounded text-sm text-gray-300 hover:text-white hover:bg-gray-700 transition-colors"
        title={t("language")}
      >
        <Globe size={16} />
        <span className="hidden sm:inline">{current.shortLabel}</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-[150] overflow-hidden min-w-[140px]">
          {LANGS.map((option) => (
            <button
              key={option.code}
              onClick={() => {
                switchLang(option.code);
                setIsOpen(false);
              }}
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                lang === option.code
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-700"
              }`}
            >
              <span>{option.shortLabel}</span>
              <span>{t(option.labelKey)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default LanguageSwitcher;
