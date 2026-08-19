
import type { IntelligenceModuleOutput } from "../intelligence-registry";
import type { CorrelationSummary } from "./OperationalCorrelationTypes";

export function buildOperationalCorrelation(
  modules: IntelligenceModuleOutput[],
): CorrelationSummary {
  const ready = modules.filter((module) => module.status === "READY");

  const confidence =
    ready.length === 0
      ? 0
      : Math.round(
          ready.reduce((sum, module) => sum + (module.confidence ?? 0), 0) /
          ready.length,
        );

  const agreement =
    modules.length === 0 ? 0 : Math.round((ready.length / modules.length) * 100);

  const supporting = ready.map((module) => module.label);

  const reinforcement =
    agreement >= 85
      ? ["Multiple intelligence engines reinforce the current operational assessment."]
      : agreement >= 60
      ? ["Most intelligence engines support the current assessment."]
      : ["Limited agreement across intelligence engines."];

  const conflicts =
    modules.length - ready.length > 0
      ? modules
          .filter((module) => module.status !== "READY")
          .map((module) => `${module.label} requires attention.`)
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
