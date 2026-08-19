
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
import { buildOperationalEvents } from "../operational-events";
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
  const events = buildOperationalEvents(moduleOutputs, correlation, decision, findings);

  return {
    raceId: "current-race",
    meetingName: "Current Meeting",
    raceNumber: 1,
    raceName: "Current Race",
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
    events,

    status:
      moduleOutputs.every((module) => module.status === "READY")
        ? "READY"
        : "PARTIAL",
  };
}
