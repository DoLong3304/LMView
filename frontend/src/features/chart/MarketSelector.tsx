import React, { useState, useRef, useEffect } from "react";
import { Search, ChevronDown, Star } from "lucide-react";
import { useI18n } from "@/i18n";
import { useSymbolMeta } from "@/hooks/useSymbolMeta";
import { DEFAULT_SYMBOL_ICON } from "@/services/symbolMetaService";

interface MarketSelectorProps {
  symbols: string[];
  selectedSymbol: string;
  onSelect: (symbol: string) => void;
  starredSymbols: string[];
  onToggleStar: (symbol: string) => void;
}

const MarketSelector: React.FC<MarketSelectorProps> = ({
  symbols,
  selectedSymbol,
  onSelect,
  starredSymbols,
  onToggleStar,
}) => {
  const { t } = useI18n();
  const { getMeta } = useSymbolMeta();
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = symbols.filter((s) => {
    const meta = getMeta(s);
    const matchesSearch =
      !searchQuery ||
      s.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (meta?.name &&
        meta.name.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesSearch;
  });

  const selectedMeta = getMeta(selectedSymbol);

  return (
    <div ref={dropdownRef} className="relative w-[148px] flex-shrink-0 sm:w-[164px]">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex h-8 w-full cursor-pointer items-center gap-2 rounded border border-[var(--lm-border-strong)] bg-[var(--lm-bg-tertiary)] px-2.5 text-sm text-[var(--lm-text-primary)] transition-colors hover:border-[var(--lm-blue-border)] hover:bg-[var(--lm-blue-soft)] focus:border-blue-500 focus:outline-none"
      >
        <img
          src={selectedMeta.icon}
          alt={selectedMeta.name}
          className="w-5 h-5 flex-shrink-0 rounded-full"
          onError={(e) => {
            e.currentTarget.src = DEFAULT_SYMBOL_ICON;
          }}
        />
        <span className="min-w-0 truncate font-medium">{selectedSymbol}</span>
        <ChevronDown size={14} className="ml-auto text-[var(--lm-text-secondary)]" />
      </button>

      {isOpen && (
        <div className="lm-menu-surface absolute top-full left-0 mt-1 w-[min(288px,calc(100vw-1rem))] overflow-hidden rounded-lg border shadow-2xl z-[150]">
          {/* Search */}
          <div className="border-b border-[var(--lm-border)] p-2">
            <div className="relative">
              <Search
                size={14}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--lm-text-secondary)]"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("searchSymbol")}
                className="w-full rounded border border-[var(--lm-border-strong)] bg-[var(--lm-bg-tertiary)] px-3 py-1.5 pl-8 text-sm text-[var(--lm-text-primary)] placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                autoFocus
              />
            </div>
          </div>

          {/* Symbol list */}
          <div className="max-h-64 overflow-y-auto">
            {filtered.length === 0 && (
              <div className="px-3 py-4 text-center text-sm text-[var(--lm-text-muted)]">
                {t("noResults")}
              </div>
            )}
            {filtered.map((s) => {
              const m = getMeta(s);
              const isActive = s === selectedSymbol;
              const isStarred = starredSymbols.includes(s);
              return (
                <div
                  key={s}
                  className={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
                    isActive
                      ? "bg-blue-600 bg-opacity-30"
                      : "hover:bg-[var(--lm-blue-soft)]"
                  }`}
                  onClick={() => {
                    onSelect(s);
                    setIsOpen(false);
                    setSearchQuery("");
                  }}
                >
                  <img
                    src={m.icon}
                    alt={m.name}
                    className="w-5 h-5 rounded-full flex-shrink-0"
                    onError={(e) => {
                      e.currentTarget.src = DEFAULT_SYMBOL_ICON;
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-[var(--lm-text-primary)]">{s}</span>
                    {m?.name && (
                      <span className="ml-2 text-xs text-[var(--lm-text-secondary)]">
                        {m.name}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleStar(s);
                    }}
                    className={`rounded p-0.5 transition-colors ${isStarred ? "text-yellow-500" : "text-[var(--lm-text-disabled)] hover:text-[var(--lm-text-secondary)]"}`}
                  >
                    <Star
                      size={14}
                      fill={isStarred ? "currentColor" : "none"}
                    />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default MarketSelector;
