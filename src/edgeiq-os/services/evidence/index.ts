import type { EvidenceModule } from "./EvidenceTypes";
import { paceEvidenceModule } from "./modules/paceEvidence";
import { runnerDnaEvidenceModule } from "./modules/runnerDnaEvidence";
import { buildGenericEvidenceModule } from "./modules/genericEvidence";

const evidenceModules: Record<string, EvidenceModule> = {
  "Pace Intelligence": paceEvidenceModule,
  "Runner DNA": runnerDnaEvidenceModule,
};

export function getEvidenceModule(name: string): EvidenceModule {
  return evidenceModules[name] ?? buildGenericEvidenceModule(name);
}

export type { EvidenceModule } from "./EvidenceTypes";
