import type { IntelligenceModuleOutput } from "../intelligence-registry";
import type { IntelligenceCoverageItem } from "./CoverageTypes";

export function buildCoverageFromModules(
  modules: IntelligenceModuleOutput[],
): IntelligenceCoverageItem[] {
  return modules.map((module) => ({
    key: module.key,
    label: module.label,
    coveragePct:
      module.status === "READY"
        ? 100
        : module.status === "PARTIAL"
        ? 50
        : 0,
    status: module.status,
  }));
}
