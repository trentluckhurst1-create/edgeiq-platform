import type { IntelligenceStatus } from "../operational-state";

export interface IntelligenceCoverageItem {
  key: string;
  label: string;
  coveragePct: number;
  status: IntelligenceStatus;
}
