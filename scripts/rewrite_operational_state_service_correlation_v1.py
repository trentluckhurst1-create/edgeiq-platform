from pathlib import Path

path = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")

path.write_text(r'''
import { buildSystemAlerts } from "../alerts";
import { registerProductionAdapterSlots } from "../adapters";
import { composeOperationalBriefing } from "../briefing";
import {
  buildRegisteredIntelligence,
  clearIntelligenceRegistry,
} from "../intelligence-registry";
import { buildCoverageFromModules } from "../intelligence-coverage";
import { buildOperationalCorrelation } from "../operational-correlation";
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

    status:
      moduleOutputs.every((module) => module.status === "READY")
        ? "READY"
        : "PARTIAL",
  };
}
''', encoding="utf-8")

print("[EDGEIQ] OperationalRaceStateService fully rewritten with correlation")
