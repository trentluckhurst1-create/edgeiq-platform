from pathlib import Path

root = Path("src/edgeiq-os/services/operational-correlation")
root.mkdir(parents=True, exist_ok=True)

(root / "OperationalCorrelationTypes.ts").write_text(r'''
export interface CorrelationSummary {
  agreementScore: number;
  agreementBand: string;
  operationalConfidence: number;
  operationalPriority: string;
  reinforcement: string[];
  conflicts: string[];
  supportingModules: string[];
}
''', encoding="utf-8")

(root / "OperationalCorrelationService.ts").write_text(r'''
import { registerAdapters } from "../adapters/registerAdapters";
import type { CorrelationSummary } from "./OperationalCorrelationTypes";

export function buildOperationalCorrelation(): CorrelationSummary {
  const modules = registerAdapters().map(adapter => adapter.buildModuleOutput());

  const ready = modules.filter(m => m.status === "READY");
  const confidence =
    ready.length === 0
      ? 0
      : Math.round(
          ready.reduce((sum, module) => sum + (module.confidence ?? 0), 0) /
          ready.length
        );

  const agreement =
    modules.length === 0
      ? 0
      : Math.round((ready.length / modules.length) * 100);

  const supporting = ready.map(m => m.label);

  const reinforcement =
    agreement >= 85
      ? ["Multiple intelligence engines reinforce the current operational assessment."]
      : agreement >= 60
      ? ["Most intelligence engines support the current assessment."]
      : ["Limited agreement across intelligence engines."];

  const conflicts =
    modules.length - ready.length > 0
      ? modules
          .filter(m => m.status !== "READY")
          .map(m => `${m.label} requires attention.`)
      : [];

  return {
    agreementScore: agreement,
    agreementBand:
      agreement >= 90
        ? "VERY HIGH"
        : agreement >= 75
        ? "HIGH"
        : agreement >= 55
        ? "MODERATE"
        : "LOW",
    operationalConfidence: confidence,
    operationalPriority:
      confidence >= 85
        ? "CRITICAL"
        : confidence >= 70
        ? "HIGH"
        : confidence >= 50
        ? "NORMAL"
        : "LOW",
    reinforcement,
    conflicts,
    supportingModules: supporting,
  };
}
''', encoding="utf-8")

(root / "index.ts").write_text(r'''
export * from "./OperationalCorrelationService";
export * from "./OperationalCorrelationTypes";
''', encoding="utf-8")

print("[EDGEIQ] Operational Correlation Engine created")
