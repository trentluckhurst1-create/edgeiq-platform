
export type OperationalFindingPriority = "CRITICAL" | "HIGH" | "NORMAL" | "LOW";

export interface OperationalFinding {
  id: string;
  title: string;
  summary: string;
  confidence: number;
  importance: number;
  priority: OperationalFindingPriority;
  supportingEngines: string[];
}
