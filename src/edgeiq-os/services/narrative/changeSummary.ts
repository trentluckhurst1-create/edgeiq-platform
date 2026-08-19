export type ChangeSummaryItem = {
  label: string;
  value: string;
  detail: string;
};

export type ChangeSummaryInput = {
  referenceRunner?: string;
  previousMarket?: string;
  currentMarket?: string;
  confidenceChange?: string;
  trackCondition?: string;
  railPosition?: string;
  weatherState?: string;
};

export function buildChangeSummary(input: ChangeSummaryInput): ChangeSummaryItem[] {
  return [
    {
      label: input.referenceRunner || "Reference",
      value: input.previousMarket && input.currentMarket ? "Market moved" : "No material move",
      detail: input.previousMarket && input.currentMarket ? `${input.previousMarket} → ${input.currentMarket}` : "Stable",
    },
    {
      label: "Confidence",
      value: input.confidenceChange || "Unchanged",
      detail: input.confidenceChange || "Stable",
    },
    {
      label: "Track",
      value: "Unchanged",
      detail: input.trackCondition || "Current",
    },
    {
      label: "Rail",
      value: "Unchanged",
      detail: input.railPosition || "Current",
    },
    {
      label: "Weather",
      value: "Unchanged",
      detail: input.weatherState || "Stable",
    },
  ];
}
