import type { EvidenceModule } from "../EvidenceTypes";

export const paceEvidenceModule: EvidenceModule = {
  id: "pace",
  title: "Pace Intelligence",
  currentInterpretation:
    "Genuine early pressure is expected, with multiple runners showing intent to lead or sit outside the leader.",
  projectedShape: ["Lead", "Pressure", "Midfield", "Back"],
  pressureBand: "High",
  settlingPattern: [
    { label: "Leaders / On Pace", value: "5" },
    { label: "Midfield", value: "6" },
    { label: "Backmarkers", value: "4" },
  ],
  closingPhase:
    "Strong closing test for backmarkers. Sustained tempo into the home turn.",
  historicalContext:
    "Similar race shapes at this course and distance have favoured on-pace runners over the past 24 months.",
  confidenceBand: "High",
};
