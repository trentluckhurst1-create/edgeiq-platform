export type CurrentAssessmentNarrative = {
  referenceProfile: string;
  runnerDetail: string;
  confidenceBand: string;
  marketPrice: string;
  supportingIntelligence: string;
};

export type CurrentAssessmentInput = {
  runnerName?: string;
  runnerNumber?: string;
  jockey?: string;
  trainer?: string;
  confidenceBand?: string;
  marketPrice?: string;
  supportingIntelligence?: string[];
};

export function buildCurrentAssessment(input: CurrentAssessmentInput): CurrentAssessmentNarrative {
  const runnerName = input.runnerName || "Reference Profile";
  const runnerNo = input.runnerNumber ? `#${input.runnerNumber}` : "Runner";
  const jockey = input.jockey ? `J: ${input.jockey}` : "J: Pending";
  const trainer = input.trainer ? `T: ${input.trainer}` : "T: Pending";

  return {
    referenceProfile: runnerName,
    runnerDetail: `${runnerNo} · ${jockey} · ${trainer}`,
    confidenceBand: input.confidenceBand || "Current",
    marketPrice: input.marketPrice || "Pending",
    supportingIntelligence: (input.supportingIntelligence || ["Pace", "DNA", "Distance", "Track", "Connections"]).join(" · "),
  };
}
