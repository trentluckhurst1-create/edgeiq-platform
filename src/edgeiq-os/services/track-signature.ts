import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";

export type TrackSignatureModel = {
  title: string;
  assessment: string;
  operationalMeaning: string;
  rail: string;
  surface: string;
  wind: string;
  moisture: string;
  historicalPattern: string;
  todayPattern: string;
  confidence: string;
  watch: string[];
};

function confidenceLabel(value: number): string {
  if (value >= 85) return "Very High";
  if (value >= 70) return "High";
  if (value >= 55) return "Moderate";
  if (value >= 40) return "Developing";
  return "Low";
}

export function buildTrackSignature(raceState: OperationalRaceState = getOperationalRaceState()): TrackSignatureModel {
  const trackEvidence = raceState.evidence.find((item) => item.category === "TRACK" || item.category === "ENVIRONMENT");

  return {
    title: "TrackSignature",
    assessment: trackEvidence?.summary ?? "TrackSignature is monitoring rail, surface and environment behaviour.",
    operationalMeaning: "TrackSignature explains how today's surface and rail setup may influence tactical advantage without exposing internal bias modelling.",
    rail: raceState.rail || "Monitoring",
    surface: raceState.trackCondition || "Monitoring",
    wind: "Monitoring",
    moisture: raceState.trackCondition?.toLowerCase().includes("soft") || raceState.trackCondition?.toLowerCase().includes("heavy")
      ? "Influential"
      : "Controlled",
    historicalPattern: "Reserved",
    todayPattern: trackEvidence ? "Active" : "Building",
    confidence: confidenceLabel(raceState.confidence),
    watch: [
      "Track downgrade",
      "Rail pattern shift",
      "Wind change",
      "Inside or outside lane advantage emerging",
    ],
  };
}
