
import type {
  EvidenceCategory,
  IntelligenceStatus,
  OperationalEvidenceItem,
  OperationalFeedHealth,
} from "../operational-state";

export interface IntelligenceModuleOutput {
  key: string;
  label: string;
  category: EvidenceCategory;
  status: IntelligenceStatus;
  confidence: number;
  importance: number;
  evidence: OperationalEvidenceItem[];
  feedHealth: OperationalFeedHealth;
}

export interface IntelligenceModule {
  key: string;
  label: string;
  category: EvidenceCategory;
  build: () => IntelligenceModuleOutput;
}
