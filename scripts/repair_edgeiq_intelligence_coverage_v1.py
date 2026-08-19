from pathlib import Path

folder = Path("src/edgeiq-os/services/intelligence-coverage")

files = {
    "CoverageTypes.ts": r'''
import type { IntelligenceStatus } from "../operational-state";

export interface IntelligenceCoverageItem {
  key: string;
  label: string;
  coveragePct: number;
  status: IntelligenceStatus;
}
''',

    "CoverageService.ts": r'''
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
''',

    "index.ts": r'''
export * from "./CoverageTypes";
export * from "./CoverageService";
'''
}

for name, text in files.items():
    (folder / name).write_text(text.strip() + "\n", encoding="utf-8")

print("[EDGEIQ] intelligence-coverage repaired")
