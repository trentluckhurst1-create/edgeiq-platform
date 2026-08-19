
import type { IntelligenceModuleOutput } from "../intelligence-registry";
import type { CorrelationSummary } from "../operational-correlation";
import type { OperationalDecision } from "../operational-decision";
import type { OperationalFinding } from "../operational-reasoning";
import type { OperationalEvent } from "./OperationalEventTypes";

function time(index: number): string {
  return `18:${String(9 - index).padStart(2, "0")}`;
}

export function buildOperationalEvents(
  modules: IntelligenceModuleOutput[],
  correlation: CorrelationSummary,
  decision: OperationalDecision,
  findings: OperationalFinding[],
): OperationalEvent[] {
  const events: OperationalEvent[] = [];

  events.push({
    id: "decision-state",
    time: time(0),
    severity: decision.state === "EXECUTE" ? "CRITICAL" : decision.state === "MONITOR" ? "IMPORTANT" : "INFO",
    title: `Decision state: ${decision.state}`,
    detail: decision.headline,
    source: "Decision Engine",
  });

  events.push({
    id: "correlation-state",
    time: time(1),
    severity: correlation.agreementScore >= 75 ? "IMPORTANT" : "WARNING",
    title: `Engine agreement: ${correlation.agreementBand}`,
    detail: `Agreement ${correlation.agreementScore}%. Operational confidence ${correlation.operationalConfidence}%.`,
    source: "Correlation Engine",
  });

  findings.slice(0, 4).forEach((finding, index) => {
    events.push({
      id: `finding-${finding.id}`,
      time: time(index + 2),
      severity: finding.priority === "CRITICAL" ? "CRITICAL" : finding.priority === "HIGH" ? "IMPORTANT" : "INFO",
      title: finding.title,
      detail: finding.summary,
      source: finding.supportingEngines.join(" + "),
    });
  });

  modules.forEach((module, index) => {
    events.push({
      id: `feed-${module.key}`,
      time: time(index + 6),
      severity: module.status === "READY" ? "INFO" : "WARNING",
      title: `${module.label}: ${module.status}`,
      detail: module.feedHealth.freshness,
      source: "Feed Health",
    });
  });

  return events;
}
