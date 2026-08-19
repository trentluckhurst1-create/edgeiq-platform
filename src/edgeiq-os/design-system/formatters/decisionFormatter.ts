export function formatDecisionState(decision: string): string {
  if (decision === "EXECUTE") return "Escalate";
  if (decision === "MONITOR") return "Maintain Monitoring";
  if (decision === "WAIT") return "Wait";
  if (decision === "REVIEW") return "Review Required";
  return decision;
}
