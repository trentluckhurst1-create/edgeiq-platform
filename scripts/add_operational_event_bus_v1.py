from pathlib import Path

root = Path("src/edgeiq-os/services/operational-events")
root.mkdir(parents=True, exist_ok=True)

(root / "OperationalEventTypes.ts").write_text(r'''
export type OperationalEventSeverity = "INFO" | "IMPORTANT" | "WARNING" | "CRITICAL";

export interface OperationalEvent {
  id: string;
  time: string;
  severity: OperationalEventSeverity;
  title: string;
  detail: string;
  source: string;
}
''', encoding="utf-8")

(root / "OperationalEventService.ts").write_text(r'''
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
''', encoding="utf-8")

(root / "index.ts").write_text(r'''
export * from "./OperationalEventTypes";
export * from "./OperationalEventService";
''', encoding="utf-8")

types = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateTypes.ts")
text = types.read_text(encoding="utf-8")

if "OperationalEvent" not in text:
    text = text.replace(
'''export interface ExecutiveSummary {
  decision: OperationalDecision;
  correlation: OperationalCorrelation;
  headline: string;
  summary: string;
  topFindings: OperationalFinding[];
  systemHealth: {
    feedsReady: number;
    feedsTotal: number;
    alerts: number;
    coverage: number;
  };
}
''',
'''export interface ExecutiveSummary {
  decision: OperationalDecision;
  correlation: OperationalCorrelation;
  headline: string;
  summary: string;
  topFindings: OperationalFinding[];
  systemHealth: {
    feedsReady: number;
    feedsTotal: number;
    alerts: number;
    coverage: number;
  };
}

export interface OperationalEvent {
  id: string;
  time: string;
  severity: "INFO" | "IMPORTANT" | "WARNING" | "CRITICAL";
  title: string;
  detail: string;
  source: string;
}
'''
    )

if "events:" not in text:
    text = text.replace(
'''  executiveSummary: ExecutiveSummary;
  status: IntelligenceStatus;
}''',
'''  executiveSummary: ExecutiveSummary;
  events: OperationalEvent[];
  status: IntelligenceStatus;
}'''
    )

types.write_text(text, encoding="utf-8")

service = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")
text = service.read_text(encoding="utf-8")

if 'from "../operational-events"' not in text:
    text = text.replace(
'import { buildExecutiveSummary } from "../executive-summary";',
'import { buildExecutiveSummary } from "../executive-summary";\nimport { buildOperationalEvents } from "../operational-events";'
    )

if "const events = buildOperationalEvents" not in text:
    text = text.replace(
'''  const executiveSummary = buildExecutiveSummary(
    decision,
    findings,
    correlation,
    moduleOutputs.map((module) => module.feedHealth),
    alerts,
    coverage,
  );
''',
'''  const executiveSummary = buildExecutiveSummary(
    decision,
    findings,
    correlation,
    moduleOutputs.map((module) => module.feedHealth),
    alerts,
    coverage,
  );
  const events = buildOperationalEvents(moduleOutputs, correlation, decision, findings);
'''
    )

if "events," not in text:
    text = text.replace(
'''    executiveSummary,

    status:''',
'''    executiveSummary,
    events,

    status:'''
    )

service.write_text(text, encoding="utf-8")

print("[EDGEIQ] Operational Event Bus created and wired into race state")
