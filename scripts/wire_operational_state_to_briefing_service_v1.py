from pathlib import Path

path = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")
text = path.read_text(encoding="utf-8")

text = text.replace(
'import { buildSystemAlerts } from "../alerts";',
'import { buildSystemAlerts } from "../alerts";\nimport { composeOperationalBriefing } from "../briefing";'
)

old = r'''
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
'''

new = r'''
  const briefing = composeOperationalBriefing(evidence);
'''

text = text.replace(old, new)

text = text.replace("    currentSituation,", "    currentSituation: briefing.currentSituation,")
text = text.replace("    whyItMatters,", "    whyItMatters: briefing.whyItMatters,")
text = text.replace("    currentAssessment,", "    currentAssessment: briefing.currentAssessment,")
text = text.replace("    marketRelationship,", "    marketRelationship: briefing.marketRelationship,")

# Remove now-unused helper.
text = text.replace(r'''
function findEvidence(
  evidence: OperationalEvidenceItem[],
  category: string,
): OperationalEvidenceItem[] {
  return evidence.filter((item) => item.category === category);
}

''', "")

text = text.replace(
'''import type {
  OperationalEvidenceItem,
  OperationalRaceState,
} from "./OperationalRaceStateTypes";''',
'''import type { OperationalRaceState } from "./OperationalRaceStateTypes";'''
)

path.write_text(text, encoding="utf-8")

print("[EDGEIQ] OperationalRaceState now uses briefing composer")
