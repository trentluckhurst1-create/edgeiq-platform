from pathlib import Path

types_path = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateTypes.ts")
service_path = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")

types_path.write_text(r'''
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
  status: IntelligenceStatus;
}
''', encoding="utf-8")

service_path.write_text(r'''
import { buildSystemAlerts } from "../alerts";
import {
  buildRegisteredIntelligence,
  clearIntelligenceRegistry,
  registerDefaultIntelligenceModules,
} from "../intelligence-registry";
import { buildCoverageFromModules } from "../intelligence-coverage";
import { seedTimeline } from "../timeline";
import type { OperationalRaceState } from "./OperationalRaceStateTypes";

export function buildOperationalRaceState(): OperationalRaceState {
  clearIntelligenceRegistry();
  registerDefaultIntelligenceModules();

  const moduleOutputs = buildRegisteredIntelligence();
  const evidence = moduleOutputs.flatMap((module) => module.evidence);
  const feedHealth = moduleOutputs.map((module) => module.feedHealth);
  const coverage = buildCoverageFromModules(moduleOutputs);
  const timeline = seedTimeline();
  const alerts = buildSystemAlerts();

  return {
    raceId: "current-race",
    meetingName: "Race Context Pending",
    raceNumber: 1,
    raceName: "Operational Race State",
    distance: "Pending",
    raceClass: "Pending",
    trackCondition: "Pending",
    rail: "Pending",
    confidence: 0,
    referenceRunner: "Pending production runner",
    currentSituation:
      "EDGEiQ OS is now assembling operational state from registered intelligence modules.",
    whyItMatters:
      "COMMAND no longer needs to manually know which intelligence engines exist. Engines register once and contribute evidence, feed health and coverage.",
    currentAssessment:
      "The platform is ready to replace placeholder modules with production intelligence adapters.",
    marketRelationship:
      "Market relationship intelligence pending production market module wiring.",
    evidence,
    timeline,
    feedHealth,
    alerts,
    coverage,
    status: moduleOutputs.some((module) => module.status === "READY") ? "PARTIAL" : "PLACEHOLDER",
  };
}
''', encoding="utf-8")

print("[EDGEIQ_OS_STATE_WIRE] OperationalRaceState now uses registry, timeline, alerts and coverage")
