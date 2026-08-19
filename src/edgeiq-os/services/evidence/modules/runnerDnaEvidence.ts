import type { EvidenceModule } from "../EvidenceTypes";

export const runnerDnaEvidenceModule: EvidenceModule = {
  id: "runner-dna",
  title: "Runner DNA",
  currentInterpretation:
    "The reference runner profiles positively across tactical suitability, distance fit and current race setup.",
  projectedShape: ["Profile", "Distance", "Track", "Class"],
  pressureBand: "Positive",
  settlingPattern: [
    { label: "Tactical Fit", value: "Strong" },
    { label: "Distance Fit", value: "Positive" },
    { label: "Track Fit", value: "Neutral" },
  ],
  closingPhase:
    "The runner remains most effective when able to settle within range before the home turn.",
  historicalContext:
    "Comparable runner profiles have performed best when race pressure remains genuine without becoming excessive.",
  confidenceBand: "High",
};
