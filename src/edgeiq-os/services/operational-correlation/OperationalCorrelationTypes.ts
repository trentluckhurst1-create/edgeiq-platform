
export interface CorrelationSummary {
  agreementScore: number;
  agreementBand: string;
  operationalConfidence: number;
  operationalPriority: string;
  reinforcement: string[];
  conflicts: string[];
  supportingModules: string[];
}
