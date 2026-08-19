
import type { OperationalDecision } from "../operational-decision";
import type { OperationalFinding } from "../operational-reasoning";
import type { CorrelationSummary } from "../operational-correlation";

export interface ExecutiveSummary {
  decision: OperationalDecision;
  correlation: CorrelationSummary;

  headline: string;
  summary: string;

  topFindings: OperationalFinding[];

  systemHealth: {
    feedsReady: number;
    feedsTotal: number;
    alerts: number;
    coverage: number;
  };
}
