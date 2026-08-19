from pathlib import Path

adapters = Path("src/edgeiq-os/services/adapters")
adapters.mkdir(parents=True, exist_ok=True)

(adapters / "AdapterTypes.ts").write_text(r'''
import type { IntelligenceModuleOutput } from "../intelligence-registry";

export interface IntelligenceAdapter {
  key: string;
  label: string;
  buildModuleOutput: () => IntelligenceModuleOutput;
}
''', encoding="utf-8")

(adapters / "createPlaceholderAdapter.ts").write_text(r'''
import type { EvidenceCategory } from "../operational-state";
import type { IntelligenceAdapter } from "./AdapterTypes";

export function createPlaceholderAdapter(
  key: string,
  label: string,
  category: EvidenceCategory,
): IntelligenceAdapter {
  return {
    key,
    label,
    buildModuleOutput: () => ({
      key,
      label,
      category,
      status: "PLACEHOLDER",
      confidence: 0,
      importance: 50,
      evidence: [
        {
          id: `${key}-adapter-placeholder`,
          category,
          title: `${label} adapter online`,
          summary: `${label} adapter is registered and ready for production feed wiring.`,
          confidence: 0,
          importance: 50,
          status: "PLACEHOLDER",
        },
      ],
      feedHealth: {
        key,
        label,
        status: "PLACEHOLDER",
        freshness: "Adapter ready; production source pending",
      },
    }),
  };
}
''', encoding="utf-8")

adapter_files = {
  "RaceShapeAdapter.ts": ("race-shape", "Race Shape", "PACE"),
  "RunnerDNAAdapter.ts": ("runner-dna", "Runner DNA", "RUNNER_DNA"),
  "ExplainabilityAdapter.ts": ("explainability", "Explainability", "GENERIC"),
  "ConnectionAdapter.ts": ("connections", "Connections", "CONNECTIONS"),
  "TrackAdapter.ts": ("track", "Track Intelligence", "TRACK"),
  "WeatherAdapter.ts": ("weather", "Weather", "WEATHER"),
  "SectionalsAdapter.ts": ("sectionals", "Sectionals", "SECTIONALS"),
  "MarketAdapter.ts": ("market", "Market", "MARKET"),
}

for filename, (key, label, category) in adapter_files.items():
    adapters.joinpath(filename).write_text(f'''import {{ createPlaceholderAdapter }} from "./createPlaceholderAdapter";

export const {filename.replace(".ts", "")} = createPlaceholderAdapter(
  "{key}",
  "{label}",
  "{category}",
);
''', encoding="utf-8")

(adapters / "registerAdapters.ts").write_text(r'''
import { registerIntelligenceModule } from "../intelligence-registry";
import type { IntelligenceAdapter } from "./AdapterTypes";
import { RaceShapeAdapter } from "./RaceShapeAdapter";
import { RunnerDNAAdapter } from "./RunnerDNAAdapter";
import { ExplainabilityAdapter } from "./ExplainabilityAdapter";
import { ConnectionAdapter } from "./ConnectionAdapter";
import { TrackAdapter } from "./TrackAdapter";
import { WeatherAdapter } from "./WeatherAdapter";
import { SectionalsAdapter } from "./SectionalsAdapter";
import { MarketAdapter } from "./MarketAdapter";

export const productionAdapterSlots: IntelligenceAdapter[] = [
  RaceShapeAdapter,
  RunnerDNAAdapter,
  ExplainabilityAdapter,
  ConnectionAdapter,
  TrackAdapter,
  WeatherAdapter,
  SectionalsAdapter,
  MarketAdapter,
];

export function registerProductionAdapterSlots(): void {
  productionAdapterSlots.forEach((adapter) => {
    registerIntelligenceModule({
      key: adapter.key,
      label: adapter.label,
      category: adapter.buildModuleOutput().category,
      build: adapter.buildModuleOutput,
    });
  });
}
''', encoding="utf-8")

(adapters / "index.ts").write_text(r'''
export * from "./AdapterTypes";
export * from "./createPlaceholderAdapter";
export * from "./RaceShapeAdapter";
export * from "./RunnerDNAAdapter";
export * from "./ExplainabilityAdapter";
export * from "./ConnectionAdapter";
export * from "./TrackAdapter";
export * from "./WeatherAdapter";
export * from "./SectionalsAdapter";
export * from "./MarketAdapter";
export * from "./registerAdapters";
''', encoding="utf-8")

state_path = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")
state_path.write_text(r'''
import { buildSystemAlerts } from "../alerts";
import { registerProductionAdapterSlots } from "../adapters";
import {
  buildRegisteredIntelligence,
  clearIntelligenceRegistry,
} from "../intelligence-registry";
import { buildCoverageFromModules } from "../intelligence-coverage";
import { seedTimeline } from "../timeline";
import type { OperationalRaceState } from "./OperationalRaceStateTypes";

export function buildOperationalRaceState(): OperationalRaceState {
  clearIntelligenceRegistry();
  registerProductionAdapterSlots();

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
      "EDGEiQ OS is now assembling operational state through production adapter slots.",
    whyItMatters:
      "Each intelligence domain now has a dedicated adapter boundary, allowing CSV, API or database sources to be swapped without changing COMMAND.",
    currentAssessment:
      "Adapter layer is online. Next step is replacing adapter placeholders with real Race Shape, Runner DNA, Explainability, Connections, Track, Weather, Sectionals and Market outputs.",
    marketRelationship:
      "Market relationship intelligence pending production market adapter wiring.",
    evidence,
    timeline,
    feedHealth,
    alerts,
    coverage,
    status: moduleOutputs.some((module) => module.status === "READY") ? "PARTIAL" : "PLACEHOLDER",
  };
}
''', encoding="utf-8")

print("[EDGEIQ_OS_ADAPTERS] Adapter layer created and wired into OperationalRaceState")
