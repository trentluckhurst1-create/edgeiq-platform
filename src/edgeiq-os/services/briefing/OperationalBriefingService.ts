
import type { OperationalEvidenceItem } from "../operational-state";

export interface OperationalBriefing {
  currentSituation: string;
  whyItMatters: string;
  currentAssessment: string;
  marketRelationship: string;
}

function first(evidence: OperationalEvidenceItem[], category: string) {
  return evidence.find((item) => item.category === category);
}

export function composeOperationalBriefing(
  evidence: OperationalEvidenceItem[],
): OperationalBriefing {
  const pace = first(evidence, "PACE");
  const dna = first(evidence, "RUNNER_DNA");
  const explain = first(evidence, "GENERIC");
  const market = first(evidence, "MARKET");

  return {
    currentSituation:
      pace?.summary ??
      "Operational intelligence pending.",

    whyItMatters:
      explain?.summary ??
      dna?.summary ??
      "No operational interpretation available.",

    currentAssessment:
      dna?.summary ??
      explain?.summary ??
      "Assessment pending.",

    marketRelationship:
      market?.summary ??
      "No significant market relationship detected.",
  };
}
