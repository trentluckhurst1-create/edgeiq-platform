export type WhyItMattersInput = {
  confidenceBand?: string;
  hasMarketDivergence?: boolean;
};

export function buildWhyItMatters(input: WhyItMattersInput): string[] {
  return [
    "Tactical positioning is expected to be important.",
    "Genuine early pressure remains likely.",
    input.hasMarketDivergence
      ? "Market behaviour differs from the EDGEiQ assessment on one profile."
      : "Market behaviour is currently aligned with the EDGEiQ assessment.",
    "Environmental conditions are stable.",
    `Assessment confidence is ${input.confidenceBand || "current"}.`,
  ];
}
