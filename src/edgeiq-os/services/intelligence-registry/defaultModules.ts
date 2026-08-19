
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
