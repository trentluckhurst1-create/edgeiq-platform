from pathlib import Path

root = Path("src/edgeiq-os/services/operational-decision")
root.mkdir(parents=True, exist_ok=True)

(root / "OperationalDecisionTypes.ts").write_text(r'''
export type OperationalDecisionState =
  | "EXECUTE"
  | "MONITOR"
  | "WAIT"
  | "REVIEW";

export interface OperationalDecision {
  state: OperationalDecisionState;
  confidence: number;
  priority: "CRITICAL" | "HIGH" | "NORMAL" | "LOW";
  headline: string;
  rationale: string;
  supportingFindings: string[];
}
''', encoding="utf-8")

(root / "OperationalDecisionService.ts").write_text(r'''
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
''', encoding="utf-8")

(root / "index.ts").write_text(r'''
export * from "./OperationalDecisionService";
export * from "./OperationalDecisionTypes";
''', encoding="utf-8")

print("[EDGEIQ] Operational Decision Engine created")
