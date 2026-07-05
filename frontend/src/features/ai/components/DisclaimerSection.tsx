/**
 * DisclaimerSection — collapsible disclaimer dropdown below AI responses.
 *
 * Renders the general trading disclaimer + any response-specific caveats
 * in a compact expandable box.
 */
import React, { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, Shield } from "lucide-react";

interface DisclaimerSectionProps {
  /** Response-specific caveats from data_caveats */
  caveats?: string[] | null;
  /** Whether this is an Interact mode response */
  isInteract?: boolean;
}

const GENERAL_DISCLAIMER =
  "This analysis is for educational purposes only and does not constitute " +
  "financial advice. Cryptocurrency trading carries significant risk. " +
  "Always do your own research before making any trading decisions.";

const INTERACT_DISCLAIMER =
  "Chart actions proposed in Interact mode are suggestions only. " +
  "Review each step before approval. Past analysis patterns do not guarantee future results.";

const DisclaimerSection: React.FC<DisclaimerSectionProps> = ({
  caveats,
  isInteract,
}) => {
  const [open, setOpen] = useState(false);

  const hasSpecificCaveats = Array.isArray(caveats) && caveats.length > 0;
  if (!hasSpecificCaveats && !isInteract) return null;

  return (
    <div className="mt-2 rounded border border-amber-500/15 bg-amber-500/[0.03]">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-2 py-1.5 text-[10px] font-medium text-amber-400/80 hover:text-amber-300"
      >
        <span className="flex items-center gap-1.5">
          <Shield size={11} />
          Disclaimer & Risks
        </span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {open && (
        <div className="space-y-1.5 border-t border-amber-500/10 px-2.5 py-2 text-[10px] leading-relaxed text-gray-400">
          <p>{GENERAL_DISCLAIMER}</p>
          {isInteract && <p className="text-amber-300/70">{INTERACT_DISCLAIMER}</p>}
          {hasSpecificCaveats && (
            <div className="pt-1">
              <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-300/60">
                Notes
              </p>
              {caveats!.map((c, i) => (
                <div key={i} className="flex items-start gap-1 text-amber-200/60">
                  <AlertTriangle size={9} className="mt-0.5 flex-shrink-0" />
                  <span>{c}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export { DisclaimerSection };
