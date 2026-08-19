import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";

export type PositionBand = "FORWARD" | "ON_PACE" | "MIDFIELD" | "BACK" | "BUILDING";
export type LaneBand = "RAIL" | "COVER" | "WIDE" | "EXPOSED" | "UNKNOWN";

export type PositionEngineModel = {
  label: string;
  position: PositionBand;
  lane: LaneBand;
  confidence: "Low" | "Developing" | "Moderate" | "High" | "Very High";
  summary: string;
  tacticalRead: string;
  watch: string[];
};

function confidenceLabel(value: number): PositionEngineModel["confidence"] {
  if (value >= 85) return "Very High";
  if (value >= 70) return "High";
  if (value >= 55) return "Moderate";
  if (value >= 40) return "Developing";
  return "Low";
}

function inferPosition(raceState: OperationalRaceState): PositionBand {
  const text = [
    ...raceState.evidence.map((item) => `${item.title} ${item.summary}`),
    ...raceState.findings.map((item) => `${item.title} ${item.summary}`),
  ].join(" ").toLowerCase();

  if (text.includes("forward") || text.includes("leader") || text.includes("speed")) return "FORWARD";
  if (text.includes("on pace") || text.includes("on-pace")) return "ON_PACE";
  if (text.includes("midfield")) return "MIDFIELD";
  if (text.includes("backmarker") || text.includes("back marker") || text.includes("back")) return "BACK";

  const pressure = buildPressureEngine(raceState);
  const tempo = buildTempoEngine(raceState);

  if (pressure.band === "HIGH" || tempo.band === "STRONG" || tempo.band === "FAST") return "ON_PACE";
  if (pressure.band === "BUILDING" || tempo.band === "BUILDING") return "BUILDING";

  return "MIDFIELD";
}

function inferLane(raceState: OperationalRaceState): LaneBand {
  const text = [
    ...raceState.evidence.map((item) => `${item.title} ${item.summary}`),
    raceState.rail,
  ].join(" ").toLowerCase();

  if (text.includes("rail")) return "RAIL";
  if (text.includes("cover")) return "COVER";
  if (text.includes("wide")) return "WIDE";
  if (text.includes("exposed")) return "EXPOSED";

  return "UNKNOWN";
}

function positionSummary(position: PositionBand, lane: LaneBand): string {
  if (position === "FORWARD") return "Forward positioning is currently projected to carry tactical value.";
  if (position === "ON_PACE") return "On-pace runners are expected to be tactically advantaged if tempo remains controlled.";
  if (position === "MIDFIELD") return "Midfield positioning appears viable if pressure remains within the expected range.";
  if (position === "BACK") return "Backmarkers may require tempo pressure or late-race compression to improve their chance.";
  return "Position intelligence is still building from available race-shape signals.";
}

function tacticalRead(position: PositionBand, lane: LaneBand): string {
  const laneText =
    lane === "RAIL"
      ? "Rail position may become relevant to the tactical read."
      : lane === "COVER"
        ? "Cover is preferred to avoid being exposed through the middle stages."
        : lane === "WIDE"
          ? "Wide exposure is a tactical risk unless tempo creates room to move."
          : lane === "EXPOSED"
            ? "Exposure without cover is a material risk."
            : "Lane preference has not yet been confirmed.";

  return `${positionSummary(position, lane)} ${laneText}`;
}

export function buildPositionEngine(
  raceState: OperationalRaceState = getOperationalRaceState(),
): PositionEngineModel {
  const position = inferPosition(raceState);
  const lane = inferLane(raceState);

  return {
    label: "Position",
    position,
    lane,
    confidence: confidenceLabel(raceState.confidence),
    summary: positionSummary(position, lane),
    tacticalRead: tacticalRead(position, lane),
    watch: [
      "Barrier impact changing early position",
      "Runner caught wide without cover",
      "Pace pressure forcing a position change",
      "Track pattern favouring a different lane",
    ],
  };
}
