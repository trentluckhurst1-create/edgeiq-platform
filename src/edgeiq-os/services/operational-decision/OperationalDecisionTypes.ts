
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
