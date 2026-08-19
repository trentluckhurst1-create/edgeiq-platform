from pathlib import Path

root = Path("src/edgeiq-os/services/operational-state")
root.mkdir(parents=True, exist_ok=True)

(root / "OperationalRaceStateTypes.ts").write_text(r'''
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
  status: IntelligenceStatus;
}
''', encoding="utf-8")

(root / "OperationalRaceStateService.ts").write_text(r'''
import type { OperationalRaceState } from "./OperationalRaceStateTypes";

export function buildOperationalRaceState(): OperationalRaceState {
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
      "EDGEiQ OS has initialised the operational state layer. Production intelligence feeds are ready to be wired into this object.",
    whyItMatters:
      "This creates one canonical race state so COMMAND, FIELD, MAP, MARKET, PERFORMANCE, CONDITIONS, RESULTS and LAB can all consume the same intelligence.",
    currentAssessment:
      "Architecture is ready. Intelligence modules now need to replace placeholder state.",
    marketRelationship:
      "Market relationship intelligence pending production market feed wiring.",
    evidence: [
      {
        id: "os-core-ready",
        category: "GENERIC",
        title: "Operational state online",
        summary:
          "The platform now has a single race-state contract for intelligence, evidence, confidence, feed health and timeline events.",
        confidence: 100,
        importance: 100,
        status: "READY",
      },
    ],
    timeline: [
      {
        id: "timeline-os-core-created",
        time: "NOW",
        title: "EDGEiQ OS Core Created",
        summary:
          "OperationalRaceState is now available as the canonical intelligence object.",
        severity: "IMPORTANT",
      },
    ],
    feedHealth: [
      {
        key: "race-context",
        label: "Race Context",
        status: "PLACEHOLDER",
        freshness: "Pending feed wiring",
      },
      {
        key: "race-shape",
        label: "Race Shape",
        status: "PLACEHOLDER",
        freshness: "Pending feed wiring",
      },
      {
        key: "runner-dna",
        label: "Runner DNA",
        status: "PLACEHOLDER",
        freshness: "Pending feed wiring",
      },
      {
        key: "market",
        label: "Market",
        status: "PLACEHOLDER",
        freshness: "Pending feed wiring",
      },
    ],
    status: "PARTIAL",
  };
}
''', encoding="utf-8")

(root / "index.ts").write_text(r'''
export * from "./OperationalRaceStateTypes";
export * from "./OperationalRaceStateService";
''', encoding="utf-8")

orch = Path("src/edgeiq-os/services/intelligence-orchestrator")
orch.mkdir(parents=True, exist_ok=True)

(orch / "IntelligenceOrchestrator.ts").write_text(r'''
import { buildOperationalRaceState } from "../operational-state";
import type { OperationalRaceState } from "../operational-state";

export function getOperationalRaceState(): OperationalRaceState {
  return buildOperationalRaceState();
}
''', encoding="utf-8")

(orch / "index.ts").write_text(r'''
export * from "./IntelligenceOrchestrator";
''', encoding="utf-8")

print("[EDGEIQ_OS_CORE] Operational state and orchestrator created")
