
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
