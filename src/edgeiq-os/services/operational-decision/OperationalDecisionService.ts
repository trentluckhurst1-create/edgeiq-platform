
import type { CorrelationSummary } from "../operational-correlation";
import type { OperationalFinding } from "../operational-reasoning";
import type { OperationalDecision } from "./OperationalDecisionTypes";

export function buildOperationalDecision(
  correlation: CorrelationSummary,
  findings: OperationalFinding[],
): OperationalDecision {

  const critical = findings.filter(f => f.priority === "CRITICAL");
  const high = findings.filter(f => f.priority === "HIGH");

  let state: OperationalDecision["state"] = "WAIT";

  if (
    correlation.operationalConfidence >= 88 &&
    correlation.agreementScore >= 85 &&
    critical.length > 0
  ) {
    state = "EXECUTE";
  }
  else if (
    correlation.operationalConfidence >= 70 &&
    high.length > 0
  ) {
    state = "MONITOR";
  }
  else if (
    correlation.conflicts.length > 0
  ) {
    state = "REVIEW";
  }

  const headline =
    state === "EXECUTE"
      ? "Independent intelligence strongly reinforces the current assessment."
      : state === "MONITOR"
      ? "Operational opportunity identified. Continue monitoring."
      : state === "REVIEW"
      ? "Operational conflict detected between intelligence engines."
      : "Await stronger operational alignment.";

  const rationale =
    [
      `Agreement ${correlation.agreementScore}% (${correlation.agreementBand}).`,
      `Operational confidence ${correlation.operationalConfidence}%.`,
      `Priority ${correlation.operationalPriority}.`
    ].join(" ");

  return {
    state,
    confidence: correlation.operationalConfidence,
    priority: correlation.operationalPriority as OperationalDecision["priority"],
    headline,
    rationale,
    supportingFindings: findings.slice(0,5).map(f=>f.title),
  };
}
