export type MarketRelationshipInput = {
  runnerName?: string;
  hasMarketDivergence?: boolean;
};

export function buildMarketRelationship(input: MarketRelationshipInput): string {
  if (!input.hasMarketDivergence) {
    return "Current market behaviour is broadly aligned with the EDGEiQ assessment. This relationship is presented as intelligence context only; the final decision remains with the user.";
  }

  const profile = input.runnerName ? ` on ${input.runnerName}` : "";
  return `Current market behaviour remains materially different from the EDGEiQ assessment${profile}. This relationship is presented as intelligence context only; the final decision remains with the user.`;
}
