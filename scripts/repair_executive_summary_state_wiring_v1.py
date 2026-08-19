from pathlib import Path

summary = Path("src/edgeiq-os/services/executive-summary/ExecutiveSummaryService.ts")

summary.write_text(r'''
import type {
  IntelligenceCoverageItem,
  OperationalAlert,
  OperationalFeedHealth,
} from "../operational-state";

import type { OperationalDecision } from "../operational-decision";
import type { OperationalFinding } from "../operational-reasoning";
import type { CorrelationSummary } from "../operational-correlation";

import type { ExecutiveSummary } from "./ExecutiveSummaryTypes";

export function buildExecutiveSummary(
  decision: OperationalDecision,
  findings: OperationalFinding[],
  correlation: CorrelationSummary,
  feedHealth: OperationalFeedHealth[],
  alerts: OperationalAlert[],
  coverage: IntelligenceCoverageItem[],
): ExecutiveSummary {
  const readyFeeds = feedHealth.filter((feed) => feed.status === "READY").length;

  const coveragePct =
    coverage.length === 0
      ? 0
      : Math.round(
          coverage.reduce((sum, item) => sum + item.coveragePct, 0) /
            coverage.length,
        );

  return {
    decision,
    correlation,
    headline: decision.headline,
    summary: decision.rationale,
    topFindings: findings.sort((a, b) => b.importance - a.importance).slice(0, 4),
    systemHealth: {
      feedsReady: readyFeeds,
      feedsTotal: feedHealth.length,
      alerts: alerts.length,
      coverage: coveragePct,
    },
  };
}
''', encoding="utf-8")

state = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")

state.write_text(r'''
import { buildSystemAlerts } from "../alerts";
import { registerProductionAdapterSlots } from "../adapters";
import { composeOperationalBriefing } from "../briefing";
import {
  buildRegisteredIntelligence,
  clearIntelligenceRegistry,
} from "../intelligence-registry";
import { buildCoverageFromModules } from "../intelligence-coverage";
import { buildOperationalCorrelation } from "../operational-correlation";
import { buildOperationalDecision } from "../operational-decision";
import { buildOperationalFindings } from "../operational-reasoning";
import { buildExecutiveSummary } from "../executive-summary";
import { seedTimeline } from "../timeline";
import type { OperationalRaceState } from "./OperationalRaceStateTypes";

export function buildOperationalRaceState(): OperationalRaceState {
  clearIntelligenceRegistry();
  registerProductionAdapterSlots();

  const moduleOutputs = buildRegisteredIntelligence();
  const evidence = moduleOutputs.flatMap((module) => module.evidence);
  const briefing = composeOperationalBriefing(evidence);
  const alerts = buildSystemAlerts();
  const coverage = buildCoverageFromModules(moduleOutputs);
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

  return {
    raceId: "current-race",
    meetingName: "Current Meeting",
    raceNumber: 1,
    raceName: "Operational State",
    distance: "",
    raceClass: "",
    trackCondition: "",
    rail: "",
    confidence: correlation.operationalConfidence,
    referenceRunner: "Production runner pending",

    currentSituation: briefing.currentSituation,
    whyItMatters: briefing.whyItMatters,
    currentAssessment: briefing.currentAssessment,
    marketRelationship: briefing.marketRelationship,

    evidence,
    timeline: seedTimeline(),
    feedHealth: moduleOutputs.map((module) => module.feedHealth),
    alerts,
    coverage,
    correlation,
    findings,
    decision,
    executiveSummary,

    status:
      moduleOutputs.every((module) => module.status === "READY")
        ? "READY"
        : "PARTIAL",
  };
}
''', encoding="utf-8")

print("[EDGEIQ] Executive summary wiring repaired")
