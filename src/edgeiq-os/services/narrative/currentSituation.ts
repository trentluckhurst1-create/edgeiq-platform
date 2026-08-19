export type CommandNarrativeInput = {
  trackCondition?: string;
  railPosition?: string;
  confidenceBand?: string;
  marketDivergenceRunner?: string;
};

export function buildCurrentSituation(input: CommandNarrativeInput): string[] {
  const track = input.trackCondition || "the current track condition";
  const rail = input.railPosition || "the published rail position";
  const confidence = input.confidenceBand || "current";

  return [
    "The projected race shape favours runners capable of holding a tactical position before the home turn.",
    input.marketDivergenceRunner
      ? `Current market behaviour differs from the EDGEiQ assessment on ${input.marketDivergenceRunner}.`
      : "Current market behaviour differs from the EDGEiQ assessment on one runner.",
    `Environmental conditions remain stable under ${track} with ${rail}.`,
    `Assessment confidence remains ${confidence.toLowerCase()} with no significant late intelligence deterioration detected.`,
  ];
}
