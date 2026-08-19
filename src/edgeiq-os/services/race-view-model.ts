import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";
import { formatConfidenceLabel, formatDecisionState } from "../design-system";

export type RaceViewModel = {
  hero: {
    title: string;
    situation: string;
    confidence: string;
    decision: string;
  };

  pressure: {
    label: string;
    value: string;
    summary: string;
  };

  tempo: {
    label: string;
    value: string;
    summary: string;
  };

  tacticalAdvantage: {
    label: string;
    value: string;
    summary: string;
  };

  watch: string[];

  race: {
    meeting: string;
    raceNumber: number;
    distance: string;
    condition: string;
    rail: string;
  };
};

function findEvidenceSummary(raceState: OperationalRaceState, category: string): string | undefined {
  return raceState.evidence.find((item) => item.category === category)?.summary;
}

function inferPressure(raceState: OperationalRaceState): RaceViewModel["pressure"] {
  const pace = findEvidenceSummary(raceState, "PACE");

  return {
    label: "Pressure",
    value: raceState.feedHealth.some((feed) => feed.label.toLowerCase().includes("shape") && feed.status === "READY")
      ? "Mapped"
      : "Building",
    summary: pace ?? "Pressure intelligence is still forming from available race-shape signals.",
  };
}

function inferTempo(raceState: OperationalRaceState): RaceViewModel["tempo"] {
  const pace = findEvidenceSummary(raceState, "PACE");

  return {
    label: "Tempo",
    value: pace ? "Assessed" : "Developing",
    summary: pace ?? "Tempo projection will strengthen as race-shape intelligence matures.",
  };
}

function inferTacticalAdvantage(raceState: OperationalRaceState): RaceViewModel["tacticalAdvantage"] {
  const findings = raceState.findings.slice(0, 2).map((finding) => finding.title);

  return {
    label: "Tactical Advantage",
    value: findings[0] ?? "Monitoring",
    summary: findings.length
      ? findings.join(" · ")
      : "No dominant tactical advantage has been confirmed yet.",
  };
}

export function buildRaceViewModel(raceState: OperationalRaceState = getOperationalRaceState()): RaceViewModel {
  return {
    hero: {
      title: "Race Situation",
      situation: raceState.currentSituation || raceState.currentAssessment || "Race intelligence is building.",
      confidence: formatConfidenceLabel(raceState.confidence),
      decision: formatDecisionState(raceState.decision.state),
    },

    pressure: inferPressure(raceState),

    tempo: inferTempo(raceState),

    tacticalAdvantage: inferTacticalAdvantage(raceState),

    watch: [
      "Late tempo change",
      "Track pattern shift",
      "Market disagreement",
      "Unexpected scratching",
    ],

    race: {
      meeting: raceState.meetingName,
      raceNumber: raceState.raceNumber,
      distance: raceState.distance,
      condition: raceState.trackCondition,
      rail: raceState.rail,
    },
  };
}
