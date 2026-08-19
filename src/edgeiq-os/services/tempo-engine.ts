import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";
import { buildPressureEngine } from "./pressure-engine";

export type TempoBand = "SLOW" | "EVEN" | "STRONG" | "FAST" | "UNSTABLE" | "BUILDING";

export type TempoEngineModel = {
  label: string;
  band: TempoBand;
  confidence: "Low" | "Developing" | "Moderate" | "High" | "Very High";
  summary: string;
  raceRead: string;
  expectedChange: string;
  watch: string[];
};

function inferTempoBand(raceState: OperationalRaceState): TempoBand {
  const pressure = buildPressureEngine(raceState);

  if (pressure.band === "BUILDING") return "BUILDING";
  if (pressure.band === "EXTREME") return "FAST";
  if (pressure.band === "HIGH") return raceState.confidence >= 80 ? "STRONG" : "EVEN";

  const text = raceState.evidence
    .map((item) => `${item.title} ${item.summary}`)
    .join(" ")
    .toLowerCase();

  if (text.includes("slow")) return "SLOW";
  if (text.includes("fast")) return "FAST";
  if (text.includes("unstable")) return "UNSTABLE";
  if (text.includes("tempo") || text.includes("pace")) return "EVEN";

  return "BUILDING";
}

function confidenceLabel(value: number): TempoEngineModel["confidence"] {
  if (value >= 85) return "Very High";
  if (value >= 70) return "High";
  if (value >= 55) return "Moderate";
  if (value >= 40) return "Developing";
  return "Low";
}

function raceRead(band: TempoBand): string {
  if (band === "FAST") return "A fast tempo may create late-race compression and expose runners unable to sustain pressure.";
  if (band === "STRONG") return "A strong tempo is expected to reward runners that can hold position without over-racing.";
  if (band === "SLOW") return "A slow tempo may favour runners with tactical speed and make it harder for backmarkers to close.";
  if (band === "UNSTABLE") return "Tempo remains unstable and may change materially before jump.";
  if (band === "BUILDING") return "Tempo intelligence is still developing and should not be treated as final.";
  return "An even tempo is currently projected, with no major distortion expected.";
}

function expectedChange(band: TempoBand): string {
  if (band === "FAST") return "Late pressure collapse remains possible.";
  if (band === "STRONG") return "Sustained speed is the key scenario to monitor.";
  if (band === "SLOW") return "Leader control is the main tactical risk.";
  if (band === "UNSTABLE") return "Reassessment likely if market or scratching changes arrive.";
  if (band === "BUILDING") return "Await race-shape confirmation.";
  return "No major tempo change currently projected.";
}

export function buildTempoEngine(
  raceState: OperationalRaceState = getOperationalRaceState(),
): TempoEngineModel {
  const band = inferTempoBand(raceState);

  return {
    label: "Tempo",
    band,
    confidence: confidenceLabel(raceState.confidence),
    summary: raceRead(band),
    raceRead: raceRead(band),
    expectedChange: expectedChange(band),
    watch: [
      "Leader challenged early",
      "Pace collapse",
      "Sustained speed through middle stages",
      "Late compression into the straight",
    ],
  };
}
