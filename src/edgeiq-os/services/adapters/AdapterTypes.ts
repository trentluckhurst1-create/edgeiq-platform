
import type { IntelligenceModuleOutput } from "../intelligence-registry";

export interface IntelligenceAdapter {
  key: string;
  label: string;
  buildModuleOutput: () => IntelligenceModuleOutput;
}
