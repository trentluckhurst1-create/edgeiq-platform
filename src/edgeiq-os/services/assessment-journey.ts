import type { OperationalRaceState, IntelligenceStatus } from "./operational-state";
import { formatDecisionState, formatConfidenceLabel } from "../design-system";

export type AssessmentJourneyStage = {
  id: string;
  label: string;
  status: IntelligenceStatus;
  summary: string;
  confidence: string;
  watch: string;
};

export type AssessmentJourneyModel = {
  title: string;
  decision: string;
  confidence: string;
  stages: AssessmentJourneyStage[];
};

function findStatus(raceState: OperationalRaceState, labels: string[]): IntelligenceStatus {
  const match = raceState.feedHealth.find((engine) =>
    labels.some((label) => engine.label.toLowerCase().includes(label.toLowerCase()))
  );

  return match?.status ?? "PARTIAL";
}

function statusSummary(status: IntelligenceStatus, ready: string, pending: string): string {
  return status === "READY" ? ready : pending;
}

export function buildAssessmentJourney(raceState: OperationalRaceState): AssessmentJourneyModel {
  const raceShapeStatus = findStatus(raceState, ["shape", "pace"]);
  const runnerStatus = findStatus(raceState, ["runner", "dna", "profile"]);
  const environmentStatus = findStatus(raceState, ["track", "weather", "environment"]);
  const marketStatus = findStatus(raceState, ["market"]);

  return {
    title: "Assessment Journey",
    decision: formatDecisionState(raceState.decision.state),
    confidence: formatConfidenceLabel(raceState.confidence),
    stages: [
      {
        id: "race-shape",
        label: "Race Shape",
        status: raceShapeStatus,
        summary: statusSummary(
          raceShapeStatus,
          "Pace intelligence is contributing to the current operational view.",
          "Race shape intelligence is still building."
        ),
        confidence: raceShapeStatus === "READY" ? "High" : "Developing",
        watch: "Late tempo changes or scratchings that alter pressure.",
      },
      {
        id: "runner-intelligence",
        label: "Runner Intelligence",
        status: runnerStatus,
        summary: statusSummary(
          runnerStatus,
          "Runner profile intelligence is reinforcing the assessment.",
          "Runner profile intelligence is awaiting further confirmation."
        ),
        confidence: runnerStatus === "READY" ? "High" : "Developing",
        watch: "Profile mismatches against today's race conditions.",
      },
      {
        id: "environment",
        label: "Track & Environment",
        status: environmentStatus,
        summary: statusSummary(
          environmentStatus,
          "Environment intelligence is aligned with the current assessment.",
          "Track and weather intelligence remain under observation."
        ),
        confidence: environmentStatus === "READY" ? "High" : "Developing",
        watch: "Track downgrade, rainfall or rail pattern changes.",
      },
      {
        id: "market",
        label: "Market Behaviour",
        status: marketStatus,
        summary: statusSummary(
          marketStatus,
          "Market intelligence is available for validation.",
          "Market confirmation has not yet fully aligned with the assessment."
        ),
        confidence: marketStatus === "READY" ? "Moderate" : "Developing",
        watch: "Late support, drift or disagreement with the operational view.",
      },
    ],
  };
}
