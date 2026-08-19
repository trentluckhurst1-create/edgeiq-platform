
import type { OperationalRaceState } from "../operational-state";
import type { ExecutiveBrief } from "./ExecutiveBriefTypes";

function alignmentLabel(score: number): string {
  if (score >= 80) return "Strong alignment";
  if (score >= 55) return "Mixed but usable";
  if (score > 0) return "Low alignment";
  return "Insufficient evidence";
}

function availabilityLabel(coverage: number): string {
  if (coverage >= 85) return "Broad evidence available";
  if (coverage >= 60) return "Partial evidence available";
  if (coverage > 0) return "Limited evidence available";
  return "Evidence unavailable";
}

export function composeExecutiveBrief(state: OperationalRaceState): ExecutiveBrief {
  const summary = state.executiveSummary;
  const decision = state.decision;
  const correlation = state.correlation;

  const partialFeeds = state.feedHealth
    .filter((feed) => feed.status !== "READY")
    .map((feed) => feed.label);

  const readyFeeds = state.feedHealth
    .filter((feed) => feed.status === "READY")
    .map((feed) => feed.label);

  const keyRisks =
    partialFeeds.length > 0
      ? partialFeeds.slice(0, 4).map((feed) => `${feed} is not yet fully available.`)
      : ["No major engine availability risks detected."];

  const keyOpportunities =
    readyFeeds.length > 0
      ? readyFeeds.slice(0, 4).map((feed) => `${feed} is currently contributing intelligence.`)
      : ["Awaiting stronger intelligence coverage."];

  const currentSituation =
    `${state.raceName} is currently in ${decision.state} mode. ` +
    `${alignmentLabel(correlation.agreementScore)} across available engines. ` +
    `${availabilityLabel(summary.systemHealth.coverage)}.`;

  const recommendedAction =
    decision.state === "EXECUTE"
      ? "Proceed only if market and late feed checks remain stable."
      : decision.state === "MONITOR"
      ? "Continue monitoring. Do not escalate until missing engines improve or market confirms the assessment."
      : decision.state === "REVIEW"
      ? "Review conflicting engines before acting."
      : "Wait for stronger operational alignment before taking action.";

  return {
    title: "Executive Brief",
    currentSituation,
    recommendedAction,
    evidenceAlignment: alignmentLabel(correlation.agreementScore),
    evidenceAvailable: availabilityLabel(summary.systemHealth.coverage),
    keyRisks,
    keyOpportunities,
    nextWatch:
      partialFeeds.length > 0
        ? `Next watch: ${partialFeeds[0]} update.`
        : "Next watch: market movement and late confidence shift.",
  };
}
