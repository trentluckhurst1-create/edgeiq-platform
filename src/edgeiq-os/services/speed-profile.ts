import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";

export type SpeedProfileModel = {
  title: string;
  assessment: string;
  operationalMeaning: string;
  launch: string;
  cruise: string;
  pressureResponse: string;
  finishStrength: string;
  recovery: string;
  confidence: string;
  watch: string[];
};

function band(score: number): string {
  if (score >= 85) return "Elite";
  if (score >= 70) return "Strong";
  if (score >= 55) return "Positive";
  if (score >= 40) return "Developing";
  return "Unknown";
}

export function buildSpeedProfile(raceState: OperationalRaceState = getOperationalRaceState()): SpeedProfileModel {
  const confidence = raceState.confidence;
  const paceEvidence = raceState.evidence.find((item) => item.category === "SECTIONALS" || item.category === "PACE");

  return {
    title: "SpeedProfile",
    assessment: paceEvidence?.summary ?? "SpeedProfile intelligence is forming from available pace, sectional and race-shape evidence.",
    operationalMeaning: "SpeedProfile describes how runners are expected to travel through the race without exposing proprietary sectional calculations.",
    launch: band(confidence - 8),
    cruise: band(confidence),
    pressureResponse: band(confidence - 5),
    finishStrength: band(confidence + 3),
    recovery: band(confidence - 2),
    confidence: band(confidence),
    watch: [
      "Compressed sprint finish",
      "Sustained tempo through middle stages",
      "Runner forced wider than expected",
      "Late race pressure change",
    ],
  };
}
