import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";

export type PressureBand = "LOW" | "NORMAL" | "HIGH" | "EXTREME" | "BUILDING";

export type PressureZone = {
  phase: "EARLY" | "MID" | "LATE";
  pressure: PressureBand;
  summary: string;
};

export type PressureEngineModel = {
  label: string;
  band: PressureBand;
  confidence: "Low" | "Developing" | "Moderate" | "High" | "Very High";
  summary: string;
  tacticalRead: string;
  zones: PressureZone[];
  watch: string[];
};

function confidenceLabel(value: number): PressureEngineModel["confidence"] {
  if (value >= 85) return "Very High";
  if (value >= 70) return "High";
  if (value >= 55) return "Moderate";
  if (value >= 40) return "Developing";
  return "Low";
}

function inferPressureBand(raceState: OperationalRaceState): PressureBand {
  const paceEvidence = raceState.evidence.filter((item) => item.category === "PACE");
  const paceReady = raceState.feedHealth.some((feed) =>
    feed.label.toLowerCase().includes("shape") && feed.status === "READY"
  );

  const text = [
    ...paceEvidence.map((item) => `${item.title} ${item.summary}`),
    ...raceState.findings.map((item) => `${item.title} ${item.summary}`),
  ].join(" ").toLowerCase();

  if (!paceReady && paceEvidence.length === 0) return "BUILDING";

  if (
    text.includes("fast") ||
    text.includes("pressure") ||
    text.includes("speed") ||
    text.includes("tempo") ||
    text.includes("leader")
  ) {
    return raceState.confidence >= 80 ? "HIGH" : "NORMAL";
  }

  return paceReady ? "NORMAL" : "BUILDING";
}

function buildZones(band: PressureBand): PressureZone[] {
  if (band === "HIGH" || band === "EXTREME") {
    return [
      {
        phase: "EARLY",
        pressure: "HIGH",
        summary: "Early pressure is expected to shape the first part of the race.",
      },
      {
        phase: "MID",
        pressure: "NORMAL",
        summary: "Pressure may stabilise once positions are established.",
      },
      {
        phase: "LATE",
        pressure: "HIGH",
        summary: "Late compression remains possible if tempo is sustained.",
      },
    ];
  }

  if (band === "BUILDING") {
    return [
      {
        phase: "EARLY",
        pressure: "BUILDING",
        summary: "Early pressure is still being assessed.",
      },
      {
        phase: "MID",
        pressure: "BUILDING",
        summary: "Mid-race pressure requires further intelligence.",
      },
      {
        phase: "LATE",
        pressure: "BUILDING",
        summary: "Late pressure profile has not yet been confirmed.",
      },
    ];
  }

  return [
    {
      phase: "EARLY",
      pressure: band,
      summary: "Early pressure is expected to remain controlled.",
    },
    {
      phase: "MID",
      pressure: band,
      summary: "Mid-race tempo should remain within the expected range.",
    },
    {
      phase: "LATE",
      pressure: "NORMAL",
      summary: "Late pressure is not currently projected to materially destabilise the race.",
    },
  ];
}

export function buildPressureEngine(
  raceState: OperationalRaceState = getOperationalRaceState(),
): PressureEngineModel {
  const band = inferPressureBand(raceState);
  const paceEvidence = raceState.evidence.find((item) => item.category === "PACE");

  return {
    label: "Pressure",
    band,
    confidence: confidenceLabel(raceState.confidence),
    summary:
      paceEvidence?.summary ??
      "Pressure assessment is forming from available race-shape intelligence.",
    tacticalRead:
      band === "HIGH" || band === "EXTREME"
        ? "Forward runners may gain tactical advantage if they absorb pressure cleanly."
        : band === "BUILDING"
          ? "No firm pressure advantage should be assumed until the race-shape view matures."
          : "The current pressure profile appears controlled and unlikely to strongly distort the race.",
    zones: buildZones(band),
    watch: [
      "Late scratching altering early speed",
      "Unexpected leader pressure",
      "Track pattern changing tactical advantage",
      "Market move suggesting a different tempo scenario",
    ],
  };
}
