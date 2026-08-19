from pathlib import Path

types = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateTypes.ts")
text = types.read_text(encoding="utf-8")

if "OperationalFinding" not in text:
    text = text.replace(
'''export interface OperationalCorrelation {
  agreementScore: number;
  agreementBand: string;
  operationalConfidence: number;
  operationalPriority: string;
  reinforcement: string[];
  conflicts: string[];
  supportingModules: string[];
}
''',
'''export interface OperationalCorrelation {
  agreementScore: number;
  agreementBand: string;
  operationalConfidence: number;
  operationalPriority: string;
  reinforcement: string[];
  conflicts: string[];
  supportingModules: string[];
}

export interface OperationalFinding {
  id: string;
  title: string;
  summary: string;
  confidence: number;
  importance: number;
  priority: "CRITICAL" | "HIGH" | "NORMAL" | "LOW";
  supportingEngines: string[];
}

export interface OperationalDecision {
  state: "EXECUTE" | "MONITOR" | "WAIT" | "REVIEW";
  confidence: number;
  priority: "CRITICAL" | "HIGH" | "NORMAL" | "LOW";
  headline: string;
  rationale: string;
  supportingFindings: string[];
}

export interface ExecutiveSummary {
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
'''
    )

if "executiveSummary:" not in text:
    text = text.replace(
'''  correlation: OperationalCorrelation;
  status: IntelligenceStatus;
}''',
'''  correlation: OperationalCorrelation;
  findings: OperationalFinding[];
  decision: OperationalDecision;
  executiveSummary: ExecutiveSummary;
  status: IntelligenceStatus;
}'''
    )

types.write_text(text, encoding="utf-8")

service = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")
text = service.read_text(encoding="utf-8")

if 'from "../operational-reasoning"' not in text:
    text = text.replace(
'import { buildOperationalCorrelation } from "../operational-correlation";',
'import { buildOperationalCorrelation } from "../operational-correlation";\nimport { buildOperationalFindings } from "../operational-reasoning";\nimport { buildOperationalDecision } from "../operational-decision";\nimport { buildExecutiveSummary } from "../executive-summary";'
    )

if "const findings = buildOperationalFindings" not in text:
    text = text.replace(
'''  const coverage = buildCoverageFromModules(moduleOutputs);
  const correlation = buildOperationalCorrelation(moduleOutputs);
''',
'''  const coverage = buildCoverageFromModules(moduleOutputs);
  const correlation = buildOperationalCorrelation(moduleOutputs);
  const findings = buildOperationalFindings(evidence, correlation);
  const decision = buildOperationalDecision(correlation, findings);
  const executiveSummary = buildExecutiveSummary(
    decision,
    findings,
    correlation,
    moduleOutputs.map((module) => module.feedHealth),
    alerts,
    coverage,
  );
'''
    )

if "findings," not in text:
    text = text.replace(
'''    coverage,
    correlation,

    status:''',
'''    coverage,
    correlation,
    findings,
    decision,
    executiveSummary,

    status:'''
    )

service.write_text(text, encoding="utf-8")

print("[EDGEIQ] Executive summary, findings and decision wired into OperationalRaceState")
