from pathlib import Path

service = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")

service.write_text(r'''
import { buildSystemAlerts } from "../alerts";
import { registerProductionAdapterSlots } from "../adapters";
import {
  buildRegisteredIntelligence,
  clearIntelligenceRegistry,
} from "../intelligence-registry";
import { buildCoverageFromModules } from "../intelligence-coverage";
import { seedTimeline } from "../timeline";
import type {
  OperationalEvidenceItem,
  OperationalRaceState,
} from "./OperationalRaceStateTypes";

function findEvidence(
  evidence: OperationalEvidenceItem[],
  category: string,
): OperationalEvidenceItem[] {
  return evidence.filter((item) => item.category === category);
}

export function buildOperationalRaceState(): OperationalRaceState {
  clearIntelligenceRegistry();
  registerProductionAdapterSlots();

  const moduleOutputs = buildRegisteredIntelligence();

  const evidence = moduleOutputs.flatMap((m) => m.evidence);

  const raceShape = findEvidence(evidence, "PACE");
  const dna = findEvidence(evidence, "RUNNER_DNA");
  const explain = findEvidence(evidence, "GENERIC");

  const currentSituation =
    raceShape[0]?.summary ??
    "Operational intelligence pending.";

  const whyItMatters =
    raceShape[1]?.summary ??
    "No operational explanation available.";

  const currentAssessment =
    explain[0]?.summary ??
    dna[0]?.summary ??
    "Assessment pending.";

  const marketRelationship =
    explain[1]?.summary ??
    "Market relationship pending.";

  return {
    raceId: "current-race",
    meetingName: "Current Meeting",
    raceNumber: 1,
    raceName: "Operational State",
    distance: "",
    raceClass: "",
    trackCondition: "",
    rail: "",
    confidence:
      moduleOutputs.length === 0
        ? 0
        : Math.round(
            moduleOutputs.reduce(
              (sum, module) => sum + module.confidence,
              0,
            ) / moduleOutputs.length,
          ),
    referenceRunner: "Production runner pending",

    currentSituation,
    whyItMatters,
    currentAssessment,
    marketRelationship,

    evidence,

    timeline: seedTimeline(),

    feedHealth: moduleOutputs.map((m) => m.feedHealth),

    alerts: buildSystemAlerts(),

    coverage: buildCoverageFromModules(moduleOutputs),

    status:
      moduleOutputs.every((m) => m.status === "READY")
        ? "READY"
        : "PARTIAL",
  };
}
''', encoding="utf-8")

print("[EDGEIQ] OperationalRaceState now composed from live adapter evidence")
