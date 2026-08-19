
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
