import { useId, useRef, useState } from "react";

export type EdgeiqMetricKey = "EPI" | "ERI" | "ESI" | "EDI" | "ETI" | "AE" | "POT" | "ROI" | "IV";

export const edgeiqMetricDefinitions: Record<EdgeiqMetricKey, { title: string; body: string }> = {
  EPI: {
    title: "EDGEIQ Performance Index",
    body: "Measures the quality of an individual performance after adjusting for race strength and context. Higher is better.",
  },
  ERI: {
    title: "EDGEIQ Race Index",
    body: "Measures the overall quality of the race. Higher ERI indicates a stronger race.",
  },
  ESI: {
    title: "EDGEIQ Sectional Index",
    body: "Measures sectional performance in lengths against the selected EDGEIQ Standard. Negative is inside standard. Positive is outside standard.",
  },
  EDI: {
    title: "EDGEIQ DNA Index",
    body: "Measures how naturally suited a horse is to today's race using historical performance characteristics.",
  },
  ETI: {
    title: "EDGEIQ Transfer Index",
    body: "Measures how closely a past run lines up with today's race conditions. Higher percentages indicate a stronger reference.",
  },
  AE: {
    title: "Actual / Expected",
    body: "Future LAB metric for measuring realised outcomes against expected outcomes.",
  },
  POT: {
    title: "Profit on Turnover",
    body: "Future LAB metric for measuring return against total turnover.",
  },
  ROI: {
    title: "Return on Investment",
    body: "Future LAB metric for measuring return against outlay.",
  },
  IV: {
    title: "Impact Value",
    body: "Future LAB metric for measuring outcome frequency relative to baseline.",
  },
};

type EdgeiqMetricTooltipProps = {
  label: string;
  title: string;
  body: string;
};

export function EdgeiqMetricTooltip({ label, title, body }: EdgeiqMetricTooltipProps) {
  const tooltipId = useId();
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);

  function showTooltip() {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setPosition({
      left: Math.min(window.innerWidth - 24, Math.max(12, rect.left + rect.width / 2)),
      top: Math.max(12, rect.top - 10),
    });
  }

  function hideTooltip() {
    setPosition(null);
  }

  return (
    <span className="eiq-metric-tooltip" onMouseLeave={hideTooltip}>
      <button
        ref={triggerRef}
        type="button"
        className="eiq-metric-tooltip__trigger"
        aria-label={`${label}: ${title}`}
        aria-describedby={position ? tooltipId : undefined}
        onBlur={hideTooltip}
        onFocus={showTooltip}
        onMouseEnter={showTooltip}
      >
        {label}
      </button>
      <span
        id={tooltipId}
        className={`eiq-metric-tooltip__card${position ? " is-visible" : ""}`}
        role="tooltip"
        style={position ? { left: position.left, top: position.top } : undefined}
      >
        <strong>{title}</strong>
        <span>{body}</span>
      </span>
    </span>
  );
}
