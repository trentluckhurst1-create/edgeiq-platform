export type EvidenceModule = {
  id: string;
  title: string;
  currentInterpretation: string;
  projectedShape?: string[];
  pressureBand?: string;
  settlingPattern?: { label: string; value: string }[];
  closingPhase?: string;
  historicalContext?: string;
  confidenceBand: string;
};
