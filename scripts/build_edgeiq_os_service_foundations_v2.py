from pathlib import Path

base = Path("src/edgeiq-os/services")

registry = base / "intelligence-registry"
registry.mkdir(parents=True, exist_ok=True)

(registry / "IntelligenceRegistryTypes.ts").write_text(r'''
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
''', encoding="utf-8")

(registry / "IntelligenceRegistry.ts").write_text(r'''
import type { IntelligenceModule, IntelligenceModuleOutput } from "./IntelligenceRegistryTypes";

const modules: IntelligenceModule[] = [];

export function registerIntelligenceModule(module: IntelligenceModule): void {
  const exists = modules.some((item) => item.key === module.key);
  if (!exists) modules.push(module);
}

export function getRegisteredIntelligenceModules(): IntelligenceModule[] {
  return [...modules];
}

export function buildRegisteredIntelligence(): IntelligenceModuleOutput[] {
  return modules.map((module) => module.build());
}

export function clearIntelligenceRegistry(): void {
  modules.splice(0, modules.length);
}
''', encoding="utf-8")

(registry / "defaultModules.ts").write_text(r'''
import { registerIntelligenceModule } from "./IntelligenceRegistry";

const placeholderModules = [
  { key: "race-shape", label: "Race Shape", category: "PACE" },
  { key: "runner-dna", label: "Runner DNA", category: "RUNNER_DNA" },
  { key: "track", label: "Track Intelligence", category: "TRACK" },
  { key: "connections", label: "Connections", category: "CONNECTIONS" },
  { key: "weather", label: "Weather", category: "WEATHER" },
  { key: "sectionals", label: "Sectionals", category: "SECTIONALS" },
  { key: "market", label: "Market", category: "MARKET" },
] as const;

export function registerDefaultIntelligenceModules(): void {
  placeholderModules.forEach((item) => {
    registerIntelligenceModule({
      key: item.key,
      label: item.label,
      category: item.category,
      build: () => ({
        key: item.key,
        label: item.label,
        category: item.category,
        status: "PLACEHOLDER",
        confidence: 0,
        importance: 50,
        evidence: [
          {
            id: `${item.key}-placeholder-evidence`,
            category: item.category,
            title: `${item.label} pending`,
            summary: `${item.label} module registered. Production feed wiring required.`,
            confidence: 0,
            importance: 50,
            status: "PLACEHOLDER",
          },
        ],
        feedHealth: {
          key: item.key,
          label: item.label,
          status: "PLACEHOLDER",
          freshness: "Pending production feed wiring",
        },
      }),
    });
  });
}
''', encoding="utf-8")

(registry / "index.ts").write_text(r'''
export * from "./IntelligenceRegistryTypes";
export * from "./IntelligenceRegistry";
export * from "./defaultModules";
''', encoding="utf-8")

timeline = base / "timeline"
timeline.mkdir(parents=True, exist_ok=True)

(timeline / "TimelineService.ts").write_text(r'''
import type { OperationalTimelineEvent } from "../operational-state";

const events: OperationalTimelineEvent[] = [];

export function appendTimelineEvent(event: OperationalTimelineEvent): void {
  events.unshift(event);
}

export function getTimelineEvents(): OperationalTimelineEvent[] {
  return [...events];
}

export function clearTimelineEvents(): void {
  events.splice(0, events.length);
}

export function seedTimeline(): OperationalTimelineEvent[] {
  if (events.length === 0) {
    appendTimelineEvent({
      id: "timeline-engine-ready",
      time: "NOW",
      title: "Timeline engine online",
      summary: "Operational timeline service is ready for snapshot and change events.",
      severity: "IMPORTANT",
    });
  }

  return getTimelineEvents();
}
''', encoding="utf-8")

(timeline / "index.ts").write_text(r'''
export * from "./TimelineService";
''', encoding="utf-8")

alerts = base / "alerts"
alerts.mkdir(parents=True, exist_ok=True)

(alerts / "AlertTypes.ts").write_text(r'''
export type OperationalAlertSeverity = "INFO" | "WATCH" | "IMPORTANT" | "CRITICAL";

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
  severity: OperationalAlertSeverity;
}
''', encoding="utf-8")

(alerts / "AlertService.ts").write_text(r'''
import type { OperationalAlert } from "./AlertTypes";

export function buildSystemAlerts(): OperationalAlert[] {
  return [
    {
      id: "os-alert-intelligence-wiring",
      category: "SYSTEM",
      title: "Integration phase active",
      summary: "EDGEiQ OS is ready for production intelligence feed wiring.",
      severity: "IMPORTANT",
    },
  ];
}
''', encoding="utf-8")

(alerts / "index.ts").write_text(r'''
export * from "./AlertTypes";
export * from "./AlertService";
''', encoding="utf-8")

coverage = base / "coverage"
coverage.mkdir(parents=True, exist_ok=True)

(coverage / "CoverageTypes.ts").write_text(r'''
import type { IntelligenceStatus } from "../operational-state";

export interface IntelligenceCoverageItem {
  key: string;
  label: string;
  coveragePct: number;
  status: IntelligenceStatus;
}
''', encoding="utf-8")

(coverage / "CoverageService.ts").write_text(r'''
import type { IntelligenceModuleOutput } from "../intelligence-registry";
import type { IntelligenceCoverageItem } from "./CoverageTypes";

export function buildCoverageFromModules(modules: IntelligenceModuleOutput[]): IntelligenceCoverageItem[] {
  return modules.map((module) => ({
    key: module.key,
    label: module.label,
    coveragePct: module.status === "READY" ? 100 : module.status === "PARTIAL" ? 50 : 0,
    status: module.status,
  }));
}
''', encoding="utf-8")

(coverage / "index.ts").write_text(r'''
export * from "./CoverageTypes";
export * from "./CoverageService";
''', encoding="utf-8")

print("[EDGEIQ_OS_SERVICES] Registry, timeline, alerts and coverage services created")
