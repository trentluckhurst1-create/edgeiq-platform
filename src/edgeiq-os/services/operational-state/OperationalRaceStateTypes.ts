
export type IntelligenceStatus = "READY" | "PARTIAL" | "PLACEHOLDER" | "ERROR";

export type EvidenceCategory =
  | "PACE"
  | "RUNNER_DNA"
  | "TRACK"
  | "CONNECTIONS"
  | "WEATHER"
  | "SECTIONALS"
  | "MARKET"
  | "ENVIRONMENT"
  | "GENERIC";

export interface OperationalEvidenceItem {
  id: string;
  category: EvidenceCategory;
  title: string;
  summary: string;
  confidence: number;
  importance: number;
  status: IntelligenceStatus;
}

export interface OperationalTimelineEvent {
  id: string;
  time: string;
  title: string;
  summary: string;
  severity: "INFO" | "WATCH" | "IMPORTANT" | "CRITICAL";
}

export interface OperationalFeedHealth {
  key: string;
  label: string;
  status: IntelligenceStatus;
  freshness: string;
}

export interface OperationalAlert {
  id: string;
  category:
    | "SYSTEM"
    | "MARKET"
    | "TRACK"
    | "WEATHER"
    | "PACE"
    | "RUNNER"
    | "CONNECTION"
    | "SECTIONAL";
  title: string;
  summary: string;
  severity: "INFO" | "WATCH" | "IMPORTANT" | "CRITICAL";
}

export interface IntelligenceCoverageItem {
  key: string;
  label: string;
  coveragePct: number;
  status: IntelligenceStatus;
}

export interface OperationalCorrelation {
  agreementScore: number;
  agreementBand: string;
  operationalConfidence: number;
  operationalPriority: string;
  reinforcement: string[];
  conflicts: string[];
  supportingModules: string[];
}

export interface OperationalFinding {
  id: string;
  title: string;
  summary: string;
  confidence: number;
  importance: number;
  priority: "CRITICAL" | "HIGH" | "NORMAL" | "LOW";
  supportingEngines: string[];
}

export interface OperationalDecision {
  state: "EXECUTE" | "MONITOR" | "WAIT" | "REVIEW";
  confidence: number;
  priority: "CRITICAL" | "HIGH" | "NORMAL" | "LOW";
  headline: string;
  rationale: string;
  supportingFindings: string[];
}

export interface ExecutiveSummary {
  decision: OperationalDecision;
  correlation: OperationalCorrelation;
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

export interface OperationalEvent {
  id: string;
  time: string;
  severity: "INFO" | "IMPORTANT" | "WARNING" | "CRITICAL";
  title: string;
  detail: string;
  source: string;
}

export interface OperationalRaceState {
  raceId: string;
  meetingName: string;
  raceNumber: number;
  raceName: string;
  distance: string;
  raceClass: string;
  trackCondition: string;
  rail: string;
  confidence: number;
  referenceRunner: string;
  currentSituation: string;
  whyItMatters: string;
  currentAssessment: string;
  marketRelationship: string;
  evidence: OperationalEvidenceItem[];
  timeline: OperationalTimelineEvent[];
  feedHealth: OperationalFeedHealth[];
  alerts: OperationalAlert[];
  coverage: IntelligenceCoverageItem[];
  correlation: OperationalCorrelation;
  findings: OperationalFinding[];
  decision: OperationalDecision;
  executiveSummary: ExecutiveSummary;
  events: OperationalEvent[];
  status: IntelligenceStatus;
}
